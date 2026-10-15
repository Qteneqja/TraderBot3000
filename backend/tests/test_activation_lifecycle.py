"""Fixture-only execution lifecycle. Positive deployment authority is explicitly mocked."""

import asyncio
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
import test_paper_faults
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.execution.paper import money, monitor, submit
from app.market_data.store import save_quote
from app.models.tables import Account, Notification, OrderRow
from app.notifications.telegram import deliver
from app.operations.diagnostic import activation_report

store = test_paper_faults.store
pytestmark = pytest.mark.usefixtures('execution_model_stub')


def test_fixture_fill_exit_net_ledger_and_confirmed_mock_notifications(store):
    engine, candidate, quote, settings, now = store
    candidate = candidate.model_copy(update={'source': 'fixture', 'deployment_id': 'FIXTURE-ONLY-MOCK'})
    quote = quote.model_copy(update={'source': 'fixture'})
    settings = settings.model_copy(update={'telegram_bot_token': SecretStr('test-only'), 'telegram_chat_id': '123'})
    with Session(engine) as db:
        save_quote(db, quote, now)
        assert submit(db, candidate, quote, settings, now) == 'FILLED'
        assert submit(db, candidate, quote, settings, now) == 'FILLED'
        order = db.get(OrderRow, candidate.id)
        assert order.stop < order.entry < order.target and order.units > 0
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 1
        entry_balance = db.get(Account, 'PAPER').balance
        db.rollback()
        exit_quote = quote.model_copy(update={'time': now + timedelta(seconds=1),
            'bid': candidate.target + Decimal('.001'), 'ask': candidate.target + Decimal('.0011')})
        save_quote(db, exit_quote, exit_quote.time)
        monitor(db, settings, exit_quote.time)
        order = db.get(OrderRow, candidate.id)
        assert order.state == 'CLOSED' and order.close_reason == 'TAKE_PROFIT'
        assert order.pnl == money((order.target - order.entry) * order.units - order.fees_paid)
        assert db.get(Account, 'PAPER').balance == money(entry_balance + order.pnl)
        messages = db.scalars(select(Notification).order_by(Notification.id)).all()
        assert len(messages) == 2
        assert all('Data source: fixture' in m.text and 'not a broker fill' in m.text for m in messages)
        closed = next(m for m in messages if m.id.endswith('CLOSED'))
        assert f'Net P&L (USD): {order.pnl}' in closed.text
        assert 'Model: unit-test-only' in closed.text

        async def send():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
                    200, json={'ok': True, 'result': {'message_id': 1, 'chat': {'id': 123}}}))) as client:
                await deliver(db, settings, client)
                await deliver(db, settings, client)
        asyncio.run(send())
        assert all(m.status == 'DELIVERED' and m.attempts == 1 for m in messages)
        report = activation_report(db, settings, exit_quote.time)
        assert report['paper_orders'] == {'CLOSED': 1}
        assert report['active_paper_deployments'] == 0
        assert report['execution_authority'] is False
        assert 'test-only' not in str(report)
