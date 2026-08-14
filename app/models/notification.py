import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class NotificationType(str, enum.Enum):
    entity_watch = "entity_watch"
    location_watch = "location_watch"
    threshold_alert = "threshold_alert"
    daily_digest = "daily_digest"

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)   
    is_read = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyst = relationship("Analyst")