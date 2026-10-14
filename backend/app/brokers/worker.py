"""Practice worker: reconciliation and protection precede any independently approved entry."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.brokers.gateway import close_once, reserve, send_once
from app.brokers.oanda import OandaPractice
from app.brokers.reconciliation import account_key, reconcile_practice
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.market_data.store import load_candles
from app.models.tables import Event, Instrument, PracticeAccount, PracticeOrder
from app.notifications.telegram import deliver
from app.schemas.domain import aware
from app.strategies.registry import evaluate


async def practice_worker():
    from app.worker import record

    settings = get_settings()
    worker_id, started = str(uuid4()), False
    async with httpx.AsyncClient(timeout=30) as client:
        adapter = OandaPractice(settings, client)
        key = account_key(settings.oanda_account_id)
        while True:
            try:
                with SessionLocal() as db:
                    result = await reconcile_practice(db, adapter, settings.oanda_account_id)
                    account = db.get(PracticeAccount, key)
                    orders = db.scalars(select(PracticeOrder).where(PracticeOrder.account_id == key)).all()
                    if not started:
                        db.add(Event(kind="practice_worker_started", detail={"worker_id": worker_id,
                                     "reconciled": result["reconciled"],
                                     "open_orders": [o.id for o in orders if o.state == "FILLED"]}))
                        db.commit()
                        started = True
                    authority = dict(account.approval)
                    pending = [(o.id, o.state, aware(o.created_at), int(o.candidate["timeframe"])) for o in orders
                               if o.state in ("FILLED", "QUARANTINED", "RESERVED")]
                now = datetime.now(timezone.utc)
                for order_id, state, opened, timeframe in pending:
                    with SessionLocal() as db:
                        if state == "QUARANTINED" and authority.get("emergency_policy") == "CLOSE_OWNED_EXPOSURE_ON_MISSING_PROTECTION":
                            await close_once(db, adapter, settings, order_id, emergency=True)
                        elif state == "FILLED" and now >= opened + timedelta(seconds=timeframe * 12):
                            await close_once(db, adapter, settings, order_id)
                        elif state == "RESERVED":
                            await send_once(db, adapter, settings, order_id)
                with SessionLocal() as db:
                    account = db.get(PracticeAccount, key)
                    enabled = bool(account and account.approval and account.reconciled and not account.suspended)
                    instruments = db.scalars(select(Instrument).where(Instrument.symbol.in_(("EUR_USD", "GBP_USD")))).all()
                if enabled:
                    for instrument in instruments:
                        with SessionLocal() as db:
                            rows = load_candles(db, instrument.symbol, 300, "oanda")
                        for candidate in evaluate(rows, datetime.now(timezone.utc), instrument.tick_size):
                            with SessionLocal() as db:
                                order_id = await reserve(db, adapter, settings, candidate)
                                if order_id:
                                    await send_once(db, adapter, settings, order_id)
                if settings.enable_notifications:
                    with SessionLocal() as db:
                        await deliver(db, settings, client)
                record("trading_worker_heartbeat", {"mode": "OANDA_PRACTICE", "worker_id": worker_id,
                       "gateway": "APPROVED" if authority else "AWAITING_OPERATOR_APPROVAL",
                       "reconciled": result["reconciled"], "suspended": result["suspended"]})
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                record("trading_worker_error", {"mode": "OANDA_PRACTICE", "error_type": type(exc).__name__})
            await asyncio.sleep(10)
