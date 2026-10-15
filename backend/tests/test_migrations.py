from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.database.bootstrap import bootstrap
from app.database.session import make_engine
from app.execution.paper import valid_execution
from app.models.tables import OrderRow


def test_upgrade_preserves_legacy_orders_and_quarantines_missing_costs(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path}/migration.db")
    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    command.upgrade(config, "0002")
    engine = make_engine(settings.database_url)
    with Session(engine) as db:
        bootstrap(db)
        db.execute(
            text("""
            INSERT INTO trade_signals(id,time,symbol,strategy,status,payload,reasons)
            VALUES ('legacy','2025-01-01','EUR_USD','trend','APPROVED','{}','[]')
        """)
        )
        db.execute(
            text("""
            INSERT INTO orders(id,signal_id,mode,state,symbol,direction,units,entry,stop,target,
                               planned_risk,opened_at,expires_at)
            VALUES ('legacy','legacy','PAPER','FILLED','EUR_USD','LONG',1,1.1,1.09,1.12,
                    0.01,'2025-01-01','2025-01-02')
        """)
        )
        db.commit()
    command.upgrade(config, "head")
    command.check(config)
    with Session(engine) as db:
        legacy = db.get(OrderRow, "legacy")
        assert legacy.state == "FILLED" and legacy.units == 1
        assert legacy.execution == {} and legacy.fees_paid == 0 and legacy.financing_bars == 0
        assert not valid_execution(legacy)
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0008"
    assert "model_predictions" in inspect(engine).get_table_names()
    assert "model_reviews" in inspect(engine).get_table_names()
    assert {"paper_deployments", "paper_deployment_slots", "paper_runs", "paper_samples"} <= set(
        inspect(engine).get_table_names()
    )
