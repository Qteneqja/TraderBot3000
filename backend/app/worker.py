import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.execution.paper import monitor, reconcile, submit
from app.execution.recorder import record_sample
from app.machine_learning.registry import record_prediction, shadow_predict
from app.market_data.providers import CoinbaseData, OandaData
from app.market_data.store import ingest, load_candles, save_quote
from app.models.tables import Event, Instrument, QuoteRow
from app.schemas.domain import Quote, aware
from app.strategies.registry import evaluate

logger = logging.getLogger("aegis.worker")


def record(kind, detail):
    with SessionLocal() as db:
        db.add(Event(kind=kind, detail=detail))
        db.commit()


async def stream_loop(provider, symbols):
    delay = 1
    while True:
        try:
            async for quote in provider.quotes(symbols):
                with SessionLocal() as db:
                    save_quote(db, quote, datetime.now(timezone.utc))
                delay = 1
            raise ConnectionError("Stream ended")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            record("feed_disconnected", {"symbols": symbols, "error_type": type(exc).__name__})
            await asyncio.sleep(delay)
            delay = min(60, delay * 2)


async def candles_loop(providers, instruments):
    while True:
        now = datetime.now(timezone.utc)
        for symbol, provider_name in instruments:
            for timeframe in (60, 300, 900, 3600):
                end = datetime.fromtimestamp(int(now.timestamp()) // timeframe * timeframe, timezone.utc)
                with SessionLocal() as db:
                    existing = load_candles(db, symbol, timeframe, provider_name, 1)
                    recent_start = end - timedelta(seconds=timeframe * 300)
                    start = max(existing[-1].time, recent_start) if existing else recent_start
                    if existing and existing[-1].time < recent_start:
                        record(
                            "market_history_gap_deferred",
                            {
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "source": provider_name,
                                "last_stored": existing[-1].time.isoformat(),
                                "recent_start": recent_start.isoformat(),
                                "reason": "Live polling is bounded; use download for historical backfill",
                            },
                        )
                    try:
                        await ingest(db, providers[provider_name], symbol, timeframe, start, end)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        record("ingestion_failed", {"symbol": symbol, "error_type": type(exc).__name__})
        record("market_worker_heartbeat", {"status": "poll_complete"})
        await asyncio.sleep(60)


async def market_worker():
    s = get_settings()
    if s.demo_mode:
        while True:
            record("market_worker_heartbeat", {"status": "OFFLINE_FIXTURES", "live_feed": False})
            await asyncio.sleep(60)
    async with httpx.AsyncClient(timeout=20) as client:
        providers = {"coinbase": CoinbaseData(client), "oanda": OandaData(s, client)}
        with SessionLocal() as db:
            instruments = [
                (i.symbol, i.provider)
                for i in db.scalars(select(Instrument)).all()
                if i.provider != "oanda" or s.oanda_api_key.get_secret_value()
            ]
        tasks = [candles_loop(providers, instruments)]
        for provider_name, provider in providers.items():
            symbols = [symbol for symbol, name in instruments if name == provider_name]
            if symbols:
                tasks.append(stream_loop(provider, symbols))
        await asyncio.gather(*tasks)


async def trading_worker():
    settings = get_settings()
    worker_id, sequence = str(uuid4()), 0
    if settings.trading_mode == "OANDA_PRACTICE":
        raise RuntimeError("Practice gateway is not enabled; complete the readiness checklist first")
    with SessionLocal() as db:
        reconcile(db, datetime.now(timezone.utc))
    while True:
        now = datetime.now(timezone.utc)
        error_type = None
        try:
            with SessionLocal() as db:
                monitor(db, settings, now)
            if not settings.demo_mode:
                with SessionLocal() as db:
                    instruments = list(db.scalars(select(Instrument)).all())
                for instrument in instruments:
                    with SessionLocal() as db:
                        q = db.get(QuoteRow, instrument.symbol)
                        candles = load_candles(db, instrument.symbol, 300, instrument.provider)
                        quote = (
                            Quote(symbol=q.symbol, time=aware(q.time), bid=q.bid, ask=q.ask, source=q.source)
                            if q
                            else None
                        )
                    if quote:
                        for candidate in evaluate(candles, now, instrument.tick_size):
                            with SessionLocal() as db:
                                shadow = shadow_predict(
                                    db, candidate, quote, Path(settings.model_artifact_dir)
                                )
                                if shadow:
                                    record_prediction(db, candidate, quote, shadow)
                                    candidate = candidate.model_copy(update={"shadow_prediction": shadow})
                                else:
                                    db.rollback()
                                submit(db, candidate, quote, settings, now)
            record(
                "trading_worker_heartbeat",
                {
                    "mode": settings.trading_mode,
                    "demo": settings.demo_mode,
                    "model": "ACCOUNT_SCOPED_PAPER_DEPLOYMENT_GATE",
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error_type = type(exc).__name__
            record("trading_worker_error", {"error_type": error_type})
        try:
            with SessionLocal() as db:
                record_sample(
                    db,
                    settings,
                    datetime.now(timezone.utc),
                    worker_id,
                    sequence,
                    time.monotonic_ns(),
                    error_type,
                )
        except Exception as exc:
            record("paper_recorder_error", {"error_type": type(exc).__name__})
        sequence += 1
        if sequence % 360 == 0:
            try:
                from app.execution.trials import export_periodic_reports

                with SessionLocal() as db:
                    export_periodic_reports(db, datetime.now(timezone.utc), "data/reports")
            except Exception as exc:
                record("paper_trial_report_error", {"error_type": type(exc).__name__})
        await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(market_worker() if len(sys.argv) > 1 and sys.argv[1] == "market" else trading_worker())
    except KeyboardInterrupt:
        pass
