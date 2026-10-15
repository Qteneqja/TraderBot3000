"""Durable claims with safe receipts; uncertain sends are never blindly replayed."""

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.tables import Event, Notification
from app.schemas.domain import aware


def enqueue(db: Session, event_id: str, text: str):
    if not db.get(Notification, event_id):
        db.add(Notification(id=event_id, text=text[:4096]))
        db.commit()


def status(db, settings):
    counts = dict(db.execute(select(Notification.status, func.count()).group_by(Notification.status)).all())
    latest = db.scalar(select(Notification).order_by(Notification.claimed_at.desc().nullslast(),
                                                    Notification.id).limit(1))
    configured = bool(settings.telegram_bot_token.get_secret_value() and settings.telegram_chat_id)
    confirmed = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.status == 'DELIVERED', Notification.delivered_at.is_not(None)))
    preflight = db.scalar(select(Event).where(Event.kind == 'telegram_connectivity_failed')
                          .order_by(Event.time.desc()).limit(1))
    state = ('NOT_CONFIGURED' if not configured else 'DISABLED' if not settings.enable_notifications
             else 'AWAITING_DELIVERY')
    if configured and settings.enable_notifications and latest is not None:
        state = latest.status
    return {'status': state, 'automatic_delivery_enabled': settings.enable_notifications,
            'monitoring_enabled': settings.enable_telegram_monitoring,
            'counts': counts, 'latest_attempt': None if latest is None else {
                'state': latest.status, 'attempts': latest.attempts, 'error_code': latest.error_code,
                'claimed_at': aware(latest.claimed_at).isoformat() if latest.claimed_at else None,
                'delivered_at': aware(latest.delivered_at).isoformat() if latest.delivered_at else None},
            'last_preflight_failure': None if preflight is None else {
                'time': aware(preflight.time).isoformat(), 'error_code': preflight.detail.get('error_code')},
            'delivery_evidence': 'API_CONFIRMED' if confirmed else 'NOT_VERIFIED'}


async def deliver(db: Session, settings: Settings, client: httpx.AsyncClient, *, event_id=None, now=None):
    now = now or datetime.now(timezone.utc)
    token = settings.telegram_bot_token.get_secret_value()
    if not token or not settings.telegram_chat_id:
        return
    db.execute(update(Notification).where(Notification.status == 'SENDING', or_(
        Notification.claimed_at.is_(None), Notification.claimed_at < now - timedelta(minutes=2)))
        .values(status='UNKNOWN', error_code='INTERRUPTED_DELIVERY'))
    db.commit()
    query = select(Notification.id).where(Notification.status == 'PENDING', or_(
        Notification.retry_at.is_(None), Notification.retry_at <= now))
    if event_id is not None:
        query = query.where(Notification.id == event_id)
    identifiers = db.scalars(query.order_by(Notification.created_at, Notification.id).limit(20)).all()
    db.rollback()
    for identifier in identifiers:
        claimed = db.execute(update(Notification).where(Notification.id == identifier,
            Notification.status == 'PENDING', or_(Notification.retry_at.is_(None), Notification.retry_at <= now))
            .values(status='SENDING', attempts=Notification.attempts + 1, claimed_at=now,
                    error_code=None, retry_at=None).returning(Notification.id)).scalar_one_or_none()
        db.commit()
        if claimed is None:
            continue
        event = db.get(Notification, identifier)
        try:
            response = await client.post(f'https://api.telegram.org/bot{token}/sendMessage',
                json={'chat_id': settings.telegram_chat_id, 'text': event.text}, timeout=10,
                follow_redirects=False)
            body = response.json() if len(response.content) <= 65536 else {}
            if not isinstance(body, dict):
                body = {}
            if response.status_code == 429 and body.get('ok') is False:
                seconds = body.get('parameters', {}).get('retry_after')
                if type(seconds) is int and 1 <= seconds <= 86400 and event.attempts < 5:
                    event.status, event.retry_at = 'PENDING', now + timedelta(seconds=seconds)
                    event.error_code = 'RATE_LIMITED'
                else:
                    event.status, event.error_code = 'FAILED', 'RATE_LIMIT_EXHAUSTED'
            elif response.is_success and body.get('ok') is True:
                receipt = body.get('result', {})
                confirmed = (isinstance(receipt, dict) and type(receipt.get('message_id')) is int
                             and receipt['message_id'] > 0 and isinstance(receipt.get('chat'), dict))
                if confirmed and settings.telegram_chat_id.lstrip('-').isdigit():
                    confirmed = str(receipt['chat'].get('id')) == settings.telegram_chat_id
                event.status = 'DELIVERED' if confirmed else 'UNKNOWN'
                event.delivered_at = datetime.now(timezone.utc) if confirmed else None
                event.error_code = None if confirmed else 'INVALID_DELIVERY_RECEIPT'
            elif 400 <= response.status_code < 500 and body.get('ok') is False:
                event.status, event.error_code = 'FAILED', f'HTTP_{response.status_code}'
            else:
                event.status, event.error_code = 'UNKNOWN', 'UNCONFIRMED_RESPONSE'
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            event.status, event.error_code = 'UNKNOWN', 'DELIVERY_UNCERTAIN'
        outcome = {key: getattr(event, key) for key in ('status', 'error_code', 'retry_at', 'delivered_at')}
        attempts = event.attempts
        db.expunge(event)
        changed = db.execute(update(Notification).where(Notification.id == identifier,
            Notification.status == 'SENDING', Notification.claimed_at == now,
            Notification.attempts == attempts).values(**outcome)).rowcount
        if changed:
            db.add(Event(kind='notification_delivery_result', detail={'event': identifier,
                         'state': outcome['status'], 'error_code': outcome['error_code']}))
        db.commit()


async def connectivity_test(db, settings, client, identifier, operator):
    """Explicit operator-only single message; never drains queued trading notifications."""
    if not identifier.strip() or len(identifier) > 40 or not operator.strip():
        raise ValueError('A stable test identifier and operator are required')
    if not settings.telegram_bot_token.get_secret_value() or not settings.telegram_chat_id:
        return {'status': 'NOT_CONFIGURED', 'message_sent': False}
    key = f'telegram-test:{identifier}'
    existing = db.get(Notification, key)
    if existing is not None:
        return {'status': existing.status, 'message_sent': existing.status == 'DELIVERED', 'automatic_retry': False}
    base = f'https://api.telegram.org/bot{settings.telegram_bot_token.get_secret_value()}'
    for method, params in (('getMe', None), ('getChat', {'chat_id': settings.telegram_chat_id})):
        try:
            response = await client.get(f'{base}/{method}', params=params, timeout=10, follow_redirects=False)
            body = response.json() if len(response.content) <= 65536 else {}
            valid = (response.is_success and isinstance(body, dict) and body.get('ok') is True
                     and isinstance(body.get('result'), dict))
            if valid and method == 'getMe':
                valid = body['result'].get('is_bot') is True
            if valid and method == 'getChat' and settings.telegram_chat_id.lstrip('-').isdigit():
                valid = str(body['result'].get('id')) == settings.telegram_chat_id
            if not valid:
                if method == 'getChat' and isinstance(body, dict) and body.get('description') == 'Bad Request: chat not found':
                    db.add(Event(kind='telegram_connectivity_failed', detail={'error_code': 'CHAT_NOT_FOUND'}))
                    db.commit()
                    return {'status': 'CHAT_NOT_FOUND', 'message_sent': False}
                raise ValueError('Preflight failed')
        except (httpx.HTTPError, ValueError, TypeError):
            code = 'BOT_AUTH_UNVERIFIED' if method == 'getMe' else 'CHAT_UNVERIFIED'
            db.add(Event(kind='telegram_connectivity_failed', detail={'error_code': code}))
            db.commit()
            return {'status': code, 'message_sent': False}
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    insert = pg_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert
    db.execute(insert(Notification).values(id=key,
        text=f'AEGISTRADE AI — CONNECTION TEST\nTrading Mode: {settings.trading_mode}\n'
             'This is a system connectivity test, not a trading signal.\n'
             'No model activation or broker order is authorized by this message.',
        status='PENDING', attempts=0).on_conflict_do_nothing(index_elements=['id']))
    db.add(Event(kind='telegram_connectivity_authorized', detail={'event': key, 'operator': operator[:120]}))
    db.commit()
    await deliver(db, settings, client, event_id=key)
    row = db.get(Notification, key)
    if row.status == 'PENDING':
        # One authorized connectivity test must not be picked up later by the general worker.
        row.status, row.error_code = 'FAILED', 'TEST_RETRY_REQUIRES_AUTHORIZATION'
        db.commit()
    return {'status': row.status, 'message_sent': row.status == 'DELIVERED', 'automatic_retry': False}
