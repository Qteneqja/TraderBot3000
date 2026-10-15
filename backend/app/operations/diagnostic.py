"""Read-only, bounded operational evidence. Counts are not qualification decisions."""

from collections import Counter

from sqlalchemy import func, select

from app.machine_learning.contracts import research_code_contract
from app.models.tables import (
    CandleRow,
    Event,
    FinalEvaluation,
    Instrument,
    LearningRun,
    ModelReview,
    ModelVersion,
    OrderRow,
    PaperDeploymentSlot,
    PracticeOrder,
    QuoteRow,
    SignalRow,
)
from app.notifications.telegram import status
from app.schemas.domain import aware


def activation_report(db, settings, now):
    def grouped(column):
        return dict(db.execute(select(column, func.count()).group_by(column)).all())

    workers = {}
    for name in ('market', 'trading', 'learning', 'llm'):
        row = db.scalar(select(Event).where(Event.kind == f'{name}_worker_heartbeat')
                        .order_by(Event.time.desc()).limit(1))
        age = (now - aware(row.time)).total_seconds() if row else None
        workers[name] = {'state': 'FRESH' if age is not None and -2 <= age <= 180 else 'STALE_OR_UNSEEN',
                         'age_seconds': age}
        if name == 'trading' and row:
            workers[name]['last_cycle'] = row.detail.get('evaluations', 'NOT_RECORDED_BY_WORKER_VERSION')
    feeds = []
    for instrument in db.scalars(select(Instrument)).all():
        quote = db.get(QuoteRow, instrument.symbol)
        age = (now - aware(quote.time)).total_seconds() if quote else None
        fresh = bool(quote and quote.source == instrument.provider and age is not None
                     and -2 <= age <= settings.max_quote_age_seconds and not settings.demo_mode)
        feeds.append({'symbol': instrument.symbol, 'provider': instrument.provider,
                      'fresh_provider_quote': fresh, 'quote_age_seconds': age})
    latest = db.execute(select(SignalRow.time, SignalRow.status, SignalRow.reasons,
                               SignalRow.payload['source'].as_string().label('source'))
                        .order_by(SignalRow.time.desc(), SignalRow.id).limit(500)).all()
    reasons = Counter(reason for _, _, values, _ in latest for reason in values)
    provider = [row for row in latest if row.source in ('oanda', 'coinbase')]
    provider_reasons = Counter(reason for row in provider for reason in row.reasons)
    active = db.scalar(select(func.count()).select_from(PaperDeploymentSlot)
                      .where(PaperDeploymentSlot.account_id == 'PAPER', PaperDeploymentSlot.deployment_id.is_not(None)))
    return {'as_of': now.isoformat(), 'mode': settings.trading_mode, 'fixture_mode': settings.demo_mode,
            'live_execution': 'UNSUPPORTED', 'workers': workers, 'feeds': feeds,
            'current_research_code_sha256': research_code_contract()['sha256'],
            'history': [{'symbol': symbol, 'source': source, 'timeframe': timeframe, 'candles': count,
                         'first': aware(first).isoformat(), 'last': aware(last).isoformat(),
                         'coverage': 'REQUIRES_SEPARATE_SESSION_AUDIT'}
                        for symbol, source, timeframe, count, first, last in db.execute(select(
                            CandleRow.symbol, CandleRow.source, CandleRow.timeframe, func.count(),
                            func.min(CandleRow.time), func.max(CandleRow.time))
                            .group_by(CandleRow.symbol, CandleRow.source, CandleRow.timeframe))],
            'models': grouped(ModelVersion.status), 'reviews': grouped(ModelReview.status),
            'learning_runs': grouped(LearningRun.state), 'final_evaluations': grouped(FinalEvaluation.state),
            'active_paper_deployments': active, 'paper_orders': grouped(OrderRow.state),
            'practice_orders': grouped(PracticeOrder.state),
            'signals': {'stored_counts': grouped(SignalRow.status), 'recent_sample_limit': 500,
                        'sample_count': len(latest), 'rejection_reasons': dict(reasons),
                        'sample_sources': dict(Counter(row.source or 'UNSPECIFIED' for row in latest)),
                        'provider_sample_count': len(provider), 'provider_rejection_reasons': dict(provider_reasons),
                        'latest_time': aware(latest[0][0]).isoformat() if latest else None,
                        'note': 'All-source counts include legacy fixtures; provider sample is separate. Stored decisions are unique by signal, not total evaluations.'},
            'telegram': status(db, settings),
            'first_entry_blocker': 'NO_ACTIVE_QUALIFIED_PAPER_DEPLOYMENT' if not active else 'RUNTIME_CHECKS_REQUIRED',
            'execution_authority': False}
