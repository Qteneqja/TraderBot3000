from decimal import Decimal as D

from app.backtesting.simulator import FillAssumptions, simulate_trade
from app.market_data.fixtures import demo_candles


def candle(**values):
    return demo_candles(count=1)[0].model_copy(update={k: D(v) for k, v in values.items()})


def test_ambiguous_bar_stop_first():
    result = simulate_trade(
        [candle(open="100", high="110", low="90", close="101")],
        "LONG",
        D(100),
        D(95),
        D(105),
        D(1),
        FillAssumptions(D(2), D(1)),
    )
    assert result["reason"] == "STOP_AMBIGUOUS"
    assert D(result["entry"]) == 102 and D(result["exit"]) == 94
    assert D(result["pnl"]) == -8


def test_touch_is_not_limit_fill():
    result = simulate_trade(
        [candle(open="103", high="104", low="99", close="102")],
        "LONG",
        D(100),
        D(95),
        D(105),
        D(1),
        FillAssumptions(D(2), D(0)),
        order_type="LIMIT",
    )
    assert result["status"] == "UNFILLED"


def test_gap_stop_worse_than_level():
    result = simulate_trade(
        [
            candle(open="100", high="102", low="98", close="100"),
            candle(open="90", high="92", low="88", close="90"),
        ],
        "LONG",
        D(100),
        D(95),
        D(105),
        D(1),
        FillAssumptions(D(2), D(1)),
    )
    assert D(result["exit"]) == 88


def test_invalid_entry_gap_abstains():
    result = simulate_trade(
        [candle(open="90", high="92", low="88", close="90")],
        "LONG",
        D(100),
        D(95),
        D(105),
        D(1),
        FillAssumptions(D(2), D(1)),
    )
    assert result["status"] == "INVALIDATED"
