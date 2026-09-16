import enum, json
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Enum, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class DetectionType(str, enum.Enum):
    temporal = "temporal"
    sequence = "sequence"
    anomaly = "anomaly"
    cross_source = "cross_source"

class DetectionStatus(str, enum.Enum):
    new = "new"
    reviewed = "reviewed"
    dismissed = "dismissed"

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True)
    type = Column(Enum(DetectionType), nullable=False)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    confidence = Column(Float, nullable=False)  
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)  
    status = Column(Enum(DetectionStatus), default=DetectionStatus.new, nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    fingerprint = Column(String(64), nullable=False, index=True)

    sector = relationship("Sector")
    reviewer = relationship("Analyst")

    __table_args__ = (UniqueConstraint("fingerprint", name="uq_detection_fingerprint"),)