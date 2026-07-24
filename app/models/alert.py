from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)  # nullable link
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)     # nullable link
    message = Column(Text, nullable=False)
    triggered_at = Column(DateTime(timezone=True), nullable=False)

    entity = relationship("Entity", back_populates="alerts")
    event = relationship("Event", back_populates="alerts")