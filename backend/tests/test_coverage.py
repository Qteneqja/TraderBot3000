from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.database.bootstrap import bootstrap
from app.database.session import Base, make_engine
from app.market_data.coverage import canada_closed, coverage_report, session_closed, weekly_closed
from app.market_data.fixtures import demo_candles
from app.market_data.store import insert_candles, load_candles


def test_isolated_dates_cannot_pass_usable_history():
    rows = demo_candles(symbol="BTC-USD", count=100)
    rows = [c.model_copy(update={"source": "coinbase"}) for c in rows]
    rows += [c.model_copy(update={"time": c.time + timedelta(days=365)}) for c in rows]
    report = coverage_report(rows, rows[0].time, rows[-1].time + timedelta(minutes=5),
                             rows[-1].time + timedelta(days=1))
    assert report["checks"]["minimum_calendar_span"]
    assert not report["research_ready"] and report["usable_days"] < 180
    assert report["unexplained_missing_count"] > 100000


def test_weekly_calendar_uses_new_york_dst_not_utc_weekday():
    assert weekly_closed(datetime(2026, 3, 6, 22, tzinfo=timezone.utc))
    assert not weekly_closed(datetime(2026, 3, 8, 21, tzinfo=timezone.utc))
    assert weekly_closed(datetime(2026, 11, 1, 21, tzinfo=timezone.utc))
    assert not weekly_closed(datetime(2026, 11, 1, 22, tzinfo=timezone.utc))


def test_duplicates_and_fixtures_never_ready():
    rows = demo_candles(count=100)
    report = coverage_report(rows + [rows[-1]], rows[0].time,
                             rows[-1].time + timedelta(minutes=5), rows[-1].time + timedelta(days=1),
                             minimum_days=0)
    assert report["duplicate_candles"] == 1 and not report["research_ready"]
    assert not report["checks"]["real_provider"]


def test_canada_breaks_partial_candles_holidays_and_dst():
    def utc(value):
        return datetime.fromisoformat(value)

    assert canada_closed(utc("2026-03-09T20:59:00+00:00"))
    assert canada_closed(utc("2026-03-09T21:04:00+00:00"))
    assert not canada_closed(utc("2026-03-09T21:05:00+00:00"))
    assert canada_closed(utc("2026-11-02T21:59:00+00:00"))
    assert session_closed(utc("2026-03-09T21:00:00+00:00"), 300, "CA")
    assert not session_closed(utc("2026-03-09T20:55:00+00:00"), 300, "CA")
    assert not session_closed(utc("2026-03-09T21:00:00+00:00"), 900, "CA")
    assert canada_closed(utc("2025-12-25T18:00:00+00:00"))
    assert not canada_closed(utc("2025-12-25T22:05:00+00:00"))
    assert canada_closed(utc("2025-12-24T23:00:00+00:00"))
    assert canada_closed(utc("2026-01-01T15:00:00+00:00"))
    # No invented 2024 holiday override: retained for explicit unresolved-gap review.
    assert not canada_closed(utc("2024-12-25T15:00:00+00:00"))


def test_usable_days_do_not_excuse_incomplete_sessions():
    rows = demo_candles(symbol="BTC-USD", timeframe=900, count=400)
    rows = [c.model_copy(update={"source": "coinbase"}) for c in rows]
    report = coverage_report(rows[:200] + rows[260:], rows[0].time,
                             rows[-1].time + timedelta(minutes=15), rows[-1].time + timedelta(days=1),
                             minimum_days=1)
    assert report["checks"]["minimum_usable_days"]
    assert not report["checks"]["session_completeness"]
    assert not report["research_ready"]
    with pytest.raises(ValueError, match="future"):
        coverage_report(rows, rows[0].time, rows[-1].time + timedelta(minutes=15), rows[0].time)


def test_bounded_database_loading_excludes_old_and_new_rows():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    rows = demo_candles(count=100)
    with Session(engine) as db:
        bootstrap(db)
        insert_candles(db, rows, rows[-1].time + timedelta(days=1))
        db.commit()
        result = load_candles(db, "EUR_USD", 300, "fixture", 1000,
                              start=rows[10].time, end=rows[20].time)
        assert [r.time for r in result] == [r.time for r in rows[10:20]]
        with pytest.raises(ValueError):
            load_candles(db, "EUR_USD", 300, "fixture", start=rows[0].time)
        with pytest.raises(ValueError):
            load_candles(db, "EUR_USD", 300, "fixture", start=rows[0].time.replace(tzinfo=None), end=rows[1].time)


def test_api_counts_full_series_without_conferring_qualification(tmp_path):
    from fastapi.testclient import TestClient

    from app.database.session import get_db
    from app.main import app

    engine = make_engine(f"sqlite:///{tmp_path}/coverage-api.db")
    Base.metadata.create_all(engine)
    rows = demo_candles(count=1001)
    with Session(engine) as db:
        bootstrap(db)
        insert_candles(db, rows, rows[-1].time + timedelta(days=1))
        insert_candles(db, [c.model_copy(update={"source": "oanda"}) for c in rows[:3]],
                       rows[-1].time + timedelta(days=1))
        db.commit()

    def override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            report = client.get("/api/data-coverage").json()
        assert {r["source"]: r["candles"] for r in report} == {"fixture": 1001, "oanda": 3}
        assert all(r["qualification"] == "NOT_ASSESSED" for r in report)
        assert report[0]["classification"] == "SYNTHETIC_FIXTURE"
    finally:
        app.dependency_overrides.clear()
