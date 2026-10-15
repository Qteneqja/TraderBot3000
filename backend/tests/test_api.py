from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.bootstrap import bootstrap
from app.database.session import Base, get_db, make_engine
from app.main import app


def test_dashboard_and_auth(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bootstrap(db)

    def override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            assert client.get("/health/live").status_code == 200
            assert client.get("/health/ready").status_code == 503  # no migration revision
            overview = client.get("/api/overview").json()
            assert overview["mode"] == "PAPER" and overview["quotes"] == []
            assert client.get("/api/candles").json()["candles"] == []
            assert client.get("/api/data-coverage").json() == []
            assert client.get("/api/practice-status").json() == []
            assert client.get('/api/final-evaluations').json() == []
            assert client.post('/api/final-evaluations').status_code == 405
            learning = client.get("/api/learning").json()
            assert learning['runs'] == learning['schedules'] == learning['outcomes'] == []
            assert learning['promotion'] == 'EXPLICIT_OPERATOR_APPROVAL_ONLY'
            assert client.post('/api/learning').status_code == 405
            assert client.get('/api/models?limit=101').status_code == 422
            assert client.post("/api/admin/suspend").status_code == 503
            assert client.post("/api/live/activate").status_code == 404
            assert len(client.get("/api/strategies").json()) == 6
            assert client.get("/api/paper-deployments").json() == []
            assert client.get("/api/paper-runs").json() == []
            assert client.get("/api/paper-runs/missing/samples").status_code == 404
            assert client.post("/api/paper-deployments").status_code == 405
    finally:
        app.dependency_overrides.clear()


def test_feed_status_requires_fresh_quotes_for_each_instrument(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from app.core.config import Settings
    from app.models.tables import QuoteRow

    engine = make_engine(f"sqlite:///{tmp_path}/feeds.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bootstrap(db)
    settings = Settings(_env_file=None, demo_mode=False, oanda_api_key="test-only-token")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    def override():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            assert client.get("/api/system").json()["oanda"] == "WAITING_FOR_FRESH_QUOTES"
            with Session(engine) as db:
                for symbol, age in (("EUR_USD", 0), ("GBP_USD", 60)):
                    db.add(
                        QuoteRow(
                            symbol=symbol,
                            time=datetime.now(timezone.utc) - timedelta(seconds=age),
                            bid=Decimal("1.1"),
                            ask=Decimal("1.1001"),
                            source="oanda",
                        )
                    )
                db.commit()
            assert client.get("/api/system").json()["oanda"] == "DEGRADED"
            with Session(engine) as db:
                db.get(QuoteRow, "GBP_USD").time = datetime.now(timezone.utc)
                db.commit()
            assert client.get("/api/system").json()["oanda"] == "CONNECTED"
            with Session(engine) as db:
                db.get(QuoteRow, "EUR_USD").source = "fixture"
                db.commit()
            assert client.get("/api/system").json()["oanda"] == "DEGRADED"
    finally:
        app.dependency_overrides.clear()
