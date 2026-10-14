import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.tables import Event
from app.schemas.domain import aware


def check(kind, max_age):
    with SessionLocal() as db:
        event = db.scalars(select(Event).where(Event.kind == kind).order_by(Event.id.desc()).limit(1)).first()
        return bool(
            event and 0 <= (datetime.now(timezone.utc) - aware(event.time)).total_seconds() <= max_age
        )


if __name__ == "__main__":
    market = len(sys.argv) > 1 and sys.argv[1] == "market"
    healthy = check(
        "market_worker_heartbeat" if market else "trading_worker_heartbeat", 180 if market else 45
    )
    sys.exit(0 if healthy else 1)
