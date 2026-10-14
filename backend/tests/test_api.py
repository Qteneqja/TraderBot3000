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
            assert client.post("/api/admin/suspend").status_code == 503
            assert client.post("/api/live/activate").status_code == 404
            assert len(client.get("/api/strategies").json()) == 6
    finally:
        app.dependency_overrides.clear()
