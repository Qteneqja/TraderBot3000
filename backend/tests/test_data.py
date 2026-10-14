from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.bootstrap import bootstrap
from app.database.session import Base, make_engine
from app.market_data.fixtures import demo_candles
from app.market_data.providers import CoinbaseData, OandaData, ProviderUnavailable
from app.market_data.quality import inspect_candles
from app.market_data.store import insert_candles
from app.models.tables import CandleRow
from app.schemas.domain import Candle, Quote


def test_quality_rejects_duplicates_and_future():
    rows = demo_candles(count=3)
    assert not inspect_candles(rows + [rows[-1]], datetime.now(timezone.utc))["valid"]
    assert not inspect_candles(rows, rows[-1].time)["valid"]
    assert inspect_candles([rows[0], rows[2]], datetime.now(timezone.utc))["gaps"]


def test_invalid_prices():
    c = demo_candles(count=1)[0].model_dump()
    with pytest.raises(ValidationError):
        Candle(**(c | {"low": Decimal(10)}))
    with pytest.raises(ValidationError):
        Candle(**(c | {"close": Decimal("NaN")}))
    with pytest.raises(ValidationError):
        Quote(symbol="EUR_USD", time=c["time"], bid=2, ask=1, source="test")


def test_ingest_idempotent():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bootstrap(db)
        for _ in range(2):
            insert_candles(db, demo_candles(count=20), datetime.now(timezone.utc))
            db.commit()
        assert db.scalar(select(func.count()).select_from(CandleRow)) == 20


async def test_coinbase_normalization():
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)

    def handler(request):
        assert "/market/products/BTC-USD/candles" in str(request.url)
        return httpx.Response(
            200,
            json={
                "candles": [
                    {
                        "start": str(int(start.timestamp())),
                        "open": "10",
                        "high": "12",
                        "low": "9",
                        "close": "11",
                        "volume": "2",
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        batches = [
            batch
            async for batch, _ in CoinbaseData(client).candles(
                "BTC-USD", 300, start, start + timedelta(minutes=5)
            )
        ]
    assert batches[0][0].close == 11
    assert batches[0][0].source == "coinbase"


async def test_missing_oanda_key_actionable():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderUnavailable, match="OANDA_API_KEY"):
            OandaData(Settings(_env_file=None), client).headers()
