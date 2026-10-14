from datetime import timedelta
from decimal import Decimal

import pandas as pd

from app.indicators.features import FEATURES, align_higher, compute, frame
from app.market_data.fixtures import demo_candles
from app.strategies.registry import evaluate


def test_features_do_not_repaint():
    candles = demo_candles(count=150)
    full = compute(frame(candles))
    partial = compute(frame(candles[:100]))
    pd.testing.assert_frame_equal(full.iloc[:100][FEATURES], partial[FEATURES])
    when = candles[99].time + timedelta(seconds=300)
    assert evaluate(candles, when, Decimal(".00001")) == evaluate(candles[:100], when, Decimal(".00001"))


def test_higher_timeframe_only_available_after_close():
    low = frame(demo_candles(timeframe=300, count=15))
    high = frame(demo_candles(timeframe=3600, count=2))
    joined = align_higher(low, high, 300, 3600)
    assert joined.iloc[:11].close_higher.isna().all()
    assert joined.iloc[11].close_higher == high.iloc[0].close
