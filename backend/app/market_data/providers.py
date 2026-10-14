import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import websockets

from app.core.config import Settings
from app.schemas.domain import Candle, Quote

OANDA_GRANULARITY = {60: "M1", 300: "M5", 900: "M15", 3600: "H1", 14400: "H4"}
COINBASE_GRANULARITY = {60: "ONE_MINUTE", 300: "FIVE_MINUTE", 900: "FIFTEEN_MINUTE", 3600: "ONE_HOUR"}


class ProviderUnavailable(RuntimeError):
    pass


async def read_json(client: httpx.AsyncClient, url: str, **kwargs):
    """GET only: bounded retries for throttling and transient transport failures."""
    for attempt in range(5):
        try:
            response = await client.get(url, **kwargs)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 4:
                    response.raise_for_status()
                retry = response.headers.get("retry-after", "0")
                delay = float(retry) if retry.replace(".", "", 1).isdigit() else 0
                await asyncio.sleep(min(30, max(delay, 2**attempt)))
                continue
            response.raise_for_status()
            return response.json()
        except httpx.TransportError:
            if attempt == 4:
                raise ProviderUnavailable("Provider transport failed; retry later") from None
            await asyncio.sleep(2**attempt)
    raise ProviderUnavailable("Provider unavailable")


class OandaData:
    base = "https://api-fxpractice.oanda.com"

    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings, self.client = settings, client

    def headers(self):
        key = self.settings.oanda_api_key.get_secret_value()
        if not key:
            raise ProviderUnavailable("Set OANDA_API_KEY to access OANDA practice market data")
        return {"Authorization": f"Bearer {key}"}

    async def candles(self, symbol: str, timeframe: int, start: datetime, end: datetime):
        granularity = OANDA_GRANULARITY[timeframe]
        cursor = start
        while cursor < end:
            until = min(end, cursor + timedelta(seconds=timeframe * 4500))
            data = await read_json(
                self.client,
                f"{self.base}/v3/instruments/{symbol}/candles",
                headers=self.headers(),
                params={
                    "from": cursor.isoformat(),
                    "to": until.isoformat(),
                    "granularity": granularity,
                    "price": "MBA",
                },
            )
            batch = []
            for raw in data["candles"]:
                if not raw["complete"]:
                    continue
                mid = raw["mid"]
                batch.append(
                    Candle(
                        symbol=symbol,
                        timeframe=timeframe,
                        time=raw["time"],
                        open=mid["o"],
                        high=mid["h"],
                        low=mid["l"],
                        close=mid["c"],
                        volume=raw["volume"],
                        source="oanda",
                        provenance={
                            "bid": raw.get("bid"),
                            "ask": raw.get("ask"),
                            "volume_type": "tick_count",
                            "environment": "practice",
                        },
                    )
                )
            yield sorted(batch, key=lambda c: c.time), until
            cursor = until

    async def quotes(self, symbols: list[str]):
        account = self.settings.oanda_account_id
        if not account:
            raise ProviderUnavailable("Set OANDA_ACCOUNT_ID for pricing streams")
        url = f"https://stream-fxpractice.oanda.com/v3/accounts/{account}/pricing/stream"
        async with self.client.stream(
            "GET", url, headers=self.headers(), params={"instruments": ",".join(symbols)}, timeout=20
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                event = json.loads(line)
                if event.get("type") == "PRICE" and event.get("tradeable"):
                    yield Quote(
                        symbol=event["instrument"],
                        time=event["time"],
                        bid=event["bids"][0]["price"],
                        ask=event["asks"][0]["price"],
                        source="oanda",
                    )


class CoinbaseData:
    base = "https://api.coinbase.com/api/v3/brokerage/market/products"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def candles(self, symbol: str, timeframe: int, start: datetime, end: datetime):
        granularity = COINBASE_GRANULARITY[timeframe]
        cursor = start
        while cursor < end:
            until = min(end, cursor + timedelta(seconds=timeframe * 300))
            data = await read_json(
                self.client,
                f"{self.base}/{symbol}/candles",
                params={
                    "start": int(cursor.timestamp()),
                    "end": int(until.timestamp()),
                    "granularity": granularity,
                    "limit": 350,
                },
            )
            batch = [
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    time=datetime.fromtimestamp(int(c["start"]), timezone.utc),
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c["volume"],
                    source="coinbase",
                    provenance={"volume_type": "traded_base", "bid_ask_available": False},
                )
                for c in data["candles"]
                if int(c["start"]) + timeframe <= end.timestamp()
            ]
            yield sorted(batch, key=lambda c: c.time), until
            cursor = until

    async def quotes(self, symbols: list[str]):
        async with websockets.connect(
            "wss://advanced-trade-ws.coinbase.com", ping_interval=10, ping_timeout=10, max_size=2**20
        ) as ws:
            for channel in ("heartbeats", "ticker"):
                await ws.send(json.dumps({"type": "subscribe", "product_ids": symbols, "channel": channel}))
            while True:
                event = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
                if event.get("channel") == "ticker":
                    for update in event.get("events", []):
                        for tick in update.get("tickers", []):
                            if tick.get("best_bid") and tick.get("best_ask"):
                                yield Quote(
                                    symbol=tick["product_id"],
                                    time=event["timestamp"],
                                    bid=tick["best_bid"],
                                    ask=tick["best_ask"],
                                    source="coinbase",
                                )
