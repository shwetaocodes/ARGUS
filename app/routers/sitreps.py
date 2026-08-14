from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.sitrep import Sitrep
from app.models.event import Event
from app.models.analyst import Analyst
from app.schemas.sitrep import SitrepCreate, SitrepOut

router = APIRouter(prefix="/sitreps", tags=["sitreps"])

@router.post("/", response_model=SitrepOut)
def create_sitrep(
    payload: SitrepCreate,
    db: Session = Depends(get_db),
    current_user: Analyst = Depends(get_current_user),
):
    if payload.event_id is not None:
        event = db.query(Event).filter(Event.id == payload.event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Referenced event not found")

    sitrep = Sitrep(
        analyst_id=current_user.id,
        event_id=payload.event_id,
        content=payload.content,
    )
    db.add(sitrep)
    db.commit()
    db.refresh(sitrep)
    return sitrep


@router.get("/", response_model=List[SitrepOut])
def list_sitreps(
    event_id: Optional[int] = Query(None),
    analyst_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Analyst = Depends(get_current_user),
):
    query = db.query(Sitrep)
    if event_id is not None:
        query = query.filter(Sitrep.event_id == event_id)
    if analyst_id is not None:
        query = query.filter(Sitrep.analyst_id == analyst_id)
    return query.order_by(Sitrep.created_at.desc()).all()