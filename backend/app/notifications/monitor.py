"""Authenticated read-only commands. No broker, deployment or risk mutation imports."""

import hashlib
from datetime import datetime, timezone

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.models.tables import (
    Account,
    ModelReview,
    ModelVersion,
    Notification,
    OrderRow,
    PaperDeploymentSlot,
    PracticeAccount,
    PracticeOrder,
    QuoteRow,
    SignalRow,
    TelegramCursor,
)
from app.schemas.domain import aware

COMMANDS = {'/status', '/models', '/positions', '/trades', '/performance', '/signals', '/risk', '/news'}


def response_text(db, settings, command, now):
    """Allowlisted aggregates only; no account IDs, balances, secrets or raw payloads."""
    def counts(column, *where):
        return dict(db.execute(select(column, func.count()).where(*where).group_by(column)).all())

    provider = SignalRow.payload['source'].as_string().in_(('oanda', 'coinbase'))
    orders = select(OrderRow.state, func.count()).join(SignalRow, OrderRow.signal_id == SignalRow.id).where(provider)
    paper_counts = dict(db.execute(orders.group_by(OrderRow.state)).all())
    practice_counts = counts(PracticeOrder.state)
    if command == '/status':
        active = db.scalar(select(func.count()).select_from(PaperDeploymentSlot).where(
            PaperDeploymentSlot.account_id == 'PAPER', PaperDeploymentSlot.deployment_id.is_not(None)))
        quotes = db.scalars(select(QuoteRow).where(QuoteRow.source.in_(('oanda', 'coinbase')))).all()
        fresh = sum(-2 <= (now-aware(q.time)).total_seconds() <= settings.max_quote_age_seconds for q in quotes)
        detail = (f'Mode: {settings.trading_mode}; fixtures: {settings.demo_mode}\n'
                  f'Active PAPER deployments: {active}\nFresh provider quotes: {fresh}/{len(quotes)} stored\n'
                  'Broker connectivity: not checked by this command\n'
                  'Telegram: reply delivery requires API receipt\nLive money: unsupported')
    elif command == '/models':
        detail = (f'Registry: {counts(ModelVersion.status)}\nReviews: {counts(ModelReview.status)}\n'
                  'Registry status alone is not qualification or deployment authority.')
    elif command in ('/positions', '/trades'):
        detail = (f'Provider PAPER order states: {paper_counts}\nPractice order states: {practice_counts}\n'
                  'Fixture PAPER orders excluded. Broker positions require separate reconciliation.')
    elif command == '/performance':
        closed, recorded, total = db.execute(select(func.count(), func.count(OrderRow.pnl), func.sum(OrderRow.pnl)).join(
            SignalRow, OrderRow.signal_id == SignalRow.id).where(provider, OrderRow.state == 'CLOSED')).one()
        pnl = 'NO_COMPLETED_TRADES' if not closed else str(total) if recorded == closed else 'UNKNOWN_INCOMPLETE_RECORDS'
        detail = (f'Provider PAPER closed orders: {closed}\n'
                  f'Recorded realized PAPER P&L (USD): {pnl}\n'
                  'Practice P&L: not aggregated here (CAD account).\nNo profitability or trial acceptance inferred.')
    elif command == '/signals':
        detail = f'Provider signal states: {counts(SignalRow.status, provider)}\nHistorical decisions; no new signal is generated.'
    elif command == '/risk':
        paper = db.get(Account, 'PAPER')
        practice = list(db.scalars(select(PracticeAccount)).all())
        detail = (f'PAPER suspended: {paper.suspended if paper else "UNKNOWN"}\n'
                  f'Practice accounts suspended: {sum(p.suspended for p in practice)}/{len(practice)} stored\n'
                  f'Risk/trade cap: {settings.risk_per_trade}; position cap: {settings.max_open_positions}\n'
                  'Read-only snapshot; deterministic entry checks still apply.')
    else:
        detail = 'News monitoring is not configured. No sentiment or trading authority is inferred.'
    return f'AEGISTRADE AI — READ-ONLY {command}\nUTC: {now.isoformat()}\n{detail}'[:4096]


async def poll(db, settings, client, *, now=None):
    """Commit cursor + reply intents atomically; existing delivery claims handle sends."""
    if not settings.enable_notifications or not settings.enable_telegram_monitoring:
        return {'status': 'DISABLED', 'enqueued': 0}
    token, chat = settings.telegram_bot_token.get_secret_value(), settings.telegram_chat_id
    if not token or not chat.isdigit() or int(chat) <= 0:
        return {'status': 'PRIVATE_NUMERIC_RECIPIENT_REQUIRED', 'enqueued': 0}
    key = hashlib.sha256(f'{token}:{chat}'.encode()).hexdigest()
    cursor = db.get(TelegramCursor, key)
    if cursor is None:
        db.add(TelegramCursor(id=key, next_update=0, initialized=False))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        cursor = db.get(TelegramCursor, key)
    old, initialized = cursor.next_update, cursor.initialized
    db.rollback()  # No DB transaction/lock held during the network call.
    try:
        response = await client.get(f'https://api.telegram.org/bot{token}/getUpdates',
            params={'offset': old if initialized else -1, 'limit': 20, 'timeout': 0,
                    'allowed_updates': '["message"]'}, timeout=10, follow_redirects=False)
        body = response.json() if len(response.content) <= 131072 else None
        if (not response.is_success or not isinstance(body, dict) or body.get('ok') is not True
                or not isinstance(body.get('result'), list) or len(body['result']) > 20):
            return {'status': 'POLL_UNCONFIRMED', 'enqueued': 0}
        updates = body['result']
        ids = [u.get('update_id') if isinstance(u, dict) else None for u in updates]
        if any(type(i) is not int or i < 0 for i in ids) or ids != sorted(set(ids)):
            return {'status': 'INVALID_UPDATE_SEQUENCE', 'enqueued': 0}
        next_update = max([old]+[i+1 for i in ids])
        claimed = db.execute(update(TelegramCursor).where(TelegramCursor.id == key,
            TelegramCursor.next_update == old, TelegramCursor.initialized == initialized)
            .values(next_update=next_update, initialized=True)).rowcount
        if not claimed:
            db.rollback()
            return {'status': 'CONCURRENT_POLL', 'enqueued': 0}
        enqueued = 0
        # First enable deliberately discards pre-existing updates; never replay old commands.
        for item in updates if initialized else []:
            if item['update_id'] < old:
                continue
            message = item.get('message')
            if not isinstance(message, dict):
                continue
            if any(key in message for key in ('forward_origin', 'forward_date', 'sender_chat')):
                continue
            recipient, sender = message.get('chat'), message.get('from')
            if (not isinstance(recipient, dict) or not isinstance(sender, dict)
                    or type(recipient.get('id')) is not int or str(recipient['id']) != chat
                    or recipient.get('type') != 'private' or type(sender.get('id')) is not int
                    or sender.get('id') != recipient['id']
                    or sender.get('is_bot') is not False):
                continue
            command = message.get('text')
            if not isinstance(command, str) or command not in COMMANDS:
                continue
            identifier = f'tg-monitor:{key[:16]}:{item["update_id"]}'
            if db.get(Notification, identifier) is None:
                db.add(Notification(id=identifier, text=response_text(db, settings, command,
                    now or datetime.now(timezone.utc))))
                enqueued += 1
        db.commit()
        return {'status': 'POLL_COMMITTED' if initialized else 'BOOTSTRAPPED_WITHOUT_REPLAY', 'enqueued': enqueued}
    except (httpx.HTTPError, ValueError, TypeError):
        db.rollback()
        return {'status': 'POLL_UNCERTAIN', 'enqueued': 0}
