"""Predeclared, explicitly approved paper trials. Reports never grant broker authority."""

import json
import os
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from sqlalchemy import select

from app.execution.paper import ACTIVE, lock_account
from app.machine_learning.deployment import runtime_contract, validate_evidence
from app.machine_learning.policy import acceptance_policy, digest
from app.machine_learning.training import scores
from app.models.tables import (
    Event,
    ModelPrediction,
    OrderRow,
    PaperDeployment,
    PaperDeploymentSlot,
    PaperRun,
    PaperSample,
    SignalRow,
)
from app.schemas.domain import aware


def proposed_policy(settings, models=()):
    policy = {
        "schema": "paper-trial-policy-v1", "status": "PROPOSED",
        "models": sorted(set(models)), "runtime": runtime_contract(settings),
        "minimum_wall_days": 30, "minimum_model_observed_days": 20,
        "minimum_closed_trades": 100, "minimum_active_exit_days": 20,
        "minimum_profit_factor": 1.2, "maximum_sampled_drawdown": 0.08,
        "maximum_target_calibration_error": 0.05,
        "require_positive_net_pnl": True, "allow_model_changes": False,
        "termination": ["Account suspension", "Invalid deployment evidence", "Changed runtime contract"],
        "limitations": ["Observation days require valid recorder continuity, not assumed uptime.",
                        "Drawdown is sampled equity, not guaranteed intratick drawdown.",
                        "No broker promotion or profitability guarantee."],
    }
    return policy | {"sha256": digest(policy)}


def validate_policy(policy, settings):
    unsigned = {k: v for k, v in policy.items() if k != "sha256"}
    expected = proposed_policy(settings, policy.get("models", []))
    if policy.get("sha256") != digest(unsigned) or policy != expected:
        raise ValueError("Changed or unsupported proposed trial policy")
    if not policy["models"] or settings.demo_mode or settings.trading_mode != "PAPER":
        raise ValueError("Trial requires approved model scopes and real-market PAPER mode")


def current_models(db, settings):
    slots = db.scalars(select(PaperDeploymentSlot).where(
        PaperDeploymentSlot.account_id == "PAPER", PaperDeploymentSlot.deployment_id.is_not(None))).all()
    deployments = []
    for slot in slots:
        row = db.get(PaperDeployment, slot.deployment_id)
        _, _, contract = validate_evidence(db, row.model_id, row.review_id, Path(settings.model_artifact_dir), settings)
        if contract != row.contract:
            raise ValueError("Deployment contract changed")
        deployments.append(row)
    return deployments


def approve_policy(db, policy, settings, operator, reason, now):
    try:
        account = lock_account(db)
        validate_policy(policy, settings)
        if not operator.strip() or not reason.strip() or account.suspended or not account.reconciled:
            raise ValueError("Operator attribution and a reconciled unsuspended account are required")
        if sorted({d.model_id for d in current_models(db, settings)}) != policy["models"]:
            raise ValueError("Policy must bind exactly the current verified paper models")
        existing = db.scalar(select(Event).where(Event.kind == "paper_trial_policy_approved",
                             Event.detail["policy_id"].as_string() == policy["sha256"]))
        if existing:
            db.rollback()
            return policy["sha256"]
        db.add(Event(time=now, kind="paper_trial_policy_approved", detail={
            "policy_id": policy["sha256"], "policy": policy,
            "operator": operator[:120], "reason": reason[:512],
        }))
        db.commit()
        return policy["sha256"]
    except Exception:
        db.rollback()
        raise


def approved_contract(db, policy_id, settings, symbols, now, account):
    approval = db.scalar(select(Event).where(Event.kind == "paper_trial_policy_approved",
                         Event.detail["policy_id"].as_string() == policy_id))
    if approval is None or aware(approval.time) > now:
        raise ValueError("Explicit prior trial policy approval is required")
    policy = approval.detail["policy"]
    validate_policy(policy, settings)
    deployments = current_models(db, settings)
    if sorted({d.model_id for d in deployments}) != policy["models"]:
        raise ValueError("Approved model configuration changed")
    if sorted({d.contract["scope"]["symbol"] for d in deployments}) != sorted(set(symbols)):
        raise ValueError("Trial instruments must match approved deployment scopes")
    if account.suspended or not account.reconciled or db.scalar(select(OrderRow.id).where(OrderRow.state.in_(ACTIVE)).limit(1)):
        raise ValueError("Trial must start flat with a reconciled unsuspended account")
    return {"policy": policy, "approval_event": approval.id,
            "deployment_ids": sorted(d.id for d in deployments), "initial_equity": str(account.equity)}


def trial_report(db, run_id, now, period_start=None, period_end=None):
    run = db.get(PaperRun, run_id)
    if run is None:
        raise ValueError("Unknown paper run")
    trial = run.contract.get("trial")
    if not trial:
        return {"run": run_id, "status": "INFRASTRUCTURE_ONLY", "performance_evidence": False}
    start = max(aware(run.started_at), period_start or aware(run.started_at))
    end = min(now, aware(run.stopped_at) if run.stopped_at else now, period_end or now)
    if end <= start:
        raise ValueError("Invalid report period")
    orders = db.scalars(select(OrderRow).where(OrderRow.mode == "PAPER", OrderRow.opened_at >= run.started_at,
                                             OrderRow.opened_at < end)).all()
    # An order belongs to the trial by immutable deployment, not by coincident dates.
    orders = [o for o in orders if o.execution.get("deployment_id") in trial["deployment_ids"]]
    closed = sorted([o for o in orders if o.state == "CLOSED" and start <= aware(o.closed_at) < end],
                    key=lambda o: (aware(o.closed_at), o.id))
    pnl = [o.pnl for o in closed]
    wins, losses = [p for p in pnl if p > 0], [p for p in pnl if p < 0]
    profit, loss = sum(wins, D(0)), -sum(losses, D(0))
    pf = profit / loss if loss else None
    samples = db.scalars(select(PaperSample).where(PaperSample.run_id == run_id,
                        PaperSample.time >= start, PaperSample.time < end).order_by(PaperSample.time)).all()
    peak, drawdown = D(trial["initial_equity"]), D(0)
    for sample in samples:
        equity = D(sample.detail["equity"])
        peak = max(peak, equity)
        drawdown = max(drawdown, (peak - equity) / peak if peak > 0 else D(1))
    observed = sum((s.model_observed_seconds for s in samples), D(0))
    active_days = len({aware(o.closed_at).date() for o in closed})
    policy = trial["policy"]
    predictions = db.scalars(select(ModelPrediction).where(
        ModelPrediction.mode == "PAPER_TRIAL", ModelPrediction.model_id.in_(policy["models"]),
        ModelPrediction.time >= start, ModelPrediction.time < end)).all()
    attributed = db.scalars(select(ModelPrediction).where(
        ModelPrediction.mode == "PAPER_TRIAL", ModelPrediction.model_id.in_(policy["models"]),
        ModelPrediction.candidate_id.in_([o.signal_id for o in closed]),
        ModelPrediction.time >= run.started_at, ModelPrediction.time < end)).all()
    indexed = {(p.candidate_id, p.model_id): p for p in attributed}
    probabilities, labels = [], []
    reasons = {"TAKE_PROFIT": 1, "STOP_LOSS": 0, "STOP_AMBIGUOUS": 0, "TIMEOUT": 2}
    for order in closed:
        signal = db.get(SignalRow, order.signal_id)
        prediction = indexed.get((order.signal_id, signal.payload.get("model_version"))) if signal else None
        if prediction and order.close_reason in reasons:
            values = [prediction.prediction.get(k) for k in ("probability_stop", "probability_target", "probability_timeout")]
            try:
                values = np.array(values, dtype=float)
                if not np.isfinite(values).all() or (values < 0).any() or not np.isclose(values.sum(), 1):
                    continue
            except (TypeError, ValueError):
                continue
            probabilities.append(values)
            labels.append(reasons[order.close_reason])
    calibration = scores(np.array(labels), np.array(probabilities)) if labels else None
    scoped_symbols = {db.get(PaperDeployment, d).contract["scope"]["symbol"] for d in trial["deployment_ids"]}
    signals = db.scalars(select(SignalRow).where(SignalRow.symbol.in_(scoped_symbols),
                        SignalRow.time >= start, SignalRow.time < end)).all()
    signals = [s for s in signals if s.payload.get("source") in ("oanda", "coinbase")]
    changed = any(s.detail["deployments"] != trial["deployment_ids"] or
                  "CONFIGURATION_CHANGED" in s.detail["issues"] or "ACCOUNT_NOT_READY" in s.detail["issues"] or
                  "DEPLOYMENT_EVIDENCE_INVALID_OR_UNRECORDED" in s.detail["issues"] for s in samples)
    changed = changed or db.scalar(select(Event.id).where(Event.kind == "paper_trial_suspended",
                                  Event.detail["run"].as_string() == run_id).limit(1)) is not None
    checks = {
        "wall_duration": (end - aware(run.started_at)).total_seconds() >= policy["minimum_wall_days"] * 86400,
        "model_observed_duration": observed >= D(policy["minimum_model_observed_days"] * 86400),
        "trade_count": len(closed) >= policy["minimum_closed_trades"],
        "active_days": active_days >= policy["minimum_active_exit_days"],
        "positive_net_pnl": sum(pnl, D(0)) > 0,
        "profit_factor": loss > 0 and pf >= D(str(policy["minimum_profit_factor"])),
        "sampled_drawdown": bool(samples) and drawdown <= D(str(policy["maximum_sampled_drawdown"])),
        "attributed_calibration_sample": len(labels) >= policy["minimum_closed_trades"],
        "target_calibration": calibration is not None and calibration["target_calibration_error"] <= policy["maximum_target_calibration_error"],
        "unchanged_approved_configuration": not changed,
    }
    full_period = period_start is None and period_end is None
    opened = [o for o in orders if aware(o.opened_at) >= start]
    return {
        "schema": "paper-trial-report-v1", "run": run_id, "policy_id": policy["sha256"],
        "classification": "ACTUAL_PAPER_TRADING", "start": start.isoformat(), "end_exclusive": end.isoformat(),
        "closed_trades": len(closed), "active_exit_days": active_days,
        "predictions": len(predictions), "eligible_signals": sum(s.status != "REJECTED" for s in signals),
        "rejected_signals": sum(s.status == "REJECTED" for s in signals),
        "orders_opened": len(opened),
        "entry_fill_rate": sum(o.state in ("FILLED", "CLOSED") for o in opened) / len(opened) if opened else None,
        "calibration_closed_scoped_fills_only": calibration,
        "net_pnl": str(sum(pnl, D(0))), "fees_paid_closed_trades": str(sum((o.fees_paid for o in closed), D(0))),
        "win_rate": len(wins) / len(pnl) if pnl else None,
        "average_win": str(profit / len(wins)) if wins else None,
        "average_loss": str(-loss / len(losses)) if losses else None,
        "profit_factor": str(pf) if pf is not None else None,
        "sampled_max_drawdown": str(drawdown), "model_observed_seconds": str(observed),
        "closure_reasons": {reason: sum(o.close_reason == reason for o in closed) for reason in {o.close_reason for o in closed}},
        "continuity_breaks": sum(s.continuity_break for s in samples), "checks": checks,
        "status": "TERMINATION_REQUIRED" if changed else (
            "READY_FOR_OPERATOR_REVIEW" if full_period and all(checks.values()) else "INSUFFICIENT_EVIDENCE"),
        "execution_approved": False,
        "limitations": ["Calibration is conditional on closed scoped fills and has selection bias; it is not calibration of all signals.",
                         "Sampled equity can miss intratick drawdowns.",
                         "Daily/weekly reports do not independently approve the full trial."],
        "research_policy": acceptance_policy(),
    }


def export_periodic_reports(db, now, directory):
    """Closed UTC days/weeks only; no report can promote a model or submit an order."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    periods = [("daily", midnight - timedelta(days=1), midnight)]
    monday = midnight - timedelta(days=midnight.weekday())
    periods.append(("weekly", monday - timedelta(days=7), monday))
    paths = []
    for run in db.scalars(select(PaperRun).where(PaperRun.status == "RUNNING")).all():
        if not run.contract.get("trial"):
            continue
        for kind, start, end in periods:
            if aware(run.started_at) >= end:
                continue
            path = Path(directory) / f"trial-{run.id}-{kind}-{start.date()}.json"
            if path.exists():
                continue
            report = trial_report(db, run.id, now, start, end)
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                json.dump(report, output, indent=2)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
            finally:
                temporary.unlink(missing_ok=True)
            paths.append(str(path))
    return paths
