"""Conservative single-position research simulator. No claim of execution-quality history."""

from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from app.schemas.domain import Candle

D = Decimal


@dataclass(frozen=True)
class FillAssumptions:
    spread: Decimal
    slippage: Decimal
    fee_rate: Decimal = D(0)
    financing_per_bar: Decimal = D(0)


def resolve_exit(candle, direction, stop, target, costs, *, allow_target=True, timeout=False):
    """Shared conservative bar exit for single-trade and portfolio simulation."""
    sign = D(1) if direction == "LONG" else D(-1)
    half = costs.spread / 2
    exit_low, exit_high = candle.low - sign * half, candle.high - sign * half
    stop_hit = exit_low <= stop if sign > 0 else exit_high >= stop
    target_hit = exit_high >= target if sign > 0 else exit_low <= target
    if stop_hit:
        opening = candle.open - sign * half
        price = (min(stop, opening) if sign > 0 else max(stop, opening)) - sign * costs.slippage
        return price, "STOP_AMBIGUOUS" if target_hit else "STOP_LOSS"
    if target_hit and allow_target:
        return target, "TAKE_PROFIT"
    if timeout:
        return candle.close - sign * (half + costs.slippage), "TIMEOUT"
    return None


def simulate_trade(
    candles: list[Candle],
    direction: str,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
    units: Decimal,
    costs: FillAssumptions,
    order_type="MARKET",
    pending_bars=3,
):
    if not candles or units <= 0:
        raise ValueError("Candles and positive units required")
    if direction not in ("LONG", "SHORT"):
        raise ValueError("Direction must be LONG or SHORT")
    if order_type not in ("MARKET", "LIMIT"):
        raise ValueError("Unsupported simulation order type")
    if min(costs.spread, costs.slippage, costs.fee_rate, costs.financing_per_bar) < 0:
        raise ValueError("Costs must be nonnegative")
    sign = D(1) if direction == "LONG" else D(-1)
    if (entry - stop) * sign <= 0 or (target - entry) * sign <= 0:
        raise ValueError("Invalid protective levels")
    filled = None
    fill_price = None
    half = costs.spread / 2
    for i, c in enumerate(candles):
        if filled is None:
            if order_type == "LIMIT":
                if i >= pending_bars:
                    return {"status": "UNFILLED", "pnl": "0"}
                # Require strict penetration of executable side; a touch alone is insufficient.
                hit = c.low + half < entry if sign > 0 else c.high - half > entry
                if not hit:
                    continue
                fill_price = entry  # no optimistic gap improvement
            else:
                fill_price = c.open + sign * (half + costs.slippage)
                if (fill_price - stop) * sign <= 0 or (target - fill_price) * sign <= 0:
                    return {"status": "INVALIDATED", "pnl": "0", "reason": "Entry gap invalidated setup"}
            filled = i
        resolved = resolve_exit(
            c,
            direction,
            stop,
            target,
            costs,
            allow_target=not (order_type == "LIMIT" and i == filled),
            timeout=i == len(candles) - 1,
        )
        if resolved is None:
            continue
        exit_price, reason = resolved
        fees = (fill_price + exit_price) * units * costs.fee_rate
        financing = costs.financing_per_bar * units * (i - filled + 1)
        pnl = (exit_price - fill_price) * sign * units - fees - financing
        return {
            "status": "CLOSED",
            "entry": str(fill_price),
            "exit": str(exit_price),
            "pnl": str(pnl),
            "reason": reason,
            "bars": i - filled + 1,
            "fees": str(fees + financing),
            "assumption": "constant spread; conservative stop-first intrabar; no liquidity model",
        }
    return {"status": "UNFILLED", "pnl": "0"}


def metrics(pnls: list[float], initial=10000.0):
    equity = np.r_[initial, initial + np.cumsum(pnls)]
    peaks = np.maximum.accumulate(equity)
    drawdown = (equity - peaks) / peaks
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    return {
        "trades": len(pnls),
        "net_return": float(equity[-1] / initial - 1),
        "max_drawdown": float(-drawdown.min()),
        "win_rate": float(np.mean(np.array(pnls) > 0)) if pnls else None,
        "profit_factor": wins / losses if losses else None,
        "expectancy": float(np.mean(pnls)) if pnls else None,
        "equity_curve": equity.tolist(),
        "drawdown_curve": drawdown.tolist(),
        "annualized_return": None,
        "sharpe": None,
        "limitations": "No annualization without a validated observation schedule; research results only",
    }
