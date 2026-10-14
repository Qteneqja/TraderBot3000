import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.core.config import Settings
from app.database.session import Base, make_engine
from app.models import tables  # noqa: F401


def test_live_cannot_be_enabled():
    assert Settings(_env_file=None).trading_mode == "PAPER"
    for values in (
        {"trading_mode": "LIVE"},
        {"enable_live_trading": True},
        {"trading_mode": "OANDA_PRACTICE", "demo_mode": True},
    ):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **values)


def test_schema_has_durable_orders():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    assert {"orders", "order_events", "market_candles", "account_snapshots"} <= set(
        inspect(engine).get_table_names()
    )
