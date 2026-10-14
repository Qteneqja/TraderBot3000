from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def utcnow():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class Instrument(Base):
    __tablename__ = "instruments"
    symbol: Mapped[str] = mapped_column(String(24), primary_key=True)
    provider: Mapped[str] = mapped_column(String(24))
    asset_class: Mapped[str] = mapped_column(String(16))
    tick_size: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    unit_step: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    min_units: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    max_spread: Mapped[Decimal] = mapped_column(Numeric(24, 10))


class CandleRow(Base):
    __tablename__ = "market_candles"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "time", "source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("instruments.symbol"), index=True)
    timeframe: Mapped[int] = mapped_column(Integer)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    high: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    low: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    close: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    volume: Mapped[Decimal] = mapped_column(Numeric(28, 10))
    source: Mapped[str] = mapped_column(String(32))
    complete: Mapped[bool] = mapped_column(Boolean, default=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class QuoteRow(Base):
    __tablename__ = "market_quotes"
    symbol: Mapped[str] = mapped_column(ForeignKey("instruments.symbol"), primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bid: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    ask: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    source: Mapped[str] = mapped_column(String(32))


class IngestionJob(Base):
    __tablename__ = "data_ingestion_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    symbol: Mapped[str] = mapped_column(String(24))
    timeframe: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="RUNNING")
    cursor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report: Mapped[dict] = mapped_column(JSON, default=dict)


class SignalRow(Base):
    __tablename__ = "trade_signals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("instruments.symbol"))
    strategy: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    reasons: Mapped[list] = mapped_column(JSON, default=list)


class OrderRow(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    signal_id: Mapped[str] = mapped_column(ForeignKey("trade_signals.id"), unique=True)
    mode: Mapped[str] = mapped_column(String(24))
    state: Mapped[str] = mapped_column(String(32))
    symbol: Mapped[str] = mapped_column(ForeignKey("instruments.symbol"))
    direction: Mapped[str] = mapped_column(String(8))
    units: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    entry: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    stop: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    target: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    planned_risk: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    broker_id: Mapped[str | None] = mapped_column(String(64))
    close_reason: Mapped[str | None] = mapped_column(String(64))
    execution: Mapped[dict] = mapped_column(JSON, default=dict)
    fees_paid: Mapped[Decimal] = mapped_column(Numeric(24, 10), default=Decimal(0))
    financing_bars: Mapped[int] = mapped_column(Integer, default=0)


class OrderEvent(Base):
    __tablename__ = "order_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    state: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(String(512), default="")


class Account(Base):
    __tablename__ = "account_snapshots"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(24, 10), default=Decimal("10000"))
    equity: Mapped[Decimal] = mapped_column(Numeric(24, 10), default=Decimal("10000"))
    day_start: Mapped[Decimal] = mapped_column(Numeric(24, 10), default=Decimal("10000"))
    week_start: Mapped[Decimal] = mapped_column(Numeric(24, 10), default=Decimal("10000"))
    peak: Mapped[Decimal] = mapped_column(Numeric(24, 10), default=Decimal("10000"))
    day: Mapped[str] = mapped_column(String(10), default="")
    week: Mapped[str] = mapped_column(String(10), default="")
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), default="EXPERIMENTAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metadata_json: Mapped[dict] = mapped_column(JSON)


class ModelReview(Base):
    __tablename__ = "model_reviews"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"))
    status: Mapped[str] = mapped_column(String(32))
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class PaperDeployment(Base):
    __tablename__ = "paper_deployments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("account_snapshots.id"))
    scope_key: Mapped[str] = mapped_column(String(64))
    model_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"))
    review_id: Mapped[str] = mapped_column(ForeignKey("model_reviews.id"))
    previous_id: Mapped[str | None] = mapped_column(ForeignKey("paper_deployments.id"))
    rollback_of: Mapped[str | None] = mapped_column(ForeignKey("paper_deployments.id"))
    operator: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(String(512))
    contract: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PaperDeploymentSlot(Base):
    __tablename__ = "paper_deployment_slots"
    account_id: Mapped[str] = mapped_column(ForeignKey("account_snapshots.id"), primary_key=True)
    scope_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    deployment_id: Mapped[str | None] = mapped_column(ForeignKey("paper_deployments.id"))


class PaperRun(Base):
    __tablename__ = "paper_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("account_snapshots.id"))
    status: Mapped[str] = mapped_column(String(24), default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contract: Mapped[dict] = mapped_column(JSON)


class PaperSample(Base):
    __tablename__ = "paper_samples"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("paper_runs.id"), index=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str] = mapped_column(String(36))
    sequence: Mapped[int] = mapped_column(Integer)
    monotonic_ns: Mapped[Decimal] = mapped_column(Numeric(24, 0))
    healthy: Mapped[bool] = mapped_column(Boolean)
    observed_seconds: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    model_observed_seconds: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    continuity_break: Mapped[bool] = mapped_column(Boolean)
    detail: Mapped[dict] = mapped_column(JSON)


class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    __table_args__ = (UniqueConstraint("model_id", "candidate_id", name="uq_prediction_candidate_model"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[str] = mapped_column(ForeignKey("model_versions.id"))
    candidate_id: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(ForeignKey("instruments.symbol"))
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    quote_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(24))
    prediction: Mapped[dict] = mapped_column(JSON)
    candidate: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notification_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text: Mapped[str] = mapped_column(String(4096))
    status: Mapped[str] = mapped_column(String(24), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class PracticeAccount(Base):
    __tablename__ = "practice_accounts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3))
    cursor: Mapped[str] = mapped_column(String(32))
    synchronized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended: Mapped[bool] = mapped_column(Boolean, default=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    risk: Mapped[dict] = mapped_column(JSON, default=dict)
    approval: Mapped[dict] = mapped_column(JSON, default=dict)


class PracticeOrder(Base):
    __tablename__ = "practice_orders"
    __table_args__ = (
        UniqueConstraint("account_id", "signal_id", name="uq_practice_account_signal"),
        UniqueConstraint("account_id", "client_id", name="uq_practice_account_client"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("practice_accounts.id"), index=True)
    signal_id: Mapped[str] = mapped_column(String(64))
    client_id: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(24), index=True)
    request: Mapped[dict] = mapped_column(JSON)
    request_sha256: Mapped[str] = mapped_column(String(64))
    candidate: Mapped[dict] = mapped_column(JSON)
    units: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    planned_risk: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    broker_order_id: Mapped[str | None] = mapped_column(String(64))
    trade_id: Mapped[str | None] = mapped_column(String(64))
    entry: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    fees_paid: Mapped[Decimal] = mapped_column(Numeric(24, 10), default=Decimal(0))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    close_reason: Mapped[str | None] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PracticeTransaction(Base):
    __tablename__ = "practice_transactions"
    account_id: Mapped[str] = mapped_column(ForeignKey("practice_accounts.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)


class TradeOutcome(Base):
    __tablename__ = "trade_outcomes"
    __table_args__ = (UniqueConstraint("mode", "order_id", name="uq_outcome_mode_order"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mode: Mapped[str] = mapped_column(String(24))
    order_id: Mapped[str] = mapped_column(String(64))
    model_id: Mapped[str | None] = mapped_column(ForeignKey("model_versions.id"), index=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32))
    detail: Mapped[dict] = mapped_column(JSON)
    detail_sha256: Mapped[str] = mapped_column(String(64))


class LearningSchedule(Base):
    __tablename__ = "learning_schedules"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    operator: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(String(512))
    plan: Mapped[dict] = mapped_column(JSON)
    next_due: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LearningRun(Base):
    __tablename__ = "learning_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("learning_schedules.id"), index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(32), index=True)
    worker_id: Mapped[str | None] = mapped_column(String(36))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict] = mapped_column(JSON, default=dict)
