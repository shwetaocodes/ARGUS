import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class EventStatus(str, enum.Enum):
    raw = "raw"
    processing = "processing"
    processed = "processed"
    failed = "failed"

class Sentiment(str, enum.Enum):
    hostile = "hostile"
    neutral = "neutral"
    de_escalatory = "de_escalatory"

class ConfidenceLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"

class ThreatLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    raw_text = Column(Text, nullable=False)
    status = Column(Enum(EventStatus), default=EventStatus.raw, nullable=False)
    dedupe_hash = Column(String, unique=True, nullable=False, index=True)

    event_date_mentioned = Column(DateTime(timezone=True), nullable=True)  

    sentiment = Column(Enum(Sentiment), nullable=True)
    sentiment_confidence = Column(Enum(ConfidenceLevel), nullable=True)
    sentiment_review_status = Column(String, default="pending")  
    sentiment_reviewed_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    original_sentiment = Column(Enum(Sentiment), nullable=True)  

    source = relationship("Source", back_populates="events")
    entity_links = relationship("EventEntity", back_populates="event")
    classification = relationship("EventClassification", back_populates="event", uselist=False)

    sitreps = relationship("Sitrep", back_populates="event")

    alerts = relationship("Alert", back_populates="event")