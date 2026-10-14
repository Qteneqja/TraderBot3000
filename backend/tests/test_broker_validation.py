from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D

import httpx
import pytest

from app.brokers.oanda import OandaPractice
from app.brokers.validation import (
    conversion_contract,
    instrument_contract,
    readiness_report,
    validate_protection,
)
from app.core.config import Settings

INSTRUMENT = {"name": "EUR_USD", "type": "CURRENCY", "displayPrecision": 5, "tradeUnitsPrecision": 0,
              "minimumTradeSize": "1", "maximumOrderUnits": "100000", "marginRate": ".02"}


def test_broker_precision_and_size_are_explicit():
    contract = instrument_contract(INSTRUMENT)
    assert D(contract["tick"]) == D('.00001') and D(contract["unit_step"]) == 1
    for change in ({"marginRate": "NaN"}, {"displayPrecision": 20}, {"minimumTradeSize": "0"}, {"type": "CFD"}):
        with pytest.raises(ValueError):
            instrument_contract(INSTRUMENT | change)


def test_confirmed_fill_requires_matching_native_protection():
    trade = {"id": "trade", "instrument": "EUR_USD", "currentUnits": "10", "price": "1.1",
             "stopLossOrder": {"id": "stop", "tradeID": "trade", "state": "PENDING", "price": "1.09"},
             "takeProfitOrder": {"id": "target", "tradeID": "trade", "state": "PENDING", "price": "1.12"}}
    assert validate_protection(trade, "EUR_USD", D(10), D('1.09'), D('1.12'))
    for name, value in (("state", "CANCELLED"), ("price", "1.08"), ("tradeID", "another")):
        broken = deepcopy(trade)
        broken["stopLossOrder"][name] = value
        with pytest.raises(ValueError):
            validate_protection(broken, "EUR_USD", D(10), D('1.09'), D('1.12'))
    with pytest.raises(ValueError):
        validate_protection(trade | {"currentUnits": "5"}, "EUR_USD", D(10), D('1.09'), D('1.12'))


@pytest.mark.parametrize('currency,mt4,watermark', [('USD', False, '7'), ('CAD', False, '7'), ('USD', True, '7'), ('USD', False, '8')])
async def test_read_only_account_validation_never_sends_order(currency, mt4, watermark):
    now = datetime(2026, 10, 14, tzinfo=timezone.utc)
    calls = []

    def handler(request):
        calls.append(request.method)
        assert request.method == 'GET'
        path = request.url.path
        if path.endswith('/accounts'):
            return httpx.Response(200, json={'accounts': [{'id': 'test', **({'mt4AccountID': 123} if mt4 else {})}]})
        if path.endswith('/instruments'):
            return httpx.Response(200, json={'instruments': [INSTRUMENT]})
        if path.endswith('/pricing'):
            return httpx.Response(200, json={'prices': [{'instrument': 'EUR_USD', 'time': now.isoformat(),
                'status': 'tradeable', 'bids': [{'price': '1.1'}], 'asks': [{'price': '1.1001'}]}],
                'homeConversions': [{'currency': 'USD', 'accountGain': '1.35', 'accountLoss': '1.36', 'positionValue': '1.355'}]})
        if path.endswith('/transactions/sinceid'):
            return httpx.Response(200, json={'transactions': [], 'lastTransactionID': watermark})
        return httpx.Response(200, json={'account': {'id': 'test', 'currency': currency, 'NAV': '1000',
            'marginAvailable': '1000', 'lastTransactionID': '7', 'trades': [], 'orders': [], 'positions': []}})

    settings = Settings(_env_file=None, trading_mode='OANDA_PRACTICE', demo_mode=False,
                        oanda_api_key='test-token', oanda_account_id='test')
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        report = await readiness_report(OandaPractice(settings, client), 'test', ['EUR_USD'], now)
    assert report['submission_enabled'] is False and len(calls) == 5
    assert report['status'] == ('READ_ONLY_CHECKS_PASSED' if not mt4 and watermark == '7' else 'BLOCKED')
    assert 'test-token' not in str(report)


def test_missing_currency_conversion_is_never_assumed_one():
    with pytest.raises(ValueError, match="Missing"):
        conversion_contract({}, 'USD', 'CAD')
    assert conversion_contract({}, 'USD', 'USD') == {'gain': D(1), 'loss': D(1), 'position': D(1)}
