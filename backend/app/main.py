import hmac
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import get_db
from app.market_data.store import load_candles
from app.models.tables import (
    Account,
    CandleRow,
    Event,
    FinalEvaluation,
    Instrument,
    LearningRun,
    LearningSchedule,
    ModelPrediction,
    ModelReview,
    ModelVersion,
    OrderRow,
    PaperDeployment,
    PaperDeploymentSlot,
    PaperRun,
    PaperSample,
    PracticeAccount,
    PracticeOrder,
    QuoteRow,
    SignalRow,
    TradeOutcome,
)
from app.schemas.domain import aware
from app.strategies.registry import STRATEGIES

configure_logging()


@asynccontextmanager
async def lifespan(app):
    get_settings()  # Validate before accepting traffic; migrations run separately.
    yield


app = FastAPI(title="AegisTrade AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def admin(authorization: str | None = Header(default=None)):
    expected = get_settings().admin_token.get_secret_value()
    if not expected:
        raise HTTPException(503, "Administrative access disabled; configure ADMIN_TOKEN")
    if not authorization or not hmac.compare_digest(authorization, f"Bearer {expected}"):
        raise HTTPException(401, "Authentication required")


def serialize(row):
    result = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        result[column.name] = (
            aware(value).isoformat()
            if isinstance(value, datetime)
            else str(value)
            if isinstance(value, Decimal)
            else value
        )
    return result


@app.get("/health/live")
def live():
    return {"status": "ok", "application": "AegisTrade AI"}


@app.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if revision != "0008" or db.get(Account, "PAPER") is None:
            raise ValueError("Uninitialized database")
    except Exception:
        raise HTTPException(503, "Database not ready; run migrations and bootstrap") from None
    return {"status": "ready", "schema": revision}


@app.get("/api/overview")
def overview(db: Session = Depends(get_db)):
    settings = get_settings()
    account = db.get(Account, "PAPER")
    if account is None:
        raise HTTPException(503, "Initialize the database with python -m app.cli init")
    quotes = db.scalars(select(QuoteRow)).all()
    now = datetime.now(timezone.utc)
    positions = db.scalars(select(OrderRow).where(OrderRow.state == "FILLED")).all()
    deployment_count = db.scalar(
        select(func.count())
        .select_from(PaperDeploymentSlot)
        .where(PaperDeploymentSlot.account_id == "PAPER", PaperDeploymentSlot.deployment_id.is_not(None))
    )
    return {
        "name": settings.app_name,
        "mode": settings.trading_mode,
        "demo": settings.demo_mode,
        "account": serialize(account),
        "open_positions": len(positions),
        "pending_orders": db.scalar(
            select(func.count()).select_from(OrderRow).where(OrderRow.state == "PENDING")
        ),
        "signals": db.scalar(select(func.count()).select_from(SignalRow)),
        "planned_risk": sum(float(p.planned_risk) for p in positions),
        "quotes": [serialize(q) | {"stale": (now - aware(q.time)).total_seconds() > 30} for q in quotes],
        "live_execution": "UNSUPPORTED",
        "model_status": "PAPER_TRIAL_CONFIGURED" if deployment_count else "NO_EXECUTION_VALIDATED_MODEL",
        "paper_deployments": deployment_count,
        "news_status": "UNAVAILABLE",
        "server_time": now.isoformat(),
    }


@app.get("/api/instruments")
def instruments(db: Session = Depends(get_db)):
    return [serialize(i) for i in db.scalars(select(Instrument)).all()]


@app.get("/api/learning")
def learning_status(db: Session = Depends(get_db)):
    schedules = db.scalars(select(LearningSchedule).order_by(LearningSchedule.created_at.desc())).all()
    keys = ('model', 'family', 'status', 'validation', 'sample_counts', 'test', 'error_type')
    # Project bounded JSON fields in SQL: never deserialize full replay curves on a dashboard poll.
    fields = [LearningRun.id, LearningRun.state, LearningRun.scheduled_for,
              LearningRun.result['error_type'].label('error_type'), LearningRun.result['final_test'].label('final_test')]
    fields += [LearningRun.result['candidates'][i][key].label(f'c{i}_{key}') for i in range(4) for key in keys]
    runs = db.execute(select(*fields).order_by(LearningRun.scheduled_for.desc()).limit(20)).mappings().all()
    return {
        "schedules": [{"id": s.id, "enabled": s.enabled, "symbol": s.plan["symbol"], "source": s.plan["source"],
                       "families": s.plan["families"], "interval_days": s.plan["interval_days"],
                       "next_due": aware(s.next_due).isoformat(), "validation_only": True} for s in schedules],
        "runs": [{"id": r['id'], "state": r['state'], "scheduled_for": aware(r['scheduled_for']).isoformat(),
                  "error_type": r['error_type'], "final_test": r['final_test'],
                  "candidates": [{key: r[f'c{i}_{key}'] for key in keys} for i in range(4) if r[f'c{i}_family']],
                  "execution_authority": False} for r in runs],
        "outcomes": [{"mode": mode, "status": status, "count": count} for mode, status, count in db.execute(
            select(TradeOutcome.mode, TradeOutcome.status, func.count()).group_by(TradeOutcome.mode, TradeOutcome.status))],
        "promotion": "EXPLICIT_OPERATOR_APPROVAL_ONLY", "live_execution": "UNSUPPORTED",
    }


@app.get('/api/final-evaluations')
def final_evaluations(db: Session = Depends(get_db)):
    return [{'id': row.id, 'parent': row.parent_id, 'model': row.model_id, 'state': row.state,
             'start': row.plan['start'], 'end': row.plan['end'], 'result': row.result,
             'execution_authority': False} for row in db.scalars(select(FinalEvaluation)
                .order_by(FinalEvaluation.created_at.desc()).limit(50))]


@app.get("/api/practice-status")
def practice_status(db: Session = Depends(get_db)):
    from app.brokers.reconciliation import account_key

    current = account_key(get_settings().oanda_account_id)
    rows = db.scalars(select(PracticeAccount).order_by(PracticeAccount.id)).all()
    return [{"account_reference": row.id[:12], "current": row.id == current, "currency": row.currency,
             "reconciled": row.reconciled, "suspended": row.suspended,
             "synchronized_at": aware(row.synchronized_at).isoformat(),
             "approval_scope": row.approval.get("scope", "NOT_APPROVED"),
             "order_states": {state: count for state, count in db.execute(select(PracticeOrder.state, func.count())
                              .where(PracticeOrder.account_id == row.id).group_by(PracticeOrder.state))}}
            for row in rows]


@app.get("/api/data-coverage")
def data_coverage(db: Session = Depends(get_db)):
    rows = db.execute(select(CandleRow.symbol, CandleRow.source, CandleRow.timeframe,
                             func.count(), func.min(CandleRow.time), func.max(CandleRow.time))
                      .group_by(CandleRow.symbol, CandleRow.source, CandleRow.timeframe)
                      .order_by(CandleRow.symbol, CandleRow.source, CandleRow.timeframe)).all()
    return [{"symbol": symbol, "source": source, "timeframe": timeframe, "candles": count,
             "first": aware(first).isoformat(), "last": aware(last).isoformat(),
             "classification": "SYNTHETIC_FIXTURE" if source == "fixture" else "PROVIDER_HISTORY",
             "qualification": "NOT_ASSESSED"} for symbol, source, timeframe, count, first, last in rows]


@app.get("/api/candles")
def candles(
    symbol: str = "EUR_USD",
    timeframe: int = Query(300, ge=60, le=14400),
    limit: int = Query(300, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    instrument = db.get(Instrument, symbol)
    if not instrument:
        raise HTTPException(404, "Unknown instrument")
    source = "fixture" if get_settings().demo_mode else instrument.provider
    return {
        "source": source,
        "execution_quality": False,
        "candles": [c.model_dump(mode="json") for c in load_candles(db, symbol, timeframe, source, limit)],
    }


@app.get("/api/signals")
def signals(db: Session = Depends(get_db)):
    return [
        serialize(s) for s in db.scalars(select(SignalRow).order_by(SignalRow.time.desc()).limit(100)).all()
    ]


@app.get("/api/orders")
def orders(db: Session = Depends(get_db)):
    return [
        serialize(s)
        for s in db.scalars(select(OrderRow).order_by(OrderRow.opened_at.desc()).limit(100)).all()
    ]


@app.get("/api/models")
def models(limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    keys = ("family", "symbol", "source", "strategy", "timeframe", "evaluation_mode", "validation", "test", "sample_counts", "limitations")
    return [{"id": m.id, "status": m.status, "created_at": aware(m.created_at).isoformat(),
             "metadata_json": {k: m.metadata_json.get(k) for k in keys}}
            for m in db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(limit)).all()]


@app.get("/api/models/{version_id}")
def model_details(version_id: str, db: Session = Depends(get_db)):
    model = db.get(ModelVersion, version_id)
    if model is None:
        raise HTTPException(404, "Unknown model version")
    return serialize(model)


@app.get("/api/predictions")
def predictions(db: Session = Depends(get_db)):
    return [
        serialize(p)
        for p in db.scalars(select(ModelPrediction).order_by(ModelPrediction.time.desc()).limit(100)).all()
    ]


@app.get("/api/model-reviews")
def model_reviews(db: Session = Depends(get_db)):
    return [
        serialize(r)
        for r in db.scalars(select(ModelReview).order_by(ModelReview.created_at.desc()).limit(50)).all()
    ]


@app.get("/api/strategies")
def strategies():
    return [
        {"id": k, **v, "version": "1", "status": "RESEARCH", "validated_edge": False}
        for k, v in STRATEGIES.items()
    ]


@app.get("/api/risk")
def risk():
    s = get_settings()
    return {
        "risk_per_trade": s.risk_per_trade,
        "max_daily_loss": s.max_daily_loss,
        "max_weekly_loss": s.max_weekly_loss,
        "max_open_positions": s.max_open_positions,
        "max_portfolio_risk": s.max_portfolio_risk,
        "max_leverage": s.max_leverage,
        "probability_threshold": s.initial_probability_threshold,
        "min_risk_reward": s.min_risk_reward,
        "max_quote_age_seconds": s.max_quote_age_seconds,
        "live_enabled": False,
    }


@app.get("/api/system")
def system(db: Session = Depends(get_db)):
    s = get_settings()
    events = db.scalars(select(Event).order_by(Event.id.desc()).limit(50)).all()
    now = datetime.now(timezone.utc)

    def feed_status(provider):
        if s.demo_mode:
            return "FIXTURES"
        if provider == "oanda" and not s.oanda_api_key.get_secret_value():
            return "NOT_CONFIGURED"
        instruments = db.scalars(select(Instrument).where(Instrument.provider == provider)).all()
        fresh = []
        for instrument in instruments:
            quote = db.get(QuoteRow, instrument.symbol)
            fresh.append(
                bool(
                    quote
                    and quote.source == provider
                    and -2 <= (now - aware(quote.time)).total_seconds() <= s.max_quote_age_seconds
                )
            )
        return (
            "CONNECTED" if fresh and all(fresh) else "DEGRADED" if any(fresh) else "WAITING_FOR_FRESH_QUOTES"
        )

    return {
        "database": "CONNECTED",
        "oanda": feed_status("oanda"),
        "coinbase": feed_status("coinbase"),
        "llm": "CONFIGURED_NOT_VERIFIED"
        if (
            s.deepseek_api_key.get_secret_value()
            if s.llm_provider == "deepseek"
            else s.openai_api_key.get_secret_value()
        )
        else "NOT_CONFIGURED",
        "telegram": "CONFIGURED_NOT_VERIFIED"
        if s.telegram_bot_token.get_secret_value()
        else "NOT_CONFIGURED",
        "economic_calendar": "UNAVAILABLE",
        "events": [serialize(e) for e in events],
    }


@app.get("/api/paper-deployments")
def paper_deployments(db: Session = Depends(get_db)):
    active = set(db.scalars(select(PaperDeploymentSlot.deployment_id)).all())
    return [
        serialize(row) | {"current": row.id in active}
        for row in db.scalars(
            select(PaperDeployment).order_by(PaperDeployment.created_at.desc()).limit(100)
        ).all()
    ]


@app.get("/api/paper-runs")
def paper_runs(db: Session = Depends(get_db)):
    from app.execution.recorder import run_report

    return [
        run_report(db, row.id, datetime.now(timezone.utc))
        for row in db.scalars(select(PaperRun).order_by(PaperRun.started_at.desc()).limit(20)).all()
    ]


@app.get("/api/paper-runs/{run_id}/evaluation")
def paper_evaluation(run_id: str, db: Session = Depends(get_db)):
    from app.execution.trials import trial_report

    if db.get(PaperRun, run_id) is None:
        raise HTTPException(404, "Unknown paper run")
    return trial_report(db, run_id, datetime.now(timezone.utc))


@app.get("/api/paper-runs/{run_id}/samples")
def paper_samples(run_id: str, db: Session = Depends(get_db)):
    if db.get(PaperRun, run_id) is None:
        raise HTTPException(404, "Unknown paper run")
    return [
        serialize(row)
        for row in db.scalars(
            select(PaperSample)
            .where(PaperSample.run_id == run_id)
            .order_by(PaperSample.time.desc())
            .limit(100)
        ).all()
    ]


@app.post("/api/admin/suspend", dependencies=[Depends(admin)])
def suspend(db: Session = Depends(get_db)):
    account = db.scalars(select(Account).where(Account.id == "PAPER").with_for_update()).one()
    account.suspended = True
    db.add(Event(kind="operator_suspend", detail={"mode": "PAPER"}))
    db.commit()
    return {"suspended": True, "message": "New entries suspended; position monitoring continues"}
