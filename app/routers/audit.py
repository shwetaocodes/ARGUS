from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import require_senior_analyst
from app.models.activity_log import ActivityLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_activity_logs(
    analyst_id: Optional[int] = None,
    method: Optional[str] = None,
    path_contains: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user=Depends(require_senior_analyst),
):
    query = db.query(ActivityLog)
    if analyst_id:
        query = query.filter(ActivityLog.analyst_id == analyst_id)
    if method:
        query = query.filter(ActivityLog.method == method.upper())
    if path_contains:
        query = query.filter(ActivityLog.path.ilike(f"%{path_contains}%"))
    if start_date:
        query = query.filter(ActivityLog.created_at >= start_date)
    if end_date:
        query = query.filter(ActivityLog.created_at <= end_date)

    rows = query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "analyst": r.analyst.username if r.analyst else "anonymous",
            "method": r.method,
            "path": r.path,
            "status_code": r.status_code,
            "ip_address": r.ip_address,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/logs/by-analyst/{analyst_id}/summary")
def analyst_activity_summary(
    analyst_id: int, db: Session = Depends(get_db), current_user=Depends(require_senior_analyst),
):
    """A quick 'what has this analyst been doing' rollup, not just a raw log dump."""
    from sqlalchemy import func
    rows = db.query(
        ActivityLog.path, func.count(ActivityLog.id).label("count")
    ).filter(ActivityLog.analyst_id == analyst_id).group_by(ActivityLog.path).order_by(func.count(ActivityLog.id).desc()).limit(20).all()

    return [{"path": path, "count": count} for path, count in rows]