import enum
from sqlalchemy import Column, Integer, Float, ForeignKey, Enum, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class EventCategory(str, enum.Enum):
    infiltration_attempt = "infiltration_attempt"
    ied = "ied"
    protest = "protest"
    troop_movement = "troop_movement"
    propaganda_broadcast = "propaganda_broadcast"
    ceasefire_violation = "ceasefire_violation"
    supply_convoy = "supply_convoy"
    aerial_activity = "aerial_activity"
    other = "other"

class ConfidenceLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"

class ReviewStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    corrected = "corrected"
    rejected = "rejected"

class EventClassification(Base):
    __tablename__ = "event_classifications"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    category = Column(Enum(EventCategory), nullable=False)
    confidence = Column(Enum(ConfidenceLevel), nullable=False)

    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.pending, nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    
    original_category = Column(Enum(EventCategory), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("Event", back_populates="classification")
    reviewer = relationship("Analyst")