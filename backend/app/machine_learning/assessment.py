"""Reproducible non-executing research acceptance reports."""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.backtesting.registered import evaluate_registered
from app.machine_learning.policy import acceptance_policy, digest
from app.machine_learning.registry import ModelUnavailable, load_verified
from app.models.tables import Event, ModelReview, ModelVersion


def daily_uncertainty(report, policy):
    """Fixed-length circular blocks retain local serial dependence; diagnostic, not a guarantee."""
    start = pd.Timestamp(report["candidate_start"]).normalize()
    end = pd.Timestamp(report["candidate_end"]).normalize()
    days = pd.date_range(start, end, freq="D")
    returns = pd.Series(0.0, index=days)
    for trade in report["trades"]:
        day = pd.Timestamp(trade["exit_time"]).normalize()
        if day not in returns.index:
            returns.loc[day] = 0.0
        returns.loc[day] += float(trade["pnl"])
    returns = returns.sort_index()
    values = returns.to_numpy()
    if not len(values) or not np.isfinite(values).all():
        raise ValueError("Invalid daily portfolio outcomes")
    block = policy["bootstrap_block_days"]
    rng = np.random.default_rng(policy["bootstrap_seed"])
    starts = rng.integers(0, len(values), size=(policy["bootstrap_draws"], int(np.ceil(len(values) / block))))
    indices = ((starts[..., None] + np.arange(block)) % len(values)).reshape(policy["bootstrap_draws"], -1)
    means = values[indices[:, : len(values)]].mean(axis=1)
    return {
        "method": "Circular block bootstrap of daily realized net P&L",
        "days": len(values),
        "active_days": len({pd.Timestamp(t["exit_time"]).date() for t in report["trades"]}),
        "mean_daily_pnl": float(values.mean()),
        "lower_mean_daily_pnl": float(np.quantile(means, policy["bootstrap_lower_quantile"])),
        "upper_mean_daily_pnl": float(np.quantile(means, 1 - policy["bootstrap_lower_quantile"])),
        "block_days": block,
        "draws": policy["bootstrap_draws"],
        "seed": policy["bootstrap_seed"],
    }


def partition_checks(report, stress, calibration, baseline, policy):
    metrics = report["metrics"]
    uncertainty = daily_uncertainty(report, policy)
    duration = (
        pd.Timestamp(report["candidate_end"]) - pd.Timestamp(report["candidate_start"])
    ).total_seconds() / 86400
    checks = {
        "PARTITION_DURATION": duration >= policy["minimum_partition_days"],
        "TRADE_COUNT": metrics["trades"] >= policy["minimum_partition_trades"],
        "ACTIVE_DAYS": uncertainty["active_days"] >= policy["minimum_active_days"],
        "POSITIVE_NET_RETURN": metrics["net_return"] > 0,
        "POSITIVE_EXPECTANCY": metrics["expectancy"] is not None and metrics["expectancy"] > 0,
        "PROFIT_FACTOR": metrics["profit_factor"] is not None
        and metrics["profit_factor"] >= policy["minimum_profit_factor"],
        "DRAWDOWN": 0 <= metrics["max_drawdown"] <= policy["maximum_drawdown"],
        "CALIBRATION": 0
        <= calibration["target_calibration_error"]
        <= policy["maximum_target_calibration_error"],
        "BEATS_CLASS_BASELINE": calibration["multiclass_brier"] < baseline["multiclass_brier"],
        "UNCERTAINTY_LOWER_BOUND": uncertainty["lower_mean_daily_pnl"] > 0,
        "STRESSED_ACTIVITY": stress["metrics"]["trades"] >= policy["minimum_partition_trades"],
        "STRESSED_NET_RETURN": stress["metrics"]["net_return"] > 0,
        "STRESSED_DRAWDOWN": 0 <= stress["metrics"]["max_drawdown"] <= policy["maximum_drawdown"],
    }
    return {
        "checks": {key: bool(value) for key, value in checks.items()},
        "uncertainty": uncertainty,
        "metrics": {k: v for k, v in metrics.items() if k not in ("equity_curve", "drawdown_curve")},
        "stressed_metrics": {
            k: v for k, v in stress["metrics"].items() if k not in ("equity_curve", "drawdown_curve")
        },
        "replay_sha256": digest(report),
        "stress_replay_sha256": digest(stress),
    }


def assess_model(db, version_id, root, settings):
    version = db.get(ModelVersion, version_id)
    if version is None:
        raise ModelUnavailable("Unknown model version")
    metadata = version.metadata_json
    policy = acceptance_policy(settings)
    artifact_ok = True
    try:
        load_verified(version, root)
    except (ModelUnavailable, ValueError, KeyError):
        artifact_ok = False
    manifest = metadata.get("input_candles", {})
    try:
        days = (
            datetime.fromisoformat(manifest["end"]) - datetime.fromisoformat(manifest["start"])
        ).total_seconds() / 86400
    except (KeyError, ValueError, TypeError):
        days = 0
    checks = {
        "PAPER_RESEARCH_MODE": settings.trading_mode == "PAPER",
        "FINAL_TEST_EVALUATED": metadata.get("evaluation_mode", "FULL") == "FULL",
        "WALK_FORWARD_VERIFIED": len(metadata.get("walk_forward", [])) == policy["walk_forward_folds"]
        and all(f.get("status") == "EVALUATED" for f in metadata.get("walk_forward", [])),
        "ARTIFACT_INTEGRITY": artifact_ok,
        "POLICY_PREDECLARED_AND_UNCHANGED": metadata.get("acceptance_policy") == policy,
        "REAL_MARKET_SOURCE": metadata.get("source") in ("oanda", "coinbase"),
        "HISTORY_DURATION": days >= policy["minimum_history_days"],
        "USABLE_DATA_COVERAGE": metadata.get("coverage", {}).get("research_ready") is True
        and metadata.get("coverage", {}).get("input_candles") == manifest
        and metadata.get("coverage", {}).get("session_coverage", 0) >= policy["minimum_session_coverage"],
        "CALIBRATION_SAMPLE_COUNT": metadata.get("sample_counts", {}).get("calibration", 0)
        >= policy["minimum_calibration_samples"],
        "THRESHOLD_AND_REWARD_FLOOR": settings.initial_probability_threshold >= Decimal(".8")
        and settings.min_risk_reward >= 2,
    }
    partitions = {}
    # Do not inspect held-out results when provenance or predeclaration already fails.
    if all(checks.values()):
        for partition in ("validation", "test"):
            try:
                base = evaluate_registered(db, version_id, root, settings, partition)
                stress = evaluate_registered(
                    db, version_id, root, settings, partition, Decimal(policy["cost_stress_multiplier"])
                )
                partitions[partition] = partition_checks(
                    base, stress, metadata[partition], metadata["class_frequency_baseline"][partition], policy
                )
            except (ModelUnavailable, ValueError, KeyError):
                partitions[partition] = {"checks": {"REPRODUCIBLE_EVIDENCE": False}}
    all_checks = checks | {
        f"{name.upper()}_{key}": value
        for name, part in partitions.items()
        for key, value in part["checks"].items()
    }
    passed = all(all_checks.values()) and len(partitions) == 2
    report = {
        "schema": "model-assessment-v1",
        "model_version": version.id,
        "artifact_sha256": metadata.get("artifact_sha256"),
        "dataset_sha256": metadata.get("dataset_sha256"),
        "policy": policy,
        "status": "RESEARCH_GATES_PASSED" if passed else "REJECTED",
        "checks": all_checks,
        "reasons": [key for key, value in all_checks.items() if not value],
        "partitions": partitions,
        "execution_allowed": False,
        "remaining_gates": [
            "Independent regime and execution-quality validation",
            "Real-time paper soak evidence",
            "Audited deployment and rollback workflow",
        ],
    }
    review_id = digest(report)
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    inserted = db.execute(
        insert(ModelReview)
        .values(id=review_id, model_id=version.id, status=report["status"], report=report)
        .on_conflict_do_nothing(index_elements=["id"]).returning(ModelReview.id)
    ).scalar_one_or_none()
    if inserted is not None:
        db.add(
            Event(
                kind="model_assessed",
                detail={
                    "review": review_id,
                    "model": version.id,
                    "status": report["status"],
                    "execution_allowed": False,
                },
            )
        )
    db.commit()
    return report | {"review_id": review_id}
