from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/")
def list_notifications(unread_only: bool = False, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = db.query(Notification).filter(Notification.analyst_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    rows = query.order_by(Notification.created_at.desc()).limit(100).all()
    return [
        {"id": n.id, "type": n.type.value, "title": n.title, "body": n.body,
         "evidence": json.loads(n.evidence) if n.evidence else None,
         "is_read": n.is_read, "created_at": n.created_at}
        for n in rows
    ]

@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.analyst_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"id": n.id, "is_read": True}