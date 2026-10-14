"""Read one public Coinbase quote. This never submits an order or writes credentials."""

import asyncio

import httpx
from app.market_data.providers import CoinbaseData


async def main():
    async with httpx.AsyncClient() as client:
        stream = CoinbaseData(client).quotes(["BTC-USD"])
        try:
            quote = await asyncio.wait_for(anext(stream), timeout=30)
            print(quote.model_dump_json())
        finally:
            await stream.aclose()


if __name__ == "__main__":
    asyncio.run(main())
