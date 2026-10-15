from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from app.indicators.features import FEATURES, align_higher, compute, frame
from app.market_data.fixtures import demo_candles
from app.strategies.registry import candidates_from_row, evaluate


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


@pytest.mark.parametrize("tick", [Decimal(".00001"), Decimal(".01"), Decimal(".05")])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("stop_ticks", [10, 11])
def test_strategy_levels_use_whole_ticks_without_reducing_reward(tick, sign, stop_ticks):
    # Eleven stop ticks previously generated an invalid 27.5-tick target.
    row = pd.Series({feature: 0.0 for feature in FEATURES})
    row["close"] = 100.0
    row["atr"] = float(tick * stop_ticks / Decimal("1.5"))
    row["atr_pct"] = .001
    row["adx"] = 30.0
    row["trend"] = sign * .001
    row["prior_high"] = row["swing_high"] = 101.0
    row["prior_low"] = row["swing_low"] = 99.0
    candidate, = candidates_from_row(
        row, "TEST", 300, "fixture", datetime(2026, 1, 1, tzinfo=UTC), tick, ["trend"]
    )
    assert candidate.direction == ("LONG" if sign > 0 else "SHORT")
    assert all(price % tick == 0 for price in (candidate.entry, candidate.stop, candidate.target))
    assert (candidate.entry - candidate.stop) * sign == tick * stop_ticks
    expected_reward_ticks = (stop_ticks * 5 + 1) // 2
    assert (candidate.target - candidate.entry) * sign == tick * expected_reward_ticks
