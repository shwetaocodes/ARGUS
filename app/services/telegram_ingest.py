from telethon.sync import TelegramClient
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.source import Source, SourceType
from app.models.event import Event, EventStatus
from app.services.dedupe import make_dedupe_hash

def get_telegram_client() -> TelegramClient:
    return TelegramClient(
        settings.TELEGRAM_SESSION_NAME,
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH,
    )

def fetch_telegram_channel(db: Session, source: Source, limit: int = 50) -> int:
    inserted = 0
    with get_telegram_client() as client:
        messages = client.get_messages(source.identifier, limit=limit)
        for msg in messages:
            if not msg.text:
                continue

            dedupe_hash = make_dedupe_hash(source.id, str(msg.id))
            exists = db.query(Event).filter(Event.dedupe_hash == dedupe_hash).first()
            if exists:
                continue

            event = Event(
                title=msg.text[:100],
                summary=msg.text[:500],
                source_id=source.id,
                published_at=msg.date.astimezone(timezone.utc) if msg.date else None,
                raw_text=msg.text,
                status=EventStatus.raw,
                dedupe_hash=dedupe_hash,
            )
            db.add(event)
            inserted += 1

    db.commit()
    return inserted


def poll_all_telegram_sources(db: Session):
    sources = db.query(Source).filter(
        Source.type == SourceType.telegram, Source.is_active == True
    ).all()

    total = 0
    for source in sources:
        try:
            count = fetch_telegram_channel(db, source)
            total += count
            print(f"[Telegram] {source.name}: {count} new events")
        except Exception as e:
            print(f"[Telegram] {source.name} failed: {e}")

    return total