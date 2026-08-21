import json
import ollama
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import Event, Sentiment, ConfidenceLevel
from app.models.event_classification import EventClassification, EventCategory
from app.models.pipeline_stage_log import PipelineStageLog, StageStatus
from app.services.entity_resolver import resolve_entity
from app.services.geocoder import geocode_place
from app.services.pipeline.retry import retry_stage
from app.services.pipeline.schemas import NERResult, ClassificationResult, SentimentResult
from app.services.confidence_calibrator import (
    compute_weighted_confidence, get_source_reliability,
    get_embedding_similarity_score, get_cross_source_agreement,
)
from app.models.confidence_score import ConfidenceScore


ollama_client = ollama.Client(host=settings.OLLAMA_HOST)


def _log_stage(db, event_id, stage, status, error=None):
    db.add(PipelineStageLog(event_id=event_id, stage=stage, status=status, error_message=error))
    db.commit()


# --- Stage 1: NER ---
NER_PROMPT = """Extract named entities from this text (may be in English, Urdu, or Chinese). Return original script, do not translate. Return ONLY valid JSON.
Format: {{"entities": [{{"name": "string", "type": "person|org|location|military_unit|weapon|topic", "confidence": "high|medium|low"}}]}}
Text: {text}"""

@retry_stage(max_attempts=3)
def run_ner_stage(db: Session, event: Event) -> NERResult:
    try:
        response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": NER_PROMPT.format(text=event.raw_text[:8000])}],
            format="json",
        )
        raw = json.loads(response["message"]["content"])
        result = NERResult(**raw)  
        _log_stage(db, event.id, "ner", StageStatus.success)
        return result
    except (json.JSONDecodeError, ValidationError, KeyError) as e:
        _log_stage(db, event.id, "ner", StageStatus.failed, str(e))
        raise


# --- Stage 2: Entity Linking ---
def run_entity_linking_stage(db: Session, event: Event, ner_result: NERResult) -> list:
    """No retry decorator here — this is deterministic DB work, not an LLM call.
    A failure here is a real bug, not a transient flake worth retrying blindly."""
    from app.models.event_entity import EventEntity
    linked_entities = []
    try:
        for item in ner_result.entities:
            entity = resolve_entity(db, item.name, item.type)
            linked_entities.append(entity)

            exists = db.query(EventEntity).filter(
                EventEntity.event_id == event.id, EventEntity.entity_id == entity.id
            ).first()
            if not exists:
                db.add(EventEntity(event_id=event.id, entity_id=entity.id, confidence=item.confidence))
        db.commit()
        _log_stage(db, event.id, "entity_linking", StageStatus.success)
        return linked_entities
    except Exception as e:
        db.rollback()
        _log_stage(db, event.id, "entity_linking", StageStatus.failed, str(e))
        raise


# --- Stage 3: Classification ---
CLASSIFY_PROMPT = """Classify this text into exactly one category. Return ONLY valid JSON.
Categories: infiltration_attempt, ied, protest, troop_movement, propaganda_broadcast, ceasefire_violation, supply_convoy, aerial_activity, other
Format: {{"category": "...", "confidence": "high|medium|low"}}
Text: {text}"""

@retry_stage(max_attempts=3)
def run_classification_stage(db: Session, event: Event) -> ClassificationResult:
    try:
        response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(text=event.raw_text[:4000])}],
            format="json",
        )
        raw = json.loads(response["message"]["content"])
        result = ClassificationResult(**raw)
        _log_stage(db, event.id, "classification", StageStatus.success)
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        _log_stage(db, event.id, "classification", StageStatus.failed, str(e))
        raise


# --- Stage 4: Geocoding  ---
def run_geocoding_stage(db: Session, event: Event, linked_entities: list):
    try:
        for entity in linked_entities:
            if entity.type.value == "location" and entity.latitude is None:
                geo = geocode_place(entity.name, context=event.raw_text)
                if geo:
                    entity.latitude = geo["lat"]
                    entity.longitude = geo["lon"]
                    entity.geocode_confidence = geo["confidence"]
        db.commit()
        _log_stage(db, event.id, "geocoding", StageStatus.success)
    except Exception as e:
        db.rollback()
        _log_stage(db, event.id, "geocoding", StageStatus.failed, str(e))
        

# --- Stage 5: Sentiment ---
SENTIMENT_PROMPT = """Determine the overall tone of this text. Return ONLY valid JSON.
Tone options: hostile, neutral, de_escalatory
Format: {{"tone": "...", "confidence": "high|medium|low"}}
Text: {text}"""

@retry_stage(max_attempts=3)
def run_sentiment_stage(db: Session, event: Event) -> SentimentResult:
    try:
        response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": SENTIMENT_PROMPT.format(text=event.raw_text[:4000])}],
            format="json",
        )
        raw = json.loads(response["message"]["content"])
        result = SentimentResult(**raw)
        _log_stage(db, event.id, "sentiment", StageStatus.success)
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        _log_stage(db, event.id, "sentiment", StageStatus.failed, str(e))
        raise

def run_confidence_calibration_stage(db: Session, event: Event, linked_entities: list, ner_result):
    """
    Runs after entity linking. Overwrites each EventEntity's stored
    'confidence' field with the calibrated weighted score — the LLM's
    self-reported 'high' no longer survives unexamined into the database.
    """
    from app.models.event_entity import EventEntity

    source_reliability = get_source_reliability(db, event.source_id)

    for entity, extracted in zip(linked_entities, ner_result.entities):
        link = db.query(EventEntity).filter(
            EventEntity.event_id == event.id, EventEntity.entity_id == entity.id
        ).first()
        if not link:
            continue

        cross_source = get_cross_source_agreement(db, entity.id, event.id)
        embedding_sim = getattr(entity, "_last_resolution_score", None)  

        result = compute_weighted_confidence(
            ner_confidence=extracted.confidence,
            embedding_similarity=embedding_sim,
            source_reliability=source_reliability,
            cross_source_agreement=cross_source,
            llm_confidence=extracted.confidence,  
        )

        link.confidence = result["confidence_level"]  
        db.add(ConfidenceScore(
            event_entity_id=link.id,
            ner_confidence=result["components"]["ner_confidence"],
            embedding_similarity=result["components"]["embedding_similarity"],
            source_reliability=result["components"]["source_reliability"],
            cross_source_agreement=result["components"]["cross_source_agreement"],
            llm_confidence=result["components"]["llm_confidence"],
            weighted_score=result["weighted_score"],
        ))

    db.commit()
    _log_stage(db, event.id, "confidence_calibration", StageStatus.success)