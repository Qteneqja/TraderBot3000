from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
import test_shadow
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.bootstrap import bootstrap
from app.database.session import Base, make_engine
from app.machine_learning.assessment import assess_model, daily_uncertainty, partition_checks
from app.machine_learning.policy import acceptance_policy, digest
from app.models.tables import ModelReview, ModelVersion, OrderRow

experiment = test_shadow.experiment


def research_fixture():
    """Explicit acceptance-test data, never model performance evidence."""
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    trades = [
        {"exit_time": (start + timedelta(days=day)).isoformat(), "pnl": str(pnl)}
        for day in range(61)
        for pnl in (3, -0.5)
    ]
    return {
        "candidate_start": start.isoformat(),
        "candidate_end": (start + timedelta(days=60)).isoformat(),
        "trades": trades,
        "metrics": {
            "trades": len(trades),
            "net_return": 0.015,
            "profit_factor": 6,
            "expectancy": 1.25,
            "max_drawdown": 0.01,
            "equity_curve": [],
            "drawdown_curve": [],
        },
    }


def test_policy_is_hashed_and_bound_to_risk_settings():
    settings = Settings(_env_file=None)
    policy = acceptance_policy(settings)
    assert policy["sha256"] == digest({k: v for k, v in policy.items() if k != "sha256"})
    assert (
        acceptance_policy(settings.model_copy(update={"max_open_positions": 1}))["sha256"] != policy["sha256"]
    )
    assert policy["minimum_partition_trades"] == 100


def test_synthetic_model_is_rejected_and_assessment_is_idempotent(experiment):
    root, metadata, _, _ = experiment
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bootstrap(db)
        db.add(ModelVersion(id=metadata["version"], status="SHADOW", metadata_json=metadata))
        db.commit()
        first = assess_model(db, metadata["version"], root, Settings(_env_file=None))
        second = assess_model(db, metadata["version"], root, Settings(_env_file=None))
        assert first == second
        assert first["checks"]["POLICY_PREDECLARED_AND_UNCHANGED"]
        assert first["status"] == "REJECTED" and "REAL_MARKET_SOURCE" in first["reasons"]
        assert first["partitions"] == {} and first["execution_allowed"] is False
        assert db.scalar(select(func.count()).select_from(ModelReview)) == 1
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 0
        assert db.get(ModelVersion, metadata["version"]).status == "SHADOW"
        assert db.get(ModelVersion, metadata["version"]).metadata_json == metadata


def test_changed_policy_cannot_reuse_old_evidence(experiment):
    root, metadata, _, _ = experiment
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(ModelVersion(id=metadata["version"], status="SHADOW", metadata_json=metadata))
        db.commit()
        settings = Settings(_env_file=None, max_open_positions=1)
        report = assess_model(db, metadata["version"], root, settings)
        assert "POLICY_PREDECLARED_AND_UNCHANGED" in report["reasons"]
        assert report["execution_allowed"] is False


def test_circular_bootstrap_is_reproducible_and_retains_zero_activity_days():
    report, policy = research_fixture(), acceptance_policy()
    assert daily_uncertainty(report, policy) == daily_uncertainty(report, policy)
    report["trades"] = []
    result = daily_uncertainty(report, policy)
    assert result["days"] == 61 and result["active_days"] == 0
    assert result["lower_mean_daily_pnl"] == result["upper_mean_daily_pnl"] == 0


def test_research_gate_requires_economics_baseline_and_stressed_activity():
    report, policy = research_fixture(), acceptance_policy()
    calibration = {"target_calibration_error": 0.01, "multiclass_brier": 0.2}
    baseline = {"multiclass_brier": 0.3}
    good = partition_checks(report, report, calibration, baseline, policy)
    assert all(good["checks"].values())
    stress = deepcopy(report)
    stress["metrics"].update(net_return=-0.01, trades=0)
    report["metrics"].update(net_return=-0.01, expectancy=-1)
    bad = partition_checks(report, stress, calibration, baseline, policy)
    assert not bad["checks"]["POSITIVE_NET_RETURN"]
    assert not bad["checks"]["POSITIVE_EXPECTANCY"]
    assert not bad["checks"]["STRESSED_ACTIVITY"]
    assert not bad["checks"]["STRESSED_NET_RETURN"]


def test_nonfinite_evidence_cannot_be_attested():
    report = research_fixture()
    report["metrics"]["net_return"] = float("nan")
    with pytest.raises(ValueError):
        partition_checks(
            report,
            report,
            {"target_calibration_error": 0.01, "multiclass_brier": 0.2},
            {"multiclass_brier": 0.3},
            acceptance_policy(),
        )


def test_passing_research_checks_never_promote_a_model(monkeypatch):
    policy = acceptance_policy()
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    metadata = {
        "source": "coinbase",
        "acceptance_policy": policy,
        "input_candles": {"start": "2025-01-01T00:00:00+00:00", "end": "2026-01-01T00:00:00+00:00"},
        "sample_counts": {"calibration": 500},
        "validation": {"target_calibration_error": 0.01, "multiclass_brier": 0.2},
        "test": {"target_calibration_error": 0.01, "multiclass_brier": 0.2},
        "class_frequency_baseline": {p: {"multiclass_brier": 0.3} for p in ("validation", "test")},
    }
    # Fake evidence only exercises orchestration. Production always verifies trusted artifacts.
    calls = []
    monkeypatch.setattr("app.machine_learning.assessment.load_verified", lambda *args: None)

    def replay(db, version, root, settings, partition, cost_multiplier=1):
        calls.append((partition, int(cost_multiplier)))
        return research_fixture()

    monkeypatch.setattr("app.machine_learning.assessment.evaluate_registered", replay)
    with Session(engine) as db:
        db.add(ModelVersion(id="TEST-ONLY", status="EXPERIMENTAL", metadata_json=metadata))
        db.commit()
        report = assess_model(db, "TEST-ONLY", None, Settings(_env_file=None))
        assert report["status"] == "RESEARCH_GATES_PASSED"
        assert not report["execution_allowed"] and report["remaining_gates"]
        assert db.get(ModelVersion, "TEST-ONLY").status == "EXPERIMENTAL"
        assert calls == [("validation", 1), ("validation", 2), ("test", 1), ("test", 2)]


def test_registered_portfolio_replay_applies_stress_costs(tmp_path):
    from decimal import Decimal

    from app.backtesting.registered import evaluate_registered
    from app.backtesting.simulator import FillAssumptions
    from app.machine_learning.candidate_training import train_candidates
    from app.market_data.fixtures import demo_candles
    from app.market_data.store import insert_candles, load_candles

    root = tmp_path / "stored-model"
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bootstrap(db)
        insert_candles(db, demo_candles(count=2000), datetime.now(timezone.utc))
        stored = load_candles(db, "EUR_USD", 300, "fixture", 2000)
        metadata = train_candidates(
            stored, Decimal(".00001"), "trend", FillAssumptions(Decimal(".00002"), Decimal(".00001")), root
        )
        db.add(ModelVersion(id=metadata["version"], status="EXPERIMENTAL", metadata_json=metadata))
        db.commit()
        report = evaluate_registered(
            db, metadata["version"], root, Settings(_env_file=None), cost_multiplier=Decimal(2)
        )
        assert report["costs"]["spread"] == "0.00004"
        assert report["costs"]["slippage"] == "0.00002"
        assert report["cost_multiplier"] == "2" and report["input_candles_verified"]
        assert report["execution_authorized"] is False
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 0
