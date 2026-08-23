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
from app.services.entity_resolver import resolve_entity
from app.services.pipeline.orchestrator import process_event_pipeline

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


def upsert_entity(db: Session, name: str, entity_type: str) -> Entity:
    entity = resolve_entity(db, name, entity_type)

    if entity_type == "location" and entity.latitude is None:
        geo = geocode_place(name)
        if geo:
            entity.latitude = geo["lat"]
            entity.longitude = geo["lon"]
            entity.geocode_confidence = geo["confidence"]
    return entity

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


def process_raw_events(db, limit=20):
    events = db.query(Event).filter(Event.status == EventStatus.raw).limit(limit).all()
    for event in events:
        process_event_pipeline(db, event)
    return len(events)