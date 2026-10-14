"""Deployment orchestration with explicitly mocked positive research, never market evidence."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path
from threading import Barrier

import numpy as np
import pytest
import test_paper_faults
import test_shadow
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_assessment import research_fixture

from app.execution.paper import monitor, submit
from app.indicators.features import FEATURES
from app.machine_learning.assessment import assess_model
from app.machine_learning.deployment import activate, authorize_candidate, deactivate, rollback, scope_key
from app.machine_learning.policy import acceptance_policy
from app.machine_learning.registry import ModelUnavailable, load_verified
from app.market_data.fixtures import demo_candles
from app.market_data.store import insert_candles, load_candles, save_quote
from app.models.tables import (
    ModelReview,
    ModelVersion,
    OrderRow,
    PaperDeployment,
    PaperDeploymentSlot,
    SignalRow,
)
from app.strategies.registry import evaluate

store = test_paper_faults.store
experiment = test_shadow.experiment


class TestEstimator:
    __test__ = False

    def predict_proba(self, features):
        return np.array([[0.08, 0.9, 0.02]])


@pytest.fixture
def deployment_store(store, monkeypatch):
    engine, candidate, quote, settings, now = store
    settings = settings.model_copy(update={"demo_mode": False})
    candidate = candidate.model_copy(update={"source": "oanda", "features": {key: 0.1 for key in FEATURES}})
    quote = quote.model_copy(update={"source": "oanda"})
    metadata = {
        "version": "TEST-ONLY-POSITIVE-EVIDENCE",
        "symbol": candidate.symbol,
        "source": "oanda",
        "strategy": candidate.strategy,
        "timeframe": 300,
        "horizon": 12,
        "tick": ".00001",
        "artifact_sha256": "test-artifact-hash",
        "dataset_sha256": "test-data-hash",
        "training_cutoff": (now - timedelta(days=400)).isoformat(),
        "costs": {"slippage": ".00001", "spread": ".0002", "fee_rate": "0", "financing_per_bar": "0"},
        "acceptance_policy": acceptance_policy(settings),
        "input_candles": {
            "start": (now - timedelta(days=800)).isoformat(),
            "end": (now - timedelta(days=400)).isoformat(),
        },
        "sample_counts": {"calibration": 500},
        "validation": {"target_calibration_error": 0.01, "multiclass_brier": 0.2},
        "test": {"target_calibration_error": 0.01, "multiclass_brier": 0.2},
        "class_frequency_baseline": {p: {"multiclass_brier": 0.3} for p in ("validation", "test")},
    }
    metadata["coverage"] = {"research_ready": True, "input_candles": metadata["input_candles"], "session_coverage": 1}
    monkeypatch.setattr("app.machine_learning.assessment.load_verified", lambda *args: TestEstimator())
    monkeypatch.setattr(
        "app.machine_learning.assessment.evaluate_registered", lambda *args: research_fixture()
    )
    monkeypatch.setattr("app.machine_learning.deployment.load_verified", lambda *args: TestEstimator())
    monkeypatch.setattr("app.machine_learning.deployment.verified_training_rows", lambda *args: [])
    monkeypatch.setattr("app.machine_learning.deployment.evaluate", lambda *args: [candidate])
    with Session(engine) as db:
        for name in ("first", "second"):
            version_id = "TEST-ONLY-" + name
            db.add(
                ModelVersion(
                    id=version_id, status="EXPERIMENTAL", metadata_json=metadata | {"version": version_id}
                )
            )
        db.commit()
        reviews = {
            name: assess_model(db, "TEST-ONLY-" + name, Path("."), settings)["review_id"]
            for name in ("first", "second")
        }
    return engine, candidate, quote, settings, now, reviews


def deploy(db, settings, now, reviews, name="first"):
    return activate(
        db,
        "TEST-ONLY-" + name,
        reviews[name],
        Path("."),
        settings,
        "test-operator",
        "test trial",
        now - timedelta(seconds=1),
    )


def test_activation_rollback_and_retirement_preserve_artifacts(deployment_store):
    engine, _, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        first = deploy(db, settings, now, reviews)
        assert deploy(db, settings, now, reviews) == first
        second = deploy(db, settings, now, reviews, "second")
        with pytest.raises(ModelUnavailable, match="no longer current"):
            deactivate(db, first, "tester", "stale request")
        restored = rollback(db, first, Path("."), settings, "tester", "restore previous", now)
        row = db.get(PaperDeployment, restored)
        assert row.rollback_of == first and row.previous_id == second
        assert db.get(PaperDeploymentSlot, ("PAPER", row.scope_key)).deployment_id == restored
        assert db.get(ModelVersion, "TEST-ONLY-first").status == "EXPERIMENTAL"
        db.rollback()
        assert rollback(db, first, Path("."), settings, "tester", "retry response", now) == restored
        deactivate(db, restored, "tester", "end trial")
        assert db.scalar(select(PaperDeploymentSlot.deployment_id)) is None


def test_concurrent_activation_has_one_slot_and_one_audit_deployment(deployment_store):
    engine, _, _, settings, now, reviews = deployment_store
    barrier = Barrier(4)

    def activate_once(_):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return deploy(db, settings, now, reviews)

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(activate_once, range(4)))
    assert len(set(ids)) == 1
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(PaperDeployment)) == 1
        assert db.scalar(select(func.count()).select_from(PaperDeploymentSlot)) == 1


@pytest.mark.parametrize("change", ["risk", "costs", "review", "artifact", "source", "demo"])
def test_activation_rejects_changed_or_unqualified_evidence(deployment_store, monkeypatch, change):
    engine, _, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        if change == "risk":
            settings = settings.model_copy(update={"max_open_positions": 1})
        elif change == "costs":
            settings = settings.model_copy(update={"paper_fee_rate": D(".001")})
        elif change == "demo":
            settings = settings.model_copy(update={"demo_mode": True})
        elif change == "artifact":

            def corrupt(*args):
                raise ModelUnavailable("Artifact checksum mismatch")

            monkeypatch.setattr("app.machine_learning.deployment.load_verified", corrupt)
        elif change == "source":
            model = db.get(ModelVersion, "TEST-ONLY-first")
            model.metadata_json = model.metadata_json | {"source": "fixture"}
            db.commit()
        else:
            review = db.get(ModelReview, reviews["first"])
            review.report = review.report | {"status": "REJECTED"}
            db.commit()
        with pytest.raises(ModelUnavailable):
            deploy(db, settings, now, reviews)
        assert db.scalar(select(func.count()).select_from(PaperDeployment)) == 0


def test_runtime_recomputes_confidence_and_preserves_idempotency(deployment_store):
    engine, candidate, quote, settings, now, reviews = deployment_store
    with Session(engine) as db:
        deployment = deploy(db, settings, now, reviews)
        forged = candidate.model_copy(update={"probability": D(".999"), "stop": D(".01"), "features": {}})
        assert submit(db, forged, quote, settings, now) == "FILLED"
        assert submit(db, forged, quote, settings, now) == "FILLED"
        signal = db.get(SignalRow, candidate.id)
        order = db.get(OrderRow, candidate.id)
        assert signal.payload["probability"] == "0.9" and order.stop == candidate.stop
        assert order.execution["deployment_id"] == deployment
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 1


def test_runtime_change_and_old_active_flag_cannot_authorize(deployment_store):
    engine, candidate, quote, settings, now, reviews = deployment_store
    with Session(engine) as db:
        # The legacy ACTIVE/execution_validated flag cannot authorize the production gateway.
        assert submit(db, candidate, quote, settings, now) == "REJECTED"
        deploy(db, settings, now, reviews)
        candidate = candidate.model_copy(update={"id": "changed-settings"})
        changed = settings.model_copy(update={"max_quote_age_seconds": 10})
        assert submit(db, candidate, quote, changed, now) == "REJECTED"
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 0


def test_rollback_revalidates_and_failed_commit_preserves_current(deployment_store):
    engine, _, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        first = deploy(db, settings, now, reviews)
        second = deploy(db, settings, now, reviews, "second")
        review = db.get(ModelReview, reviews["first"])
        saved = deepcopy(review.report)
        review.report = saved | {"checks": {"tampered": False}}
        db.commit()
        with pytest.raises(ModelUnavailable):
            rollback(db, first, Path("."), settings, "tester", "must fail", now)
        assert db.scalar(select(PaperDeploymentSlot.deployment_id)) == second
        db.rollback()
        review = db.get(ModelReview, reviews["first"])
        review.report = saved
        db.commit()

        def crash():
            raise RuntimeError("commit fault")

        db.commit = crash
        with pytest.raises(RuntimeError, match="commit fault"):
            rollback(db, first, Path("."), settings, "tester", "crash test", now)
    with Session(engine) as db:
        assert db.scalar(select(PaperDeploymentSlot.deployment_id)) == second
        assert db.scalar(select(func.count()).select_from(PaperDeployment)) == 2


def test_deactivation_blocks_entries_but_existing_protection_still_closes(deployment_store):
    engine, candidate, quote, settings, now, reviews = deployment_store
    with Session(engine) as db:
        current = deploy(db, settings, now, reviews)
        assert submit(db, candidate, quote, settings, now) == "FILLED"
        deactivate(db, current, "tester", "end new entries")
        assert (
            submit(db, candidate.model_copy(update={"id": "after-deactivation"}), quote, settings, now)
            == "REJECTED"
        )
        closing = quote.model_copy(
            update={
                "time": now + timedelta(seconds=1),
                "bid": candidate.target,
                "ask": candidate.target + D(".0001"),
            }
        )
        save_quote(db, closing, closing.time)
        monitor(db, settings, closing.time)
        assert db.get(OrderRow, candidate.id).state == "CLOSED"


def test_real_artifact_inference_reconstructs_causal_features(store, experiment, monkeypatch):
    """Mock only prior eligibility; use a real synthetic artifact and actual stored-candle inference."""
    engine, _, _, settings, now = store
    root, report, _, quote = experiment
    settings = settings.model_copy(update={"model_artifact_dir": str(root)})
    with Session(engine) as db:
        insert_candles(db, demo_candles(count=2000), now)
        rows = load_candles(db, quote.symbol, 300, "fixture")
        candidate = next(
            p
            for end in range(len(rows), 60, -1)
            for p in evaluate(rows[:end], rows[end - 1].time + timedelta(seconds=300), D(".00001"), ["trend"])
        )
        quote = quote.model_copy(
            update={
                "time": candidate.time,
                "bid": candidate.entry - D(".00001"),
                "ask": candidate.entry + D(".00001"),
            }
        )
        version = ModelVersion(id=report["version"], status="EXPERIMENTAL", metadata_json=report)
        db.add(version)
        db.flush()
        db.add(ModelReview(id="TEST-ELIGIBILITY", model_id=version.id, status="TEST", report={}))
        db.flush()
        deployment = PaperDeployment(
            account_id="PAPER",
            scope_key=scope_key(report),
            model_id=version.id,
            review_id="TEST-ELIGIBILITY",
            operator="test",
            reason="isolated inference test",
            contract={},
            created_at=candidate.time - timedelta(seconds=1),
        )
        db.add(deployment)
        db.flush()
        db.add(
            PaperDeploymentSlot(account_id="PAPER", scope_key=scope_key(report), deployment_id=deployment.id)
        )
        db.commit()
        # Eligibility is mocked only here because synthetic data must never pass production review.
        monkeypatch.setattr(
            "app.machine_learning.deployment.validate_evidence",
            lambda *args: (version, load_verified(version, root), {}),
        )
        forged = candidate.model_copy(update={"probability": D(".999"), "features": {}, "stop": D(".01")})
        inferred = authorize_candidate(db, forged, quote, settings, candidate.time)
        assert inferred.calibrated and inferred.stop == candidate.stop
        assert inferred.features == candidate.features and inferred.probability != D(".999")
        assert inferred.deployment_id == deployment.id
        db.rollback()
        # Corruption is still checked before every inference even with mocked research eligibility.
        version.metadata_json = report | {"artifact_sha256": "0" * 64}
        db.commit()
        assert not authorize_candidate(db, forged, quote, settings, candidate.time).calibrated
