from sqlalchemy.orm import Session
from app.models.event import Event, EventStatus, Sentiment, ConfidenceLevel
from app.models.event_classification import EventClassification, EventCategory
from app.services.pipeline.stages import (
    run_ner_stage, run_entity_linking_stage, run_classification_stage,
    run_geocoding_stage, run_sentiment_stage,
)
from app.services.pipeline.schemas import NERResult
from app.services.pipeline.stages import run_confidence_calibration_stage


def process_event_pipeline(db: Session, event: Event):
    """
    Each stage is independent: a failure in one doesn't undo successes in
    another. The event's final status reflects how many stages actually
    succeeded, not an all-or-nothing outcome.
    """
    event.status = EventStatus.processing
    db.commit()

    stage_failures = []
    linked_entities = []

    try:
        ner_result = run_ner_stage(db, event)
        linked_entities = run_entity_linking_stage(db, event, ner_result)
    except Exception:
        stage_failures.append("ner_or_linking")
        ner_result = NERResult(entities=[])

    if linked_entities:
        run_confidence_calibration_stage(db, event, linked_entities, ner_result)

    try:
        classification = run_classification_stage(db, event)
        db.add(EventClassification(
            event_id=event.id,
            category=EventCategory(classification.category),
            confidence=ConfidenceLevel(classification.confidence),
        ))
        db.commit()
    except Exception:
        stage_failures.append("classification")

    if linked_entities:
        run_geocoding_stage(db, event, linked_entities)  
    try:
        sentiment = run_sentiment_stage(db, event)
        event.sentiment = Sentiment(sentiment.tone)
        event.sentiment_confidence = ConfidenceLevel(sentiment.confidence)
        db.commit()
    except Exception:
        stage_failures.append("sentiment")

    if not stage_failures:
        event.status = EventStatus.processed
    elif len(stage_failures) < 3:
        event.status = EventStatus.processed  
    else:
        event.status = EventStatus.failed

    db.commit()
    return {"event_id": event.id, "failed_stages": stage_failures}