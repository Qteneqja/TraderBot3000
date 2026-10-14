from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256

import pandas as pd

from app.indicators.features import FEATURES, compute, frame
from app.schemas.domain import Candidate, Candle


def regime(row) -> str:
    if pd.isna(row.volatility) or pd.isna(row.adx):
        return "UNCERTAIN"
    if row.atr_pct > 0.025:
        return "HIGH_VOLATILITY"
    if row.atr_pct < 0.00015:
        return "LOW_VOLATILITY"
    if row.adx > 25 and abs(row.trend) > 0.0004:
        return "BULLISH_TREND" if row.trend > 0 else "BEARISH_TREND"
    if row.adx < 22:
        return "RANGE"
    return "UNCERTAIN"


# Strategies are hypotheses, not validated trading advantages.
STRATEGIES = {
    "trend": {"name": "Trend following", "regimes": ["BULLISH_TREND", "BEARISH_TREND"]},
    "momentum": {"name": "Momentum continuation", "regimes": ["BULLISH_TREND", "BEARISH_TREND"]},
    "mean_reversion": {"name": "Mean reversion", "regimes": ["RANGE"]},
    "breakout": {"name": "Range breakout", "regimes": ["BULLISH_TREND", "BEARISH_TREND", "RANGE"]},
    "structure": {"name": "Confirmed market structure", "regimes": ["BULLISH_TREND", "BEARISH_TREND"]},
    "volatility": {"name": "Volatility expansion", "regimes": ["BULLISH_TREND", "BEARISH_TREND"]},
}


def directions(row) -> dict[str, int]:
    sign = 1 if row.trend > 0 else -1
    return {
        "trend": sign if abs(row.trend) > 0.0004 else 0,
        "momentum": 1 if row.rsi > 55 and row.roc > 0 else -1 if row.rsi < 45 and row.roc < 0 else 0,
        "mean_reversion": -1 if row.zscore > 2 else 1 if row.zscore < -2 else 0,
        "breakout": 1 if row.close > row.prior_high else -1 if row.close < row.prior_low else 0,
        "structure": 1 if row.close > row.swing_high else -1 if row.close < row.swing_low else 0,
        "volatility": sign if abs(row.return_1) > 1.5 * row.volatility else 0,
    }


def evaluate(candles: list[Candle], as_of: datetime, tick: Decimal, enabled=None) -> list[Candidate]:
    data = compute(frame(candles, as_of))
    if len(data) < 60:
        return []
    if (data.index[-60:].to_series().diff().dropna().dt.total_seconds() != candles[-1].timeframe).any():
        return []  # Wait for a contiguous warm-up after an unverified gap or market closure.
    row = data.iloc[-1]
    latest = candles[-1]
    signal_time = data.index[-1].to_pydatetime() + timedelta(seconds=latest.timeframe)
    return candidates_from_row(
        row, latest.symbol, latest.timeframe, latest.source, signal_time, tick, enabled
    )


def candidates_from_row(row, symbol, timeframe, source, signal_time, tick, enabled=None):
    """Shared completed-candle proposal logic for historical research and the worker."""
    if row[FEATURES].isna().any():
        return []
    state = regime(row)
    candidates = []
    for name, direction in directions(row).items():
        if not direction or state not in STRATEGIES[name]["regimes"] or (enabled and name not in enabled):
            continue

        def quant(value):
            return (Decimal(str(value)) / tick).to_integral_value(rounding=ROUND_HALF_EVEN) * tick

        entry = quant(row.close)
        distance = max(quant(row.atr * 1.5), tick * 10)
        identity = f"{symbol}:{timeframe}:{signal_time.isoformat()}:{name}:v1:{source}"
        candidates.append(
            Candidate(
                id=sha256(identity.encode()).hexdigest()[:32],
                symbol=symbol,
                strategy=name,
                direction="LONG" if direction > 0 else "SHORT",
                time=signal_time,
                expires_at=signal_time + timedelta(seconds=timeframe),
                entry=entry,
                stop=entry - direction * distance,
                target=entry + direction * distance * Decimal("2.5"),
                timeframe=timeframe,
                regime=state,
                features={f: float(row[f]) for f in FEATURES},
                invalidation="Fixed ATR stop, expired setup, stale quote, or risk restriction",
                source=source,
            )
        )
    return candidates
