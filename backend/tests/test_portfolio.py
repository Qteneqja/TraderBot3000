from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D

from app.backtesting.portfolio import run_portfolio
from app.backtesting.simulator import FillAssumptions
from app.core.config import Settings
from app.market_data.fixtures import demo_candles
from app.risk_management.engine import InstrumentRules
from app.schemas.domain import Candidate


def inputs():
    candles = [
        c.model_copy(update={"open": D(100), "close": D(100), "high": D("100.1"), "low": D("99.9")})
        for c in demo_candles(count=85)
    ]
    rules = InstrumentRules("EUR_USD", D(".01"), D(1), D(1), D(".1"))

    def propose(i, bar):
        return [
            Candidate(
                id=str(i),
                symbol=bar.symbol,
                strategy="test-only",
                direction="LONG",
                time=bar.time,
                expires_at=bar.time + timedelta(minutes=5),
                entry=D(100),
                stop=D(99),
                target=D(103),
                timeframe=300,
                regime="BULLISH_TREND",
                features={},
                invalidation="test",
                source="fixture",
            )
        ]

    # Explicit test fixture probabilities, never a production model or claimed confidence.
    def prediction(s, q):
        return {
            "model_version": "TEST-ONLY",
            "probability_target": 0.85,
            "probability_stop": 0.1,
            "probability_timeout": 0.05,
        }

    return candles, rules, propose, prediction


def test_portfolio_reuses_risk_and_accounts_for_costs():
    candles, rules, propose, predict = inputs()
    report = run_portfolio(
        candles,
        rules,
        Settings(_env_file=None),
        FillAssumptions(D(".02"), D(".01"), D(".001")),
        predict,
        proposer=propose,
        horizon=4,
    )
    assert report["maximum_open_positions"] <= 3
    assert report["trades"] and all(D(t["pnl"]) < 0 for t in report["trades"])
    assert report["rejections"]["CONSECUTIVE_LOSS_LIMIT"] > 0
    assert report["metrics"]["max_drawdown"] > 0
    final_balance = D(report["metrics"]["equity_curve"][-1]["balance"])
    assert final_balance == D(10000) + sum(D(t["pnl"]) for t in report["trades"])
    assert report["execution_authorized"] is False


def test_unvalidated_predictions_do_not_force_activity():
    candles, rules, propose, _ = inputs()
    report = run_portfolio(
        candles,
        rules,
        Settings(_env_file=None),
        FillAssumptions(D(".02"), D(".01")),
        lambda s, q: None,
        proposer=propose,
    )
    assert report["trades"] == []
    assert report["rejections"]["NO_VALIDATED_CALIBRATED_MODEL"] == 25


def test_margin_caps_size_instead_of_exceeding_budget():
    from test_risk import setup_risk

    from app.risk_management.engine import approve

    s, q, state, rules, settings, now = setup_risk()
    decision = approve(s, q, replace(state, free_margin=D(100)), rules, settings, now)
    assert decision.approved and decision.units == 90
    assert decision.planned_risk < state.equity * settings.risk_per_trade
