import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.tables import Notification


def enqueue(db: Session, event_id: str, text: str):
    if not db.get(Notification, event_id):
        db.add(Notification(id=event_id, text=text[:4096]))
        db.commit()


async def deliver(db: Session, settings: Settings, client: httpx.AsyncClient):
    token = settings.telegram_bot_token.get_secret_value()
    if not token or not settings.telegram_chat_id:
        return
    rows = db.scalars(
        select(Notification)
        .where(Notification.status == "PENDING")
        .limit(20)
        .with_for_update(skip_locked=True)
    ).all()
    for event in rows:
        event.status, event.attempts = "SENDING", event.attempts + 1
        db.commit()  # Ambiguous delivery is quarantined, never blindly retried.
        try:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": settings.telegram_chat_id, "text": event.text},
                timeout=10,
            )
            if response.status_code == 429:
                event.status = "PENDING" if event.attempts < 5 else "FAILED"
            elif response.is_success and response.json().get("ok"):
                event.status = "DELIVERED"
            else:
                event.status = "FAILED"
        except (httpx.HTTPError, ValueError):
            event.status = "UNKNOWN"
        db.commit()
