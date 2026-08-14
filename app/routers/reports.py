from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_senior_analyst
from app.models.report import Report, ReportVersion, ReportStatus
from app.models.sector import Sector
from app.services.report_generator import build_report_context, generate_report_draft

router = APIRouter(prefix="/reports", tags=["reports"])

class ReportGenerateRequest(BaseModel):
    title: str
    sector_id: Optional[int] = None
    polygon: Optional[dict] = None
    start_date: datetime
    end_date: datetime
    event_types: Optional[str] = None

@router.post("/generate")
def generate_report(payload: ReportGenerateRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sector = db.query(Sector).filter(Sector.id == payload.sector_id).first() if payload.sector_id else None
    context = build_report_context(
        db, sector=sector, polygon_geojson=payload.polygon,
        start_date=payload.start_date, end_date=payload.end_date, event_types=payload.event_types,
    )
    draft = generate_report_draft(context)

    report = Report(
        title=payload.title, sector_id=payload.sector_id,
        polygon_geojson=str(payload.polygon) if payload.polygon else None,
        start_date=payload.start_date, end_date=payload.end_date, event_types=payload.event_types,
        situation=draft["situation"], analysis=draft["analysis"],
        implications=draft["implications"], recommendation=draft["recommendation"],
        status=ReportStatus.draft, version=1, created_by_id=current_user.id,
    )
    db.add(report); db.flush()
    db.add(ReportVersion(
        report_id=report.id, version=1, situation=report.situation, analysis=report.analysis,
        implications=report.implications, recommendation=report.recommendation, edited_by_id=current_user.id,
    ))
    db.commit(); db.refresh(report)
    return {"id": report.id, "status": report.status.value, "version": report.version}


class ReportEdit(BaseModel):
    situation: Optional[str] = None
    analysis: Optional[str] = None
    implications: Optional[str] = None
    recommendation: Optional[str] = None

@router.patch("/{report_id}")
def edit_report(report_id: int, payload: ReportEdit, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status == ReportStatus.published:
        raise HTTPException(status_code=400, detail="Cannot edit a published report — publishing is final")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(report, field, value)
    report.version += 1
    db.add(ReportVersion(
        report_id=report.id, version=report.version, situation=report.situation, analysis=report.analysis,
        implications=report.implications, recommendation=report.recommendation, edited_by_id=current_user.id,
    ))
    db.commit()
    return {"id": report.id, "version": report.version}


@router.post("/{report_id}/publish")
def publish_report(report_id: int, db: Session = Depends(get_db), current_user=Depends(require_senior_analyst)):
    """Publishing requires senior-analyst sign-off — the literal 'analyst exercises judgment and signs off' from the spec."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = ReportStatus.published
    report.published_by_id = current_user.id
    report.published_at = datetime.utcnow()
    db.commit()
    return {"id": report.id, "status": "published", "published_by": current_user.username}


@router.get("/")
def list_reports(status: Optional[str] = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    rows = query.order_by(Report.created_at.desc()).all()
    return [{"id": r.id, "title": r.title, "status": r.status.value, "version": r.version, "created_at": r.created_at} for r in rows]


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": r.id, "title": r.title, "status": r.status.value, "version": r.version,
        "situation": r.situation, "analysis": r.analysis, "implications": r.implications, "recommendation": r.recommendation,
        "created_by": r.creator.username, "published_by": r.publisher.username if r.publisher else None,
        "published_at": r.published_at,
    }


@router.get("/{report_id}/versions")
def get_report_versions(report_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(ReportVersion).filter(ReportVersion.report_id == report_id).order_by(ReportVersion.version).all()
    return [{"version": v.version, "edited_by": v.editor.username, "created_at": v.created_at} for v in rows]