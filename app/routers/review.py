from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.analyst import Analyst
from app.models.event import Event
from app.models.event_entity import EventEntity
from app.models.event_classification import EventClassification, EventCategory
from app.models.extraction_correction import ExtractionCorrection

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue")
def get_review_queue(db: Session = Depends(get_db), current_user: Analyst = Depends(get_current_user)):
    """Events with any pending extraction awaiting review."""
    pending_entities = db.query(EventEntity).filter(EventEntity.review_status == "pending").all()
    pending_classifications = db.query(EventClassification).filter(
        EventClassification.review_status == "pending"
    ).all()

    return {
        "pending_entity_links": [
            {"id": e.id, "event_id": e.event_id, "entity_name": e.entity.name,
             "entity_type": e.entity.type.value, "confidence": e.confidence}
            for e in pending_entities
        ],
        "pending_classifications": [
            {"id": c.id, "event_id": c.event_id, "category": c.category.value, "confidence": c.confidence.value}
            for c in pending_classifications
        ],
    }


class EntityReviewAction(BaseModel):
    action: str  
    corrected_entity_type: Optional[str] = None


@router.post("/entity-link/{link_id}")
def review_entity_link(
    link_id: int, payload: EntityReviewAction,
    db: Session = Depends(get_db), current_user: Analyst = Depends(get_current_user),
):
    link = db.query(EventEntity).filter(EventEntity.id == link_id).first()
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
        event_id=link.event_id, analyst_id=current_user.id, extraction_type="entity",
        original_value=json.dumps(original),
        corrected_value=json.dumps({"entity_type": payload.corrected_entity_type}) if payload.action == "correct" else None,
        action=payload.action,
    ))

    db.commit()
    return {"status": "reviewed", "link_id": link.id, "action": payload.action}


class ClassificationReviewAction(BaseModel):
    action: str  # accept / reject / correct
    corrected_category: Optional[str] = None


@router.post("/classification/{classification_id}")
def review_classification(
    classification_id: int, payload: ClassificationReviewAction,
    db: Session = Depends(get_db), current_user: Analyst = Depends(get_current_user),
):
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
        event_id=cls.event_id, analyst_id=current_user.id, extraction_type="classification",
        original_value=json.dumps({"category": original_category}),
        corrected_value=json.dumps({"category": payload.corrected_category}) if payload.action == "correct" else None,
        action=payload.action,
    ))

    db.commit()
    return {"status": "reviewed", "classification_id": cls.id, "action": payload.action}