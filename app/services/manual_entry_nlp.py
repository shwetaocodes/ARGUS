"""
Runs entity extraction on manually-entered incidents and sitreps — closes
the gap where field-analyst reports never entered the entity graph, unlike
ingested events. Deliberately narrower than the full event pipeline: no
classification (analyst already set Incident.type), no sentiment.
"""
import json
import ollama
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.entity_resolver import resolve_entity
from app.services.geocoder import geocode_place
from app.services.pipeline.schemas import NERResult
from app.services.pipeline.retry import retry_stage

ollama_client = ollama.Client(host=settings.OLLAMA_HOST)

NER_PROMPT = """Extract named entities from this field report text. Return original script, do not translate. Return ONLY valid JSON.
Format: {{"entities": [{{"name": "string", "type": "person|org|location|military_unit|weapon|topic", "confidence": "high|medium|low"}}]}}
Text: {text}"""


@retry_stage(max_attempts=3)
def _extract_entities(text: str) -> NERResult:
    response = ollama_client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[{"role": "user", "content": NER_PROMPT.format(text=text[:8000])}],
        format="json",
    )
    raw = json.loads(response["message"]["content"])
    return NERResult(**raw)  


def process_incident_entities(db: Session, incident):
    from app.models.incident_entity import IncidentEntity
    from app.models.entity import EntityType

    try:
        result = _extract_entities(incident.description)
    except (json.JSONDecodeError, ValidationError, Exception) as e:
        print(f"[manual_entry_nlp] incident {incident.id} extraction failed: {e}")
        return

    for item in result.entities:
        entity = resolve_entity(db, item.name, item.type)

        if entity.type == EntityType.location and entity.latitude is None:
            geo = geocode_place(item.name, context=incident.description)
            if geo:
                entity.latitude, entity.longitude, entity.geocode_confidence = geo["lat"], geo["lon"], geo["confidence"]

        exists = db.query(IncidentEntity).filter(
            IncidentEntity.incident_id == incident.id, IncidentEntity.entity_id == entity.id
        ).first()
        if not exists:
            db.add(IncidentEntity(incident_id=incident.id, entity_id=entity.id, confidence=item.confidence))

    db.commit()


def process_sitrep_entities(db: Session, sitrep):
    from app.models.sitrep_entity import SitrepEntity
    from app.models.entity import EntityType

    try:
        result = _extract_entities(sitrep.content)
    except (json.JSONDecodeError, ValidationError, Exception) as e:
        print(f"[manual_entry_nlp] sitrep {sitrep.id} extraction failed: {e}")
        return

    for item in result.entities:
        entity = resolve_entity(db, item.name, item.type)

        if entity.type == EntityType.location and entity.latitude is None:
            geo = geocode_place(item.name, context=sitrep.content)
            if geo:
                entity.latitude, entity.longitude, entity.geocode_confidence = geo["lat"], geo["lon"], geo["confidence"]

        exists = db.query(SitrepEntity).filter(
            SitrepEntity.sitrep_id == sitrep.id, SitrepEntity.entity_id == entity.id
        ).first()
        if not exists:
            db.add(SitrepEntity(sitrep_id=sitrep.id, entity_id=entity.id, confidence=item.confidence))

    db.commit()