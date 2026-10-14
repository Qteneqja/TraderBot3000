from datetime import timedelta

import pytest
import test_deployment
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.execution.recorder import record_sample, start_run
from app.execution.trials import approve_policy, export_periodic_reports, proposed_policy, trial_report
from app.machine_learning.deployment import deactivate
from app.models.tables import Account, Event, ModelPrediction, OrderRow, PaperRun, SignalRow

store = test_deployment.store
deployment_store = test_deployment.deployment_store


def test_no_model_cannot_approve_or_start_trial(store):
    engine, _, quote, settings, now = store
    settings = settings.model_copy(update={"demo_mode": False})
    with Session(engine) as db:
        with pytest.raises(ValueError, match="model scopes"):
            approve_policy(db, proposed_policy(settings), settings, "operator", "test", now)
        with pytest.raises(ValueError, match="prior trial policy approval"):
            start_run(db, settings, [quote.symbol], now, "unapproved")
        run = start_run(db, settings, [quote.symbol], now)
        assert trial_report(db, run, now + timedelta(days=40))["status"] == "INFRASTRUCTURE_ONLY"


def test_approved_trial_is_bound_and_changes_suspend_new_entries(deployment_store):
    engine, candidate, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        deployment = test_deployment.deploy(db, settings, now, reviews)
        policy = proposed_policy(settings, ["TEST-ONLY-first"])
        approval = approve_policy(db, policy, settings, "test-operator", "Mock evidence test", now)
        assert approve_policy(db, policy, settings, "test-operator", "Idempotent", now) == approval
        run = start_run(db, settings, [candidate.symbol], now, approval)
        report = trial_report(db, run, now + timedelta(days=40))
        assert report["closed_trades"] == 0
        assert report["model_observed_seconds"] == "0"
        assert report["status"] == "INSUFFICIENT_EVIDENCE"
        db.rollback()
        deactivate(db, deployment, "operator", "End model trial")
        assert db.get(Account, "PAPER").suspended
        assert trial_report(db, run, now + timedelta(days=40))["status"] == "TERMINATION_REQUIRED"


def test_trial_policy_cannot_be_weakened_after_proposal(deployment_store):
    engine, _, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        test_deployment.deploy(db, settings, now, reviews)
        policy = proposed_policy(settings, ["TEST-ONLY-first"])
        policy["minimum_closed_trades"] = 1
        with pytest.raises(ValueError, match="Changed or unsupported"):
            approve_policy(db, policy, settings, "operator", "test", now)
        assert not db.scalar(select(Event.id).where(Event.kind == "paper_trial_policy_approved"))


def test_daily_weekly_exports_are_scoped_and_do_not_approve(deployment_store, tmp_path):
    engine, candidate, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        test_deployment.deploy(db, settings, now, reviews)
        policy = proposed_policy(settings, ["TEST-ONLY-first"])
        approval = approve_policy(db, policy, settings, "operator", "test", now)
        run = start_run(db, settings, [candidate.symbol], now, approval)
        paths = export_periodic_reports(db, now + timedelta(days=10), tmp_path)
        assert len(paths) == 2
        assert export_periodic_reports(db, now + timedelta(days=10), tmp_path) == []
        assert db.get(PaperRun, run).status == "RUNNING"
        assert not db.get(Account, "PAPER").suspended


def test_recorder_suspends_bound_trial_on_invalid_evidence(deployment_store):
    engine, candidate, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        test_deployment.deploy(db, settings, now, reviews)
        policy = proposed_policy(settings, ["TEST-ONLY-first"])
        approval = approve_policy(db, policy, settings, "operator", "test", now)
        run = start_run(db, settings, [candidate.symbol], now, approval)
        # No source-matching completed candles are installed in this orchestration fixture.
        record_sample(db, settings, now, "test", 0, 1000000000)
        assert db.get(Account, "PAPER").suspended
        assert trial_report(db, run, now + timedelta(seconds=1))["status"] == "TERMINATION_REQUIRED"


def test_trial_uses_authoritative_signal_even_when_shadow_record_already_exists(deployment_store):
    engine, candidate, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        deployment = test_deployment.deploy(db, settings, now, reviews)
        policy = proposed_policy(settings, ["TEST-ONLY-first"])
        approval = approve_policy(db, policy, settings, "operator", "mock evidence test", now)
        run = start_run(db, settings, [candidate.symbol], now, approval)
        payload = {"source": "oanda", "model_version": "TEST-ONLY-first", "deployment_id": deployment,
                   "calibrated": True, "probability": ".8", "probability_stop": ".1", "probability_timeout": ".1"}
        db.add(SignalRow(id="actual-test", time=now + timedelta(seconds=1), symbol=candidate.symbol,
                         strategy="trend", status="APPROVED", payload=payload, reasons=[]))
        db.add(ModelPrediction(model_id="TEST-ONLY-first", candidate_id="actual-test", symbol=candidate.symbol,
                               time=now + timedelta(seconds=1), quote_time=now, mode="SHADOW",
                               prediction={"probability_target": .2}, candidate={}))
        db.flush()
        db.add(OrderRow(id="actual-test", signal_id="actual-test", mode="PAPER", state="CLOSED",
                        symbol=candidate.symbol, direction="LONG", units=1, entry=candidate.entry,
                        stop=candidate.stop, target=candidate.target, planned_risk=1,
                        opened_at=now + timedelta(seconds=1), expires_at=now + timedelta(minutes=60),
                        closed_at=now + timedelta(seconds=2), close_reason="TAKE_PROFIT", pnl=1,
                        fees_paid=0, execution={"deployment_id": deployment}))
        db.commit()
        report = trial_report(db, run, now + timedelta(seconds=3))
        assert report["predictions"] == report["closed_trades"] == 1
        assert report["calibration_closed_scoped_fills_only"]["multiclass_brier"] == pytest.approx(.06)
        assert report["status"] == "INSUFFICIENT_EVIDENCE"
