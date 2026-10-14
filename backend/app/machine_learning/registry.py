"""Trusted local artifact verification and explicit shadow deployment; never automatic promotion."""

import hashlib
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.machine_learning.candidate_training import CANDIDATE_FEATURES, EVENT_SCHEMA, prediction_features
from app.models.tables import Event, ModelPrediction, ModelVersion


class ModelUnavailable(RuntimeError):
    pass


def matches(metadata, candidate):
    return all(
        metadata.get(key) == getattr(candidate, key) for key in ("symbol", "strategy", "timeframe", "source")
    )


def artifact_path(metadata, root: Path):
    root = root.resolve()
    filename = metadata.get("artifact_filename", "")
    if not filename or Path(filename).name != filename:
        raise ModelUnavailable("Artifact must be a filename within the configured trusted directory")
    path = (root / filename).resolve()
    if path.parent != root or path.suffix != ".joblib" or not path.is_file():
        raise ModelUnavailable("Artifact is missing or outside the trusted directory")
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata.get("artifact_sha256"):
        raise ModelUnavailable("Artifact checksum mismatch; inference blocked")
    return path


def load_verified(version, root):
    metadata = version.metadata_json
    if metadata.get("version") != version.id:
        raise ModelUnavailable("Registry identifier differs from artifact version")
    if metadata.get("event_schema") != EVENT_SCHEMA or metadata.get("features") != CANDIDATE_FEATURES:
        raise ModelUnavailable("Model event/feature schema is incompatible")
    path = artifact_path(metadata, root)
    # Local artifact directory and registry are operator-controlled; hashes are integrity, not trust signatures.
    bundle = joblib.load(path)
    embedded = bundle["report"]
    registered_evidence = {
        k: v for k, v in metadata.items() if k not in ("artifact_sha256", "artifact_filename")
    }
    if embedded != registered_evidence:
        raise ModelUnavailable("Embedded model metadata differs from registered evidence")
    if list(bundle["model"].classes_) != [0, 1, 2]:
        raise ModelUnavailable("Model outcome classes do not match stop/target/timeout")
    return bundle["model"]


def deploy_shadow(db, version_id, root: Path):
    version = db.get(ModelVersion, version_id)
    if not version or version.status not in ("EXPERIMENTAL", "SHADOW", "RETIRED"):
        raise ModelUnavailable("Only experimental, shadow or retired research models can enter shadow mode")
    load_verified(version, root)
    for other in db.scalars(select(ModelVersion).where(ModelVersion.status == "SHADOW")).all():
        if other.id != version.id and all(
            other.metadata_json.get(k) == version.metadata_json.get(k)
            for k in ("symbol", "strategy", "timeframe", "source")
        ):
            other.status = "RETIRED"
    version.status = "SHADOW"
    db.add(Event(kind="model_shadow_deployed", detail={"version": version.id, "execution_allowed": False}))
    db.commit()
    return version.id


def shadow_predict(db, candidate, quote, root: Path):
    if quote.symbol != candidate.symbol or quote.source != candidate.source:
        raise ModelUnavailable("Quote and candidate identities differ")
    records = [
        v
        for v in db.scalars(select(ModelVersion).where(ModelVersion.status == "SHADOW")).all()
        if matches(v.metadata_json, candidate)
    ]
    if not records:
        return None
    if len(records) != 1:
        raise ModelUnavailable("Multiple shadow models match this scope")
    version = records[0]
    prediction = predict_version(version, candidate, quote, load_verified(version, root))
    return prediction | {
        "status": "SHADOW",
        "execution_allowed": False,
        "calibration_status": "EXPERIMENTAL_NOT_EXECUTION_VALIDATED",
    }


def predict_version(version, candidate, quote, model):
    if (
        not matches(version.metadata_json, candidate)
        or quote.symbol != candidate.symbol
        or quote.source != candidate.source
    ):
        raise ModelUnavailable("Prediction scope mismatch")
    cutoff = version.metadata_json.get("training_cutoff")
    if cutoff is None or pd.Timestamp(candidate.time) < pd.Timestamp(cutoff):
        raise ModelUnavailable("Prediction precedes the model's final calibration outcome")
    features = pd.DataFrame([prediction_features(candidate, quote)])[CANDIDATE_FEATURES]
    if not np.isfinite(features.to_numpy()).all():
        raise ModelUnavailable("Non-finite inference features")
    probabilities = np.asarray(model.predict_proba(features)[0], dtype=float)
    if (
        probabilities.shape != (3,)
        or not np.isfinite(probabilities).all()
        or (probabilities < 0).any()
        or (probabilities > 1).any()
        or not np.isclose(probabilities.sum(), 1)
    ):
        raise ModelUnavailable("Invalid model output probabilities")
    return {
        "model_version": version.id,
        "probability_stop": float(probabilities[0]),
        "probability_target": float(probabilities[1]),
        "probability_timeout": float(probabilities[2]),
        "event_schema": EVENT_SCHEMA,
    }


def record_prediction(db, candidate, quote, prediction, mode="SHADOW"):
    if mode not in ("SHADOW", "SHADOW_REPLAY") or prediction["execution_allowed"]:
        raise ModelUnavailable("Only non-executing shadow predictions can be recorded here")
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    db.execute(
        insert(ModelPrediction)
        .values(
            model_id=prediction["model_version"],
            candidate_id=candidate.id,
            symbol=candidate.symbol,
            time=candidate.time,
            quote_time=quote.time,
            mode=mode,
            prediction=prediction,
            candidate=candidate.model_dump(mode="json"),
        )
        .on_conflict_do_nothing(index_elements=["model_id", "candidate_id"])
    )
    db.commit()
