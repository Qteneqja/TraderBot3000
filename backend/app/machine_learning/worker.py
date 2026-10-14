"""Separate candidate-research process; never blocks the trading worker or promotes models."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update

from app.brokers.reconciliation import account_key
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.machine_learning.learning import queue_due
from app.machine_learning.monitoring import enforce_monitor, monitor_model
from app.machine_learning.outcomes import collect_outcomes
from app.models.tables import Event, LearningRun, PaperDeployment, PaperDeploymentSlot, PracticeAccount


async def learning_worker():
    settings = get_settings()
    worker = str(uuid4())
    child, job = None, None
    while True:
        now = datetime.now(timezone.utc)
        try:
            with SessionLocal() as db:
                collect_outcomes(db)
                models = list(db.scalars(select(PaperDeployment.model_id).join(PaperDeploymentSlot,
                                        PaperDeploymentSlot.deployment_id == PaperDeployment.id)).all())
                practice_key = account_key(settings.oanda_account_id) if settings.oanda_account_id else None
                practice_models = {m for a in db.scalars(select(PracticeAccount).where(PracticeAccount.id == practice_key)).all()
                                   for m in a.approval.get("models", [])}
                db.rollback()
                for model, mode in [(m, "PAPER") for m in models] + [(m, "OANDA_PRACTICE") for m in practice_models]:
                    report = monitor_model(db, model, mode, account_fingerprint=practice_key if mode == "OANDA_PRACTICE" else None)
                    enforce_monitor(db, report, settings)
                    db.rollback()
                queue_due(db, now)
                db.execute(update(LearningRun).where(LearningRun.state == "RUNNING",
                    LearningRun.heartbeat_at < now - timedelta(minutes=2)).values(state="UNKNOWN"))
                db.commit()
                if child is not None:
                    run = db.get(LearningRun, job)
                    if child.returncode is None:
                        if run.state == "RUNNING" and run.worker_id == worker:
                            run.heartbeat_at = now
                            db.commit()
                    else:
                        if (run.state == "RUNNING" and run.worker_id == worker) or run.state == "QUEUED":
                            run.state, run.finished_at = "FAILED", now
                            run.result = {"failure": "CHILD_EXITED_WITHOUT_RESULT", "exit_code": child.returncode}
                            db.commit()
                        child, job = None, None
                if child is None:
                    queued = db.scalar(select(LearningRun).where(LearningRun.state == "QUEUED")
                                       .order_by(LearningRun.scheduled_for).limit(1))
                    if queued:
                        job = queued.id
                        child = await asyncio.create_subprocess_exec(sys.executable, "-m", "app.cli", "learning-run",
                            job, "--worker", worker, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                db.add(Event(kind="learning_worker_heartbeat", detail={"worker": worker, "run": job,
                                                                     "model_promotion": "OPERATOR_ONLY"}))
                db.commit()
        except asyncio.CancelledError:
            if child and child.returncode is None:
                child.terminate()
            raise
        except Exception as exc:
            with SessionLocal() as db:
                db.add(Event(kind="learning_worker_error", detail={"error_type": type(exc).__name__}))
                db.commit()
        await asyncio.sleep(15)


if __name__ == "__main__":
    try:
        asyncio.run(learning_worker())
    except KeyboardInterrupt:
        pass
