from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from app.core.config import Settings
from app.risk_management.engine import InstrumentRules, RiskState, approve
from app.schemas.domain import Candidate, Quote


def setup_risk():
    now = datetime.now(timezone.utc)
    candidate = Candidate(
        id="risk-test",
        symbol="EUR_USD",
        strategy="trend",
        direction="LONG",
        time=now,
        expires_at=now + timedelta(minutes=5),
        entry=D("1.1"),
        stop=D("1.09"),
        target=D("1.125"),
        timeframe=300,
        regime="BULLISH_TREND",
        features={},
        invalidation="stop",
        source="test",
        probability=D(".85"),
        probability_stop=D(".1"),
        probability_timeout=D(".05"),
        model_version="unit-test-only",
        calibrated=True,
    )
    quote = Quote(symbol="EUR_USD", time=now, bid="1.0999", ask="1.1001", source="test")
    state = RiskState(D(10000), D(10000), D(10000), D(10000), D(10000), reconciled=True, account_fresh=True)
    rules = InstrumentRules("EUR_USD", D(".00001"), D(1), D(1), D(".0003"))
    return candidate, quote, state, rules, Settings(_env_file=None), now


def test_known_sizing():
    s, q, state, r, settings, now = setup_risk()
    result = approve(s, q, state, r, settings, now)
    assert result.approved
    assert result.units == 4844  # floor(50 / (0.01+0.0001+0.0002+0.00002))
    assert result.planned_risk == D("49.99008")
    assert result.expected_value == D(".01953")


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"equity": D(9799)}, "DAILY_LOSS_LIMIT"),
        ({"equity": D(9400), "day_start": D(9400)}, "WEEKLY_LOSS_LIMIT"),
        ({"reconciled": False}, "ACCOUNT_NOT_RECONCILED"),
        ({"suspended": True}, "TRADING_SUSPENDED"),
        ({"free_margin": D(1)}, "INSUFFICIENT_MARGIN"),
        ({"open_positions": 3}, "POSITION_LIMIT"),
        ({"consecutive_losses": 5}, "CONSECUTIVE_LOSS_LIMIT"),
    ],
)
def test_risk_blocks(change, reason):
    s, q, state, r, settings, now = setup_risk()
    result = approve(s, q, replace(state, **change), r, settings, now)
    assert not result.approved and reason in result.reasons


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"stop": D("1.11")}, "INVALID_PROTECTIVE_LEVELS"),
        ({"probability": None}, "NO_VALIDATED_CALIBRATED_MODEL"),
        ({"calibrated": False}, "NO_VALIDATED_CALIBRATED_MODEL"),
        ({"probability": D(".6")}, "INVALID_OUTCOME_PROBABILITIES"),
    ],
)
def test_candidate_rejections(change, reason):
    s, q, state, r, settings, now = setup_risk()
    result = approve(s.model_copy(update=change), q, state, r, settings, now)
    assert reason in result.reasons


def test_stale_quote_blocks():
    s, q, state, r, settings, now = setup_risk()
    result = approve(s, q.model_copy(update={"time": now - timedelta(minutes=1)}), state, r, settings, now)
    assert "STALE_OR_FUTURE_QUOTE" in result.reasons


def test_probability_bounds_rechecked_at_risk_boundary():
    s, q, state, r, settings, now = setup_risk()
    forged = s.model_copy(
        update={"probability": D(".85"), "probability_stop": D("-.1"), "probability_timeout": D(".25")}
    )
    result = approve(forged, q, state, r, settings, now)
    assert "INVALID_OUTCOME_PROBABILITIES" in result.reasons


def test_slippage_cannot_place_fill_outside_protection():
    s, q, state, r, settings, now = setup_risk()
    result = approve(s, q, state, replace(r, slippage=D(".1")), settings, now)
    assert not result.approved and "SLIPPAGE_INVALIDATES_PROTECTION" in result.reasons
