from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.event_entity import EventEntity
from app.models.incident_entity import IncidentEntity
from app.models.sitrep_entity import SitrepEntity
from app.models.event_classification import EventClassification, EventCategory
from app.models.extraction_correction import ExtractionCorrection
from app.models.source import Source

router = APIRouter(prefix="/review", tags=["review"])

LINK_TABLES = {
    "event": (EventEntity, "event_id"),
    "incident": (IncidentEntity, "incident_id"),
    "sitrep": (SitrepEntity, "sitrep_id"),
}


@router.get("/queue")
def get_review_queue(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Pending items across ALL entity sources — event, incident, and sitrep —
    plus event classifications. This is the fix: previously only event-sourced
    entities appeared here at all."""
    result = {"pending_entity_links": [], "pending_classifications": []}

    for kind, (model, _) in LINK_TABLES.items():
        rows = db.query(model).filter(model.review_status == "pending").all()
        for link in rows:
            result["pending_entity_links"].append({
                "id": link.id, "kind": kind,
                "entity_name": link.entity.name, "entity_type": link.entity.type.value,
                "confidence": link.confidence,
            })

    classifications = db.query(EventClassification).filter(EventClassification.review_status == "pending").all()
    for c in classifications:
        result["pending_classifications"].append({
            "id": c.id, "event_id": c.event_id, "category": c.category.value, "confidence": c.confidence.value,
        })

    return result


class EntityLinkReviewAction(BaseModel):
    kind: str  
    action: str  
    corrected_entity_type: Optional[str] = None


@router.post("/entity-link/{link_id}")
def review_entity_link(
    link_id: int, payload: EntityLinkReviewAction,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    """
    Now takes a `kind` in the body to disambiguate which table link_id refers
    to — link IDs are only unique WITHIN each table, not across all three,
    so this can't be inferred from the ID alone.
    """
    if payload.kind not in LINK_TABLES:
        raise HTTPException(status_code=400, detail=f"kind must be one of {list(LINK_TABLES.keys())}")

    model, source_fk = LINK_TABLES[payload.kind]
    link = db.query(model).filter(model.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Entity link not found")

    original = {"entity_name": link.entity.name, "entity_type": link.entity.type.value, "confidence": link.confidence}

    if payload.action == "accept":
        link.review_status = "accepted"
    elif payload.action == "reject":
        link.review_status = "rejected"
    elif payload.action == "correct":
        link.review_status = "corrected"
        if payload.corrected_entity_type:
            link.entity.type = payload.corrected_entity_type
    else:
        raise HTTPException(status_code=400, detail="action must be accept, reject, or correct")

    link.reviewed_by_id = current_user.id
    link.reviewed_at = datetime.now(timezone.utc)

    db.add(ExtractionCorrection(
        event_id=getattr(link, "event_id", None),  
        source_table=payload.kind,
        source_record_id=getattr(link, source_fk),
        analyst_id=current_user.id, extraction_type="entity",
        original_value=json.dumps(original),
        corrected_value=json.dumps({"entity_type": payload.corrected_entity_type}) if payload.action == "correct" else None,
        action=payload.action,
    ))

    #--- Source reliability feedback loop ---
    source = None
    if payload.kind == "event":
        source = db.query(Source).filter(Source.id == link.event.source_id).first()
    
    if source:
        source.total_reviewed_extractions += 1
        if payload.action == "accept":
            source.correct_extractions += 1

    db.commit()
    return {"status": "reviewed", "kind": payload.kind, "link_id": link.id, "action": payload.action}


class ClassificationReviewAction(BaseModel):
    action: str
    corrected_category: Optional[str] = None

@router.post("/classification/{classification_id}")
def review_classification(
    classification_id: int, payload: ClassificationReviewAction,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    """Unchanged — classification only ever applies to ingested events;
    incidents already carry an analyst-assigned type, sitreps have none."""
    cls = db.query(EventClassification).filter(EventClassification.id == classification_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Classification not found")

    original_category = cls.category.value

    if payload.action == "accept":
        cls.review_status = "accepted"
    elif payload.action == "reject":
        cls.review_status = "rejected"
    elif payload.action == "correct":
        if not payload.corrected_category or payload.corrected_category not in [c.value for c in EventCategory]:
            raise HTTPException(status_code=400, detail="Valid corrected_category required")
        cls.original_category = cls.category
        cls.category = EventCategory(payload.corrected_category)
        cls.review_status = "corrected"
    else:
        raise HTTPException(status_code=400, detail="action must be accept, reject, or correct")

    cls.reviewed_by_id = current_user.id
    cls.reviewed_at = datetime.now(timezone.utc)

    db.add(ExtractionCorrection(
        event_id=cls.event_id, source_table="event", source_record_id=cls.event_id,
        analyst_id=current_user.id, extraction_type="classification",
        original_value=json.dumps({"category": original_category}),
        corrected_value=json.dumps({"category": payload.corrected_category}) if payload.action == "correct" else None,
        action=payload.action,
    ))
    db.commit()
    return {"status": "reviewed", "classification_id": cls.id, "action": payload.action}