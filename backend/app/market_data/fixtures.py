"""Deterministic synthetic OHLC for software demonstration only; never historical evidence."""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.schemas.domain import Candle


def demo_candles(symbol="EUR_USD", timeframe=300, count=360):
    bases = {"EUR_USD": 1.08, "GBP_USD": 1.27, "BTC-USD": 60000, "ETH-USD": 2500}
    base = bases[symbol]
    start = datetime(2025, 1, 6, tzinfo=timezone.utc)
    previous = base
    candles = []
    for i in range(count):
        close = base * (1 + 0.000035 * i + 0.003 * math.sin(i / 17) + 0.0007 * math.sin(i / 3))
        pad = base * (0.0003 + abs(math.sin(i)) * 0.0002)
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                time=start + timedelta(seconds=i * timeframe),
                open=Decimal(str(previous)),
                close=Decimal(str(close)),
                high=Decimal(str(max(previous, close) + pad)),
                low=Decimal(str(min(previous, close) - pad)),
                volume=Decimal(100 + i % 71),
                source="fixture",
                provenance={"synthetic": True, "seed": "deterministic-v1", "execution_quality": False},
            )
        )
        previous = close
    return candles
