from decimal import Decimal as D

import httpx
import pytest

from app.brokers.oanda import OandaPractice
from app.core.config import Settings
from app.market_data.providers import ProviderUnavailable


def test_practice_schema_contains_atomic_protection():
    order = OandaPractice.market_payload("unique", "EUR_USD", D(10), D("1.09"), D("1.13"), D("1.1"))["order"]
    assert order["stopLossOnFill"]["price"] == "1.09"
    assert order["takeProfitOnFill"]["price"] == "1.13"
    assert order["positionFill"] == "OPEN_ONLY" and order["timeInForce"] == "FOK"


async def test_broker_direct_submission_cannot_bypass_risk():
    settings = Settings(
        _env_file=None,
        demo_mode=False,
        trading_mode="OANDA_PRACTICE",
        oanda_api_key="test",
        oanda_account_id="test",
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderUnavailable, match="disabled"):
            await OandaPractice(settings, client).submit()
