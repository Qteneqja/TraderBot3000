"""Risk-locked practice reservations. POST/PUT are never automatically repeated."""

from datetime import datetime, timezone
from decimal import Decimal as D

import httpx
from sqlalchemy import select

from app.brokers.reconciliation import OPEN, account_key, lock_practice, reconcile_practice
from app.brokers.validation import conversion_contract, decimal, instrument_contract, readiness_report
from app.execution.trials import current_models, trial_report
from app.machine_learning.deployment import authorize_candidate, runtime_contract
from app.machine_learning.policy import digest
from app.models.tables import Event, Instrument, Notification, PracticeOrder
from app.risk_management.engine import InstrumentRules, RiskState, approve
from app.schemas.domain import Candidate, Quote, aware


def paper_settings(settings):
    return settings.model_copy(update={"trading_mode": "PAPER"})


def reject_reservation(db, key, order_id, candidate, reasons, now):
    db.add(PracticeOrder(id=order_id, account_id=key, signal_id=candidate.id,
                         client_id="ag-" + order_id[:40], state="REJECTED", request={},
                         request_sha256=digest({}), candidate=candidate.model_dump(mode="json") | {"rejection_reasons": reasons},
                         units=D(0), planned_risk=D(0), created_at=now, updated_at=now))
    db.add(Event(kind="practice_signal_rejected", detail={"signal": candidate.id, "reasons": reasons}))
    db.commit()
    return None


def validate_authority(db, account, settings):
    if settings.demo_mode or settings.trading_mode != "OANDA_PRACTICE" or settings.enable_live_trading:
        raise ValueError("Gateway requires real-market practice mode; LIVE is unsupported")
    approval = account.approval
    if not approval or approval.get("sha256") != digest({k: v for k, v in approval.items() if k != "sha256"}):
        raise ValueError("Explicit practice gateway approval is required")
    if approval["runtime"] != runtime_contract(paper_settings(settings)) or approval["account"] != account.id:
        raise ValueError("Practice approval configuration changed")
    models = current_models(db, paper_settings(settings))
    if sorted({m.model_id for m in models}) != approval["models"]:
        raise ValueError("Practice models differ from approved paper evidence")
    evidence = db.scalar(select(Event).where(Event.kind == "practice_gateway_approved",
                         Event.detail["approval_id"].as_string() == approval["sha256"]))
    if evidence is None:
        raise ValueError("Practice approval audit record missing")
    return approval


async def approve_gateway(db, adapter, settings, trial_id, operator, reason, now=None, test_only=True):
    now = now or datetime.now(timezone.utc)
    if not operator.strip() or not reason.strip():
        raise ValueError("Operator attribution and reason required")
    report = trial_report(db, trial_id, now)
    if report["status"] != "READY_FOR_OPERATOR_REVIEW":
        db.rollback()
        raise ValueError("A completed approved-model paper trial is required before practice authorization")
    db.rollback()
    readiness = await readiness_report(adapter, settings.oanda_account_id, ["EUR_USD", "GBP_USD"])
    if readiness["status"] != "READ_ONLY_CHECKS_PASSED":
        raise ValueError("Read-only practice checks failed")
    key = account_key(settings.oanda_account_id)
    try:
        account = lock_practice(db, key)
        if account is None or not account.reconciled or (now - aware(account.synchronized_at)).total_seconds() > 30:
            raise ValueError("Recent durable practice reconciliation required")
        if account.risk.get("blocked_cost_runtime") == digest(runtime_contract(paper_settings(settings))):
            raise ValueError("Reviewed costs were exceeded; updated research/runtime evidence is required")
        if db.scalar(select(PracticeOrder.id).where(PracticeOrder.account_id == key, PracticeOrder.state.in_(OPEN)).limit(1)):
            raise ValueError("Resolve all outstanding broker reservations before approval")
        if not test_only:
            review = db.scalar(select(Event.id).where(Event.kind == "practice_external_lifecycle_approved",
                               Event.detail["account_fingerprint"].as_string() == key,
                               Event.detail["test_approval"].as_string() == account.approval.get("sha256", "")).limit(1))
            if review is None:
                raise ValueError("Verified external lifecycle review required before autonomous practice submission")
        models = current_models(db, paper_settings(settings))
        if not models:
            raise ValueError("No current verified paper models")
        contract = {"schema": "practice-gateway-approval-v1", "account": key, "trial": trial_id,
                    "trial_report_sha256": digest(report), "readiness_sha256": digest(readiness),
                    "runtime": runtime_contract(paper_settings(settings)), "models": sorted({m.model_id for m in models}),
                    "instruments": readiness["instruments"], "operator": operator[:120],
                    "reason": reason[:512], "approved_at": now.isoformat(),
                    "scope": "ONE_ORDER_PRACTICE_TEST" if test_only else "AUTONOMOUS_PRACTICE",
                    "maximum_test_units": "1" if test_only else None,
                    "emergency_policy": "CLOSE_OWNED_EXPOSURE_ON_MISSING_PROTECTION"}
        contract["sha256"] = digest(contract)
        account.approval, account.suspended = contract, False
        db.add(Event(time=now, kind="practice_gateway_approved", detail={"approval_id": contract["sha256"],
                                                                     "account_fingerprint": key, "trial": trial_id,
                                                                     "operator": operator[:120], "reason": reason[:512]}))
        db.commit()
        return contract["sha256"]
    except Exception:
        db.rollback()
        raise


async def reserve(db, adapter, settings, candidate: Candidate, now=None):
    if candidate.symbol not in ("EUR_USD", "GBP_USD") or candidate.source != "oanda":
        raise ValueError("Practice gateway supports configured OANDA Forex only")
    pricing = await adapter.pricing([candidate.symbol])
    available = await adapter.instruments()
    matching = [i for i in available["instruments"] if i["name"] == candidate.symbol]
    if len(matching) != 1:
        raise ValueError("Broker instrument is not available")
    actual_contract = instrument_contract(matching[0])
    now = now or datetime.now(timezone.utc)
    prices = [p for p in pricing["prices"] if p["instrument"] == candidate.symbol]
    if len(prices) != 1 or prices[0].get("status") != "tradeable":
        raise ValueError("Instrument is not tradeable")
    price = prices[0]
    quote = Quote(symbol=candidate.symbol, source="oanda", time=price["time"],
                  bid=price["bids"][0]["price"], ask=price["asks"][0]["price"])
    key = account_key(settings.oanda_account_id)
    order_id = digest([key, candidate.id])
    try:
        account = lock_practice(db, key)
        if account is None:
            raise ValueError("Practice account has not been reconciled")
        authority = validate_authority(db, account, settings)
        existing = db.get(PracticeOrder, order_id)
        if existing:
            result = None if existing.state == "REJECTED" else existing.id
            db.rollback()
            return result
        if authority.get("scope") == "ONE_ORDER_PRACTICE_TEST" and db.scalar(select(PracticeOrder.id).where(
            PracticeOrder.account_id == key, PracticeOrder.candidate["gateway_approval_id"].as_string() == authority["sha256"]).limit(1)):
            return reject_reservation(db, key, order_id, candidate, ["PRACTICE_TEST_BUDGET_EXHAUSTED"], now)
        conversion = conversion_contract(pricing, "USD", account.currency)
        broker_contract = next(i for i in authority["instruments"] if i["symbol"] == candidate.symbol)
        if any(decimal(actual_contract[k]) != decimal(broker_contract[k]) for k in (
            "tick", "unit_step", "minimum_units", "maximum_order_units", "margin_rate")):
            raise ValueError("Broker instrument contract changed since operator approval")
        instrument = db.get(Instrument, candidate.symbol)
        if instrument is None or instrument.tick_size != decimal(broker_contract["tick"]):
            raise ValueError("Configured and broker precision differ")
        orders = db.scalars(select(PracticeOrder).where(PracticeOrder.account_id == key,
                                                      PracticeOrder.state.in_(OPEN))).all()
        notional = sum((abs(o.units) * (o.entry or decimal(o.request["order"]["priceBound"])) * conversion["position"] for o in orders), D(0))
        reserved_risk = sum((o.planned_risk for o in orders), D(0))
        margins = {c["symbol"]: decimal(c["margin_rate"]) for c in authority["instruments"]}
        reserved_margin = sum((abs(o.units) * decimal(o.request["order"]["priceBound"]) * conversion["position"] * margins[o.candidate["symbol"]]
                               for o in orders if o.state != "FILLED"), D(0))
        state = RiskState(decimal(account.snapshot["NAV"]), decimal(account.risk["day_start"]),
                          decimal(account.risk["week_start"]), decimal(account.risk["peak"]),
                          max(D(0), decimal(account.snapshot["marginAvailable"]) - reserved_margin),
                          len(orders), reserved_risk, notional, reserved_risk,
                          int(account.risk["consecutive_losses"]), account.reconciled, account.suspended,
                          -2 <= (now - aware(account.synchronized_at)).total_seconds() <= 30)
        rules = InstrumentRules(candidate.symbol, decimal(broker_contract["tick"]),
                                decimal(broker_contract["unit_step"]), decimal(broker_contract["minimum_units"]),
                                instrument.max_spread, conversion["loss"], decimal(broker_contract["margin_rate"]),
                                slippage=instrument.tick_size * settings.paper_slippage_ticks,
                                fee_rate=settings.paper_fee_rate,
                                extra_cost_per_unit=settings.paper_financing_per_unit_per_bar * 12,
                                gain_to_account=conversion["gain"], position_to_account=conversion["position"])
        canonical = authorize_candidate(db, candidate, quote, paper_settings(settings), now)
        if canonical.model_version not in authority["models"]:
            return reject_reservation(db, key, order_id, canonical, ["MODEL_NOT_PRACTICE_APPROVED"], now)
        decision = approve(canonical, quote, state, rules, settings, now)
        if not decision.approved:
            return reject_reservation(db, key, order_id, canonical, decision.reasons, now)
        units = min(decision.units, decimal(broker_contract["maximum_order_units"]))
        if authority.get("scope") == "ONE_ORDER_PRACTICE_TEST":
            units = min(units, decimal(authority["maximum_test_units"]))
        if units < rules.min_units or units % rules.unit_step:
            raise ValueError("Approved units do not satisfy broker precision/minimum")
        if quote.bid % rules.tick or quote.ask % rules.tick:
            raise ValueError("Broker quote does not match explicit instrument precision")
        planned = decision.planned_risk * units / decision.units
        signed = units if canonical.direction == "LONG" else -units
        bound = quote.ask + rules.slippage if signed > 0 else quote.bid - rules.slippage
        price_quantum = rules.tick.normalize()
        unit_quantum = rules.unit_step.normalize()
        payload = adapter.market_payload("ag-" + order_id[:40], canonical.symbol, signed.quantize(unit_quantum),
                                         canonical.stop.quantize(price_quantum), canonical.target.quantize(price_quantum),
                                         bound.quantize(price_quantum))
        db.add(PracticeOrder(id=order_id, account_id=key, signal_id=candidate.id,
                             client_id=payload["order"]["clientExtensions"]["id"], state="RESERVED",
                             request=payload, request_sha256=digest(payload),
                             candidate=canonical.model_dump(mode="json") | {
                                 "broker_quote_time": quote.time.isoformat(),
                                 "gateway_approval_id": authority.get("sha256"),
                                 "account_equity_at_reservation": str(state.equity),
                                 "reviewed_fee_financing_home_budget": str(units * conversion["loss"] * (
                                     (canonical.entry + max(canonical.stop, canonical.target)) * settings.paper_fee_rate
                                     + settings.paper_financing_per_unit_per_bar * 12))},
                             units=signed, planned_risk=planned, created_at=now, updated_at=now))
        db.add(Event(kind="practice_order_reserved", detail={"order": order_id, "signal": candidate.id}))
        db.commit()
        return order_id
    except Exception:
        db.rollback()
        raise


async def send_once(db, adapter, settings, order_id, now=None):
    now = now or datetime.now(timezone.utc)
    key = account_key(settings.oanda_account_id)
    try:
        account = lock_practice(db, key)
        if account is None:
            raise ValueError("Unknown practice account")
        validate_authority(db, account, settings)
        order = db.get(PracticeOrder, order_id)
        if order is None or order.account_id != key:
            raise ValueError("Unknown reservation")
        if order.state != "RESERVED":
            db.rollback()
            return order.state  # Never retry a claimed, unknown or completed POST.
        if account.suspended or not account.reconciled or order.request_sha256 != digest(order.request):
            raise ValueError("Account or immutable reservation is not ready")
        if not -2 <= (now - aware(account.synchronized_at)).total_seconds() <= 30:
            order.state = "CANCELLED"
            db.commit()
            return "CANCELLED"
        if now >= datetime.fromisoformat(order.candidate["expires_at"]) or not 0 <= (
            now - datetime.fromisoformat(order.candidate["broker_quote_time"])).total_seconds() <= 30:
            order.state = "CANCELLED"
            db.commit()
            return "CANCELLED"
        order.state, order.updated_at = "SUBMITTING", now
        account.reconciled = False
        payload = order.request
        db.commit()  # Durable claim precedes the network mutation, including crash-before-POST.
    except Exception:
        db.rollback()
        raise
    error = None
    try:
        response = await adapter.client.post(f"{adapter.base}/orders", headers=adapter.headers,
                                             json=payload, timeout=20)
        response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        error = type(exc).__name__
    account = lock_practice(db, key)
    order = db.get(PracticeOrder, order_id)
    order.state, order.updated_at = "UNKNOWN", now
    if error:
        account.suspended = True
    db.add(Event(kind="practice_submission_observed", detail={"order": order_id, "error_type": error,
                                                            "fill_confirmed": False}))
    db.commit()
    # Only transaction replay and independent trade protection can confirm a fill.
    await reconcile_practice(db, adapter, settings.oanda_account_id)
    order = db.get(PracticeOrder, order_id)
    return order.state


async def close_once(db, adapter, settings, order_id, emergency=False):
    key = account_key(settings.oanda_account_id)
    account = lock_practice(db, key)
    order = db.get(PracticeOrder, order_id)
    if account is None or order is None or order.account_id != key:
        db.rollback()
        raise ValueError("Unknown owned practice trade")
    if settings.trading_mode != "OANDA_PRACTICE" or settings.demo_mode:
        db.rollback()
        raise ValueError("Closure requires practice mode")
    if order.state not in (("FILLED", "QUARANTINED") if emergency else ("FILLED",)) or not order.trade_id:
        db.rollback()
        return order.state
    approval = account.approval
    audit = db.scalar(select(Event.id).where(Event.kind == "practice_gateway_approved",
                      Event.detail["approval_id"].as_string() == approval.get("sha256", "")).limit(1))
    if (not approval or approval.get("sha256") != digest({k: v for k, v in approval.items() if k != "sha256"})
        or not audit or order.candidate.get("gateway_approval_id") != approval.get("sha256")
        or order.request_sha256 != digest(order.request)):
        db.rollback()
        raise ValueError("Ownership or reservation evidence invalid")
    trade_id, units = order.trade_id, abs(order.units)
    symbol, signed_units = order.candidate["symbol"], order.units
    order.state = "CLOSING"
    account.reconciled = False
    if emergency:
        account.suspended = True
    db.add(Event(kind="practice_close_requested", detail={"order": order.id, "emergency": emergency}))
    db.commit()
    try:
        actual = (await adapter.trade(trade_id))["trade"]
        if actual["instrument"] != symbol or decimal(actual["initialUnits"]) != signed_units:
            raise ValueError("Broker trade ownership or original exposure mismatch")
        remaining = decimal(actual["currentUnits"])
        if remaining * signed_units <= 0 or abs(remaining) > units:
            raise ValueError("Owned trade exposure unexpectedly increased or reversed")
        await adapter.close_trade(trade_id, abs(remaining))
    except Exception as exc:
        account = lock_practice(db, key)
        account.suspended = True
        db.add(Event(kind="practice_close_uncertain", detail={"order": order_id, "error_type": type(exc).__name__}))
        db.commit()
    return await reconcile_practice(db, adapter, settings.oanda_account_id)


def approve_external_lifecycle(db, settings, order_id, operator, reason, now=None):
    """Explicit review of actual durable lifecycle evidence, not a self-attestation flag."""
    now = now or datetime.now(timezone.utc)
    key = account_key(settings.oanda_account_id)
    try:
        account = lock_practice(db, key)
        order = db.get(PracticeOrder, order_id)
        if account is None or order is None or order.account_id != key or not account.reconciled:
            raise ValueError("Reconciled owned practice order required")
        if not operator.strip() or not reason.strip():
            raise ValueError("Operator attribution required")
        if (account.approval.get("scope") != "ONE_ORDER_PRACTICE_TEST"
            or account.approval.get("sha256") != digest({k: v for k, v in account.approval.items() if k != "sha256"})
            or order.candidate.get("gateway_approval_id") != account.approval.get("sha256")
            or order.state != "CLOSED" or order.realized_pnl is None
            or order.request_sha256 != digest(order.request)):
            raise ValueError("Completed explicitly approved practice test required")
        protected = db.scalar(select(Event.id).where(Event.kind == "practice_fill_protected",
                             Event.detail["order"].as_string() == order.id).limit(1))
        boots = db.scalars(select(Event).where(Event.kind == "practice_worker_started", Event.time > order.created_at)).all()
        restart = any(order.id in e.detail.get("open_orders", []) and e.detail.get("reconciled") for e in boots)
        notifications = [db.get(Notification, f"practice-{order.id[:40]}-{state}") for state in ("FILLED", "CLOSED")]
        if not protected or not restart or any(n is None or n.status != "DELIVERED" for n in notifications):
            raise ValueError("Protection, restart-with-open-trade and delivered notification evidence required")
        payload = {"account_fingerprint": key, "test_order": order.id, "test_approval": account.approval["sha256"],
                   "operator": operator[:120], "reason": reason[:512], "reviewed_at": now.isoformat()}
        db.add(Event(time=now, kind="practice_external_lifecycle_approved", detail=payload))
        db.commit()
        return payload
    except Exception:
        db.rollback()
        raise
