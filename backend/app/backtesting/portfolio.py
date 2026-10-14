"""Chronological single-instrument portfolio replay with shared deterministic risk.

This module has no broker or database execution capability. Experimental calibrated
predictions are evaluated as research hypotheses, never promoted by simulation.
"""

from collections import Counter
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal

import numpy as np

from app.backtesting.simulator import FillAssumptions, metrics, resolve_exit
from app.indicators.features import compute, frame
from app.risk_management.engine import RiskState, approve
from app.schemas.domain import Quote
from app.strategies.registry import candidates_from_row

D = Decimal


@dataclass
class SimPosition:
    candidate: object
    units: Decimal
    entry: Decimal
    planned_risk: Decimal
    opened_index: int
    fees: Decimal


def run_portfolio(
    candles,
    rules,
    settings,
    costs: FillAssumptions,
    predictor,
    *,
    strategy="trend",
    initial=D(10000),
    horizon=12,
    start=None,
    end=None,
    proposer=None,
):
    if initial <= 0 or horizon < 1 or min(vars(costs).values()) < 0:
        raise ValueError("Invalid portfolio or cost assumptions")
    if settings.trading_mode != "PAPER":
        raise ValueError("Portfolio research requires PAPER configuration")
    data = compute(frame(candles))
    if len(data) != len(candles) or list(data.index) != [c.time for c in candles]:
        raise ValueError("Portfolio input must contain ordered completed candles")
    rules = replace(
        rules,
        slippage=costs.slippage,
        fee_rate=costs.fee_rate,
        extra_cost_per_unit=costs.financing_per_bar * horizon,
    )
    balance = equity = day_start = week_start = peak = initial
    day = week = None
    positions, trades, curve = [], [], []
    seen = set()
    rejected = Counter()
    losses, max_open, candidates_seen = 0, 0, 0
    half, conversion = costs.spread / 2, rules.quote_to_account

    def unrealized(mid):
        return sum(
            (
                (mid - (1 if p.candidate.direction == "LONG" else -1) * half - p.entry)
                * p.units
                * (1 if p.candidate.direction == "LONG" else -1)
                * conversion
                for p in positions
            ),
            D(0),
        )

    for i in range(60, len(candles)):
        bar = candles[i]
        now = bar.time
        if start is not None and now < start:
            continue
        equity = balance + unrealized(bar.open)
        period_day, period_week = now.date(), now.isocalendar()[:2]
        if day != period_day:
            day, day_start = period_day, equity
        if week != period_week:
            week, week_start = period_week, equity
        peak = max(peak, equity)
        quote = Quote(
            symbol=bar.symbol, source=bar.source, time=now, bid=bar.open - half, ask=bar.open + half
        )
        proposals = []
        contiguous = (
            data.index[i - 60 : i + 1].to_series().diff().dropna().dt.total_seconds() == bar.timeframe
        ).all()
        if contiguous and (end is None or now <= end):
            proposals = (
                proposer(i, bar)
                if proposer
                else candidates_from_row(
                    data.iloc[i - 1], bar.symbol, bar.timeframe, bar.source, now, rules.tick, [strategy]
                )
            )
        for candidate in proposals:
            if candidate.id in seen:
                continue
            seen.add(candidate.id)
            candidates_seen += 1
            prediction = predictor(candidate, quote)
            if prediction:
                candidate = candidate.model_copy(
                    update={
                        "probability": D(str(prediction["probability_target"])),
                        "probability_stop": D(str(prediction["probability_stop"])),
                        "probability_timeout": D(str(prediction["probability_timeout"])),
                        "model_version": prediction["model_version"],
                        "calibrated": True,
                    }
                )
            risk_total = sum((p.planned_risk for p in positions), D(0))
            gross = sum((p.units * bar.open * conversion for p in positions), D(0))
            state = RiskState(
                equity,
                day_start,
                week_start,
                peak,
                max(D(0), equity - gross * rules.margin_rate),
                len(positions),
                risk_total,
                gross,
                risk_total,
                losses,
                True,
                False,
                True,
            )
            decision = approve(candidate, quote, state, rules, settings, now)
            if not decision.approved:
                rejected.update(decision.reasons)
                continue
            sign = D(1) if candidate.direction == "LONG" else D(-1)
            fill = (quote.ask if sign > 0 else quote.bid) + sign * costs.slippage
            fee = fill * decision.units * costs.fee_rate * conversion
            balance -= fee
            positions.append(SimPosition(candidate, decision.units, fill, decision.planned_risk, i, fee))
            equity = balance + unrealized(bar.open)
            max_open = max(max_open, len(positions))

        had_exposure = bool(positions)
        for position in list(positions):
            fee = costs.financing_per_bar * position.units * conversion
            position.fees += fee
            balance -= fee
            candidate = position.candidate
            due = i - position.opened_index + 1 >= horizon or i == len(candles) - 1
            resolved = resolve_exit(
                bar, candidate.direction, candidate.stop, candidate.target, costs, timeout=due
            )
            if resolved is None:
                continue
            exit_price, reason = resolved
            sign = D(1) if candidate.direction == "LONG" else D(-1)
            gross_pnl = (exit_price - position.entry) * position.units * sign * conversion
            exit_fee = exit_price * position.units * costs.fee_rate * conversion
            balance += gross_pnl - exit_fee
            pnl = gross_pnl - position.fees - exit_fee
            losses = losses + 1 if pnl < 0 else 0
            trades.append(
                {
                    "candidate_id": candidate.id,
                    "entry_time": candidate.time.isoformat(),
                    "exit_time": (bar.time + timedelta(seconds=bar.timeframe)).isoformat(),
                    "direction": candidate.direction,
                    "units": str(position.units),
                    "entry": str(position.entry),
                    "exit": str(exit_price),
                    "stop": str(candidate.stop),
                    "target": str(candidate.target),
                    "pnl": str(pnl),
                    "fees": str(position.fees + exit_fee),
                    "planned_risk": str(position.planned_risk),
                    "reason": reason,
                    "holding_bars": i - position.opened_index + 1,
                }
            )
            positions.remove(position)
        equity = balance + unrealized(bar.close)
        peak = max(peak, equity)
        curve.append(
            {
                "time": (bar.time + timedelta(seconds=bar.timeframe)).isoformat(),
                "equity": str(equity),
                "balance": str(balance),
                "open_positions": len(positions),
                "had_exposure": had_exposure,
            }
        )
    report = metrics([float(t["pnl"]) for t in trades], float(initial))
    values = np.array([float(initial)] + [float(p["equity"]) for p in curve])
    report["max_drawdown"] = float(np.max(1 - values / np.maximum.accumulate(values)))
    report["net_return"] = float(equity / initial - 1)
    report["equity_curve"] = curve
    report["drawdown_curve"] = (1 - values / np.maximum.accumulate(values)).tolist()
    report["average_holding_bars"] = float(np.mean([t["holding_bars"] for t in trades])) if trades else None
    report["total_fees"] = str(sum((D(t["fees"]) for t in trades), D(0)))
    report["exposure_fraction"] = sum(p["had_exposure"] for p in curve) / len(curve) if curve else 0
    return {
        "source": candles[0].source if candles else None,
        "research_only": True,
        "execution_authorized": False,
        "costs": {k: str(v) for k, v in vars(costs).items()},
        "metrics": report,
        "trades": trades,
        "candidates": candidates_seen,
        "rejections": dict(rejected),
        "maximum_open_positions": max_open,
        "benchmark_no_trade_return": 0,
        "limitations": [
            "Single instrument; global correlation bucket",
            "Constant costs; no depth or partial fills",
            "Conservative intrabar sequencing",
            "Research model eligibility is not deployment approval",
        ],
    }
