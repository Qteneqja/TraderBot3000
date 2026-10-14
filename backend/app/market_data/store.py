from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.market_data.quality import inspect_candles
from app.models.tables import CandleRow, IngestionJob, QuoteRow
from app.schemas.domain import Candle, Quote, aware


def insert_candles(db: Session, candles: list[Candle], now: datetime):
    report = inspect_candles(candles, now)
    if not report["valid"]:
        raise ValueError(f"Invalid candle batch: {report['issues']}")
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    for candle in candles:
        db.execute(
            insert(CandleRow)
            .values(**candle.model_dump())
            .on_conflict_do_nothing(index_elements=["symbol", "timeframe", "time", "source"])
        )
    db.flush()
    return report


def save_quote(db: Session, quote: Quote, now: datetime):
    age = (now - quote.time).total_seconds()
    if age < -2 or age > 60:
        return False
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(QuoteRow).values(**quote.model_dump())
    db.execute(
        statement.on_conflict_do_update(
            index_elements=["symbol"],
            set_=quote.model_dump(exclude={"symbol"}),
            where=QuoteRow.time < quote.time,
        )
    )
    db.commit()
    return True


def load_candles(db: Session, symbol: str, timeframe: int, source: str, limit=500, *, start=None, end=None):
    if (start is None) != (end is None):
        raise ValueError("Provide both dataset start and end")
    if start is not None and (start.tzinfo is None or end.tzinfo is None or start >= end):
        raise ValueError("Dataset boundaries must be timezone-aware and increasing")
    query = select(CandleRow).where(
        CandleRow.symbol == symbol, CandleRow.timeframe == timeframe, CandleRow.source == source
    )
    if start is not None:
        query = query.where(CandleRow.time >= start, CandleRow.time < end)
    rows = db.scalars(
        query.order_by(CandleRow.time.desc()).limit(limit)
    ).all()
    return [
        Candle(
            symbol=r.symbol,
            timeframe=r.timeframe,
            time=aware(r.time),
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            volume=r.volume,
            complete=r.complete,
            source=r.source,
            provenance=r.provenance,
        )
        for r in reversed(rows)
    ]


async def ingest(
    db: Session,
    provider,
    symbol: str,
    timeframe: int,
    start: datetime,
    end: datetime,
    job_id: str | None = None,
):
    job = db.get(IngestionJob, job_id) if job_id else None
    if job and (job.symbol != symbol or job.timeframe != timeframe):
        raise ValueError("Resume parameters do not match job")
    if job is None:
        job = IngestionJob(symbol=symbol, timeframe=timeframe)
        db.add(job)
        db.commit()
    cursor = aware(job.cursor) if job.cursor else start
    job.status = "RUNNING"
    db.commit()
    try:
        async for batch, next_cursor in provider.candles(symbol, timeframe, cursor, end):
            report = insert_candles(db, batch, datetime.now(timezone.utc))
            job.cursor, job.report = next_cursor, report
            db.commit()  # Data and resume cursor are atomic.
        job.status = "COMPLETE"
        db.commit()
    except Exception as exc:
        db.rollback()
        job.status, job.report = "FAILED", {"error_type": type(exc).__name__}
        db.commit()
        raise
    return job.id
