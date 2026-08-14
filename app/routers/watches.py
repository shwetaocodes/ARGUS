from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.watch import EntityWatch, LocationWatch, ThresholdAlert

router = APIRouter(prefix="/watches", tags=["watches"])

class EntityWatchCreate(BaseModel):
    entity_id: int

@router.post("/entity")
def create_entity_watch(payload: EntityWatchCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    watch = EntityWatch(analyst_id=current_user.id, entity_id=payload.entity_id)
    db.add(watch); db.commit(); db.refresh(watch)
    return {"id": watch.id, "entity_id": watch.entity_id}

@router.get("/entity")
def list_entity_watches(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(EntityWatch).filter(EntityWatch.analyst_id == current_user.id).all()
    return [{"id": w.id, "entity_id": w.entity_id, "entity_name": w.entity.name} for w in rows]


class LocationWatchCreate(BaseModel):
    name: str
    sector_id: Optional[int] = None
    polygon: Optional[dict] = None

@router.post("/location")
def create_location_watch(payload: LocationWatchCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    import json
    if not payload.sector_id and not payload.polygon:
        raise HTTPException(status_code=400, detail="Provide either sector_id or polygon")
    watch = LocationWatch(
        analyst_id=current_user.id, name=payload.name, sector_id=payload.sector_id,
        polygon_geojson=json.dumps(payload.polygon) if payload.polygon else None,
    )
    db.add(watch); db.commit(); db.refresh(watch)
    return {"id": watch.id, "name": watch.name}


class ThresholdAlertCreate(BaseModel):
    name: str
    sector_id: int
    event_category: str
    threshold_count: int
    window_days: int

@router.post("/threshold")
def create_threshold_alert(payload: ThresholdAlertCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    alert = ThresholdAlert(analyst_id=current_user.id, **payload.dict())
    db.add(alert); db.commit(); db.refresh(alert)
    return {"id": alert.id, "name": alert.name}

@router.get("/threshold")
def list_threshold_alerts(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(ThresholdAlert).filter(ThresholdAlert.analyst_id == current_user.id).all()
    return [{"id": a.id, "name": a.name, "threshold_count": a.threshold_count, "window_days": a.window_days, "is_active": a.is_active} for a in rows]