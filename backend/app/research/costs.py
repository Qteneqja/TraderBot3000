"""Allowlisted current practice terms and historical close-spread evidence, never approval."""

import argparse
import asyncio
import json
from datetime import datetime, timezone
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

import httpx
from sqlalchemy import select

from app.brokers.oanda import OandaPractice
from app.brokers.validation import decimal, readiness_report
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.machine_learning.contracts import research_code_contract
from app.machine_learning.prospective import training_end
from app.market_data.store import load_candles
from app.models.tables import ModelVersion
from app.research.lab import write_json


def disclosed_terms(raw):
    commission = raw.get('commission')
    if commission is not None:
        values = {key: decimal(commission[key]) for key in ('commission', 'unitsTraded', 'minimumCommission')}
        if values['unitsTraded'] <= 0 or min(values.values()) < 0:
            raise ValueError('Invalid disclosed commission terms')
        commission = {key: str(value) for key, value in values.items()}
    financing = raw.get('financing')
    if financing is not None:
        financing = {key: str(decimal(financing[key])) for key in ('longRate', 'shortRate')}
        days = raw['financing'].get('financingDaysOfWeek')
        if days is not None:
            if any(item['dayOfWeek'] not in ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY')
                   or type(item['daysCharged']) is not int or not 0 <= item['daysCharged'] <= 7 for item in days):
                raise ValueError('Invalid disclosed financing-day terms')
            financing['financingDaysOfWeek'] = [
                {'dayOfWeek': item['dayOfWeek'], 'daysCharged': item['daysCharged']} for item in days]
    return {'commission': {'classification': 'OBSERVED' if commission is not None else 'UNKNOWN', 'terms': commission},
            'financing': {'classification': 'OBSERVED' if financing is not None else 'UNKNOWN', 'terms': financing,
                          'historical_applicability': 'UNKNOWN'},
            'limitations': 'Current account instrument disclosure, not historical rates or confirmed fill charges.'}


def spread_summary(rows):
    values = []
    for candle in rows:
        components = candle.provenance
        bid, ask = components.get('bid'), components.get('ask')
        if isinstance(bid, dict) and isinstance(ask, dict) and 'c' in bid and 'c' in ask:
            spread = decimal(ask['c'])-decimal(bid['c'])
            if spread < 0:
                raise ValueError('Crossed historical bid/ask close')
            values.append(spread)
    values.sort()
    return {'classification': 'OBSERVED' if values else 'UNKNOWN', 'candles': len(rows),
            'bid_ask_close_samples': len(values),
            'quantiles_nearest_rank': {str(q): str(values[max(0, int((Decimal(str(q))*len(values)).to_integral_value(
                rounding=ROUND_CEILING))-1)])
                                      for q in (0, .5, .9, .95, .99, 1)} if values else None,
            'limitations': 'Observed candle-close spreads; not intrabar spread paths, depth, fills or slippage.'}


async def collect(db, settings, client):
    if settings.demo_mode or settings.oanda_environment != 'practice' or settings.enable_live_trading:
        raise ValueError('Only real-provider practice read-only observations are supported')
    adapter = OandaPractice(settings.model_copy(update={'trading_mode': 'OANDA_PRACTICE'}), client)
    checked = await readiness_report(adapter, settings.oanda_account_id, ['EUR_USD', 'GBP_USD'])
    raw = await adapter.instruments()
    now = datetime.now(timezone.utc)
    scopes = []
    models = [v.metadata_json for v in db.scalars(select(ModelVersion)).all()
              if v.metadata_json.get('research_code') == research_code_contract()
              and v.metadata_json.get('evaluation_mode') == 'VALIDATION_ONLY']
    for item in raw['instruments']:
        if item['name'] not in ('EUR_USD', 'GBP_USD'):
            continue
        matching = [m for m in models if m['symbol'] == item['name'] and m['timeframe'] == 300]
        if not matching:
            raise ValueError('A declared pre-final reference scope is required')
        start = min(datetime.fromisoformat(m['input_candles']['start']) for m in matching)
        end = min(datetime.fromisoformat(m['partitions']['test'][0]) for m in matching)
        end = training_end(db, item['name'], 'oanda', start, end)
        rows = load_candles(db, item['name'], 300, 'oanda', 1_000_000, start=start, end=end)
        scopes.append({'symbol': item['name'], 'account_currency': checked['currency'],
                      'current_terms': disclosed_terms(item), 'historical_close_spreads': spread_summary(rows),
                      'historical_period': {'start': start.isoformat(), 'end_exclusive': end.isoformat(),
                                            'scope': 'PRE_FINAL_PREFIX_ONLY'},
                      'slippage': {'classification': 'ESTIMATED', 'assumption': 'one adverse instrument tick per fill',
                                   'external_fill_evidence': 'UNKNOWN'}})
    return {'schema': 'execution-cost-evidence-v1', 'checked_at': now.isoformat(),
            'environment': 'OANDA_PRACTICE', 'division': settings.oanda_division,
            'account_currency': checked['currency'], 'read_only_checks': checked['checks'],
            'current_usd_to_home_conversion': {'classification': 'OBSERVED', 'values': checked['usd_to_home_conversion'],
                'limitations': 'Current distinct gain/loss/position factors; historical CAD conversion path is UNKNOWN.'},
            'instruments': scopes, 'crypto': {'maker_fee': 'UNKNOWN', 'taker_fee': 'UNKNOWN',
                'account_tier': 'UNKNOWN', 'historical_spread': 'UNKNOWN',
                'existing_research_fee': {'classification': 'ESTIMATED', 'rate_per_side': '.012'}},
            'documented_financing': {'classification': 'BROKER_DOCUMENTED',
                'source': 'https://www.oanda.com/ca-en/trading/financing-costs/',
                'description': 'Direction/instrument/date-dependent rollover; a constant per-bar zero is not verified broker financing.'},
            'economic_qualification': 'BLOCKED_BY_UNVERIFIED_HISTORICAL_EXECUTION_COSTS', 'execution_authority': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()

    async def main():
        with SessionLocal() as db:
            async with httpx.AsyncClient(timeout=20) as client:
                report = await collect(db, get_settings(), client)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, report)
        print(json.dumps({'status': report['economic_qualification'], 'currency': report['account_currency'],
                          'instruments': len(report['instruments']), 'execution_authority': False}))

    try:
        asyncio.run(main())
    except Exception as exc:
        print(json.dumps({'status': 'UNVERIFIED', 'error_type': type(exc).__name__}))
        raise SystemExit(1) from None
