import asyncio

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import Base, make_engine
from app.models.tables import Notification
from app.notifications.telegram import deliver, enqueue


def test_two_deliverers_claim_each_notification_once(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/notifications.db")
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token="test-only", telegram_chat_id="test-only")
    sent = []

    async def second(request):
        sent.append(request.content)
        return httpx.Response(200, json={"ok": True})

    async def first(request):
        sent.append(request.content)
        with Session(engine) as other:
            async with httpx.AsyncClient(transport=httpx.MockTransport(second)) as client:
                await deliver(other, settings, client)
        return httpx.Response(200, json={"ok": True})

    async def run():
        with Session(engine) as db:
            enqueue(db, "a", "first")
            enqueue(db, "b", "second")
            async with httpx.AsyncClient(transport=httpx.MockTransport(first)) as client:
                await deliver(db, settings, client)
            assert len(sent) == len(set(sent)) == 2
            assert all(n.status == "DELIVERED" and n.attempts == 1 for n in db.scalars(select(Notification)))

    asyncio.run(run())


def test_ambiguous_timeout_is_not_retried(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/timeout.db")
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token="test-only", telegram_chat_id="test-only")
    calls = []

    def fail(request):
        calls.append(1)
        raise httpx.ReadTimeout("mock timeout")

    async def run():
        with Session(engine) as db:
            enqueue(db, "a", "test")
            async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
                await deliver(db, settings, client)
                await deliver(db, settings, client)
            assert db.get(Notification, "a").status == "UNKNOWN" and len(calls) == 1

    asyncio.run(run())
