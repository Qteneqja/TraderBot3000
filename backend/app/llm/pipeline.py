"""Durable event-driven commentary. LLM text is never a trading or training input."""

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.execution.paper import lock_account, valid_execution
from app.llm.explain import request_explanation
from app.machine_learning.policy import digest
from app.models.tables import (
    Event,
    LearningRun,
    LearningSchedule,
    NarrativeRecord,
    OrderRow,
    PracticeOrder,
)
from app.schemas.domain import aware
from app.strategies.registry import STRATEGIES

PROMPT_VERSION = 'narrative-evidence-v1'
ASSETS = {'EUR_USD', 'GBP_USD', 'BTC-USD', 'ETH-USD'}
FAMILIES = {'logistic', 'random_forest', 'lightgbm', 'xgboost'}


def prompt_hash():
    return hashlib.sha256(Path(__file__).with_name('explain.py').read_text(encoding='utf-8').encode()).hexdigest()


def number(value):
    if value is None:
        return None
    result = Decimal(str(value))
    if not result.is_finite() or len(str(result)) > 64:
        raise ValueError('Nonfinite or oversized narrative fact')
    return str(result)


def source_snapshot(db, kind, source_id):
    if kind == 'RESEARCH':
        run = db.get(LearningRun, source_id)
        if run is None or run.state not in ('COMPLETED', 'FAILED'):
            return None
        schedule = db.get(LearningSchedule, run.schedule_id)
        plan = schedule.plan
        if plan['symbol'] not in ASSETS or plan['strategy'] not in STRATEGIES:
            raise ValueError('Unsupported narrative scope')
        candidates = []
        for candidate in run.result.get('candidates', [])[:4]:
            if candidate.get('family') not in FAMILIES:
                raise ValueError('Unknown research family')
            metric = candidate.get('portfolio', {}).get('metrics', {})
            validation = candidate.get('validation', {})
            candidates.append({'family': candidate['family'],
                'state': 'EXPERIMENTAL' if candidate.get('status') == 'EXPERIMENTAL' else 'FAILED',
                'validation_brier': number(validation.get('multiclass_brier')),
                'validation_calibration_error': number(validation.get('target_calibration_error')),
                'validation_trades': number(metric.get('trades')), 'validation_net_return': number(metric.get('net_return')),
                'validation_profit_factor': number(metric.get('profit_factor')),
                'validation_drawdown': number(metric.get('max_drawdown')),
                'stressed_validation_trades': number(candidate.get('stressed_portfolio', {}).get('metrics', {}).get('trades'))})
        return {'schema': 'narrative-snapshot-v1', 'kind': 'RESEARCH_PERFORMANCE', 'classification': 'PROVIDER_RESEARCH',
                'symbol': plan['symbol'], 'source': plan['source'] if plan['source'] in ('oanda', 'coinbase') else 'UNKNOWN',
                'strategy': plan['strategy'], 'state': run.state, 'candidates': candidates,
                'final_test': 'NOT_EVALUATED', 'activation': 'NOT_AUTHORIZED',
                'limitations': ['Validation-only selection evidence', 'Costs include explicitly unverified assumptions',
                                'No demonstrated live or practice profitability', 'No automatic model promotion']}
    if kind in ('PAPER_FILLED', 'PAPER_CLOSED'):
        order = db.get(OrderRow, source_id)
        if (order is None or order.mode != 'PAPER' or order.state != kind.removeprefix('PAPER_')
            or not valid_execution(order)):
            return None
        source = order.execution['source']
        snapshot = {'classification': 'SYNTHETIC_FIXTURE' if source == 'fixture' else 'SIMULATED_PAPER',
                    'symbol': order.symbol, 'direction': order.direction, 'state': order.state,
                    'entry': number(order.entry), 'exit': number(order.exit), 'net_pnl': number(order.pnl),
                    'fees': number(order.fees_paid)}
    elif kind in ('PRACTICE_FILLED', 'PRACTICE_CLOSED'):
        order = db.get(PracticeOrder, source_id)
        if (order is None or order.state != kind.removeprefix('PRACTICE_')
            or order.request_sha256 != digest(order.request)):
            return None
        snapshot = {'classification': 'OANDA_PRACTICE', 'symbol': order.candidate.get('symbol'),
                    'direction': order.candidate.get('direction'), 'state': order.state,
                    'entry': number(order.entry), 'exit': number(order.exit), 'net_pnl': number(order.realized_pnl),
                    'fees': number(order.fees_paid)}
    else:
        raise ValueError('Unsupported narrative event')
    if snapshot['symbol'] not in ASSETS or snapshot['direction'] not in ('LONG', 'SHORT'):
        raise ValueError('Invalid recorded trade scope')
    return snapshot | {'schema': 'narrative-snapshot-v1', 'kind': 'TRADE_UPDATE',
                       'execution_authority': False, 'limitations': ['Recorded event only; no trading instructions']}


def enqueue(db, kind, source_id, settings):
    identifier = digest([PROMPT_VERSION, kind, source_id, settings.llm_provider, settings.llm_model])
    if db.get(NarrativeRecord, identifier) is not None:
        return None
    snapshot = source_snapshot(db, kind, source_id)
    if snapshot is None:
        return None
    # No arbitrary caller snapshot, provider response, raw account record, secrets or order instructions.
    checksum = digest(snapshot)
    insert = pg_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert
    inserted = db.execute(insert(NarrativeRecord).values(id=identifier, source_kind=kind, source_id=source_id,
        provider=settings.llm_provider, model=settings.llm_model, state='PENDING', snapshot=snapshot,
        snapshot_sha256=checksum, result={'prompt_sha256': prompt_hash()}).on_conflict_do_nothing(index_elements=['id'])
        .returning(NarrativeRecord.id)).scalar_one_or_none()
    db.commit()
    return inserted


def enqueue_events(db, settings):
    if not settings.enable_llm_narratives:
        return []
    events = [('RESEARCH', identifier) for identifier in db.scalars(select(LearningRun.id)
        .where(LearningRun.state.in_(('COMPLETED', 'FAILED'))).order_by(LearningRun.scheduled_for.desc()).limit(20))]
    events += [('PAPER_' + state, identifier) for identifier, state in db.execute(select(OrderRow.id, OrderRow.state)
        .where(OrderRow.mode == 'PAPER', OrderRow.state.in_(('FILLED', 'CLOSED')))
        .order_by(OrderRow.opened_at.desc()).limit(20))]
    events += [('PRACTICE_' + state, identifier) for identifier, state in db.execute(select(PracticeOrder.id, PracticeOrder.state)
        .where(PracticeOrder.state.in_(('FILLED', 'CLOSED'))).order_by(PracticeOrder.created_at.desc()).limit(20))]
    queued = []
    for kind, identifier in events:
        result = enqueue(db, kind, identifier, settings)
        if result:
            queued.append(result)
    db.rollback()
    return queued


def claim_next(db, settings, now):
    if not settings.enable_llm_narratives:
        return None
    try:
        lock_account(db)  # Budget lock only; no account/risk mutation and no network under the lock.
        db.execute(update(NarrativeRecord).where(NarrativeRecord.state == 'REQUESTING',
            NarrativeRecord.attempted_at < now-timedelta(minutes=2)).values(state='UNKNOWN',
                result={'error_type': 'INTERRUPTED_REQUEST', 'automatic_retry': False}))
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        calls = db.scalar(select(func.count()).select_from(NarrativeRecord).where(NarrativeRecord.attempted_at >= day_start))
        latest = db.scalar(select(func.max(NarrativeRecord.attempted_at)))
        if calls >= settings.llm_max_calls_per_day or (latest and (now-aware(latest)).total_seconds() < settings.llm_min_interval_seconds):
            db.commit()
            return None
        row = db.scalar(select(NarrativeRecord).where(NarrativeRecord.state == 'PENDING',
            NarrativeRecord.provider == settings.llm_provider, NarrativeRecord.model == settings.llm_model)
            .order_by(NarrativeRecord.created_at, NarrativeRecord.id).limit(1))
        if row is None:
            db.commit()
            return None
        if row.snapshot_sha256 != digest(row.snapshot) or row.result.get('prompt_sha256') != prompt_hash():
            row.state, row.result = 'FAILED', {'error_type': 'EVIDENCE_OR_PROMPT_CHANGED'}
            db.commit()
            return None
        row.state, row.attempted_at = 'REQUESTING', now
        identifier = row.id
        db.commit()  # Durable claim before a potentially billable request; never auto-retry ambiguity.
        return identifier
    except Exception:
        db.rollback()
        raise


async def process_one(db, settings, client, now=None):
    now = now or datetime.now(timezone.utc)
    identifier = claim_next(db, settings, now)
    if identifier is None:
        return None
    row = db.get(NarrativeRecord, identifier)
    snapshot = dict(row.snapshot)
    db.rollback()
    try:
        result = await request_explanation(snapshot, settings, client)
        evidence = {'prompt_sha256': prompt_hash(), 'usage': result.usage, 'error_type': result.error_type,
                    'explanation': result.explanation.model_dump() if result.explanation else None,
                    'execution_authority': False, 'training_input': False}
        state = result.state
    except Exception:
        state, evidence = 'UNKNOWN', {'error_type': 'UNEXPECTED_REQUEST_ERROR', 'automatic_retry': False}
    # A stale process cannot replace an interrupt quarantine or another operator's state.
    changed = db.execute(update(NarrativeRecord).where(NarrativeRecord.id == identifier,
        NarrativeRecord.state == 'REQUESTING', NarrativeRecord.attempted_at == now)
        .values(state=state, result=evidence).returning(NarrativeRecord.id)).scalar_one_or_none()
    if changed:
        db.add(Event(kind='llm_narrative_result', detail={'narrative': identifier, 'state': state,
                                                      'execution_authority': False, 'training_input': False}))
    db.commit()
    return {'id': identifier, 'state': state if changed else 'CLAIM_LOST', 'execution_authority': False}


def status(db, settings):
    configured = bool((settings.deepseek_api_key if settings.llm_provider == 'deepseek' else settings.openai_api_key).get_secret_value())
    latest = db.scalar(select(NarrativeRecord).where(NarrativeRecord.provider == settings.llm_provider,
        NarrativeRecord.model == settings.llm_model, NarrativeRecord.attempted_at.is_not(None))
        .order_by(NarrativeRecord.attempted_at.desc()).limit(1))
    result = 'DISABLED' if not settings.enable_llm_narratives else 'NOT_CONFIGURED' if not configured else 'AWAITING_FIRST_RESPONSE'
    if settings.enable_llm_narratives and configured and latest:
        result = latest.state
        if latest.state == 'SUCCEEDED' and (datetime.now(timezone.utc)-aware(latest.attempted_at)).total_seconds() > 86400:
            result = 'LAST_SUCCESS_STALE'
    return result
