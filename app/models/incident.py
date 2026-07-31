import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class IncidentType(str, enum.Enum):
    border_clash = "border_clash"
    ceasefire_violation = "ceasefire_violation"
    troop_movement = "troop_movement"
    civilian_incident = "civilian_incident"
    influence_operation = "influence_operation"
    other = "other"

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  

    incident_date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String, nullable=False)
    type = Column(Enum(IncidentType), nullable=False)
    description = Column(Text, nullable=False)
    reliability_rating = Column(Integer, nullable=False)  

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analyst = relationship("Analyst")
    event = relationship("Event")