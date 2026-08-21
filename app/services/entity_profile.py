from sqlalchemy.orm import Session
from datetime import datetime, timezone
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
    """
    Full cross-source timeline for one entity — ingested events, manually
    logged incidents, and free-text sitreps, merged into one chronological
    list. This is the literal fulfillment of the entity-memory requirement:
    an entity mentioned in an RSS article and again in a field incident
    report shows up together here, ordered by date, regardless of source.
    """
    from app.models.incident_entity import IncidentEntity
    from app.models.incident import Incident
    from app.models.sitrep_entity import SitrepEntity
    from app.models.sitrep import Sitrep

    timeline = []

    # --- Ingested events ---
    event_rows = db.query(Event, EventEntity).join(
        EventEntity, EventEntity.event_id == Event.id
    ).filter(EventEntity.entity_id == entity_id).all()

    for e, ee in event_rows:
        timeline.append({
            "source_type": "event",
            "id": e.id,
            "title": e.title,
            "date": e.published_at,
            "relevance_score": ee.relevance_score,
            "confidence": ee.confidence,
            "status": e.status.value,
        })

    # --- Manually logged incidents ---
    incident_rows = db.query(Incident, IncidentEntity).join(
        IncidentEntity, IncidentEntity.incident_id == Incident.id
    ).filter(IncidentEntity.entity_id == entity_id).all()

    for i, ie in incident_rows:
        timeline.append({
            "source_type": "incident",
            "id": i.id,
            "title": f"{i.type.value}: {i.location}",
            "date": i.incident_date,
            "relevance_score": None,
            "confidence": ie.confidence,
            "reliability_rating": i.reliability_rating,
        })

    # --- Free-text sitreps ---
    sitrep_rows = db.query(Sitrep, SitrepEntity).join(
        SitrepEntity, SitrepEntity.sitrep_id == Sitrep.id
    ).filter(SitrepEntity.entity_id == entity_id).all()

    for s, se in sitrep_rows:
        timeline.append({
            "source_type": "sitrep",
            "id": s.id,
            "title": s.content[:100],
            "date": s.created_at,
            "relevance_score": None,
            "confidence": se.confidence,
        })

    timeline.sort(key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc))
    return timeline


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