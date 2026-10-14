from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from app.schemas.domain import Candle

FEATURES = ["return_1", "volatility", "atr_pct", "rsi", "macd_pct", "trend", "zscore", "roc", "adx"]


def frame(candles: list[Candle], as_of: datetime | None = None) -> pd.DataFrame:
    if len({(c.symbol, c.timeframe, c.source) for c in candles}) > 1:
        raise ValueError("Features require a single instrument, timeframe and source")
    rows = [
        c.model_dump()
        for c in candles
        if c.complete and (as_of is None or c.time + timedelta(seconds=c.timeframe) <= as_of)
    ]
    if not rows:
        return pd.DataFrame()
    data = pd.DataFrame(rows).set_index("time").sort_index()
    if data.index.has_duplicates:
        raise ValueError("Duplicate candles in feature input")
    for col in ("open", "high", "low", "close", "volume"):
        data[col] = data[col].astype(float)
    return data


def compute(data: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        return data.copy()
    f = data.copy()
    close, high, low = f.close, f.high, f.low
    f["return_1"] = close.pct_change()
    f["volatility"] = f.return_1.rolling(24).std()
    true_range = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    f["atr"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    f["atr_pct"] = f.atr / close
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    f["rsi"] = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).where(loss != 0, 100)
    f.loc[(gain == 0) & (loss == 0), "rsi"] = 50
    f["ema_fast"] = close.ewm(span=12, adjust=False, min_periods=12).mean()
    f["ema_slow"] = close.ewm(span=26, adjust=False, min_periods=26).mean()
    f["macd_pct"] = (f.ema_fast - f.ema_slow) / close
    f["trend"] = f.ema_fast / f.ema_slow - 1
    f["zscore"] = (close - close.rolling(20).mean()) / close.rolling(20).std().replace(0, np.nan)
    f["roc"] = close.pct_change(10)
    f["prior_high"] = high.rolling(20).max().shift(1)
    f["prior_low"] = low.rolling(20).min().shift(1)
    up, down = high.diff(), -low.diff()
    plus = up.where((up > down) & (up > 0), 0).ewm(alpha=1 / 14, adjust=False).mean()
    minus = down.where((down > up) & (down > 0), 0).ewm(alpha=1 / 14, adjust=False).mean()
    dx = 100 * (plus - minus).abs() / (plus + minus).replace(0, np.nan)
    f["adx"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    # A pivot at t-2 is only recognized at t, after two confirming bars.
    f["swing_high"] = high.shift(2).where(high.shift(2) == high.rolling(5).max()).ffill()
    f["swing_low"] = low.shift(2).where(low.shift(2) == low.rolling(5).min()).ffill()
    return f.replace([np.inf, -np.inf], np.nan)


def align_higher(lower: pd.DataFrame, higher: pd.DataFrame, lower_seconds: int, higher_seconds: int):
    """Join by availability (candle close), never by the candle's opening timestamp."""
    left = lower.copy().reset_index()
    right = higher.copy().reset_index()
    left["available_at"] = left["time"] + pd.to_timedelta(lower_seconds, unit="s")
    right["available_at"] = right["time"] + pd.to_timedelta(higher_seconds, unit="s")
    return pd.merge_asof(
        left.sort_values("available_at"),
        right.sort_values("available_at"),
        on="available_at",
        direction="backward",
        suffixes=("", "_higher"),
    )
