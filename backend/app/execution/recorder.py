"""Durable operational observations, never automatic acceptance or proof of a trading edge."""

from decimal import Decimal as D
from pathlib import Path

from sqlalchemy import case, func, select

from app.execution.paper import ACTIVE, lock_account
from app.machine_learning.deployment import runtime_contract, validate_evidence
from app.machine_learning.policy import digest
from app.machine_learning.registry import ModelUnavailable
from app.market_data.store import load_candles
from app.models.tables import (
    Event,
    Instrument,
    OrderRow,
    PaperDeployment,
    PaperDeploymentSlot,
    PaperRun,
    PaperSample,
    QuoteRow,
)
from app.schemas.domain import aware

MAX_INTERVAL_SECONDS = 30


def start_run(db, settings, symbols, now, trial_policy_id=None):
    try:
        account = lock_account(db)
        if settings.trading_mode != "PAPER":
            raise ValueError("Recorder requires PAPER mode")
        scopes = []
        for symbol in sorted(set(symbols)):
            instrument = db.get(Instrument, symbol)
            if instrument is None:
                raise ValueError("Unknown recorder instrument")
            scopes.append({"symbol": symbol, "source": instrument.provider})
        if not scopes:
            raise ValueError("At least one recorder instrument is required")
        contract = {
            "runtime": runtime_contract(settings),
            "scopes": scopes,
            "classification": "FIXTURE_DIAGNOSTIC" if settings.demo_mode else "REAL_MARKET_PAPER",
            "maximum_interval_seconds": MAX_INTERVAL_SECONDS,
        }
        if trial_policy_id:
            from app.execution.trials import approved_contract

            contract["trial"] = approved_contract(db, trial_policy_id, settings, symbols, now, account)
        current = db.scalar(
            select(PaperRun).where(PaperRun.account_id == "PAPER", PaperRun.status == "RUNNING")
        )
        if current:
            if current.contract != contract:
                raise ValueError("Stop the running recorder before changing its configuration")
            result = current.id
            db.rollback()
            return result
        run = PaperRun(account_id="PAPER", status="RUNNING", started_at=now, contract=contract)
        db.add(run)
        db.flush()
        db.add(
            Event(
                kind="paper_recording_started",
                detail={"run": run.id, "classification": contract["classification"]},
            )
        )
        result = run.id
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def stop_run(db, run_id, now):
    try:
        lock_account(db)
        run = db.get(PaperRun, run_id)
        if run is None:
            raise ValueError("Unknown paper run")
        if run.status == "RUNNING":
            run.status, run.stopped_at = "STOPPED", now
            db.add(Event(kind="paper_recording_stopped", detail={"run": run.id}))
        db.commit()
    except Exception:
        db.rollback()
        raise


def record_sample(db, settings, now, worker_id, sequence, monotonic_ns, error_type=None):
    """One sample per worker cycle. Gaps, restarts and clock jumps earn no observed duration."""
    try:
        account = lock_account(db)
        run = db.scalar(select(PaperRun).where(PaperRun.account_id == "PAPER", PaperRun.status == "RUNNING"))
        if run is None:
            db.rollback()
            return None
        sample_id = digest([run.id, worker_id, sequence])
        if db.get(PaperSample, sample_id):
            db.rollback()
            return sample_id
        previous = db.scalar(
            select(PaperSample)
            .where(PaperSample.run_id == run.id)
            .order_by(PaperSample.time.desc(), PaperSample.id.desc())
            .limit(1)
        )
        issues = []
        if settings.demo_mode:
            issues.append("FIXTURE_MODE")
        if settings.trading_mode != "PAPER" or run.contract["runtime"] != runtime_contract(settings):
            issues.append("CONFIGURATION_CHANGED")
        if not account.reconciled or account.suspended:
            issues.append("ACCOUNT_NOT_READY")
        if error_type:
            issues.append("WORKER_ERROR")
        orders = db.scalars(select(OrderRow).where(OrderRow.mode == "PAPER")).all()
        open_orders = [o for o in orders if o.state in ACTIVE]
        scopes = {(s["symbol"], s["source"]) for s in run.contract["scopes"]}
        scopes.update((o.symbol, o.execution.get("source", "UNKNOWN")) for o in open_orders)
        feeds = []
        for symbol, source in sorted(scopes):
            quote = db.get(QuoteRow, symbol)
            age = (now - aware(quote.time)).total_seconds() if quote else None
            fresh = bool(quote and quote.source == source and -2 <= age <= settings.max_quote_age_seconds)
            feeds.append(
                {
                    "symbol": symbol,
                    "source": source,
                    "fresh": fresh,
                    "age_seconds": age,
                    "quote_time": aware(quote.time).isoformat() if quote else None,
                }
            )
        if not all(feed["fresh"] for feed in feeds):
            issues.append("FEED_UNAVAILABLE_OR_STALE")
        deployments = sorted(
            db.scalars(
                select(PaperDeploymentSlot.deployment_id).where(
                    PaperDeploymentSlot.account_id == "PAPER", PaperDeploymentSlot.deployment_id.is_not(None)
                )
            ).all()
        )
        for deployment_id in deployments:
            deployment = db.get(PaperDeployment, deployment_id)
            try:
                _, _, contract = validate_evidence(
                    db, deployment.model_id, deployment.review_id, Path(settings.model_artifact_dir), settings
                )
                if contract != deployment.contract:
                    raise ModelUnavailable("Changed deployment contract")
                scope = contract["scope"]
                if (scope["symbol"], scope["source"]) not in scopes:
                    raise ModelUnavailable("Deployment outside recorded feed scope")
                candles = load_candles(db, scope["symbol"], scope["timeframe"], scope["source"], 1)
                if (
                    not candles
                    or not scope["timeframe"]
                    <= (now - candles[-1].time).total_seconds()
                    <= scope["timeframe"] * 2
                ):
                    raise ModelUnavailable("Completed candles unavailable or stale")
            except (ModelUnavailable, ValueError, KeyError, TypeError, ArithmeticError, OSError):
                issues.append("DEPLOYMENT_EVIDENCE_INVALID_OR_UNRECORDED")
        trial = run.contract.get("trial")
        if trial and (deployments != trial["deployment_ids"] or any(issue in issues for issue in (
            "CONFIGURATION_CHANGED", "ACCOUNT_NOT_READY", "DEPLOYMENT_EVIDENCE_INVALID_OR_UNRECORDED"
        ))):
            issues.append("TRIAL_TERMINATION_REQUIRED")
            if not account.suspended:
                account.suspended = True
                db.add(Event(kind="paper_trial_suspended", detail={"run": run.id, "issues": issues}))
        # No active model is an honest infrastructure-only recording, not model soak evidence.
        healthy = not issues
        observed = D(0)
        continuity = "FIRST_SAMPLE"
        wall_delta = None
        if previous:
            wall_delta = (now - aware(previous.time)).total_seconds()
            mono_delta = D(monotonic_ns - int(previous.monotonic_ns)) / D(1_000_000_000)
            if previous.worker_id != worker_id:
                continuity = "WORKER_RESTART_OR_OVERLAP"
            elif sequence != previous.sequence + 1:
                continuity = "SEQUENCE_GAP"
            elif not 0 < wall_delta <= MAX_INTERVAL_SECONDS or not 0 < mono_delta <= MAX_INTERVAL_SECONDS:
                continuity = "TIME_GAP_OR_CLOCK_CHANGE"
            elif abs(D(str(wall_delta)) - mono_delta) > D(2):
                continuity = "CLOCK_CHANGE"
            elif deployments != previous.detail["deployments"]:
                continuity = "DEPLOYMENT_CHANGED"
            else:
                continuity = "CONTIGUOUS"
                if healthy and previous.healthy:
                    observed = min(D(str(wall_delta)), mono_delta).quantize(D(".000001"))
        detail = {
            "issues": issues,
            "feeds": feeds,
            "deployments": deployments,
            "continuity": continuity,
            "wall_delta_seconds": wall_delta,
            "worker_error_type": error_type,
            "balance": str(account.balance),
            "equity": str(account.equity),
            "equity_updated_at": aware(account.updated_at).isoformat(),
            "open_positions": len(open_orders),
            "closed_positions": sum(o.state == "CLOSED" for o in orders),
            "total_fees_paid": str(sum((o.fees_paid for o in orders), D(0))),
            "realized_pnl": str(sum((o.pnl or D(0) for o in orders if o.state == "CLOSED"), D(0))),
            "reserved_risk": str(sum((o.planned_risk for o in open_orders), D(0))),
            "configuration_sha256": digest(runtime_contract(settings)),
        }
        db.add(
            PaperSample(
                id=sample_id,
                run_id=run.id,
                time=now,
                worker_id=worker_id,
                sequence=sequence,
                monotonic_ns=D(monotonic_ns),
                healthy=healthy,
                observed_seconds=observed,
                model_observed_seconds=observed if deployments else D(0),
                continuity_break=continuity not in ("FIRST_SAMPLE", "CONTIGUOUS"),
                detail=detail,
            )
        )
        db.commit()
        return sample_id
    except Exception:
        db.rollback()
        raise


def run_report(db, run_id, now):
    run = db.get(PaperRun, run_id)
    if run is None:
        raise ValueError("Unknown paper run")
    totals = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(PaperSample.observed_seconds), 0),
            func.coalesce(func.sum(PaperSample.model_observed_seconds), 0),
            func.coalesce(func.sum(case((PaperSample.healthy.is_(False), 1), else_=0)), 0),
            func.count(func.distinct(PaperSample.worker_id)),
            func.coalesce(func.sum(case((PaperSample.continuity_break.is_(True), 1), else_=0)), 0),
        ).where(PaperSample.run_id == run_id)
    ).one()
    last = db.scalar(
        select(PaperSample)
        .where(PaperSample.run_id == run_id)
        .order_by(PaperSample.time.desc(), PaperSample.id.desc())
        .limit(1)
    )
    return {
        "id": run.id,
        "status": run.status,
        "classification": run.contract["classification"],
        "started_at": aware(run.started_at).isoformat(),
        "stopped_at": aware(run.stopped_at).isoformat() if run.stopped_at else None,
        "wall_elapsed_seconds": max(
            0, ((aware(run.stopped_at) if run.stopped_at else now) - aware(run.started_at)).total_seconds()
        ),
        "healthy_observed_seconds": str(totals[1]),
        "model_observed_seconds": str(totals[2]),
        "samples": totals[0],
        "unhealthy_samples": totals[3],
        "worker_instances": totals[4],
        "continuity_breaks": totals[5],
        "last_sample_at": aware(last.time).isoformat() if last else None,
        "recorder_stale": last is None
        or not 0 <= (now - aware(last.time)).total_seconds() <= MAX_INTERVAL_SECONDS,
        "latest": last.detail if last else None,
        "execution_approved": False,
        "acceptance_status": "OBSERVATIONS_ONLY",
        "contract": run.contract,
    }
