"""Broker lifecycle mocks with explicitly mocked prior model/operator approval, not market evidence."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal as D

import httpx
import pytest
import test_paper_faults
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.brokers.gateway import close_once, reserve, send_once
from app.brokers.gateway import validate_authority as real_validate_authority
from app.brokers.oanda import OandaPractice
from app.brokers.reconciliation import account_key, reconcile_practice, validate_transactions
from app.machine_learning.policy import digest
from app.models.tables import Event, PracticeAccount, PracticeOrder, PracticeTransaction

store = test_paper_faults.store
MOCK_APPROVAL = {'test_only_mock_operator_and_model_evidence': True}
MOCK_APPROVAL['sha256'] = digest(MOCK_APPROVAL)


def test_new_broker_cashflow_suspends_entries_without_resetting_loss_baselines(store):
    engine, _, _, _, now = store

    async def run():
        adapter = FakePractice(now)
        try:
            with Session(engine) as db:
                await reconcile_practice(db, adapter, 'test', now)
                account = db.get(PracticeAccount, account_key('test'))
                before = dict(account.risk)
                account.suspended = False
                db.commit()
                adapter.append('TRANSFER_FUNDS', amount='100', fundingReason='CLIENT_FUNDING')
                result = await reconcile_practice(db, adapter, 'test', now)
                assert result['suspended'] and not result['reconciled']
                assert 'BROKER_CASHFLOW_REQUIRES_REVIEW' in result['issues']
                assert account.risk['day_start'] == before['day_start']
                assert adapter.calls == []  # No POST or PUT in reconciliation.
        finally:
            await adapter.client.aclose()

    asyncio.run(run())


class FakePractice(OandaPractice):
    def __init__(self, now, mode='normal'):
        self.now, self.mode = now, mode
        self.base = 'https://api-fxpractice.oanda.com/v3/accounts/test'
        self.headers = {'Authorization': 'Bearer test-only-token'}
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(self.handle))
        self.log, self.trades, self.calls, self.closed = [], {}, [], {}

    def append(self, kind, **values):
        tx = {'id': str(8 + len(self.log)), 'type': kind, 'time': self.now.isoformat(),
              'accountID': 'test', 'userID': 123, **values}
        self.log.append(tx)
        return tx

    async def handle(self, request):
        import json

        self.calls.append(request.method)
        if request.method == 'POST':
            if self.mode == 'timeout_before_fill':
                raise httpx.ReadTimeout('test timeout')
            order = json.loads(request.content)['order']
            created = self.append('MARKET_ORDER', instrument=order['instrument'], units=order['units'],
                                  clientExtensions=order['clientExtensions'])
            filled = self.append('ORDER_FILL', orderID=created['id'],
                                 tradeOpened={'tradeID': 'trade', 'units': order['units'], 'price': order['priceBound']},
                                 commission='.1' if self.mode == 'fees' else '0', financing='0')
            stop = self.append('STOP_LOSS', tradeID='trade')
            target = self.append('TAKE_PROFIT', tradeID='trade')
            self.trades['trade'] = {'id': 'trade', 'instrument': order['instrument'], 'currentUnits': order['units'],
                'initialUnits': order['units'], 'price': order['priceBound'], 'financing': '0',
                'stopLossOrder': {'id': stop['id'], 'tradeID': 'trade', 'state': 'PENDING', 'price': order['stopLossOnFill']['price']},
                'takeProfitOrder': {'id': target['id'], 'tradeID': 'trade', 'state': 'PENDING', 'price': order['takeProfitOnFill']['price']}}
            if self.mode == 'unprotected':
                del self.trades['trade']['stopLossOrder']
            if self.mode == 'timeout_after_fill':
                raise httpx.ReadTimeout('test timeout after confirmed broker effect')
            return httpx.Response(201, json={'orderFillTransaction': filled})
        if request.method == 'PUT':
            self.append('MARKET_ORDER', tradeClose={'tradeID': 'trade'})
            self.append('ORDER_FILL', tradesClosed=[{'tradeID': 'trade', 'units': self.trades['trade']['currentUnits'],
                                                    'realizedPL': '5'}], commission='.2' if self.mode == 'fees' else '0', financing='0', reason='MARKET_ORDER_TRADE_CLOSE')
            self.closed['trade'] = self.trades['trade'] | {'state': 'CLOSED', 'currentUnits': '0',
                                                         'closeTime': (self.now + timedelta(seconds=1)).isoformat(),
                                                         'averageClosePrice': '1.101',
                                                         'realizedPL': '5', 'financing': '-.3' if self.mode == 'fees' else '0'}
            self.trades.clear()
            return httpx.Response(200, json={})
        raise AssertionError('Unexpected network method')

    async def account_details(self):
        trades = list(self.trades.values())
        units = D(trades[0]['currentUnits']) if trades else D(0)
        return {'account': {'id': 'test', 'currency': 'CAD', 'lastTransactionID': str(7 + len(self.log)),
                'NAV': '10000', 'balance': '10000', 'marginAvailable': '10000', 'marginUsed': '0',
                'orders': [], 'trades': deepcopy(trades), 'positions': [{'instrument': 'EUR_USD',
                 'long': {'units': str(max(D(0), units))}, 'short': {'units': str(min(D(0), units))}}]}}

    async def transactions(self, cursor):
        return {'transactions': deepcopy([t for t in self.log if int(t['id']) > int(cursor)]),
                'lastTransactionID': str(7 + len(self.log))}

    async def pricing(self, symbols):
        return {'prices': [{'instrument': symbols[0], 'status': 'tradeable', 'time': self.now.isoformat(),
                           'bids': [{'price': '1.0999'}], 'asks': [{'price': '1.1001'}]}],
                'homeConversions': [{'currency': 'USD', 'accountGain': '1.35', 'accountLoss': '1.36', 'positionValue': '1.355'}]}

    async def instruments(self):
        return {'instruments': [{'name': 'EUR_USD', 'type': 'CURRENCY', 'displayPrecision': 5,
                 'tradeUnitsPrecision': 0, 'minimumTradeSize': '1', 'maximumOrderUnits': '100000', 'marginRate': '.05'}]}

    async def trade(self, trade_id):
        return {'trade': deepcopy(self.trades[trade_id] if trade_id in self.trades else self.closed[trade_id])}


@pytest.fixture
def practice(store, monkeypatch):
    engine, candidate, _, settings, now = store
    settings = settings.model_copy(update={'demo_mode': False, 'trading_mode': 'OANDA_PRACTICE', 'oanda_account_id': 'test'})
    candidate = candidate.model_copy(update={'source': 'oanda'})
    authority = {'sha256': MOCK_APPROVAL['sha256'], 'models': [candidate.model_version], 'instruments': [{
        'symbol': 'EUR_USD', 'tick': '.00001', 'unit_step': '1', 'minimum_units': '1',
        'maximum_order_units': '100000', 'margin_rate': '.05'}]}
    monkeypatch.setattr('app.brokers.gateway.validate_authority', lambda *args: authority)
    monkeypatch.setattr('app.brokers.gateway.authorize_candidate', lambda db, c, *args: c)
    return engine, candidate, settings, now


async def initialize(db, adapter, now):
    await reconcile_practice(db, adapter, 'test', now)
    account = db.get(PracticeAccount, account_key('test'))
    account.suspended = False
    account.approval = dict(MOCK_APPROVAL)
    db.add(Event(kind='practice_gateway_approved', detail={'approval_id': MOCK_APPROVAL['sha256']}))
    db.commit()


@pytest.mark.parametrize('mode', ['normal', 'timeout_after_fill'])
async def test_durable_fill_protection_close_and_restart_idempotency(practice, mode):
    engine, candidate, settings, now = practice
    adapter = FakePractice(now, mode)
    try:
        with Session(engine) as db:
            await initialize(db, adapter, now)
            order_id = await reserve(db, adapter, settings, candidate, now)
            assert await reserve(db, adapter, settings, candidate, now) == order_id
            assert await send_once(db, adapter, settings, order_id, now) == 'FILLED'
            assert await send_once(db, adapter, settings, order_id, now) == 'FILLED'
        with Session(engine) as db:
            await reconcile_practice(db, adapter, 'test', now)
            assert db.scalar(select(func.count()).select_from(PracticeOrder)) == 1
            assert db.scalar(select(func.count()).select_from(PracticeTransaction)) == 4
            assert all('accountID' not in t.payload for t in db.scalars(select(PracticeTransaction)))
            db.rollback()
            await close_once(db, adapter, settings, order_id)
            assert db.get(PracticeOrder, order_id).state == 'CLOSED'
            db.rollback()
            await close_once(db, adapter, settings, order_id)
        assert adapter.calls == ['POST', 'PUT']
    finally:
        await adapter.client.aclose()


async def test_uncertain_post_is_never_blindly_repeated(practice):
    engine, candidate, settings, now = practice
    adapter = FakePractice(now, 'timeout_before_fill')
    try:
        with Session(engine) as db:
            await initialize(db, adapter, now)
            order_id = await reserve(db, adapter, settings, candidate, now)
            assert await send_once(db, adapter, settings, order_id, now) == 'UNKNOWN'
            assert await send_once(db, adapter, settings, order_id, now) == 'UNKNOWN'
            assert db.get(PracticeAccount, account_key('test')).suspended
        assert adapter.calls == ['POST']
    finally:
        await adapter.client.aclose()


async def test_unprotected_fill_stays_quarantined(practice):
    engine, candidate, settings, now = practice
    adapter = FakePractice(now, 'unprotected')
    try:
        with Session(engine) as db:
            await initialize(db, adapter, now)
            order_id = await reserve(db, adapter, settings, candidate, now)
            assert await send_once(db, adapter, settings, order_id, now) == 'QUARANTINED'
            assert db.get(PracticeAccount, account_key('test')).suspended
    finally:
        await adapter.client.aclose()


async def test_reservation_risk_cap_and_expiration(practice):
    engine, candidate, settings, now = practice
    adapter = FakePractice(now)
    try:
        with Session(engine) as db:
            await initialize(db, adapter, now)
            ids = [await reserve(db, adapter, settings, candidate.model_copy(update={'id': f'candidate-{i}'}), now) for i in range(6)]
            assert 0 < sum(i is not None for i in ids) <= 3
            assert sum(o.planned_risk for o in db.scalars(select(PracticeOrder))) <= D(100)
            db.rollback()
            first = next(i for i in ids if i)
            assert await send_once(db, adapter, settings, first, now + timedelta(minutes=6)) == 'CANCELLED'
        assert adapter.calls == []
    finally:
        await adapter.client.aclose()


def test_cursor_never_skips_missing_transactions():
    with pytest.raises(ValueError, match='Incomplete'):
        validate_transactions([{'id': '9'}], '7', '9')
    with pytest.raises(ValueError):
        validate_transactions([{'id': '8'}, {'id': '8'}], '7', '9')


async def test_crash_after_claim_before_post_is_not_retried(practice, monkeypatch):
    engine, candidate, settings, now = practice
    adapter = FakePractice(now)
    try:
        with Session(engine) as db:
            await initialize(db, adapter, now)
            order_id = await reserve(db, adapter, settings, candidate, now)
            commit = db.commit

            def crash():
                commit()
                raise RuntimeError('simulated process failure after durable claim')

            monkeypatch.setattr(db, 'commit', crash)
            with pytest.raises(RuntimeError):
                await send_once(db, adapter, settings, order_id, now)
        with Session(engine) as db:
            assert db.get(PracticeOrder, order_id).state == 'SUBMITTING'
            db.rollback()
            assert await send_once(db, adapter, settings, order_id, now) == 'SUBMITTING'
            db.rollback()
            report = await reconcile_practice(db, adapter, 'test', now)
            assert not report['reconciled']
        assert adapter.calls == []
    finally:
        await adapter.client.aclose()


async def test_foreign_exposure_is_quarantined_without_closure(practice):
    engine, _, _, now = practice
    adapter = FakePractice(now)
    adapter.trades['foreign'] = {'id': 'foreign', 'instrument': 'EUR_USD', 'currentUnits': '10'}
    try:
        with Session(engine) as db:
            report = await reconcile_practice(db, adapter, 'test', now)
            assert not report['reconciled'] and 'UNOWNED_BROKER_TRADES' in report['issues']
        assert adapter.calls == []
    finally:
        await adapter.client.aclose()


def test_concurrent_duplicate_reservations_are_one_order(practice):
    engine, candidate, settings, now = practice
    adapter = FakePractice(now)
    try:
        with Session(engine) as db:
            asyncio.run(initialize(db, adapter, now))

        def submit_duplicate(_):
            with Session(engine) as db:
                return asyncio.run(reserve(db, adapter, settings, candidate, now))

        with ThreadPoolExecutor(max_workers=6) as pool:
            ids = list(pool.map(submit_duplicate, range(6)))
        assert len(set(ids)) == 1
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(PracticeOrder)) == 1
        assert adapter.calls == []
    finally:
        asyncio.run(adapter.client.aclose())


async def test_realized_broker_costs_are_not_double_counted_and_halt_on_drift(practice):
    engine, candidate, settings, now = practice
    adapter = FakePractice(now, 'fees')
    try:
        with Session(engine) as db:
            await initialize(db, adapter, now)
            order_id = await reserve(db, adapter, settings, candidate, now)
            assert await send_once(db, adapter, settings, order_id, now) == 'FILLED'
            assert db.get(PracticeAccount, account_key('test')).suspended
            db.rollback()
            await close_once(db, adapter, settings, order_id)
            assert db.get(PracticeOrder, order_id).realized_pnl == D('4.4')
            assert db.get(PracticeOrder, order_id).fees_paid == D('.3')
            db.rollback()
            await reconcile_practice(db, adapter, 'test', now)
            assert db.get(PracticeOrder, order_id).realized_pnl == D('4.4')
    finally:
        await adapter.client.aclose()


async def test_real_approval_gate_rejects_unapproved_account_before_post(practice, monkeypatch):
    engine, candidate, settings, now = practice
    adapter = FakePractice(now)
    monkeypatch.setattr('app.brokers.gateway.validate_authority', real_validate_authority)
    try:
        with Session(engine) as db:
            await reconcile_practice(db, adapter, 'test', now)
            with pytest.raises(ValueError, match='Explicit practice gateway approval'):
                await reserve(db, adapter, settings, candidate, now)
        assert adapter.calls == []
    finally:
        await adapter.client.aclose()


async def test_practice_worker_starts_read_only_without_approval(practice, monkeypatch):
    from app.brokers.worker import practice_worker

    engine, _, settings, now = practice
    adapter = FakePractice(now)
    events = []
    monkeypatch.setattr('app.brokers.worker.get_settings', lambda: settings)
    monkeypatch.setattr('app.brokers.worker.SessionLocal', lambda: Session(engine, expire_on_commit=False))
    monkeypatch.setattr('app.brokers.worker.OandaPractice', lambda *args: adapter)
    monkeypatch.setattr('app.brokers.worker.httpx.AsyncClient', lambda **kwargs: adapter.client)
    monkeypatch.setattr('app.worker.record', lambda kind, detail: events.append((kind, detail)))

    async def stop(_):
        raise asyncio.CancelledError()

    monkeypatch.setattr('app.brokers.worker.asyncio.sleep', stop)
    with pytest.raises(asyncio.CancelledError):
        await practice_worker()
    assert adapter.calls == []
    assert events[-1][1]['gateway'] == 'AWAITING_OPERATOR_APPROVAL'
