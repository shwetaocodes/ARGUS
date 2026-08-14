import json
import ollama
from sqlalchemy.orm import Session
from sqlalchemy import or_
from itertools import combinations

from app.core.config import settings
from app.models.event import Event, EventStatus, Sentiment, ConfidenceLevel
from app.models.entity import Entity, EntityType
from app.models.event_entity import EventEntity
from app.models.event_classification import EventClassification, EventCategory
from app.services.geocoding import geocode_place
from app.services.geocoder import geocode_place
from app.models.entity_relationship import EntityRelationship
from app.services.watch_service import check_entity_watches, check_location_watches

ollama_client = ollama.Client(host=settings.OLLAMA_HOST)

VALID_ENTITY_TYPES = {e.value for e in EntityType}
VALID_CATEGORIES = {c.value for c in EventCategory}
VALID_SENTIMENTS = {s.value for s in Sentiment}
VALID_CONFIDENCE = {c.value for c in ConfidenceLevel}

EXTRACTION_PROMPT = """Analyze the following text (may be in English, Urdu, or Chinese) and extract structured intelligence data. Return ONLY valid JSON, no markdown, no explanation.

Format:
{{
  "entities": [
    {{"name": "string (original script, do not translate)", "type": "person|org|location|military_unit|weapon|topic", "relevance": 0.0-1.0, "confidence": "high|medium|low"}}
  ],
  "classification": {{"category": "infiltration_attempt|ied|protest|troop_movement|propaganda_broadcast|ceasefire_violation|supply_convoy|aerial_activity|other", "confidence": "high|medium|low"}},
  "sentiment": {{"tone": "hostile|neutral|de_escalatory", "confidence": "high|medium|low"}},
  "date_mentioned": "YYYY-MM-DD or null if no specific date is mentioned in the text"
}}

Text:
{text}
"""

def extract_structured_data(text: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(text=text[:8000])
    response = ollama_client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )
    return json.loads(response["message"]["content"])


def upsert_entity(db: Session, name: str, entity_type: str, context: str = "") -> Entity:
    existing = db.query(Entity).filter(
        or_(Entity.name.ilike(name), Entity.aliases.any(name))
    ).first()
    if existing:
        return existing

    entity = Entity(name=name, type=EntityType(entity_type), aliases=[])

    if entity_type == "location":
        geo = geocode_place(name, context=context)
        if geo:
            entity.latitude = geo["lat"]
            entity.longitude = geo["lon"]
            entity.geocode_confidence = geo["confidence"]
        else:
            entity.geocode_confidence = "failed"

    db.add(entity)
    db.flush()
    return entity

def process_event(db: Session, event: Event):
    event.status = EventStatus.processing
    db.commit()

    try:
        data = extract_structured_data(event.raw_text)

        linked_entities = []

        # --- entities ---
        for item in data.get("entities", []):
            if item.get("type") not in VALID_ENTITY_TYPES or not item.get("name"):
                continue
            entity = upsert_entity(db, item["name"], item["type"])
            linked_entities.append(entity)

            link = db.query(EventEntity).filter(
                EventEntity.event_id == event.id, EventEntity.entity_id == entity.id
            ).first()
            if not link:
                db.add(EventEntity(
                    event_id=event.id,
                    entity_id=entity.id,
                    relevance_score=item.get("relevance"),
                    confidence=item.get("confidence") if item.get("confidence") in VALID_CONFIDENCE else None,
                ))

        # --- existing relationship graph update  ---
        entity_ids_for_relationships = [e.id for e in linked_entities]
        update_entity_relationships(db, entity_ids_for_relationships, event.published_at)

        # --- watch checks ---
        check_entity_watches(db, event, [e.id for e in linked_entities])
        location_entities = [e for e in linked_entities if e.type == EntityType.location]
        check_location_watches(db, event, location_entities)

        # --- classification ---
        classification = data.get("classification", {}) 
        if classification.get("category") in VALID_CATEGORIES:
            db.add(EventClassification(
                event_id=event.id,
                category=EventCategory(classification["category"]),
                confidence=ConfidenceLevel(classification.get("confidence", "low")),
            ))

        # --- sentiment ---
        sentiment = data.get("sentiment", {})
        if sentiment.get("tone") in VALID_SENTIMENTS:
            event.sentiment = Sentiment(sentiment["tone"])
            event.sentiment_confidence = ConfidenceLevel(sentiment.get("confidence", "low"))

        # --- date  ---
        date_str = data.get("date_mentioned")
        if date_str and date_str.lower() != "null":
            from datetime import datetime
            try:
                event.event_date_mentioned = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pass  

        event.status = EventStatus.processed
        db.commit()

    except Exception as e:
        db.rollback()
        event.status = EventStatus.failed
        db.commit()
        print(f"[NLP] Event {event.id} failed: {e}")

    def update_entity_relationships(db: Session, entity_ids: list[int], event_timestamp):
        """Called after all entities for one event are linked — updates co-occurrence for every pair."""
        unique_ids = sorted(set(entity_ids))
        for id_a, id_b in combinations(unique_ids, 2):
            rel = db.query(EntityRelationship).filter(
                EntityRelationship.entity_a_id == id_a,
                EntityRelationship.entity_b_id == id_b,
            ).first()

            if rel:
                rel.co_occurrence_count += 1
                if event_timestamp:
                    if not rel.first_co_occurred_at or event_timestamp < rel.first_co_occurred_at:
                        rel.first_co_occurred_at = event_timestamp
                    if not rel.last_co_occurred_at or event_timestamp > rel.last_co_occurred_at:
                        rel.last_co_occurred_at = event_timestamp
            else:
                db.add(EntityRelationship(
                    entity_a_id=id_a, entity_b_id=id_b, co_occurrence_count=1,
                    first_co_occurred_at=event_timestamp, last_co_occurred_at=event_timestamp,
                ))        


def process_raw_events(db: Session, limit: int = 20):
    events = db.query(Event).filter(Event.status == EventStatus.raw).limit(limit).all()
    for event in events:
        process_event(db, event)
    return len(events)

