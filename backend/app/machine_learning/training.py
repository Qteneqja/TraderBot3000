"""Reproducible research training. Artifacts are experimental; promotion is never automatic."""

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.indicators.features import FEATURES, compute, frame


def barrier_labels(data, horizon=12, reward_risk=2.5):
    """Three outcomes: 0 stop, 1 target, 2 timeout. Same-bar ambiguity is a stop.

    Entry is next-bar open; distances are fixed using prior completed ATR. No late
    samples are labeled without their complete outcome horizon. Costs are excluded
    from labels and must be assessed in execution validation before any promotion.
    """
    labels = np.full(len(data), np.nan)
    for i in range(len(data) - horizon):
        distance = data.atr.iloc[i] * 1.5
        if not np.isfinite(distance) or distance <= 0:
            continue
        sign = 1 if data.trend.iloc[i] > 0 else -1
        entry = data.open.iloc[i + 1]
        stop, target = entry - sign * distance, entry + sign * distance * reward_risk
        outcome = 2
        for j in range(i + 1, i + horizon + 1):
            bar = data.iloc[j]
            stop_hit = bar.low <= stop if sign > 0 else bar.high >= stop
            tp_hit = bar.high >= target if sign > 0 else bar.low <= target
            if stop_hit or tp_hit:
                outcome = 0 if stop_hit else 1
                break
        labels[i] = outcome
    return labels


def chronological_partitions(n, horizon):
    # Purge complete label horizons before every held-out segment.
    a, b, c = int(n * 0.5), int(n * 0.65), int(n * 0.8)
    parts = [np.arange(0, a - horizon), np.arange(a, b - horizon), np.arange(b, c - horizon), np.arange(c, n)]
    if any(len(p) < 20 for p in parts):
        raise ValueError("Insufficient data after purging; provide at least 400 completed candles")
    return parts


def scores(y, probabilities):
    one_hot = np.eye(3)[y]
    brier = float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1)))
    buckets = []
    error = 0.0
    bucket_ids = np.minimum((probabilities[:, 1] * 10).astype(int), 9)
    for bucket_id in range(10):
        lo = bucket_id / 10
        mask = bucket_ids == bucket_id
        if mask.any():
            predicted, observed = float(probabilities[mask, 1].mean()), float((y[mask] == 1).mean())
            error += mask.mean() * abs(predicted - observed)
            buckets.append(
                {"lower": float(lo), "count": int(mask.sum()), "predicted": predicted, "observed": observed}
            )
    return {
        "multiclass_brier": brier,
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1, 2])),
        "target_calibration_error": float(error),
        "reliability": buckets,
        "samples": len(y),
    }


def estimator(name):
    if name == "logistic":
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42))
    if name == "lightgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(n_estimators=100, max_depth=3, verbosity=-1, random_state=42, n_jobs=1)
    if name == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(n_estimators=100, max_depth=3, random_state=42, n_jobs=1)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=20, random_state=42, n_jobs=1)
    raise ValueError("Unknown model family")


def walk_forward(data, y, horizon, family):
    reports = []
    for fraction in (0.5, 0.65, 0.8):
        boundary = int(len(data) * fraction)
        end = min(len(data), boundary + max(20, int(len(data) * 0.12)))
        train = np.arange(0, boundary - horizon)
        valid = np.arange(boundary, end)
        if len(train) < 30 or len(set(y[train])) != 3:
            continue
        model = estimator(family).fit(data.iloc[train][FEATURES], y[train])
        reports.append(
            {
                "train_end": str(data.index[train[-1]]),
                "validation_start": str(data.index[valid[0]]),
                **scores(y[valid], model.predict_proba(data.iloc[valid][FEATURES])),
            }
        )
    return reports


def train(candles, output: Path, family="logistic", horizon=12):
    data = compute(frame(candles))
    data["label"] = barrier_labels(data, horizon)
    data = data.dropna(subset=FEATURES + ["label"])
    if len(data) < 300:
        raise ValueError("Need more history: at least 300 feature-complete labeled observations")
    training, calibration, validation, test = chronological_partitions(len(data), horizon)
    y = data.label.to_numpy(dtype=int)
    if any(len(set(y[part])) < 3 for part in (training, calibration)):
        raise ValueError(
            "Training and calibration require all three outcomes; no probability will be invented"
        )
    model = estimator(family).fit(data.iloc[training][FEATURES], y[training])
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
    calibrated.fit(data.iloc[calibration][FEATURES], y[calibration])
    valid_scores = scores(y[validation], calibrated.predict_proba(data.iloc[validation][FEATURES]))
    test_scores = scores(y[test], calibrated.predict_proba(data.iloc[test][FEATURES]))
    base = np.bincount(y[training], minlength=3) / len(training)
    baseline = scores(y[test], np.tile(base, (len(test), 1)))
    fingerprint = hashlib.sha256(data.to_csv().encode()).hexdigest()
    version = f"{family}-{fingerprint[:12]}-h{horizon}"
    report = {
        "version": version,
        "status": "EXPERIMENTAL",
        "family": family,
        "seed": 42,
        "source": candles[0].source,
        "symbol": candles[0].symbol,
        "timeframe": candles[0].timeframe,
        "event": "Target before stop within 12 bars after next-open fill; trend direction",
        "horizon": horizon,
        "features": FEATURES,
        "dataset_sha256": fingerprint,
        "partitions": {
            name: [str(data.index[p[0]]), str(data.index[p[-1]])]
            for name, p in zip(
                ["train", "calibration", "validation", "test"],
                [training, calibration, validation, test],
                strict=True,
            )
        },
        "validation": valid_scores,
        "test": test_scores,
        "baseline_test": baseline,
        "walk_forward": walk_forward(
            data.iloc[: validation[-1] + 1], y[: validation[-1] + 1], horizon, family
        ),
        "execution_validated": False,
        "limitations": [
            "No demonstrated net trading edge",
            "Labels omit spread and liquidity",
            "Next-open labels are not directly deployable on candidate-close entries",
            "Final test must not guide repeated model selection",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / f"{version}.joblib"
    if artifact.exists():
        raise ValueError("Immutable artifact already exists; use a new experiment directory")
    joblib.dump({"model": calibrated, "report": report}, artifact)
    report["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (output / f"{version}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
