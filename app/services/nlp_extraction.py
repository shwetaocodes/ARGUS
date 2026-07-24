import json
import ollama
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.models.event import Event, EventStatus
from app.models.entity import Entity, EntityType
from app.models.event_entity import EventEntity

ollama_client = ollama.Client(host=settings.OLLAMA_HOST)

VALID_TYPES = {e.value for e in EntityType}

EXTRACTION_PROMPT = """Extract named entities from the following text. Return ONLY valid JSON.

Format:
{{"entities": [{{"name": "string", "type": "person|org|location|topic", "relevance": 0.0-1.0}}]}}

If no entities are found, return {{"entities": []}}.

Text:
{text}
"""

def extract_entities_from_text(text: str) -> list[dict]:
    prompt = EXTRACTION_PROMPT.format(text=text[:8000])

    response = ollama_client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )

    raw = response["message"]["content"]
    parsed = json.loads(raw)  
    entities = parsed.get("entities", [])

    valid_entities = [e for e in entities if e.get("type") in VALID_TYPES and e.get("name")]
    return valid_entities


def upsert_entity(db: Session, name: str, entity_type: str) -> Entity:
    existing = db.query(Entity).filter(
        or_(
            Entity.name.ilike(name),
            Entity.aliases.any(name),
        )
    ).first()

    if existing:
        return existing

    entity = Entity(name=name, type=EntityType(entity_type), aliases=[])
    db.add(entity)
    db.flush()
    return entity


def process_event(db: Session, event: Event):
    event.status = EventStatus.processing
    db.commit()

    try:
        extracted = extract_entities_from_text(event.raw_text)

        for item in extracted:
            entity = upsert_entity(db, item["name"], item["type"])

            link_exists = db.query(EventEntity).filter(
                EventEntity.event_id == event.id,
                EventEntity.entity_id == entity.id,
            ).first()

            if not link_exists:
                link = EventEntity(
                    event_id=event.id,
                    entity_id=entity.id,
                    relevance_score=item.get("relevance"),
                )
                db.add(link)

        event.status = EventStatus.processed
        db.commit()

    except Exception as e:
        db.rollback()
        event.status = EventStatus.failed
        db.commit()
        print(f"[NLP] Event {event.id} failed: {e}")


def process_raw_events(db: Session, limit: int = 20):
    events = db.query(Event).filter(Event.status == EventStatus.raw).limit(limit).all()
    processed_count = 0

    for event in events:
        process_event(db, event)
        processed_count += 1

    return processed_count