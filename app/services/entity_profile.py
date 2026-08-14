from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.entity import Entity
from app.models.event_entity import EventEntity
from app.models.event import Event
from app.models.entity_relationship import EntityRelationship
from app.models.entity_annotation import EntityAnnotation


def get_entity_profile(db: Session, entity_id: int) -> dict:
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        return None

    stats = db.query(
        func.count(EventEntity.id).label("event_count"),
        func.min(Event.published_at).label("first_seen"),
        func.max(Event.published_at).label("last_seen"),
    ).join(Event, Event.id == EventEntity.event_id).filter(
        EventEntity.entity_id == entity_id
    ).first()

    return {
        "id": entity.id,
        "name": entity.name,
        "aliases": entity.aliases,
        "type": entity.type.value,
        "threat_level": entity.threat_level.value if entity.threat_level else None,
        "first_seen": stats.first_seen,
        "last_seen": stats.last_seen,
        "event_count": stats.event_count,
        "latitude": entity.latitude,
        "longitude": entity.longitude,
    }


def get_entity_timeline(db: Session, entity_id: int) -> list[dict]:
    """All events linked to this entity, across every source, chronologically."""
    rows = db.query(Event, EventEntity).join(
        EventEntity, EventEntity.event_id == Event.id
    ).filter(
        EventEntity.entity_id == entity_id
    ).order_by(Event.published_at.asc()).all()

    return [
        {
            "event_id": e.id,
            "title": e.title,
            "published_at": e.published_at,
            "source_id": e.source_id,
            "relevance_score": ee.relevance_score,
            "status": e.status.value,
        }
        for e, ee in rows
    ]


def get_entity_relationships(db: Session, entity_id: int) -> list[dict]:
    rels = db.query(EntityRelationship).filter(
        (EntityRelationship.entity_a_id == entity_id) | (EntityRelationship.entity_b_id == entity_id)
    ).order_by(EntityRelationship.co_occurrence_count.desc()).all()

    result = []
    for r in rels:
        other_id = r.entity_b_id if r.entity_a_id == entity_id else r.entity_a_id
        other = db.query(Entity).filter(Entity.id == other_id).first()
        result.append({
            "entity_id": other.id,
            "name": other.name,
            "type": other.type.value,
            "co_occurrence_count": r.co_occurrence_count,
            "first_co_occurred_at": r.first_co_occurred_at,
            "last_co_occurred_at": r.last_co_occurred_at,
        })
    return result