from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

from app.core.config import Settings
from app.schemas.domain import Candidate, Quote, RiskDecision, aware

D = Decimal


@dataclass(frozen=True)
class RiskState:
    equity: Decimal
    day_start: Decimal
    week_start: Decimal
    peak: Decimal
    free_margin: Decimal
    open_positions: int = 0
    portfolio_risk: Decimal = D(0)
    gross_notional: Decimal = D(0)
    correlated_risk: Decimal = D(0)
    consecutive_losses: int = 0
    reconciled: bool = False
    suspended: bool = False
    account_fresh: bool = False


@dataclass(frozen=True)
class InstrumentRules:
    symbol: str
    tick: Decimal
    unit_step: Decimal
    min_units: Decimal
    max_spread: Decimal
    quote_to_account: Decimal = D(1)
    margin_rate: Decimal = D(1)
    slippage: Decimal | None = None
    fee_rate: Decimal = D(0)
    extra_cost_per_unit: Decimal = D(0)


def approve(
    candidate: Candidate,
    quote: Quote,
    state: RiskState,
    rules: InstrumentRules,
    settings: Settings,
    now: datetime,
) -> RiskDecision:
    reasons = []
    s, q, r = candidate, quote, rules
    positive_rules = (r.tick, r.unit_step, r.min_units, r.max_spread, r.quote_to_account, r.margin_rate)
    slippage = r.tick if r.slippage is None else r.slippage
    if (
        any(not value.is_finite() or value <= 0 for value in positive_rules)
        or any(not value.is_finite() or value < 0 for value in (slippage, r.fee_rate, r.extra_cost_per_unit))
        or r.fee_rate >= 1
    ):
        return RiskDecision(approved=False, reasons=["INVALID_INSTRUMENT_RULES"])
    fees = (s.entry + max(s.stop, s.target)) * r.fee_rate + r.extra_cost_per_unit
    if settings.trading_mode == "SIGNAL_ONLY":
        reasons.append("SIGNAL_ONLY_MODE")
    if s.symbol != q.symbol or s.symbol != r.symbol or s.source != q.source:
        reasons.append("DATA_IDENTITY_MISMATCH")
    if s.source == "fixture" and not settings.demo_mode:
        reasons.append("FIXTURE_NOT_ALLOWED")
    if not state.reconciled or not state.account_fresh:
        reasons.append("ACCOUNT_NOT_RECONCILED")
    if state.suspended:
        reasons.append("TRADING_SUSPENDED")
    if aware(s.time) > now or now >= aware(s.expires_at):
        reasons.append("SIGNAL_EXPIRED_OR_FUTURE")
    if not -2 <= (now - q.time).total_seconds() <= settings.max_quote_age_seconds:
        reasons.append("STALE_OR_FUTURE_QUOTE")
    if s.regime in ("UNCERTAIN", "HIGH_VOLATILITY"):
        reasons.append("UNSUITABLE_REGIME")
    sign = D(1) if s.direction == "LONG" else D(-1)
    if (s.entry - s.stop) * sign <= 0 or (s.target - s.entry) * sign <= 0:
        reasons.append("INVALID_PROTECTIVE_LEVELS")
    if any(price % r.tick != 0 for price in (s.entry, s.stop, s.target)):
        reasons.append("INVALID_PRICE_PRECISION")
    spread = q.ask - q.bid
    if spread > r.max_spread:
        reasons.append("EXCESSIVE_SPREAD")
    distance, reward = abs(s.entry - s.stop), abs(s.target - s.entry)
    if not distance or reward < settings.min_risk_reward * distance:
        reasons.append("INSUFFICIENT_REWARD_RISK")
    if spread > reward * D("0.1"):
        reasons.append("SPREAD_EXCEEDS_REWARD_BUDGET")
    market = q.ask if sign > 0 else q.bid
    fill = market + sign * slippage
    if (fill - s.stop) * sign <= 0 or (s.target - fill) * sign <= 0:
        reasons.append("SLIPPAGE_INVALIDATES_PROTECTION")
    if abs(market - s.entry) > max(distance * D("0.1"), r.tick * 2):
        reasons.append("PRICE_MOVED_OUTSIDE_ENTRY_ZONE")
    if state.equity <= 0 or min(state.day_start, state.week_start, state.peak) <= 0:
        reasons.append("INVALID_ACCOUNT_EQUITY")
    else:
        if (state.day_start - state.equity) / state.day_start >= settings.max_daily_loss:
            reasons.append("DAILY_LOSS_LIMIT")
        if (state.week_start - state.equity) / state.week_start >= settings.max_weekly_loss:
            reasons.append("WEEKLY_LOSS_LIMIT")
        if (state.peak - state.equity) / state.peak >= settings.max_drawdown:
            reasons.append("DRAWDOWN_LIMIT")
    if state.consecutive_losses >= 5:
        reasons.append("CONSECUTIVE_LOSS_LIMIT")
    if state.open_positions >= settings.max_open_positions:
        reasons.append("POSITION_LIMIT")
    ev = None
    probs = [s.probability, s.probability_stop, s.probability_timeout]
    if not s.calibrated or not s.model_version or any(p is None for p in probs):
        reasons.append("NO_VALIDATED_CALIBRATED_MODEL")
    elif any(not p.is_finite() or p < 0 or p > 1 for p in probs) or abs(sum(probs) - 1) > D("0.000001"):
        reasons.append("INVALID_OUTCOME_PROBABILITIES")
    else:
        if s.probability < settings.initial_probability_threshold:
            reasons.append("PROBABILITY_BELOW_THRESHOLD")
        # Conservative timeout loss; never allow a supplied timeout forecast to improve EV.
        cost = spread + slippage * 2 + fees
        ev = s.probability * reward - s.probability_stop * distance - s.probability_timeout * distance - cost
        if ev <= 0:
            reasons.append("NONPOSITIVE_EXPECTED_VALUE")
    if r.quote_to_account <= 0 or r.margin_rate <= 0 or r.unit_step <= 0:
        reasons.append("INVALID_INSTRUMENT_RULES")
    if reasons:
        return RiskDecision(approved=False, reasons=reasons, expected_value=ev)
    # Include adverse entry movement, slippage and spread in planned loss.
    per_unit_risk = (distance + abs(market - s.entry) + spread + slippage * 2 + fees) * r.quote_to_account
    portfolio_budget = state.equity * settings.max_portfolio_risk - state.portfolio_risk
    correlation_budget = state.equity * D("0.01") - state.correlated_risk
    budget = max(D(0), min(state.equity * settings.risk_per_trade, portfolio_budget, correlation_budget))
    leverage_room = max(D(0), state.equity * settings.max_leverage - state.gross_notional)
    margin_units = max(D(0), state.free_margin) / (fill * r.quote_to_account * (r.margin_rate + r.fee_rate))
    leverage_units = leverage_room / (fill * r.quote_to_account)
    size = min(budget / per_unit_risk, margin_units, leverage_units)
    units = (size / r.unit_step).to_integral_value(rounding=ROUND_FLOOR) * r.unit_step
    planned = units * per_unit_risk
    notional = units * fill * r.quote_to_account
    if units < r.min_units:
        reasons.append("BELOW_MINIMUM_UNITS")
        if margin_units < r.min_units:
            reasons.append("INSUFFICIENT_MARGIN")
        if leverage_units < r.min_units:
            reasons.append("LEVERAGE_LIMIT")
        if portfolio_budget < per_unit_risk * r.min_units:
            reasons.append("PORTFOLIO_RISK_LIMIT")
        if correlation_budget < per_unit_risk * r.min_units:
            reasons.append("CORRELATED_RISK_LIMIT")
    if state.portfolio_risk + planned > state.equity * settings.max_portfolio_risk:
        reasons.append("PORTFOLIO_RISK_LIMIT")
    if state.correlated_risk + planned > state.equity * D("0.01"):
        reasons.append("CORRELATED_RISK_LIMIT")
    if state.gross_notional + notional > state.equity * settings.max_leverage:
        reasons.append("LEVERAGE_LIMIT")
    if notional * (r.margin_rate + r.fee_rate) > state.free_margin:
        reasons.append("INSUFFICIENT_MARGIN")
    return RiskDecision(
        approved=not reasons,
        reasons=reasons,
        units=units if not reasons else D(0),
        planned_risk=planned if not reasons else D(0),
        expected_value=ev,
        reward_risk=reward / distance,
    )
