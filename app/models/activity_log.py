from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)  
    method = Column(String, nullable=False)
    path = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    ip_address = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analyst = relationship("Analyst")