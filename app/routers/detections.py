from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.sector import Sector
from app.models.detection import Detection, DetectionType, DetectionStatus
from app.services.anomaly_detector import run_anomaly_detection
from app.services.sequence_matcher import run_sequence_detection
from app.services.cross_source_correlator import run_cross_source_correlation
from app.models.sector_baseline import SectorBaseline
from app.services.baseline_service import compute_sector_baseline


router = APIRouter(prefix="/detections", tags=["detections"])


@router.post("/run/anomaly/{sector_id}")
def trigger_anomaly_detection(sector_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector not found")
    detections = run_anomaly_detection(db, sector)
    return {"detections_created": len(detections)}


@router.post("/run/sequence/{sector_id}")
def trigger_sequence_detection(sector_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector not found")
    detections = run_sequence_detection(db, sector)
    return {"detections_created": len(detections)}


@router.post("/run/cross-source")
def trigger_cross_source(window_hours: int = 48, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    detections = run_cross_source_correlation(db, window_hours=window_hours)
    return {"detections_created": len(detections)}


@router.get("/")
def list_detections(
    type: Optional[str] = None, status: Optional[str] = None, sector_id: Optional[int] = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    query = db.query(Detection)
    if type:
        query = query.filter(Detection.type == type)
    if status:
        query = query.filter(Detection.status == status)
    if sector_id:
        query = query.filter(Detection.sector_id == sector_id)
    rows = query.order_by(Detection.created_at.desc()).all()
    return [
        {"id": d.id, "type": d.type.value, "confidence": d.confidence, "title": d.title,
         "description": d.description, "status": d.status.value, "created_at": d.created_at}
        for d in rows
    ]


@router.get("/{detection_id}")
def get_detection(detection_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    import json
    d = db.query(Detection).filter(Detection.id == detection_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Detection not found")
    return {
        "id": d.id, "type": d.type.value, "confidence": d.confidence,
        "title": d.title, "description": d.description,
        "evidence": json.loads(d.evidence), "status": d.status.value, "created_at": d.created_at,
    }


@router.patch("/{detection_id}/status")
def update_detection_status(detection_id: int, status: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    d = db.query(Detection).filter(Detection.id == detection_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Detection not found")
    if status not in [s.value for s in DetectionStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")
    d.status = DetectionStatus(status)
    d.reviewed_by_id = current_user.id
    db.commit()
    return {"id": d.id, "status": d.status.value}

@router.post("/baseline/{sector_id}/recompute")
def recompute_baseline(sector_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sector = db.query(Sector).filter(Sector.id == sector_id).first()
    if not sector:
        raise HTTPException(status_code=404, detail="Sector not found")
    results = compute_sector_baseline(db, sector)
    return {"baseline_rows": len(results)}

@router.get("/baseline/{sector_id}")
def get_baseline(sector_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(SectorBaseline).filter(SectorBaseline.sector_id == sector_id).all()
    return [{"category": r.category, "month": r.month, "mean_count": r.mean_count, "std_count": r.std_count, "sample_years": r.sample_years} for r in rows]