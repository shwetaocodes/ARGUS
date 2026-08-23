import feedparser
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.source import Source, SourceType
from app.models.event import Event, EventStatus
from app.services.dedupe import make_dedupe_hash
from app.core.kafka_config import get_producer, TOPIC_RAW_EVENTS


def fetch_rss_feed(db: Session, source: Source) -> int:
    """Fetch one RSS source, insert new raw events. Returns count inserted."""
    producer = get_producer()
    parsed = feedparser.parse(source.identifier)
    inserted = 0

    for entry in parsed.entries:
        link = entry.get("link", "")
        if not link:
            continue

        dedupe_hash = make_dedupe_hash(source.id, link)

        exists = db.query(Event).filter(Event.dedupe_hash == dedupe_hash).first()
        if exists:
            continue

        published = entry.get("published_parsed")
        published_at = (
            datetime(*published[:6], tzinfo=timezone.utc) if published else None
        )

        event = Event(
            title=entry.get("title", "")[:500],
            summary=entry.get("summary", ""),
            source_id=source.id,
            published_at=published_at,
            raw_text=entry.get("summary", "") or entry.get("title", ""),
            status=EventStatus.raw,
            dedupe_hash=dedupe_hash,
        )
        db.add(event)
        db.flush()

        producer.send(TOPIC_RAW_EVENTS, {"event_id": event.id})
        inserted += 1

    db.commit()
    producer.flush()
    return inserted


def poll_all_news_sources(db: Session):
    sources = db.query(Source).filter(
        Source.type == SourceType.news, Source.is_active == True
    ).all()

    total = 0
    for source in sources:
        try:
            count = fetch_rss_feed(db, source)
            total += count
            print(f"[RSS] {source.name}: {count} new events")
        except Exception as e:
            print(f"[RSS] {source.name} failed: {e}")

    return total