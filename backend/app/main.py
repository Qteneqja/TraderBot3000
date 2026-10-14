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
    Event,
    Instrument,
    ModelPrediction,
    ModelReview,
    ModelVersion,
    OrderRow,
    QuoteRow,
    SignalRow,
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
        if revision != "0004" or db.get(Account, "PAPER") is None:
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
        "model_status": "NO_EXECUTION_VALIDATED_MODEL",
        "news_status": "UNAVAILABLE",
        "server_time": now.isoformat(),
    }


@app.get("/api/instruments")
def instruments(db: Session = Depends(get_db)):
    return [serialize(i) for i in db.scalars(select(Instrument)).all()]


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
def models(db: Session = Depends(get_db)):
    return [
        serialize(m) for m in db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc())).all()
    ]


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
    return {
        "database": "CONNECTED",
        "oanda": "CONFIGURED_NOT_VERIFIED" if s.oanda_api_key.get_secret_value() else "NOT_CONFIGURED",
        "coinbase": "FIXTURES" if s.demo_mode else "SEE_FEED_HEARTBEAT",
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


@app.post("/api/admin/suspend", dependencies=[Depends(admin)])
def suspend(db: Session = Depends(get_db)):
    account = db.scalars(select(Account).where(Account.id == "PAPER").with_for_update()).one()
    account.suspended = True
    db.add(Event(kind="operator_suspend", detail={"mode": "PAPER"}))
    db.commit()
    return {"suspended": True, "message": "New entries suspended; position monitoring continues"}
