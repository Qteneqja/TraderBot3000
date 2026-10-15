"""Durable practice transaction replay. Unknown or foreign exposure stays quarantined."""

from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select, text

from app.brokers.validation import decimal, validate_protection
from app.machine_learning.policy import digest
from app.models.tables import Event, Notification, PracticeAccount, PracticeOrder, PracticeTransaction
from app.notifications.messages import practice_message
from app.schemas.domain import aware

OPEN = ("RESERVED", "SUBMITTING", "UNKNOWN", "FILLED", "CLOSING", "QUARANTINED")


def account_key(account_id):
    return sha256(account_id.encode()).hexdigest()


def sanitized(value):
    if isinstance(value, dict):
        return {k: sanitized(v) for k, v in value.items() if k.lower() not in (
            "accountid", "userid", "createdbyuserid", "authorization", "password", "token", "api_key", "alias")}
    if isinstance(value, list):
        return [sanitized(v) for v in value]
    return value


def lock_practice(db, key):
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    return db.scalar(select(PracticeAccount).where(PracticeAccount.id == key).with_for_update())


def validate_transactions(transactions, cursor, watermark):
    if not str(cursor).isdigit() or not str(watermark).isdigit() or int(watermark) < int(cursor):
        raise ValueError("Invalid or reversed transaction cursor")
    ids = [int(t["id"]) for t in transactions]
    if ids != list(range(int(cursor) + 1, int(watermark) + 1)):
        raise ValueError("Incomplete, duplicate or unordered transaction response")


def client_id(transaction):
    return transaction.get("clientExtensions", {}).get("id") or transaction.get("clientOrderID")


def notify_state(db, order, state):
    identifier = f"practice-{order.id[:40]}-{state}"
    if db.get(Notification, identifier) is None:
        db.add(Notification(id=identifier, text=practice_message(db, order, state)))


def apply_transaction(db, account, transaction, orders, now):
    key = (account.id, str(transaction["id"]))
    body = sanitized(transaction)
    previous = db.get(PracticeTransaction, key)
    if previous:
        if previous.payload != body:
            raise ValueError("Previously recorded broker transaction changed")
        return
    db.add(PracticeTransaction(account_id=account.id, id=key[1],
                              time=datetime.fromisoformat(transaction["time"].replace("Z", "+00:00")), payload=body))
    order = next((o for o in orders if o.client_id == client_id(transaction)), None)
    if order is None and transaction.get("orderID"):
        order = next((o for o in orders if o.broker_order_id == str(transaction["orderID"])), None)
    kind = transaction["type"]
    if order and kind in ("MARKET_ORDER", "LIMIT_ORDER", "STOP_ORDER"):
        if transaction.get("instrument") != order.candidate["symbol"] or decimal(transaction["units"]) != order.units:
            raise ValueError("Broker order does not match durable reservation")
        order.broker_order_id = str(transaction["id"])
    elif order and kind.endswith("ORDER_REJECT"):
        if order.trade_id is not None:
            raise ValueError("Reject transaction cannot discard existing exposure")
        order.state = "REJECTED"
    elif order and kind == "ORDER_CANCEL":
        if order.trade_id is not None:
            raise ValueError("Cancellation cannot discard filled exposure")
        order.state = "CANCELLED"
    elif order and kind == "ORDER_FILL" and transaction.get("tradeOpened"):
        opened = transaction["tradeOpened"]
        if decimal(opened["units"]) != order.units or transaction.get("tradeReduced") or transaction.get("tradesClosed"):
            raise ValueError("Unexpected partial, netted or reversed entry")
        order.trade_id, order.entry = str(opened["tradeID"]), decimal(opened["price"])
        fee = decimal(transaction["commission"]) + decimal(transaction.get("guaranteedExecutionFee", "0"))
        if fee < 0:
            raise ValueError("Negative broker execution fee")
        order.fees_paid += fee
        # FILLED requires independently verified protection below, never merely HTTP success.
        order.state = "QUARANTINED"
    if kind == "ORDER_FILL":
        for closed in transaction.get("tradesClosed", []):
            owner = next((o for o in orders if o.trade_id == str(closed["tradeID"])), None)
            if owner:
                if len(transaction.get("tradesClosed", [])) != 1 or transaction.get("tradeReduced") or transaction.get("tradeOpened"):
                    raise ValueError("Complex close requires explicit broker cost allocation")
                if not 0 < abs(decimal(closed["units"])) <= abs(owner.units):
                    raise ValueError("Invalid close exposure")
                owner.state = "CLOSED"
                owner.close_reason = transaction.get("reason", "UNCLASSIFIED_BROKER_CLOSE")
                fee = decimal(transaction["commission"]) + decimal(transaction.get("guaranteedExecutionFee", "0"))
                if fee < 0:
                    raise ValueError("Negative broker execution fee")
                owner.fees_paid += fee
                owner.updated_at = now
        if transaction.get("tradeReduced"):
            reduced = transaction["tradeReduced"]
            owner = next((o for o in orders if o.trade_id == str(reduced["tradeID"])), None)
            if owner:
                if transaction.get("tradesClosed") or transaction.get("tradeOpened"):
                    raise ValueError("Complex partial reduction requires explicit cost allocation")
                fee = decimal(transaction["commission"]) + decimal(transaction.get("guaranteedExecutionFee", "0"))
                if fee < 0:
                    raise ValueError("Negative broker execution fee")
                owner.fees_paid += fee
                owner.state = "QUARANTINED"
                owner.updated_at = now
                account.suspended = True
    if order:
        order.updated_at = now


async def reconcile_practice(db, adapter, actual_account_id, now=None):
    """Fetch a stable watermark before atomically applying evidence and advancing the cursor."""
    key = account_key(actual_account_id)
    stored = db.get(PracticeAccount, key)
    cursor = stored.cursor if stored else None
    known = db.scalars(select(PracticeOrder).where(PracticeOrder.account_id == key)).all()
    known_clients = {o.client_id for o in known}
    known_ids = {o.broker_order_id for o in known if o.broker_order_id}
    owned_trades = {o.trade_id for o in known if o.trade_id}
    db.rollback()
    try:
        snapshot = await adapter.account_details()
        if snapshot["account"]["id"] != actual_account_id:
            raise ValueError("Practice snapshot identity mismatch")
        if cursor is None:
            cursor = str(snapshot["account"]["lastTransactionID"])
        for _ in range(3):
            response = await adapter.transactions(cursor)
            watermark = str(response["lastTransactionID"])
            transactions = response["transactions"]
            validate_transactions(transactions, cursor, watermark)
            snapshot = await adapter.account_details()
            if str(snapshot["account"]["lastTransactionID"]) == watermark:
                break
        else:
            raise ValueError("Broker snapshot did not stabilize")
        for transaction in transactions:
            if client_id(transaction) in known_clients and transaction["type"] == "MARKET_ORDER":
                known_ids.add(str(transaction["id"]))
            if str(transaction.get("orderID", "")) in known_ids and transaction.get("tradeOpened"):
                owned_trades.add(str(transaction["tradeOpened"]["tradeID"]))
        account_snapshot = snapshot["account"]
        open_trades = account_snapshot.get("trades", [])
        details = {}
        for trade in open_trades:
            if str(trade["id"]) in owned_trades:
                details[str(trade["id"])] = (await adapter.trade(str(trade["id"])))["trade"]
        closing = {str(t["tradeID"]) for tx in transactions for t in tx.get("tradesClosed", [])} & owned_trades
        for trade_id in closing:
            details[trade_id] = (await adapter.trade(trade_id))["trade"]
        now = now or datetime.now(timezone.utc)
        account = lock_practice(db, key)
        if account and account.cursor != cursor:
            raise ValueError("Concurrent reconciliation advanced cursor; retry read-only reconciliation")
        if account is None:
            account = PracticeAccount(id=key, currency=account_snapshot["currency"], cursor=cursor,
                                      synchronized_at=now, reconciled=False, suspended=True,
                                      snapshot={}, risk={}, approval={})
            db.add(account)
            db.flush()
        if account.currency != account_snapshot["currency"]:
            raise ValueError("Broker account currency changed")
        orders = db.scalars(select(PracticeOrder).where(PracticeOrder.account_id == key)).all()
        for transaction in transactions:
            apply_transaction(db, account, transaction, orders, now)
        open_ids = {str(t["id"]) for t in open_trades}
        issues = []
        if any(tx['type'] == 'TRANSFER_FUNDS' for tx in transactions):
            issues.append('BROKER_CASHFLOW_REQUIRES_REVIEW')
        owned_ids = {o.trade_id for o in orders if o.trade_id}
        if open_ids - owned_ids:
            issues.append("UNOWNED_BROKER_TRADES")
        client_ids = {o.client_id for o in orders}
        if any((o.get("tradeID") not in owned_ids if o.get("type") in (
            "STOP_LOSS", "TAKE_PROFIT", "GUARANTEED_STOP_LOSS") else o.get("clientExtensions", {}).get("id") not in client_ids)
               for o in account_snapshot.get("orders", [])):
            issues.append("UNOWNED_PENDING_ORDERS")
        positions = {p["instrument"]: p for p in account_snapshot.get("positions", [])}
        for symbol in set(positions) | {o.candidate["symbol"] for o in orders if o.trade_id in open_ids}:
            actual = positions.get(symbol)
            for side, sign in (("long", 1), ("short", -1)):
                expected = sum((o.units for o in orders if o.trade_id in open_ids and o.candidate["symbol"] == symbol
                                and o.units * sign > 0), decimal(0))
                observed = decimal(actual[side]["units"]) if actual else decimal(0)
                if observed != expected:
                    issues.append("BROKER_POSITION_MISMATCH")
        for order in orders:
            if order.request_sha256 != digest(order.request):
                issues.append("RESERVATION_TAMPERED")
            if order.trade_id in open_ids:
                try:
                    trade = details[order.trade_id]
                    entry = order.request["order"]
                    validate_protection(trade, order.candidate["symbol"], order.units,
                                        decimal(entry["stopLossOnFill"]["price"]),
                                        decimal(entry["takeProfitOnFill"]["price"]))
                    if order.state not in ("CLOSING", "CLOSED"):
                        if order.state != "FILLED":
                            db.add(Event(time=now, kind="practice_fill_protected", detail={"order": order.id, "cursor": watermark}))
                            notify_state(db, order, "FILLED")
                        order.state = "FILLED"
                except (KeyError, ValueError, TypeError):
                    issues.append("OWNED_TRADE_UNPROTECTED_OR_MISMATCHED")
                    order.state = "QUARANTINED"
                    notify_state(db, order, "QUARANTINED")
                if order.state == "FILLED":
                    try:
                        if order.fees_paid + max(decimal(0), -decimal(trade["financing"])) > decimal(
                            order.candidate["reviewed_fee_financing_home_budget"]):
                            issues.append("REVIEWED_COST_BUDGET_EXCEEDED")
                    except (KeyError, ValueError, TypeError):
                        issues.append("BROKER_COST_EVIDENCE_MISSING")
            elif order.state in ("FILLED", "CLOSING", "QUARANTINED"):
                issues.append("OWNED_TRADE_MISSING_WITHOUT_CLOSE_TRANSACTION")
            if order.state in ("SUBMITTING", "UNKNOWN", "CLOSING", "QUARANTINED"):
                issues.append("UNCERTAIN_EXECUTION")
            if order.state == "CLOSED" and order.trade_id in closing:
                closed_trade = details[order.trade_id]
                if (closed_trade["state"] != "CLOSED" or decimal(closed_trade["currentUnits"]) != 0
                    or decimal(closed_trade["initialUnits"]) != order.units
                    or closed_trade["instrument"] != order.candidate["symbol"]):
                    raise ValueError("Closed trade evidence differs from owned exposure")
                order.realized_pnl = decimal(closed_trade["realizedPL"]) + decimal(closed_trade["financing"]) + decimal(
                    closed_trade.get("dividendAdjustment", "0")) - order.fees_paid
                order.closed_at = datetime.fromisoformat(closed_trade["closeTime"].replace("Z", "+00:00"))
                order.exit = decimal(closed_trade["averageClosePrice"])
                db.add(Event(time=now, kind="practice_trade_closed", detail={"order": order.id,
                             "net_pnl": str(order.realized_pnl), "fees": str(order.fees_paid)}))
                notify_state(db, order, "CLOSED")
                if order.fees_paid + max(decimal(0), -decimal(closed_trade["financing"])) > decimal(
                    order.candidate["reviewed_fee_financing_home_budget"]):
                    issues.append("REVIEWED_COST_BUDGET_EXCEEDED")
        previous_sync = aware(account.synchronized_at)
        previous_nav = decimal(account.snapshot.get("NAV", account_snapshot["NAV"]))
        account.cursor, account.synchronized_at = watermark, now
        nav = decimal(account_snapshot["NAV"])
        risk = dict(account.risk)
        day, week = now.date().isoformat(), f"{now.isocalendar().year}-{now.isocalendar().week}"
        if risk and (risk.get("day") != day or risk.get("week") != week) and (now - previous_sync).total_seconds() > 30:
            if open_ids or any(t["type"] in ("ORDER_FILL", "DAILY_FINANCING") for t in transactions):
                issues.append("ROLLOVER_EQUITY_UNVERIFIED_AFTER_GAP")
        if risk.get("day") != day:
            risk.update(day=day, day_start=str(max(nav, previous_nav)))
        if risk.get("week") != week:
            risk.update(week=week, week_start=str(max(nav, previous_nav)))
        risk["peak"] = str(max(nav, decimal(risk.get("peak", nav))))
        closed_orders = sorted((o for o in orders if o.state == "CLOSED"), key=lambda o: (aware(o.closed_at or o.updated_at), o.id))
        losses = 0
        for order in reversed(closed_orders):
            if order.realized_pnl is None or order.realized_pnl >= 0:
                break
            losses += 1
        risk["consecutive_losses"] = losses
        if "REVIEWED_COST_BUDGET_EXCEEDED" in issues and account.approval.get("runtime"):
            risk["blocked_cost_runtime"] = digest(account.approval["runtime"])
        account.risk = risk
        account.snapshot = {k: account_snapshot[k] for k in ("NAV", "balance", "marginAvailable", "marginUsed")}
        account.reconciled = not issues
        if issues:
            account.suspended = True
        db.add(Event(kind="practice_reconciled", detail={"account_fingerprint": key, "cursor": watermark,
                                                        "issues": sorted(set(issues)), "orders": len(orders)}))
        db.commit()
        return {"account_fingerprint": key, "cursor": watermark, "reconciled": not issues,
                "suspended": account.suspended, "issues": sorted(set(issues)), "submission_enabled": False}
    except Exception as exc:
        db.rollback()
        account = lock_practice(db, key)
        if account:
            account.reconciled, account.suspended = False, True
            db.add(Event(kind="practice_reconciliation_failed", detail={"account_fingerprint": key,
                                                                       "error_type": type(exc).__name__}))
        db.commit()
        raise
