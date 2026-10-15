import asyncio
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import Base, make_engine
from app.models.tables import Notification, TelegramCursor
from app.notifications.monitor import COMMANDS, poll, response_text


def test_monitor_bootstrap_authentication_idempotency_and_no_execution_mutations(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/monitor.db')
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token='not-a-real-token', telegram_chat_id='123',
                        enable_notifications=True, enable_telegram_monitoring=True)

    def message(identifier, command, *, chat=123, sender=123, kind='private'):
        return {'update_id': identifier, 'message': {'chat': {'id': chat, 'type': kind},
            'from': {'id': sender, 'is_bot': False}, 'text': command}}

    async def run():
        batch = [message(1, '/status')]
        async def handler(request):
            assert request.method == 'GET' and request.url.path.endswith('/getUpdates')
            return httpx.Response(200, json={'ok': True, 'result': batch})
        with Session(engine) as db:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                assert (await poll(db, settings, client))['status'] == 'BOOTSTRAPPED_WITHOUT_REPLAY'
                assert not db.scalar(select(func.count()).select_from(Notification))
                batch[:] = [message(2, '/status', chat=999), message(3, '/risk', sender=999),
                    message(4, '/trades', kind='group'), message(5, '/activate'), message(6, '/status')]
                assert (await poll(db, settings, client))['enqueued'] == 1
                assert (await poll(db, settings, client))['enqueued'] == 0
                reply = db.scalar(select(Notification))
                assert 'Active PAPER deployments: 0' in reply.text
                assert 'not-a-real-token' not in reply.text and reply.status == 'PENDING'
                assert db.scalar(select(TelegramCursor)).next_update == 7
                # Only cursor/reply intents can be written; all other tables stay empty.
                for table in Base.metadata.sorted_tables:
                    if table.name not in ('telegram_monitor_cursors', 'notification_events'):
                        assert db.scalar(select(func.count()).select_from(table)) == 0
    asyncio.run(run())


def test_monitor_disabled_bad_responses_and_atomic_reply_rollback(tmp_path, monkeypatch):
    engine = make_engine(f'sqlite:///{tmp_path}/rollback.db')
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token='fake', telegram_chat_id='123',
                        enable_notifications=True, enable_telegram_monitoring=True)
    batch = []
    async def handler(request):
        return httpx.Response(200, json={'ok': True, 'result': batch})
    async def run():
        with Session(engine) as db:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                assert (await poll(db, settings.model_copy(update={'enable_telegram_monitoring': False}), client))['status'] == 'DISABLED'
                assert not db.scalar(select(func.count()).select_from(TelegramCursor))
                await poll(db, settings, client)
                batch[:] = [{'update_id': 3}, {'update_id': 2}]
                assert (await poll(db, settings, client))['status'] == 'INVALID_UPDATE_SEQUENCE'
                assert db.scalar(select(TelegramCursor)).next_update == 0
                batch[:] = [{'update_id': 4, 'message': {'chat': {'id': 123, 'type': 'private'},
                    'from': {'id': 123, 'is_bot': False}, 'text': '/status'}}]
                def fail(*args):
                    raise ValueError('simulated formatting failure')
                monkeypatch.setattr('app.notifications.monitor.response_text', fail)
                assert (await poll(db, settings, client))['status'] == 'POLL_UNCERTAIN'
                assert db.scalar(select(TelegramCursor)).next_update == 0
                assert not db.scalar(select(func.count()).select_from(Notification))
    asyncio.run(run())


def test_all_commands_are_read_only_and_report_missing_evidence(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/commands.db')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for command in COMMANDS:
            text = response_text(db, Settings(_env_file=None), command, datetime.now(timezone.utc))
            assert 'READ-ONLY' in text and len(text) <= 4096
        assert 'UNKNOWN' in response_text(db, Settings(_env_file=None), '/risk', datetime.now(timezone.utc))
        assert 'NO_COMPLETED_TRADES' in response_text(db, Settings(_env_file=None), '/performance', datetime.now(timezone.utc))
        assert not db.new and not db.dirty


def test_two_pollers_only_one_commits_reply_intent(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/concurrent.db')
    Base.metadata.create_all(engine)
    settings = Settings(_env_file=None, telegram_bot_token='fake', telegram_chat_id='123',
                        enable_notifications=True, enable_telegram_monitoring=True)
    body = {'ok': True, 'result': [{'update_id': 2, 'message': {'text': '/status',
        'chat': {'id': 123, 'type': 'private'}, 'from': {'id': 123, 'is_bot': False}}}]}
    async def run():
        with Session(engine) as db:
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, json={'ok': True, 'result': []}))) as client:
                await poll(db, settings, client)
        async def first(request):
            with Session(engine) as other:
                async with httpx.AsyncClient(transport=httpx.MockTransport(
                        lambda request: httpx.Response(200, json=body))) as client:
                    assert (await poll(other, settings, client))['enqueued'] == 1
            return httpx.Response(200, json=body)
        with Session(engine) as db:
            async with httpx.AsyncClient(transport=httpx.MockTransport(first)) as client:
                assert (await poll(db, settings, client))['status'] == 'CONCURRENT_POLL'
            assert db.scalar(select(func.count()).select_from(Notification)) == 1
    asyncio.run(run())
