"""Durable paper execution. All entry paths pass through the deterministic risk engine."""

from datetime import datetime, timedelta
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.tables import (
    Account,
    Event,
    Instrument,
    ModelVersion,
    OrderEvent,
    OrderRow,
    QuoteRow,
    SignalRow,
)
from app.risk_management.engine import InstrumentRules, RiskState, approve
from app.schemas.domain import Candidate, Quote, aware

D = Decimal
ACTIVE = ("SUBMITTING", "UNKNOWN", "PENDING", "FILLED")
LEDGER_QUANTUM = D(".0000000001")


def money(value):
    return value.quantize(LEDGER_QUANTUM)


def valid_execution(order):
    """Unproven legacy positions remain quarantined, never assigned invented costs."""
    try:
        record = order.execution
        costs = [D(record[key]) for key in ("fee_rate", "slippage", "financing_per_bar")]
        return (
            record["schema"] == "paper-cost-v1"
            and bool(record["source"])
            and int(record["timeframe"]) > 0
            and all(value.is_finite() and value >= 0 for value in costs)
            and costs[0] < 1
            and order.fees_paid >= 0
            and order.financing_bars >= 0
        )
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return False


def usable_quote(order, quote, now, max_age):
    return (
        quote is not None
        and valid_execution(order)
        and quote.source == order.execution["source"]
        and aware(quote.time) >= aware(order.opened_at)
        and -2 <= (now - aware(quote.time)).total_seconds() <= max_age
    )


def lock_account(db: Session) -> Account:
    # One account lock serializes risk evaluation and portfolio reservation across workers.
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    return db.scalars(select(Account).where(Account.id == "PAPER").with_for_update()).one()


def transition(db: Session, order: OrderRow, state: str, detail=""):
    allowed = {
        "PROPOSED": {"RISK_APPROVED", "REJECTED"},
        "RISK_APPROVED": {"SUBMITTING"},
        "SUBMITTING": {"FILLED", "PENDING", "REJECTED", "UNKNOWN"},
        "PENDING": {"FILLED", "CANCELLED"},
        "FILLED": {"CLOSED"},
        "UNKNOWN": {"FILLED", "PENDING", "REJECTED", "CANCELLED"},
    }
    if state not in allowed.get(order.state, set()):
        raise ValueError(f"Invalid order transition {order.state} -> {state}")
    order.state = state
    db.add(OrderEvent(order_id=order.id, state=state, detail=detail))


def reconcile(db: Session, now: datetime):
    account = lock_account(db)
    orders = db.scalars(select(OrderRow).where(OrderRow.mode == "PAPER", OrderRow.state.in_(ACTIVE))).all()
    unsafe = any(
        o.state != "FILLED"
        or not valid_execution(o)
        or o.units <= 0
        or o.stop <= 0
        or not ((o.stop < o.entry < o.target) if o.direction == "LONG" else (o.target < o.entry < o.stop))
        for o in orders
    )
    account.reconciled = not unsafe
    if unsafe:
        account.suspended = True
    account.updated_at = now
    db.add(Event(kind="paper_reconciliation", detail={"success": not unsafe, "positions": len(orders)}))
    db.commit()
    return not unsafe


def mark_account(db: Session, account: Account, now: datetime, max_age=30):
    orders = db.scalars(select(OrderRow).where(OrderRow.mode == "PAPER", OrderRow.state.in_(ACTIVE))).all()
    unrealized = D(0)
    fresh = True
    for o in orders:
        quote = db.get(QuoteRow, o.symbol)
        if not usable_quote(o, quote, now, max_age):
            fresh = False
            continue
        mark = quote.bid if o.direction == "LONG" else quote.ask
        unrealized += (mark - o.entry) * o.units * (1 if o.direction == "LONG" else -1)
    if fresh:
        account.equity = money(account.balance + unrealized)
        day, week = now.date().isoformat(), f"{now.isocalendar().year}-{now.isocalendar().week:02d}"
        if account.day != day:
            account.day, account.day_start = day, account.equity
        if account.week != week:
            account.week, account.week_start = week, account.equity
        account.peak = max(account.peak, account.equity)
        account.updated_at = now
    return orders, fresh


def submit(db: Session, candidate: Candidate, quote: Quote, settings: Settings, now: datetime):
    if settings.trading_mode not in ("PAPER", "SIGNAL_ONLY"):
        raise ValueError("Paper gateway cannot submit broker orders")
    account = lock_account(db)
    existing = db.get(SignalRow, candidate.id)
    if existing:
        db.rollback()
        return existing.status
    instrument = db.get(Instrument, candidate.symbol)
    if instrument is None:
        db.rollback()
        raise ValueError("Unknown instrument")
    orders, fresh = mark_account(db, account, now, settings.max_quote_age_seconds)
    risk_total = sum((o.planned_risk for o in orders), D(0))
    gross = (
        sum((o.units * max(o.entry, db.get(QuoteRow, o.symbol).ask) for o in orders), D(0))
        if fresh
        else sum((o.units * o.entry for o in orders), D(0))
    )
    # USD account only; conservative all-symbol correlation bucket until validated grouping exists.
    state = RiskState(
        account.equity,
        account.day_start,
        account.week_start,
        account.peak,
        max(D(0), account.equity - gross),
        len(orders),
        risk_total,
        gross,
        risk_total,
        account.consecutive_losses,
        account.reconciled,
        account.suspended,
        fresh,
    )
    rules = InstrumentRules(
        instrument.symbol,
        instrument.tick_size,
        instrument.unit_step,
        instrument.min_units,
        instrument.max_spread,
        slippage=instrument.tick_size * settings.paper_slippage_ticks,
        fee_rate=settings.paper_fee_rate,
        extra_cost_per_unit=settings.paper_financing_per_unit_per_bar * 12,
    )
    version = db.get(ModelVersion, candidate.model_version) if candidate.model_version else None
    evidence = version.metadata_json if version else {}
    scope_ok = (
        evidence.get("symbol") == candidate.symbol
        and evidence.get("strategy") == candidate.strategy
        and evidence.get("timeframe") == candidate.timeframe
        and evidence.get("source") == candidate.source
    )
    if not version or version.status != "ACTIVE" or not evidence.get("execution_validated") or not scope_ok:
        candidate = candidate.model_copy(update={"calibrated": False})
    decision = approve(candidate, quote, state, rules, settings, now)
    db.add(
        SignalRow(
            id=candidate.id,
            time=candidate.time,
            symbol=candidate.symbol,
            strategy=candidate.strategy,
            status="APPROVED" if decision.approved else "REJECTED",
            payload=candidate.model_dump(mode="json") | {"decision": decision.model_dump(mode="json")},
            reasons=decision.reasons,
        )
    )
    db.flush()
    if not decision.approved:
        db.commit()
        return "REJECTED"
    sign = D(1) if candidate.direction == "LONG" else D(-1)
    fill = (quote.ask if sign > 0 else quote.bid) + sign * rules.slippage
    entry_fee = money(fill * decision.units * settings.paper_fee_rate)
    order = OrderRow(
        id=candidate.id,
        signal_id=candidate.id,
        mode="PAPER",
        state="PROPOSED",
        symbol=candidate.symbol,
        direction=candidate.direction,
        units=decision.units,
        entry=fill,
        stop=candidate.stop,
        target=candidate.target,
        planned_risk=decision.planned_risk,
        opened_at=now,
        expires_at=now + timedelta(seconds=candidate.timeframe * 12),
        execution={
            "schema": "paper-cost-v1",
            "source": candidate.source,
            "quote_time": quote.time.isoformat(),
            "fee_rate": str(settings.paper_fee_rate),
            "slippage": str(rules.slippage),
            "financing_per_bar": str(settings.paper_financing_per_unit_per_bar),
            "timeframe": candidate.timeframe,
            "assumptions": "Configured constant paper costs; not verified provider charges",
        },
        fees_paid=entry_fee,
        financing_bars=0,
    )
    db.add(order)
    db.flush()
    db.add(OrderEvent(order_id=order.id, state="PROPOSED"))
    transition(db, order, "RISK_APPROVED")
    transition(db, order, "SUBMITTING")
    transition(db, order, "FILLED", "Simulated executable quote plus persisted adverse slippage")
    account.balance = money(account.balance - entry_fee)
    # Mark the new fill immediately; fees and bid/ask entry loss are never hidden until the next tick.
    account.equity = money(
        account.equity - entry_fee - (quote.ask - quote.bid + rules.slippage) * order.units
    )
    db.commit()
    return "FILLED"


def monitor(db: Session, settings: Settings, now: datetime):
    account = lock_account(db)
    orders = db.scalars(select(OrderRow).where(OrderRow.mode == "PAPER", OrderRow.state == "FILLED")).all()
    for order in orders:
        if not valid_execution(order):
            account.suspended, account.reconciled = True, False
            continue
        elapsed = max(D(0), D(str((now - aware(order.opened_at)).total_seconds())))
        # Financing is an explicit per-unit charge per started holding bar.
        bars = int((elapsed / D(order.execution["timeframe"])).to_integral_value(rounding=ROUND_CEILING))
        additional = max(0, bars - order.financing_bars)
        financing = money(D(order.execution["financing_per_bar"]) * order.units * additional)
        account.balance = money(account.balance - financing)
        order.fees_paid = money(order.fees_paid + financing)
        order.financing_bars += additional
        q = db.get(QuoteRow, order.symbol)
        if not usable_quote(order, q, now, settings.max_quote_age_seconds):
            continue
        sign = D(1) if order.direction == "LONG" else D(-1)
        mark = q.bid if sign > 0 else q.ask
        reason = (
            "STOP_LOSS"
            if (mark - order.stop) * sign <= 0
            else "TAKE_PROFIT"
            if (mark - order.target) * sign >= 0
            else "TIMEOUT"
            if now >= aware(order.expires_at)
            else None
        )
        if reason:
            order.exit = (
                order.target if reason == "TAKE_PROFIT" else mark - sign * D(order.execution["slippage"])
            )
            gross_pnl = money((order.exit - order.entry) * order.units * sign)
            exit_fee = money(order.exit * order.units * D(order.execution["fee_rate"]))
            order.fees_paid = money(order.fees_paid + exit_fee)
            order.pnl = money(gross_pnl - order.fees_paid)
            order.closed_at, order.close_reason = now, reason
            account.balance = money(account.balance + gross_pnl - exit_fee)
            account.consecutive_losses = account.consecutive_losses + 1 if order.pnl < 0 else 0
            transition(db, order, "CLOSED", reason)
    db.flush()
    mark_account(db, account, now, settings.max_quote_age_seconds)
    db.commit()
