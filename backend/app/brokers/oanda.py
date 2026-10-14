"""Practice-only transport. Not wired to autonomous execution until account validation is complete."""

from decimal import Decimal

import httpx

from app.core.config import Settings
from app.market_data.providers import OandaData, ProviderUnavailable, read_json


class SubmissionUncertain(RuntimeError):
    """Reconcile by client ID and transactions; never resubmit on this exception."""


class OandaPractice:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        if settings.trading_mode != "OANDA_PRACTICE" or settings.demo_mode:
            raise ValueError("Practice transport requires OANDA_PRACTICE and non-fixture data")
        if not settings.oanda_account_id:
            raise ProviderUnavailable("Set OANDA_ACCOUNT_ID")
        self.client = client
        self.headers = OandaData(settings, client).headers()
        self.base = f"https://api-fxpractice.oanda.com/v3/accounts/{settings.oanda_account_id}"

    async def snapshot(self):
        account = await read_json(self.client, f"{self.base}/summary", headers=self.headers)
        orders = await read_json(self.client, f"{self.base}/pendingOrders", headers=self.headers)
        trades = await read_json(self.client, f"{self.base}/openTrades", headers=self.headers)
        return {"account": account["account"], "orders": orders["orders"], "trades": trades["trades"]}

    async def lookup_order(self, client_id: str):
        return await read_json(self.client, f"{self.base}/orders/@{client_id}", headers=self.headers)

    async def transactions(self, since_id: str):
        return await read_json(
            self.client, f"{self.base}/transactions/sinceid", headers=self.headers, params={"id": since_id}
        )

    async def instruments(self):
        return await read_json(self.client, f"{self.base}/instruments", headers=self.headers)

    @staticmethod
    def market_payload(
        client_id: str, symbol: str, units: Decimal, stop: Decimal, target: Decimal, price_bound: Decimal
    ):
        if not units or min(stop, target, price_bound) <= 0:
            raise ValueError("Positive protective prices and nonzero units required")
        if not ((stop < price_bound < target) if units > 0 else (target < price_bound < stop)):
            raise ValueError("Invalid protection direction")
        return {
            "order": {
                "type": "MARKET",
                "instrument": symbol,
                "units": str(units),
                "timeInForce": "FOK",
                "positionFill": "OPEN_ONLY",
                "priceBound": str(price_bound),
                "clientExtensions": {"id": client_id},
                "tradeClientExtensions": {"id": client_id},
                "stopLossOnFill": {"price": str(stop), "timeInForce": "GTC"},
                "takeProfitOnFill": {"price": str(target), "timeInForce": "GTC"},
            }
        }

    async def submit(self, *args, **kwargs):
        # Fail closed until durable broker reservation, transaction reconciliation,
        # account currency conversion, and protective-order verification are integrated.
        raise ProviderUnavailable("Practice submission disabled pending broker gateway acceptance tests")

    async def close_trade(self, trade_id: str, units: Decimal):
        if units <= 0:
            raise ValueError("Close units must be positive")
        # Trade-specific closure cannot reverse an aggregate position. Never automatically retry PUT.
        try:
            response = await self.client.put(
                f"{self.base}/trades/{trade_id}/close", headers=self.headers, json={"units": str(units)}
            )
        except httpx.TransportError:
            raise SubmissionUncertain("Closure outcome unknown; reconcile before further action") from None
        response.raise_for_status()
        return response.json()
