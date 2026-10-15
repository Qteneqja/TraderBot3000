"""Plain-text lifecycle facts; no account identifiers or LLM assertions."""

from decimal import Decimal

from app.models.tables import PracticeAccount, SignalRow
from app.schemas.domain import aware


def paper_message(db, order, state):
    signal = db.get(SignalRow, order.signal_id)
    setup = signal.payload if signal else {}
    distance = abs(order.entry - order.stop)
    reward = abs(order.target - order.entry)
    lines = [f"AEGISTRADE AI — PAPER {state}", "Internal simulation; not a broker fill.",
             f"Data source: {order.execution.get('source')}",
             f"Market: {order.symbol}", f"Direction: {order.direction}",
             f"Order: {order.id}", f"Entry: {order.entry}", f"Stop-loss: {order.stop}",
             f"Take-profit: {order.target}", f"Units: {order.units}",
             f"Planned risk (USD): {order.planned_risk}",
             f"Reward/risk at fill: {reward / distance if distance else 'UNAVAILABLE'}",
             f"Model: {setup.get('model_version') or 'UNAVAILABLE'}",
             f"Strategy: {setup.get('strategy') or 'UNAVAILABLE'}",
             f"Timeframe (seconds): {order.execution.get('timeframe')}",
             f"Target probability: {setup.get('probability') or 'UNAVAILABLE'}"]
    if state == "CLOSED":
        seconds = (aware(order.closed_at) - aware(order.opened_at)).total_seconds()
        lines += [f"Exit: {order.exit}", f"Net P&L (USD): {order.pnl}",
                  f"Fees and financing (USD): {order.fees_paid}",
                  f"Holding seconds: {Decimal(str(seconds))}", f"Close reason: {order.close_reason}"]
    return "\n".join(lines)[:4096]


def practice_message(db, order, state):
    setup = order.candidate
    account = db.get(PracticeAccount, order.account_id)
    currency = account.currency if account else 'UNVERIFIED'
    classification = ('Execution or protection unverified; simulated funds.' if state == 'QUARANTINED'
                      else 'Broker-confirmed demo records; simulated funds.')
    lines = [f'AEGISTRADE AI — OANDA PRACTICE {state}', classification,
             f"Market: {setup['symbol']}", f"Direction: {setup['direction']}",
             f'Order reference: {order.id}', f'Broker order: {order.broker_order_id}',
             f'Fill entry: {order.entry}', f"Requested stop-loss: {setup.get('stop')}",
             f"Requested take-profit: {setup.get('target')}", f'Signed units: {order.units}',
             f'Planned risk ({currency}): {order.planned_risk}',
             f"Model: {setup.get('model_version', 'UNAVAILABLE')}",
             f"Strategy: {setup.get('strategy', 'UNAVAILABLE')}",
             f"Target probability: {setup.get('probability', 'UNAVAILABLE')}"]
    if state == 'CLOSED':
        lines += [f'Exit: {order.exit}', f'Net realized P&L ({currency}): {order.realized_pnl}',
                  f'Allocated fees ({currency}): {order.fees_paid}',
                  'Net result includes broker cumulative financing and dividend adjustments.',
                  f'Close reason: {order.close_reason}']
    if state == 'QUARANTINED':
        lines += ['Protection or ownership is unverified; new entries are suspended.']
    return '\n'.join(lines)[:4096]
