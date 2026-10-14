"""Immutable outcome attribution. Observed trades never become automatic training authority."""

from decimal import Decimal as D

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.execution.paper import valid_execution
from app.machine_learning.policy import digest
from app.models.tables import (
    Event,
    ModelVersion,
    OrderRow,
    PaperDeployment,
    PracticeAccount,
    PracticeOrder,
    SignalRow,
    TradeOutcome,
)
from app.schemas.domain import aware


def outcome_payload(db, order, mode):
    if mode == "PAPER":
        signal = db.get(SignalRow, order.signal_id)
        candidate = signal.payload if signal else {}
        model_id = candidate.get("model_version")
        model = db.get(ModelVersion, model_id) if model_id else None
        deployment_id = order.execution.get("deployment_id")
        deployment = db.get(PaperDeployment, deployment_id) if deployment_id else None
        valid = (valid_execution(order) and model is not None and order.pnl is not None and deployment is not None
                 and deployment.model_id == model_id and aware(deployment.created_at) <= aware(order.opened_at)
                 and candidate.get("deployment_id") == deployment_id)
        source = order.execution.get("source")
        status = "VERIFIED_PAPER" if valid and source in ("oanda", "coinbase") else "QUARANTINED"
        if source == "fixture":
            status = "FIXTURE_DIAGNOSTIC"
        net, fees, currency = order.pnl, order.fees_paid, "USD"
        reason, closed, exit_price = order.close_reason, order.closed_at, order.exit
        label = {"TAKE_PROFIT": 1, "STOP_LOSS": 0, "STOP_AMBIGUOUS": 0, "TIMEOUT": 2}.get(reason)
        execution = dict(order.execution)
    else:
        candidate = order.candidate
        model_id = candidate.get("model_version")
        model = db.get(ModelVersion, model_id) if model_id else None
        account = db.get(PracticeAccount, order.account_id)
        source = candidate.get("source")
        approval = db.scalar(select(Event.id).where(Event.kind == "practice_gateway_approved",
                             Event.detail["approval_id"].as_string() == candidate.get("gateway_approval_id", "")).limit(1))
        valid = (model is not None and account is not None and order.realized_pnl is not None and approval is not None
                 and order.request_sha256 == digest(order.request))
        status = "VERIFIED_PRACTICE" if valid and source == "oanda" else "QUARANTINED"
        net, fees, currency = order.realized_pnl, order.fees_paid, account.currency if account else None
        reason, closed, exit_price = order.close_reason, order.closed_at, order.exit
        label = {"TAKE_PROFIT_ORDER": 1, "STOP_LOSS_ORDER": 0}.get(reason)
        if reason == "MARKET_ORDER_TRADE_CLOSE" and closed and (
            aware(closed) - aware(order.created_at)).total_seconds() >= int(candidate.get("timeframe", 300)) * 12:
            label = 2
        execution = {"broker_order_id": order.broker_order_id, "trade_id": order.trade_id,
                     "account_fingerprint": order.account_id,
                     "request_sha256": order.request_sha256, "gateway_approval_id": candidate.get("gateway_approval_id")}
    if closed is None:
        return None
    symbol = order.symbol if mode == "PAPER" else candidate.get("symbol")
    if status != "FIXTURE_DIAGNOSTIC" and (model is None or model.metadata_json.get("source") != source
                                          or model.metadata_json.get("symbol") != symbol):
        status = "QUARANTINED"
    opened = aware(order.opened_at if mode == "PAPER" else order.created_at)
    if (aware(closed) < opened or order.entry is None or exit_price is None
        or min(order.entry, exit_price) <= 0):
        status = "QUARANTINED"
    equity = (order.execution.get("account_equity_at_entry") if mode == "PAPER" else
              candidate.get("account_equity_at_reservation"))
    probabilities = {name: candidate.get(key) for name, key in (
        ("stop", "probability_stop"), ("target", "probability"), ("timeout", "probability_timeout"))}
    try:
        values = [D(str(p)) for p in probabilities.values()]
        if any(not p.is_finite() or not 0 <= p <= 1 for p in values) or abs(sum(values) - 1) > D('.000001'):
            status = "QUARANTINED"
    except (ValueError, ArithmeticError):
        status = "QUARANTINED"
    detail = {"schema": "trade-outcome-v1", "mode": mode, "order_id": order.id,
              "model_id": model_id if model else None, "artifact_sha256": model.metadata_json.get("artifact_sha256") if model else None,
              "symbol": order.symbol if mode == "PAPER" else candidate.get("symbol"), "source": source,
              "strategy": candidate.get("strategy"), "regime": candidate.get("regime"),
              "prediction_time": candidate.get("time"), "opened_at": opened.isoformat(),
              "closed_at": aware(closed).isoformat(), "holding_seconds": (aware(closed) - opened).total_seconds(),
              "probabilities": probabilities, "outcome_label": label,
              "entry": str(order.entry), "exit": str(exit_price), "stop": str(order.stop if mode == "PAPER" else candidate.get("stop")),
              "target": str(order.target if mode == "PAPER" else candidate.get("target")),
              "units": str(order.units), "currency": currency, "net_pnl": str(net) if net is not None else None,
              "fees_paid": str(fees), "close_reason": reason, "execution": execution,
              "equity_at_entry": equity, "planned_risk": str(order.planned_risk),
              "net_r": str(net / order.planned_risk) if net is not None and order.planned_risk > 0 else None,
              "status": status, "training_eligible": False,
              "limitations": ["Executed-trade outcomes are selected observations, not independent samples.",
                              "Research retraining uses causally reconstructed market labels; outcomes are not duplicated into its training set."]}
    return detail


def collect_outcomes(db, limit=200):
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    added = 0
    try:
        for mode, table in (("PAPER", OrderRow), ("OANDA_PRACTICE", PracticeOrder)):
            existing = select(TradeOutcome.order_id).where(TradeOutcome.mode == mode)
            query = select(table).where(table.state == "CLOSED", table.id.not_in(existing))
            if mode == "PAPER":
                query = query.where(OrderRow.mode == "PAPER")
            for order in db.scalars(query.order_by(table.id).limit(limit)).all():
                detail = outcome_payload(db, order, mode)
                if detail is None:
                    continue
                identifier = digest([mode, order.id])
                checksum = digest(detail)
                inserted = db.execute(insert(TradeOutcome).values(id=identifier, mode=mode, order_id=order.id,
                    model_id=detail["model_id"], closed_at=aware(order.closed_at), status=detail["status"],
                    detail=detail, detail_sha256=checksum).on_conflict_do_nothing(index_elements=["id"])
                    .returning(TradeOutcome.id)).scalar_one_or_none()
                if db.get(TradeOutcome, identifier).detail_sha256 != checksum:
                    raise ValueError("Immutable outcome attribution changed")
                added += int(inserted is not None)
        db.commit()
        return added
    except Exception:
        db.rollback()
        raise
