from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.incident import Incident
from app.models.event import Event
from app.models.analyst import Analyst
from app.schemas.incident import IncidentCreate, IncidentOut
from app.services.manual_entry_nlp import process_incident_entities

router = APIRouter(prefix="/incidents", tags=["incidents"])

@router.post("/", response_model=IncidentOut)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: Analyst = Depends(get_current_user),
):
    if payload.event_id is not None:
        event = db.query(Event).filter(Event.id == payload.event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Referenced event not found")

    incident = Incident(
        analyst_id=current_user.id,
        event_id=payload.event_id,
        incident_date=payload.incident_date,
        location=payload.location,
        type=payload.type,
        description=payload.description,
        reliability_rating=payload.reliability_rating,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    process_incident_entities(db, incident)
    return incident


@router.get("/", response_model=List[IncidentOut])
def list_incidents(
    location: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    min_reliability: Optional[int] = Query(None, ge=1, le=5),
    db: Session = Depends(get_db),
    current_user: Analyst = Depends(get_current_user),
):
    query = db.query(Incident)
    if location:
        query = query.filter(Incident.location.ilike(f"%{location}%"))
    if type:
        query = query.filter(Incident.type == type)
    if min_reliability:
        query = query.filter(Incident.reliability_rating >= min_reliability)
    return query.order_by(Incident.incident_date.desc()).all()