from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class EventEntity(Base):
    __tablename__ = "event_entities"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    relevance_score = Column(Float, nullable=True)  

    event = relationship("Event", back_populates="entity_links")
    entity = relationship("Entity", back_populates="event_links")

    __table_args__ = (
        UniqueConstraint("event_id", "entity_id", name="uq_event_entity"),
    )