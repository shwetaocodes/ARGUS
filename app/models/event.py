import enum
from sqlalchemy import Column, Integer,String, Text, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class EventStatus(str, enum.Enum):
    raw = "raw"
    processing = "processing"
    processed = "processed"
    failed = "failed"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    status = Column(Enum(EventStatus), nullable=False, default=EventStatus.raw)
    raw_text = Column(Text, nullable=False)
    dedupe_hash = Column(String, unique=True, nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=False)

    source = relationship("Source", back_populates="events")
    entity_links = relationship("EventEntity", back_populates="event")
    sitreps = relationship("Sitrep", back_populates="event")
    alerts = relationship("Alert", back_populates="event")