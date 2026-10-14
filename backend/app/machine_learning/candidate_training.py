"""Cost-aware, candidate-specific research. Only shadow deployment is supported."""

import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from app.backtesting.simulator import FillAssumptions, simulate_trade
from app.indicators.features import FEATURES, compute, frame
from app.machine_learning.training import estimator, scores
from app.market_data.fingerprint import candle_manifest
from app.schemas.domain import Quote
from app.strategies.registry import STRATEGIES, candidates_from_row

EVENT_SCHEMA = "candidate-market-v1"
CANDIDATE_FEATURES = FEATURES + [
    "direction",
    "stop_distance_pct",
    "reward_risk",
    "spread_pct",
    "entry_deviation_pct",
]


def prediction_features(candidate, quote):
    sign = 1 if candidate.direction == "LONG" else -1
    market = quote.ask if sign > 0 else quote.bid
    return candidate.features | {
        "direction": float(sign),
        "stop_distance_pct": float(abs(candidate.entry - candidate.stop) / candidate.entry),
        "reward_risk": float(abs(candidate.target - candidate.entry) / abs(candidate.entry - candidate.stop)),
        "spread_pct": float((quote.ask - quote.bid) / candidate.entry),
        "entry_deviation_pct": float((market - candidate.entry) / candidate.entry),
    }


def dataset(candles, tick, strategy, costs: FillAssumptions, horizon=12):
    if strategy not in STRATEGIES:
        raise ValueError("Unknown strategy")
    data = compute(frame(candles))
    if len(data) != len(candles):
        raise ValueError("Training requires completed, ordered candles only")
    if list(data.index) != [c.time for c in candles]:
        raise ValueError("Training input must be chronologically ordered")
    samples, excluded = [], {"entry_drift": 0, "unfilled": 0, "gaps": 0}
    for i in range(59, len(candles) - horizon):
        c = candles[i]
        window = data.index[i - 59 : i + horizon + 1].to_series().diff().dropna().dt.total_seconds()
        if (window != c.timeframe).any():
            excluded["gaps"] += 1
            continue
        when = c.time + timedelta(seconds=c.timeframe)
        for candidate in candidates_from_row(
            data.iloc[i], c.symbol, c.timeframe, c.source, when, tick, [strategy]
        ):
            # This quote is observed at prediction time, after the proposal candle closes.
            quote = Quote(
                symbol=c.symbol,
                time=when,
                bid=candles[i + 1].open - costs.spread / 2,
                ask=candles[i + 1].open + costs.spread / 2,
                source=c.source,
            )
            market = quote.ask if candidate.direction == "LONG" else quote.bid
            distance = abs(candidate.entry - candidate.stop)
            if abs(market - candidate.entry) > max(distance * Decimal("0.1"), tick * 2):
                excluded["entry_drift"] += 1
                continue
            result = simulate_trade(
                candles[i + 1 : i + horizon + 1],
                candidate.direction,
                candidate.entry,
                candidate.stop,
                candidate.target,
                Decimal(1),
                costs,
            )
            if result["status"] != "CLOSED":
                excluded["unfilled"] += 1
                continue
            label = 1 if result["reason"] == "TAKE_PROFIT" else 2 if result["reason"] == "TIMEOUT" else 0
            samples.append(
                prediction_features(candidate, quote)
                | {
                    "time": when,
                    "label_end": candles[i + horizon].time + timedelta(seconds=c.timeframe),
                    "label": label,
                    "net_per_unit": float(result["pnl"]),
                    "net_r": float(Decimal(result["pnl"]) / distance),
                    "candidate_id": candidate.id,
                }
            )
    return pd.DataFrame(samples), excluded


def purged_partitions(samples):
    n = len(samples)
    boundaries = [0, int(n * 0.5), int(n * 0.65), int(n * 0.8), n]
    parts = []
    for start, stop in zip(boundaries, boundaries[1:]):
        part = np.arange(start, stop)
        if stop < n:
            part = part[(samples.iloc[part].label_end < samples.iloc[stop].time).to_numpy()]
        if len(part) < 20:
            raise ValueError("Insufficient candidate history after time-based purging; download more data")
        parts.append(part)
    return parts


def economic_report(samples, probabilities, threshold=0.8):
    selected = probabilities[:, 1] >= threshold
    returns = samples.net_r.to_numpy()[selected]
    # Overlapping candidate returns are diagnostic, never a portfolio equity curve.
    return {
        "threshold": threshold,
        "selected_candidates": int(selected.sum()),
        "signal_frequency": float(selected.mean()),
        "mean_net_r": float(returns.mean()) if len(returns) else None,
        "positive_fraction": float(np.mean(returns > 0)) if len(returns) else None,
        "portfolio_validated": False,
        "note": "Candidates may overlap; portfolio simulation remains required",
    }


def train_candidates(
    candles, tick: Decimal, strategy: str, costs: FillAssumptions, output: Path, family="logistic", horizon=12
):
    samples, excluded = dataset(candles, tick, strategy, costs, horizon)
    if len(samples) < 300:
        raise ValueError(f"Only {len(samples)} filled candidates; need at least 300 before purging")
    parts = purged_partitions(samples)
    training, calibration, validation, test = parts
    y = samples.label.to_numpy(dtype=int)
    for name, part in (("training", training), ("calibration", calibration)):
        if np.bincount(y[part], minlength=3).min() < 5:
            raise ValueError(f"Insufficient {name} outcomes: require at least five examples of each outcome")
    scope = {
        "event_schema": EVENT_SCHEMA,
        "strategy": strategy,
        "symbol": candles[0].symbol,
        "source": candles[0].source,
        "timeframe": candles[0].timeframe,
        "horizon": horizon,
        "tick": str(tick),
        "costs": {k: str(v) for k, v in vars(costs).items()},
        "family": family,
        "input_candles": candle_manifest(candles),
    }
    digest = hashlib.sha256(
        (samples.to_csv(index=False) + json.dumps(scope, sort_keys=True)).encode()
    ).hexdigest()
    version = f"candidate-{family}-{digest[:16]}"
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / f"{version}.joblib"
    if artifact.exists():
        raise ValueError("Immutable candidate artifact already exists")
    model = estimator(family).fit(samples.iloc[training][CANDIDATE_FEATURES], y[training])
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
    calibrated.fit(samples.iloc[calibration][CANDIDATE_FEATURES], y[calibration])
    valid_p = calibrated.predict_proba(samples.iloc[validation][CANDIDATE_FEATURES])
    test_p = calibrated.predict_proba(samples.iloc[test][CANDIDATE_FEATURES])
    report = scope | {
        "version": version,
        "status": "EXPERIMENTAL",
        "seed": 42,
        "dataset_sha256": digest,
        "features": CANDIDATE_FEATURES,
        "excluded": excluded,
        "event": "Specified target before specified stop within holding horizon, conditional on market entry",
        "partitions": {
            name: [str(samples.iloc[p[0]].time), str(samples.iloc[p[-1]].time)]
            for name, p in zip(["train", "calibration", "validation", "test"], parts, strict=True)
        },
        "training_cutoff": str(samples.iloc[calibration].label_end.max()),
        "validation": scores(y[validation], valid_p),
        "test": scores(y[test], test_p),
        "validation_economics": economic_report(samples.iloc[validation], valid_p),
        "test_economics": economic_report(samples.iloc[test], test_p),
        "execution_validated": False,
        "limitations": [
            "Shadow inference only",
            "Constant spread/slippage assumptions",
            "No demonstrated portfolio advantage",
            "No execution promotion permitted",
            "Synthetic fixtures are not market evidence"
            if candles[0].source == "fixture"
            else "Requires independent provider execution-quality validation",
        ],
    }
    joblib.dump({"model": calibrated, "report": report}, artifact)
    report["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    report["artifact_filename"] = artifact.name
    (output / f"{version}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
