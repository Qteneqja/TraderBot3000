from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from app.backtesting.portfolio import run_portfolio
from app.backtesting.simulator import FillAssumptions
from app.machine_learning.candidate_training import CANDIDATE_FEATURES, prediction_features
from app.machine_learning.policy import risk_contract
from app.machine_learning.registry import ModelUnavailable, load_verified
from app.market_data.fingerprint import verified_training_rows
from app.market_data.store import load_candles
from app.models.tables import Instrument, ModelVersion
from app.risk_management.engine import InstrumentRules


def evaluate_registered(
    db, version_id, root: Path, settings, partition="validation", cost_multiplier=Decimal(1)
):
    if not cost_multiplier.is_finite() or cost_multiplier < 1:
        raise ValueError("Cost stress multiplier must be finite and at least one")
    if partition not in ("validation", "test"):
        raise ValueError("Only held-out validation or test partitions may be evaluated")
    version = db.get(ModelVersion, version_id)
    if not version:
        raise ModelUnavailable("Unknown model version")
    model = load_verified(version, root)
    metadata = version.metadata_json
    start, end = [datetime.fromisoformat(t) for t in metadata["partitions"][partition]]
    if start < datetime.fromisoformat(metadata["training_cutoff"]):
        raise ModelUnavailable("Evaluation overlaps model fitting/calibration outcomes")
    rows = load_candles(db, metadata["symbol"], metadata["timeframe"], metadata["source"], 1_000_000)
    rows = verified_training_rows(rows, metadata.get("input_candles"))
    rows = [c for c in rows if c.time <= end + timedelta(seconds=metadata["timeframe"] * metadata["horizon"])]
    instrument = db.get(Instrument, metadata["symbol"])
    if not rows or instrument is None:
        raise ValueError("Model's source dataset or instrument is unavailable")
    rules = InstrumentRules(
        instrument.symbol,
        instrument.tick_size,
        instrument.unit_step,
        instrument.min_units,
        instrument.max_spread,
    )
    costs = FillAssumptions(**{k: Decimal(v) * cost_multiplier for k, v in metadata["costs"].items()})

    def predict(candidate, quote):
        values = model.predict_proba(
            pd.DataFrame([prediction_features(candidate, quote)])[CANDIDATE_FEATURES]
        )[0]
        if (
            not np.isfinite(values).all()
            or (values < 0).any()
            or (values > 1).any()
            or not np.isclose(values.sum(), 1)
        ):
            raise ModelUnavailable("Invalid model probability output")
        return {
            "model_version": version.id,
            "probability_stop": float(values[0]),
            "probability_target": float(values[1]),
            "probability_timeout": float(values[2]),
        }

    report = run_portfolio(
        rows,
        rules,
        settings,
        costs,
        predict,
        strategy=metadata["strategy"],
        horizon=metadata["horizon"],
        start=start,
        end=end,
    )
    report.update(
        {
            "model_version": version.id,
            "partition": partition,
            "candidate_start": start.isoformat(),
            "candidate_end": end.isoformat(),
            "risk_settings": risk_contract(settings),
            "cost_multiplier": str(cost_multiplier),
            "promotion_status": "UNCHANGED",
            "dataset_sha256": metadata["dataset_sha256"],
            "input_candles": metadata["input_candles"],
            "input_candles_verified": True,
        }
    )
    return report
