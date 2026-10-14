from datetime import timedelta
from decimal import Decimal as D

import pytest
import test_paper_faults
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.execution.recorder import record_sample, run_report, start_run, stop_run
from app.market_data.store import save_quote
from app.models.tables import PaperRun, PaperSample

store = test_paper_faults.store


def test_recorder_restart_gaps_clock_jumps_and_duplicate_samples(store):
    engine, _, quote, settings, now = store
    settings = settings.model_copy(update={"demo_mode": False})
    quote = quote.model_copy(update={"source": "oanda"})
    with Session(engine) as db:
        run_id = start_run(db, settings, [quote.symbol], now)
        assert start_run(db, settings, [quote.symbol], now) == run_id

    def sample(seconds, worker, sequence, monotonic, error=None):
        when = now + timedelta(seconds=seconds)
        with Session(engine) as db:
            # Existing fixture quote has the same initial timestamp; use a genuinely newer update.
            fresh_time = when + timedelta(microseconds=1)
            save_quote(db, quote.model_copy(update={"time": fresh_time}), fresh_time)
            return record_sample(db, settings, when, worker, sequence, monotonic * 1_000_000_000, error)

    sample(0, "worker-a", 0, 100)
    sample(10, "worker-a", 1, 110)
    assert sample(10, "worker-a", 1, 110) == sample(10, "worker-a", 1, 110)
    sample(20, "worker-b", 0, 200)  # Restart earns no credit for the interval.
    sample(30, "worker-b", 1, 210)
    sample(100, "worker-b", 2, 280)  # Missing cycles are visible, never interpolated.
    sample(110, "worker-b", 3, 281)  # Wall time and monotonic clock disagree.
    sample(120, "worker-b", 4, 291, "InjectedFailure")
    sample(130, "worker-b", 5, 301)
    with Session(engine) as db:
        report = run_report(db, run_id, now + timedelta(seconds=131))
        assert D(report["healthy_observed_seconds"]) == 20
        assert D(report["model_observed_seconds"]) == 0
        assert report["worker_instances"] == 2 and report["continuity_breaks"] == 3
        assert report["samples"] == 8 and report["unhealthy_samples"] == 1
        assert not report["execution_approved"] and not report["recorder_stale"]
        assert run_report(db, run_id, now + timedelta(seconds=170))["recorder_stale"]
        db.rollback()
        stop_run(db, run_id, now + timedelta(seconds=180))
        assert (
            record_sample(db, settings, now + timedelta(seconds=190), "worker-b", 6, 311_000_000_000) is None
        )
        assert db.get(PaperRun, run_id).status == "STOPPED"


def test_fixtures_stale_feeds_and_config_changes_never_count_as_soak(store):
    engine, _, quote, settings, now = store
    with Session(engine) as db:
        run_id = start_run(db, settings, [quote.symbol], now)
        record_sample(db, settings, now, "test", 0, 10_000_000_000)
        record_sample(db, settings, now + timedelta(seconds=10), "test", 1, 20_000_000_000)
        changed = settings.model_copy(update={"demo_mode": False})
        record_sample(db, changed, now + timedelta(seconds=20), "test", 2, 30_000_000_000)
        report = run_report(db, run_id, now + timedelta(seconds=20))
        assert report["classification"] == "FIXTURE_DIAGNOSTIC"
        assert D(report["healthy_observed_seconds"]) == 0
        assert report["unhealthy_samples"] == 3
        assert "CONFIGURATION_CHANGED" in report["latest"]["issues"]
        assert "FEED_UNAVAILABLE_OR_STALE" in report["latest"]["issues"]
        db.rollback()
        with pytest.raises(ValueError, match="Stop the running recorder"):
            start_run(db, changed, [quote.symbol], now)


def test_recorder_failed_commit_can_retry_without_partial_sample(store):
    engine, _, quote, settings, now = store
    with Session(engine) as db:
        run_id = start_run(db, settings, [quote.symbol], now)
        commit = db.commit

        def fault():
            raise RuntimeError("recorder crash")

        db.commit = fault
        with pytest.raises(RuntimeError, match="recorder crash"):
            record_sample(db, settings, now, "test", 0, 10_000_000_000)
        db.commit = commit
        record_sample(db, settings, now, "test", 0, 10_000_000_000)
        assert (
            db.scalar(select(func.count()).select_from(PaperSample).where(PaperSample.run_id == run_id)) == 1
        )
