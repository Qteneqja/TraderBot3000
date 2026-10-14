from datetime import timedelta
from decimal import Decimal as D

import numpy as np
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.backtesting.simulator import FillAssumptions
from app.core.config import Settings
from app.database.bootstrap import bootstrap
from app.database.session import Base, make_engine
from app.execution.paper import reconcile, submit
from app.machine_learning.candidate_training import dataset, purged_partitions, train_candidates
from app.machine_learning.registry import (
    ModelUnavailable,
    deploy_shadow,
    load_verified,
    record_prediction,
    shadow_predict,
)
from app.market_data.fixtures import demo_candles
from app.models.tables import ModelPrediction, ModelVersion, OrderRow
from app.schemas.domain import Quote
from app.strategies.registry import evaluate


@pytest.fixture(scope="module")
def experiment(tmp_path_factory):
    root = tmp_path_factory.mktemp("shadow-models")
    candles = demo_candles(count=2000)
    report = train_candidates(candles, D(".00001"), "trend", FillAssumptions(D(".00002"), D(".00001")), root)
    candidate = None
    for n in range(len(candles), 1800, -1):
        found = evaluate(candles[:n], candles[n - 1].time + timedelta(seconds=300), D(".00001"), ["trend"])
        if found:
            candidate = found[0]
            break
    assert candidate is not None
    quote = Quote(
        symbol=candidate.symbol,
        source="fixture",
        time=candidate.time,
        bid=candidate.entry - D(".00001"),
        ask=candidate.entry + D(".00001"),
    )
    return root, report, candidate, quote


def test_candidate_labels_use_shared_proposals_and_purged_time():
    candles = demo_candles(count=1200)
    samples, _ = dataset(candles, D(".00001"), "trend", FillAssumptions(D(".00002"), D(".00001")))
    parts = purged_partitions(samples)
    for before, after in zip(parts, parts[1:]):
        assert samples.iloc[before].label_end.max() < samples.iloc[after].time.min()
    first = samples.iloc[0]
    candidates = evaluate(candles, first.time.to_pydatetime(), D(".00001"), ["trend"])
    assert first.candidate_id == candidates[0].id


def test_shadow_deployment_predicts_but_cannot_execute(experiment):
    root, report, candidate, quote = experiment
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        bootstrap(db)
        version = ModelVersion(id=report["version"], metadata_json=report, status="EXPERIMENTAL")
        db.add(version)
        db.commit()
        assert deploy_shadow(db, version.id, root) == version.id
        prediction = shadow_predict(db, candidate, quote, root)
        assert prediction["execution_allowed"] is False
        record_prediction(db, candidate, quote, prediction)
        record_prediction(db, candidate, quote, prediction)
        assert db.scalar(select(func.count()).select_from(ModelPrediction)) == 1
        assert np.isclose(
            sum(prediction[k] for k in ("probability_stop", "probability_target", "probability_timeout")), 1
        )
        db.rollback()
        assert reconcile(db, candidate.time)
        # Even malicious caller flags cannot promote a SHADOW registry entry.
        forged = candidate.model_copy(
            update={
                "model_version": version.id,
                "calibrated": True,
                "probability": D(".99"),
                "probability_stop": D(".01"),
                "probability_timeout": D(0),
                "shadow_prediction": prediction,
            }
        )
        db.rollback()
        assert submit(db, forged, quote, Settings(_env_file=None), candidate.time) == "REJECTED"
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 0


def test_checksum_checked_before_deserialization(experiment, monkeypatch):
    root, report, _, _ = experiment

    def forbidden(*args, **kwargs):
        raise AssertionError("Corrupted artifacts must not be deserialized")

    monkeypatch.setattr("app.machine_learning.registry.joblib.load", forbidden)
    version = ModelVersion(
        id=report["version"], status="SHADOW", metadata_json=report | {"artifact_sha256": "0" * 64}
    )
    with pytest.raises(ModelUnavailable, match="checksum"):
        load_verified(version, root)


def test_prediction_cannot_use_future_calibration(experiment):
    root, report, candidate, quote = experiment
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(ModelVersion(id=report["version"], metadata_json=report, status="SHADOW"))
        db.commit()
        old = candidate.model_copy(update={"time": candidate.time - timedelta(days=100)})
        with pytest.raises(ModelUnavailable, match="precedes"):
            shadow_predict(db, old, quote, root)


def test_legacy_directional_artifact_cannot_be_deployed():
    version = ModelVersion(id="legacy", metadata_json={"version": "legacy"}, status="EXPERIMENTAL")
    with pytest.raises(ModelUnavailable, match="incompatible"):
        load_verified(version, __import__("pathlib").Path("."))


def test_registry_cannot_rewrite_calibration_evidence(experiment):
    root, report, _, _ = experiment
    version = ModelVersion(
        id=report["version"],
        status="SHADOW",
        metadata_json=report | {"training_cutoff": "2000-01-01T00:00:00+00:00"},
    )
    with pytest.raises(ModelUnavailable, match="metadata differs"):
        load_verified(version, root)


def test_candle_manifest_detects_changes_but_allows_new_history():
    from app.market_data.fingerprint import candle_manifest, verified_training_rows

    candles = demo_candles(count=100)
    expected = candle_manifest(candles[:90])
    assert len(verified_training_rows(candles, expected)) == 90
    # SQL Numeric scale does not change financial values or dataset identity.
    scaled = [c.model_copy(update={"volume": c.volume.quantize(D(".0000000001"))}) for c in candles]
    assert candle_manifest(scaled[:90]) == expected
    changed = candles.copy()
    changed[1] = changed[1].model_copy(update={"volume": changed[1].volume + 1})
    with pytest.raises(ValueError, match="changed or are missing"):
        verified_training_rows(changed, expected)
    with pytest.raises(ValueError, match="changed or are missing"):
        verified_training_rows(candles[1:], expected)
