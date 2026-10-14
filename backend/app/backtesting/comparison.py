"""Research-only common-period incumbent replay. Never adjusts execution or approvals."""

from datetime import datetime, timedelta
from pathlib import Path

from app.backtesting.portfolio import run_portfolio
from app.machine_learning.registry import load_verified, predict_version
from app.market_data.fingerprint import candle_manifest, verified_training_rows
from app.market_data.store import load_candles
from app.models.tables import Instrument, ModelVersion
from app.risk_management.engine import InstrumentRules


def compare_incumbent(db, identifier, candidate_metadata, costs, settings):
    version = db.get(ModelVersion, identifier)
    if version is None:
        raise ValueError("Incumbent model is missing")
    metadata = version.metadata_json
    scope = ("symbol", "source", "timeframe", "strategy", "horizon")
    if any(metadata[k] != candidate_metadata[k] for k in scope):
        raise ValueError("Common-period comparison requires matching model scope")
    start, end = [datetime.fromisoformat(t) for t in candidate_metadata["partitions"]["validation"]]
    if start <= datetime.fromisoformat(metadata["training_cutoff"]):
        raise ValueError("Incumbent fitting/calibration overlaps comparison period")
    # A validation-only artifact may not expose its sealed period through this path.
    if metadata.get("evaluation_mode") == "VALIDATION_ONLY":
        sealed = datetime.fromisoformat(metadata["partitions"]["test"][0])
        if end >= sealed:
            raise ValueError("Comparison would expose a sealed final test")
    model = load_verified(version, Path(settings.model_artifact_dir))
    rows = load_candles(db, metadata["symbol"], metadata["timeframe"], metadata["source"], 1_000_000)
    verified_training_rows(rows, metadata["input_candles"])
    timeframe, horizon = metadata["timeframe"], metadata["horizon"]
    rows = verified_training_rows(rows, candidate_metadata["input_candles"])
    rows = [c for c in rows if c.time <= end + timedelta(seconds=horizon*timeframe)]
    if not rows or rows[-1].time < end + timedelta(seconds=(horizon-1)*timeframe):
        raise ValueError("Comparison outcome horizon is incomplete")
    instrument = db.get(Instrument, metadata["symbol"])
    rules = InstrumentRules(instrument.symbol, instrument.tick_size, instrument.unit_step,
                            instrument.min_units, instrument.max_spread)
    report = run_portfolio(rows, rules, settings, costs,
        lambda candidate, quote: predict_version(version, candidate, quote, model),
        strategy=metadata["strategy"], horizon=horizon, start=start, end=end)
    return {"model": identifier, "candidate_start": start.isoformat(), "candidate_end": end.isoformat(),
            "input_candles": candle_manifest(rows), "shared_costs": {k: str(v) for k, v in vars(costs).items()},
            "portfolio": report, "qualification_evidence": False, "execution_authority": False,
            "limitation": "Common-period validation comparison is selection evidence, not an untouched final test."}
