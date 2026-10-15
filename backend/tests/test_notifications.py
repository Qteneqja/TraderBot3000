import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import Base, make_engine
from app.models.tables import Notification
from app.notifications.telegram import connectivity_test, deliver, enqueue, status


def test_two_deliverers_claim_each_notification_once(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/notifications.db")
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token="test-only", telegram_chat_id="test-only")
    sent = []

    async def second(request):
        sent.append(request.content)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1, "chat": {"id": 123}}})

    async def first(request):
        sent.append(request.content)
        with Session(engine) as other:
            async with httpx.AsyncClient(transport=httpx.MockTransport(second)) as client:
                await deliver(other, settings, client)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 2, "chat": {"id": 123}}})

    async def run():
        with Session(engine) as db:
            enqueue(db, "a", "first")
            enqueue(db, "b", "second")
            async with httpx.AsyncClient(transport=httpx.MockTransport(first)) as client:
                await deliver(db, settings, client)
            assert len(sent) == len(set(sent)) == 2
            assert all(n.status == "DELIVERED" and n.attempts == 1 for n in db.scalars(select(Notification)))

    asyncio.run(run())


@pytest.mark.parametrize('body', [{'ok': True}, {'ok': 'true'}, [],
    {'ok': True, 'result': {'message_id': 1, 'chat': {'id': 456}}}])
def test_invalid_or_wrong_chat_receipt_is_not_delivery(tmp_path, body):
    engine = make_engine(f'sqlite:///{tmp_path}/receipts.db')
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token='secret-test-token', telegram_chat_id='123')

    async def run():
        with Session(engine) as db:
            enqueue(db, 'a', 'test')
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, json=body))) as client:
                await deliver(db, settings, client)
                await deliver(db, settings, client)
            assert db.get(Notification, 'a').status == 'UNKNOWN'
            assert db.get(Notification, 'a').attempts == 1
            assert 'secret-test-token' not in str(status(db, settings))
    asyncio.run(run())


def test_rate_limit_honors_deadline_and_interrupted_claim_is_quarantined(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/retry.db')
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token='test-only', telegram_chat_id='123')
    now = datetime.now(timezone.utc)
    calls = []

    def respond(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={'ok': False, 'parameters': {'retry_after': 60}})
        return httpx.Response(200, json={'ok': True, 'result': {'message_id': 1, 'chat': {'id': 123}}})

    async def run():
        with Session(engine) as db:
            enqueue(db, 'a', 'test')
            db.add(Notification(id='crashed', text='never blindly resend', status='SENDING',
                                claimed_at=now-timedelta(minutes=3)))
            db.commit()
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                await deliver(db, settings, client, now=now)
                await deliver(db, settings, client, now=now+timedelta(seconds=59))
                assert len(calls) == 1
                await deliver(db, settings, client, now=now+timedelta(seconds=60))
            assert db.get(Notification, 'a').status == 'DELIVERED'
            assert db.get(Notification, 'crashed').status == 'UNKNOWN'
            assert db.get(Notification, 'crashed').attempts == 0
    asyncio.run(run())


def test_connectivity_preflight_sends_only_one_test_and_never_drains_queue(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/connectivity.db')
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token='test-only', telegram_chat_id='123')
    calls = []

    def respond(request):
        calls.append(request.url.path.rsplit('/', 1)[-1])
        result = {'is_bot': True} if calls[-1] == 'getMe' else {'id': 123} if calls[-1] == 'getChat' else {
            'message_id': 10, 'chat': {'id': 123}}
        return httpx.Response(200, json={'ok': True, 'result': result})

    async def run():
        with Session(engine) as db:
            enqueue(db, 'unrelated', 'do not send')
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                report = await connectivity_test(db, settings, client, 'approved-test', 'operator')
                assert report['message_sent'] is True
                assert (await connectivity_test(db, settings, client, 'approved-test', 'operator')) == report
            assert calls == ['getMe', 'getChat', 'sendMessage']
            assert db.get(Notification, 'unrelated').attempts == 0
            assert status(db, settings)['status'] == 'DISABLED'
            assert status(db, settings)['delivery_evidence'] == 'API_CONFIRMED'
    asyncio.run(run())


def test_stale_delivery_response_cannot_overwrite_quarantine(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/stale.db')
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token='test-only', telegram_chat_id='123')
    now = datetime.now(timezone.utc)

    async def interrupted(request):
        with Session(engine) as other:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: pytest.fail('No resend'))) as client:
                await deliver(other, settings, client, now=now+timedelta(minutes=3))
        return httpx.Response(200, json={'ok': True, 'result': {'message_id': 1, 'chat': {'id': 123}}})

    async def run():
        with Session(engine) as db:
            enqueue(db, 'a', 'test')
            async with httpx.AsyncClient(transport=httpx.MockTransport(interrupted)) as client:
                await deliver(db, settings, client, now=now)
            row = db.get(Notification, 'a')
            assert row.status == 'UNKNOWN' and row.error_code == 'INTERRUPTED_DELIVERY'
            assert row.delivered_at is None
    asyncio.run(run())


def test_chat_not_found_prevents_any_message_send(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/badchat.db')
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token='secret-test-token', telegram_chat_id='wrong')

    def respond(request):
        assert request.method == 'GET'
        if request.url.path.endswith('getMe'):
            return httpx.Response(200, json={'ok': True, 'result': {'is_bot': True}})
        return httpx.Response(400, json={'ok': False, 'description': 'Bad Request: chat not found'})

    async def run():
        with Session(engine) as db:
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                result = await connectivity_test(db, settings, client, 'test', 'operator')
            assert result == {'status': 'CHAT_NOT_FOUND', 'message_sent': False}
            assert not db.scalars(select(Notification)).all()
            assert status(db, settings)['last_preflight_failure']['error_code'] == 'CHAT_NOT_FOUND'
            assert 'secret-test-token' not in str(status(db, settings))
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
