"""Optional commentary worker, completely separate from market and trading loops."""

import asyncio

import httpx

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.llm.pipeline import enqueue_events, process_one
from app.models.tables import Event


async def narrative_worker():
    settings = get_settings()
    async with httpx.AsyncClient(follow_redirects=False) as client:
        while True:
            try:
                with SessionLocal() as db:
                    enqueue_events(db, settings)
                    await process_one(db, settings, client)
                    db.add(Event(kind='llm_worker_heartbeat', detail={'enabled': settings.enable_llm_narratives,
                                                                  'execution_authority': False}))
                    db.commit()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                with SessionLocal() as db:
                    db.add(Event(kind='llm_worker_error', detail={'error_type': type(error).__name__}))
                    db.commit()
            await asyncio.sleep(15)


if __name__ == '__main__':
    asyncio.run(narrative_worker())
