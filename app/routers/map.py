from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.map_service import get_events_with_locations, filter_events_by_polygon, build_heatmap_data
from app.models.sector import Sector

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/events")
def map_events(
    start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    """Pins for the map, optionally filtered by date range and category — frontend clusters at zoom-out client-side."""
    return get_events_with_locations(db, start_date, end_date, category)


class PolygonQuery(BaseModel):
    polygon: dict  
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@router.post("/events/polygon")
def map_events_in_polygon(payload: PolygonQuery, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    events = get_events_with_locations(db, payload.start_date, payload.end_date)
    return filter_events_by_polygon(events, payload.polygon)


@router.get("/heatmap")
def map_heatmap(
    start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    events = get_events_with_locations(db, start_date, end_date)
    return build_heatmap_data(events)


@router.get("/timelapse")
def map_timelapse(
    start_date: datetime, end_date: datetime,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    """Events ordered chronologically for frame-by-frame playback on the frontend."""
    events = get_events_with_locations(db, start_date, end_date)
    return sorted(events, key=lambda e: e["published_at"] or datetime.min)


# --- Sectors ---
class SectorCreate(BaseModel):
    name: str
    polygon: dict  

@router.post("/sectors")
def create_sector(payload: SectorCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    import json
    sector = Sector(analyst_id=current_user.id, name=payload.name, polygon_geojson=json.dumps(payload.polygon))
    db.add(sector)
    db.commit()
    db.refresh(sector)
    return {"id": sector.id, "name": sector.name}


@router.get("/sectors")
def list_sectors(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    import json
    rows = db.query(Sector).filter(Sector.analyst_id == current_user.id).all()
    return [{"id": s.id, "name": s.name, "polygon": json.loads(s.polygon_geojson)} for s in rows]


@router.get("/sectors/{sector_id}/events")
def sector_events(
    sector_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    import json
    sector = db.query(Sector).filter(Sector.id == sector_id, Sector.analyst_id == current_user.id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector not found")
    events = get_events_with_locations(db, start_date, end_date)
    return filter_events_by_polygon(events, json.loads(sector.polygon_geojson))