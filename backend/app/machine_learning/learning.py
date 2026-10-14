"""Explicit scheduled, validation-only research. No model promotion or execution mutation."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import select, text, update

from app.backtesting.comparison import compare_incumbent
from app.backtesting.registered import evaluate_registered
from app.backtesting.simulator import FillAssumptions
from app.machine_learning.candidate_training import train_candidates
from app.machine_learning.policy import acceptance_policy, digest
from app.market_data.coverage import coverage_report
from app.market_data.providers import CoinbaseData, OandaData
from app.market_data.store import ingest, load_candles
from app.models.tables import (
    Event,
    Instrument,
    LearningRun,
    LearningSchedule,
    ModelVersion,
    PaperDeployment,
    PaperDeploymentSlot,
)
from app.schemas.domain import aware
from app.strategies.registry import STRATEGIES

FAMILIES = {"logistic", "lightgbm", "xgboost", "random_forest"}


class ResearchLeaseLost(RuntimeError):
    pass


def owned_run(db, run_id, worker_id):
    run = db.scalar(select(LearningRun).where(LearningRun.id == run_id).with_for_update()
                    .execution_options(populate_existing=True))
    if run is None or run.state != "RUNNING" or run.worker_id != worker_id:
        raise ResearchLeaseLost("Research lease changed; results require manual review")
    return run


def validate_plan(plan):
    fields = {"schema", "symbol", "source", "timeframe", "strategy", "history_days", "interval_days",
              "families", "costs", "cost_evidence", "validation_only"}
    if set(plan) != fields or plan.get("strategy") not in STRATEGIES:
        raise ValueError("Unknown or missing research plan fields/strategy")
    if plan.get("schema") != "learning-plan-v1" or plan.get("validation_only") is not True:
        raise ValueError("Scheduled training must seal final test results")
    if plan.get("source") not in ("oanda", "coinbase") or plan.get("timeframe") != 300:
        raise ValueError("Only provider five-minute candidate research is currently supported")
    if not 180 <= plan.get("history_days", 0) <= 1095 or not 7 <= plan.get("interval_days", 0) <= 365:
        raise ValueError("Invalid research history or scheduling interval")
    families = plan.get("families", [])
    if not families or len(families) != len(set(families)) or not set(families) <= FAMILIES:
        raise ValueError("Unsupported or repeated model family")
    if set(plan.get("costs", {})) != {"spread", "slippage", "fee_rate", "financing_per_bar"}:
        raise ValueError("Explicit research costs required")
    costs = {k: Decimal(v) for k, v in plan["costs"].items()}
    if any(not v.is_finite() or v < 0 for v in costs.values()) or costs["spread"] <= 0 or costs["fee_rate"] >= 1:
        raise ValueError("Invalid research costs")
    if not plan.get("cost_evidence"):
        raise ValueError("Cost provenance/assumptions must be documented")
    return costs


def schedule_research(db, plan, operator, reason, first_due, now):
    validate_plan(plan)
    if first_due.tzinfo is None or now.tzinfo is None or first_due < now:
        raise ValueError("First scheduled time must be aware and not in the past")
    if not operator.strip() or not reason.strip():
        raise ValueError("Explicit operator attribution required")
    identifier = digest(plan)
    try:
        if db.bind.dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        existing = db.get(LearningSchedule, identifier)
        if existing:
            db.rollback()
            return existing.id
        instrument = db.get(Instrument, plan["symbol"])
        if instrument is None or instrument.provider != plan["source"]:
            raise ValueError("Research source does not match configured instrument")
        db.add(LearningSchedule(id=identifier, enabled=True, operator=operator[:120], reason=reason[:512],
                                plan=plan, next_due=first_due, created_at=now))
        db.add(Event(kind="learning_schedule_enabled", detail={"schedule": identifier, "operator": operator[:120],
                                                               "execution_authority": False}))
        db.commit()
        return identifier
    except Exception:
        db.rollback()
        raise


def queue_due(db, now):
    try:
        if db.bind.dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        schedules = db.scalars(select(LearningSchedule).where(LearningSchedule.enabled.is_(True),
                              LearningSchedule.next_due <= now).with_for_update(skip_locked=True)).all()
        ids = []
        for schedule in schedules:
            validate_plan(schedule.plan)
            if schedule.id != digest(schedule.plan):
                raise ValueError("Immutable research plan changed")
            due = aware(schedule.next_due)
            identifier = digest([schedule.id, due.isoformat()])
            if db.get(LearningRun, identifier) is None:
                db.add(LearningRun(id=identifier, schedule_id=schedule.id, scheduled_for=due,
                                   state="QUEUED", result={"plan_sha256": schedule.id, "execution_authority": False}))
                ids.append(identifier)
            # Coalesce missed weeks; never launch a burst of stale historical jobs.
            interval = timedelta(days=schedule.plan["interval_days"])
            schedule.next_due = due + interval * (int((now - due) / interval) + 1)
        db.commit()
        return ids
    except Exception:
        db.rollback()
        raise


def claim_run(db, run_id, worker_id, now):
    changed = db.execute(update(LearningRun).where(LearningRun.id == run_id, LearningRun.state == "QUEUED").values(
        state="RUNNING", worker_id=worker_id, started_at=now, heartbeat_at=now)).rowcount
    db.commit()
    return bool(changed)


def run_research(db, run_id, worker_id, settings, now=None):
    now = now or datetime.now(timezone.utc)
    if settings.demo_mode or settings.trading_mode == "LIVE" or settings.enable_live_trading:
        raise ValueError("Learning requires real-market research and disabled live execution")
    if not claim_run(db, run_id, worker_id, now):
        return {"status": "NOT_CLAIMED"}
    run = db.get(LearningRun, run_id)
    schedule = db.get(LearningSchedule, run.schedule_id)
    plan = dict(schedule.plan)
    try:
        if aware(run.scheduled_for) > now:
            raise ValueError("Research run is not due")
        costs = FillAssumptions(**validate_plan(plan))
        if not schedule.enabled or digest(plan) != schedule.id:
            raise ValueError("Research schedule disabled or changed")
        end = aware(run.scheduled_for).replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=plan["history_days"])
        instrument = db.get(Instrument, plan["symbol"])
        if instrument is None or instrument.provider != plan["source"]:
            raise ValueError("Research instrument/source changed")
        rows = load_candles(db, plan["symbol"], 300, plan["source"], 1_000_000, start=start, end=end)
        # Refresh the tail through a read-only provider; completed-bar labels exclude the last horizon.
        refresh_start = max(start, rows[-1].time if rows else start)

        async def refresh():
            async with httpx.AsyncClient(timeout=30) as client:
                provider = OandaData(settings, client) if plan["source"] == "oanda" else CoinbaseData(client)
                if refresh_start < end:
                    await ingest(db, provider, plan["symbol"], 300, refresh_start, end)

        asyncio.run(refresh())
        rows = load_candles(db, plan["symbol"], 300, plan["source"], 1_000_000, start=start, end=end)
        coverage = coverage_report(rows, start, end, now, oanda_division=settings.oanda_division)
        if not coverage["research_ready"]:
            raise ValueError("Research coverage or usable-day requirements failed")
        research_settings = settings.model_copy(update={"trading_mode": "PAPER"})
        candidates = []
        for family in plan["families"]:
            try:
                metadata = train_candidates(rows, instrument.tick_size, plan["strategy"], costs,
                            Path(settings.model_artifact_dir), family=family, settings=research_settings,
                            validation_only=True, experiment={"learning_run": run_id, "plan_sha256": schedule.id,
                                                            "prospective_final_test_required": True})
                owned_run(db, run_id, worker_id)
                db.add(ModelVersion(id=metadata["version"], status="EXPERIMENTAL", metadata_json=metadata))
                db.commit()
                base = evaluate_registered(db, metadata["version"], Path(settings.model_artifact_dir), research_settings, "validation")
                stress = evaluate_registered(db, metadata["version"], Path(settings.model_artifact_dir), research_settings, "validation", Decimal(2))
                candidates.append({"model": metadata["version"], "family": family, "status": "EXPERIMENTAL",
                                   "validation": metadata["validation"], "validation_period": metadata["partitions"]["validation"],
                                   "sample_counts": metadata["sample_counts"], "coverage": coverage["input_candles"],
                                   "portfolio": base, "stressed_portfolio": stress,
                                   "walk_forward": metadata["walk_forward"], "test": "NOT_EVALUATED"})
            except ResearchLeaseLost:
                raise
            except Exception as exc:
                db.rollback()
                candidates.append({"family": family, "status": "FAILED", "error_type": type(exc).__name__,
                                   "reason": str(exc) if isinstance(exc, ValueError) else type(exc).__name__})
        deployments = db.scalars(select(PaperDeployment).join(PaperDeploymentSlot,
                                PaperDeploymentSlot.deployment_id == PaperDeployment.id)).all()
        active = [d.model_id for d in deployments if d.contract["scope"]["symbol"] == plan["symbol"]]
        comparisons = []
        for candidate in candidates:
            if candidate['status'] != 'EXPERIMENTAL':
                continue
            metadata = db.get(ModelVersion, candidate['model']).metadata_json
            for identifier in active:
                try:
                    comparisons.append({'candidate': candidate['model'], 'incumbent': identifier, 'status': 'EVALUATED',
                        'evidence': compare_incumbent(db, identifier, metadata, costs, research_settings)})
                except Exception as exc:
                    comparisons.append({'candidate': candidate['model'], 'incumbent': identifier, 'status': 'NOT_COMPARABLE',
                        'error_type': type(exc).__name__})
        result = {"schema": "learning-run-result-v1", "run": run_id, "plan_sha256": schedule.id,
                  "data": coverage, "policy": acceptance_policy(research_settings), "candidates": candidates,
                  "active_models": active, "comparison": "NO_ACTIVE_MODEL" if not active else "COMMON_PERIOD_VALIDATION",
                  "comparisons": comparisons,
                  "selection_inputs": "Validation and walk-forward evidence only; no final test metrics",
                  "final_test": "PROSPECTIVE_UNTOUCHED_PERIOD_REQUIRED", "execution_authority": False,
                  "limitations": ["Trade outcomes are monitoring evidence; selected fills are not duplicated as independent training cases.",
                                  "Previous full-test experiments exist; their periods cannot be represented as newly untouched tests."]}
        run = owned_run(db, run_id, worker_id)
        run.result, run.state = result, "COMPLETED" if any(c["status"] == "EXPERIMENTAL" for c in candidates) else "FAILED"
        run.finished_at = datetime.now(timezone.utc)
        db.add(Event(kind="learning_run_completed", detail={"run": run_id, "state": run.state, "promoted": False}))
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        try:
            run = owned_run(db, run_id, worker_id)
        except ResearchLeaseLost:
            db.rollback()
            return {"status": "LEASE_LOST", "execution_authority": False, "automatic_retry": False}
        run.state, run.finished_at = "FAILED", datetime.now(timezone.utc)
        run.result = {"error_type": type(exc).__name__, "reason": str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
                      "execution_authority": False}
        db.commit()
        return run.result
