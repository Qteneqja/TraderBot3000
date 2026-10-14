import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app import worker


@pytest.mark.parametrize("age_days", [0, 600])
async def test_live_poll_does_not_block_other_markets_on_old_history(monkeypatch, age_days):
    calls, events = [], []
    now = datetime.now(timezone.utc)
    stored = now - timedelta(days=age_days, minutes=2)

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    async def ingest(db, provider, symbol, timeframe, start, end):
        calls.append((symbol, timeframe, start, end))

    async def stop_after_poll(delay):
        raise asyncio.CancelledError()

    monkeypatch.setattr(worker, "SessionLocal", Database)
    monkeypatch.setattr(worker, "load_candles", lambda *args: [SimpleNamespace(time=stored)])
    monkeypatch.setattr(worker, "ingest", ingest)
    monkeypatch.setattr(worker, "record", lambda kind, detail: events.append((kind, detail)))
    monkeypatch.setattr(worker.asyncio, "sleep", stop_after_poll)
    with pytest.raises(asyncio.CancelledError):
        await worker.candles_loop({"coinbase": object()}, [("BTC-USD", "coinbase"), ("ETH-USD", "coinbase")])
    assert len(calls) == 8 and {c[0] for c in calls} == {"BTC-USD", "ETH-USD"}
    for _, timeframe, start, end in calls:
        assert start == max(stored, end - timedelta(seconds=timeframe * 300))
        assert end - start <= timedelta(seconds=timeframe * 300)
    deferred = [event for event in events if event[0] == "market_history_gap_deferred"]
    assert len(deferred) == (8 if age_days else 0)
    assert events[-1][0] == "market_worker_heartbeat"
