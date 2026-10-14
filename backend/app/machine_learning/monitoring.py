"""Sample-aware monitoring. Advisory by default; suspension requires explicit policy approval."""

from datetime import datetime
from decimal import Decimal as D
from math import sqrt

import numpy as np
from sqlalchemy import select

from app.brokers.reconciliation import account_key, lock_practice
from app.execution.paper import lock_account
from app.machine_learning.policy import digest
from app.machine_learning.training import scores
from app.models.tables import (
    Event,
    ModelVersion,
    Notification,
    PaperDeployment,
    PaperDeploymentSlot,
    PracticeOrder,
    SignalRow,
    TradeOutcome,
)
from app.schemas.domain import aware


def drift_policy():
    policy = {"schema": "drift-policy-v1", "minimum_independent_outcomes_per_window": 200, "windows": 2,
              "wilson_z": 1.96, "calibration_gap": .05, "brier_deterioration": .05,
              "feature_z_warning": 3.0, "prediction_psi_warning": .2,
              "purpose": "Suspend new entries only after repeated outcome deterioration; never replace a model"}
    return policy | {"sha256": digest(policy)}


def wilson(successes, count, z=1.96):
    if not count:
        return None
    p = successes / count
    denominator = 1 + z*z / count
    center = (p + z*z / (2*count)) / denominator
    half = z * sqrt(p*(1-p)/count + z*z/(4*count*count)) / denominator
    return [max(0, center-half), min(1, center+half)]


def psi(reference, observed):
    a, b = np.array(reference, dtype=float), np.array(observed, dtype=float)
    if len(a) != len(b) or not len(a) or min(a.sum(), b.sum()) <= 0:
        return None
    a, b = (a + .5) / (a.sum() + .5*len(a)), (b + .5) / (b.sum() + .5*len(b))
    return float(np.sum((b-a) * np.log(b/a)))


def monitor_model(db, model_id, mode="PAPER", limit=1000, account_fingerprint=None):
    if mode not in ("PAPER", "OANDA_PRACTICE"):
        raise ValueError("Unsupported outcome monitoring mode")
    model = db.get(ModelVersion, model_id)
    if model is None:
        raise ValueError("Unknown monitored model")
    query = select(TradeOutcome).where(TradeOutcome.model_id == model_id, TradeOutcome.mode == mode,
                                       TradeOutcome.status.in_(("VERIFIED_PAPER", "VERIFIED_PRACTICE")))
    if mode == "OANDA_PRACTICE":
        if not account_fingerprint:
            raise ValueError("Practice monitoring requires an explicit account scope")
        query = query.where(TradeOutcome.detail["execution"]["account_fingerprint"].as_string() == account_fingerprint)
    rows = list(reversed(db.scalars(query.order_by(TradeOutcome.closed_at.desc()).limit(limit)).all()))
    if any(digest(row.detail) != row.detail_sha256 for row in rows):
        raise ValueError("Outcome evidence checksum mismatch")
    currencies = {r.detail["currency"] for r in rows}
    if len(currencies) > 1:
        raise ValueError("Mixed account currencies cannot be pooled")
    net = [D(row.detail["net_pnl"]) for row in rows]
    wins, losses = sum(p > 0 for p in net), [p for p in net if p < 0]
    profit, loss = sum((p for p in net if p > 0), D(0)), -sum(losses, D(0))
    independent, last_close = [], None
    for row in rows:
        if row.detail["outcome_label"] is None:
            continue
        opened = datetime.fromisoformat(row.detail["opened_at"])
        if last_close is None or opened >= last_close:
            independent.append(row)
            last_close = aware(row.closed_at)
    policy = drift_policy()
    n = policy["minimum_independent_outcomes_per_window"]
    windows = []
    if len(independent) >= n * 2:
        for window in (independent[-2*n:-n], independent[-n:]):
            labels = np.array([r.detail["outcome_label"] for r in window], dtype=int)
            probabilities = np.array([[float(r.detail["probabilities"][k]) for k in ("stop", "target", "timeout")] for r in window])
            metric = scores(labels, probabilities)
            interval = wilson(int((labels == 1).sum()), len(labels), policy["wilson_z"])
            baseline = model.metadata_json.get("validation", {}).get("multiclass_brier")
            deterioration = (baseline is not None and interval[1] < probabilities[:, 1].mean() - policy["calibration_gap"]
                             and metric["multiclass_brier"] > baseline + policy["brier_deterioration"])
            windows.append({"samples": len(window), "first": window[0].detail["opened_at"],
                            "last": window[-1].detail["closed_at"], "metrics": metric,
                            "target_observed_wilson_interval": interval, "deteriorated": bool(deterioration)})
    if mode == "PAPER":
        payloads = [s.payload for s in db.scalars(select(SignalRow).where(SignalRow.payload["model_version"].as_string() == model_id)
                    .order_by(SignalRow.time.desc()).limit(limit)).all()]
    else:
        payloads = [s.candidate for s in db.scalars(select(PracticeOrder).where(PracticeOrder.account_id == account_fingerprint,
                    PracticeOrder.candidate["model_version"].as_string() == model_id).order_by(PracticeOrder.created_at.desc()).limit(limit)).all()]
    reference = model.metadata_json.get("feature_reference_training_only", {})
    feature_shifts = {}
    if len(payloads) >= n:
        for feature, stats in reference.items():
            values = [float(p["features"][feature]) for p in payloads if feature in p.get("features", {})]
            if len(values) >= n and stats["std"] > 0:
                feature_shifts[feature] = abs(float(np.mean(values)) - stats["mean"]) / stats["std"]
    probabilities = [float(p["probability"]) for p in payloads if p.get("probability") is not None]
    prediction_shift = None
    if len(probabilities) >= n:
        prediction_shift = psi(model.metadata_json.get("prediction_reference_validation_only", []),
                               np.histogram(probabilities, bins=np.linspace(0, 1, 11))[0])
    warning = any(z > policy["feature_z_warning"] for z in feature_shifts.values()) or (
        prediction_shift is not None and prediction_shift > policy["prediction_psi_warning"])
    status = "INSUFFICIENT_DATA" if len(windows) < 2 else "OBSERVING"
    if warning:
        status = "INPUT_DISTRIBUTION_WARNING"
    if len(windows) == 2 and all(w["deteriorated"] for w in windows):
        status = "DETERIORATION_DETECTED"
    initial = D(rows[0].detail["equity_at_entry"]) if rows and rows[0].detail.get("equity_at_entry") else None
    drawdown = None
    if initial is not None and initial > 0:
        equity, peak, drawdown = initial, initial, D(0)
        for pnl in net:
            equity += pnl
            peak = max(peak, equity)
            drawdown = max(drawdown, (peak-equity)/peak)
    regimes = {}
    for row in rows:
        regime = row.detail.get("regime") or "UNCLASSIFIED"
        group = regimes.setdefault(regime, {"trades": 0, "wins": 0, "net_pnl": D(0)})
        group["trades"] += 1
        group["wins"] += D(row.detail["net_pnl"]) > 0
        group["net_pnl"] += D(row.detail["net_pnl"])
    regimes = {name: value | {"net_pnl": str(value["net_pnl"]), "win_rate": value["wins"]/value["trades"]}
               for name, value in regimes.items()}
    return {"schema": "model-monitor-v1", "model": model_id, "mode": mode, "currency": next(iter(currencies), None),
            "account_fingerprint": account_fingerprint,
            "status": status, "closed_trades": len(rows), "nonoverlapping_labeled_outcomes": len(independent),
            "win_rate": wins / len(net) if net else None, "win_rate_wilson_interval": wilson(wins, len(net)),
            "net_pnl": str(sum(net, D(0))), "profit_factor": str(profit/loss) if loss else None,
            "mean_realized_net_r": str(sum(D(r.detail["net_r"]) for r in rows if r.detail.get("net_r")) /
                sum(bool(r.detail.get("net_r")) for r in rows)) if any(r.detail.get("net_r") for r in rows) else None,
            "windows": windows, "feature_mean_standardized_shifts": feature_shifts,
            "prediction_psi": prediction_shift, "policy": policy, "execution_authority": False,
            "realized_trade_sequence_drawdown": str(drawdown) if drawdown is not None else None,
            "regimes": regimes,
            "limitations": ["Closed fills have selection bias. Nonoverlap filtering does not eliminate serial market dependence.",
                            "Wilson intervals assume binomial sampling; PSI and standardized shifts are heuristic warnings.",
                            "Input-distribution warnings alone never suspend or replace a model."]}


def approve_drift_policy(db, operator, reason, now):
    if not operator.strip() or not reason.strip():
        raise ValueError("Operator attribution required")
    policy = drift_policy()
    db.add(Event(time=now, kind="drift_policy_approved", detail={"policy": policy,
                "operator": operator[:120], "reason": reason[:512]}))
    db.commit()
    return policy


def enforce_monitor(db, report, settings):
    if not settings.enable_drift_suspension or report["status"] != "DETERIORATION_DETECTED":
        return False
    if report["mode"] == "OANDA_PRACTICE" and report.get("account_fingerprint") != account_key(settings.oanda_account_id):
        return False
    policy = drift_policy()
    approval = db.scalar(select(Event).where(Event.kind == "drift_policy_approved").order_by(Event.id.desc()).limit(1))
    if approval is None or approval.detail.get("policy") != policy or report["policy"] != policy:
        db.rollback()
        return False
    db.rollback()
    try:
        if report["mode"] == "PAPER":
            account = lock_account(db)
            active = set(db.scalars(select(PaperDeployment.model_id).join(PaperDeploymentSlot,
                                    PaperDeploymentSlot.deployment_id == PaperDeployment.id)).all())
        else:
            account = lock_practice(db, account_key(settings.oanda_account_id))
            active = set(account.approval.get("models", [])) if account else set()
        if account is None or account.suspended or report["model"] not in active:
            db.rollback()
            return False
        fresh = monitor_model(db, report["model"], report["mode"], account_fingerprint=report.get("account_fingerprint"))
        if digest(fresh) != digest(report) or fresh["status"] != "DETERIORATION_DETECTED":
            db.rollback()
            return False
        account.suspended = True
        identifier = digest([report["model"], report["mode"], digest(report)])
        db.add(Event(kind="model_drift_suspended", detail={"model": report["model"], "mode": report["mode"],
                                                         "report_sha256": digest(report), "policy": policy["sha256"]}))
        if db.get(Notification, identifier) is None:
            db.add(Notification(id=identifier, text=f"{report['mode']} entries suspended: repeated outcome deterioration for {report['model']}. Existing position management remains enabled."))
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
