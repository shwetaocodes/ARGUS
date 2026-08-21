from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class IncidentEntity(Base):
    __tablename__ = "incident_entities"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    confidence = Column(String, nullable=True)
    review_status = Column(String, default="pending")
    reviewed_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    incident = relationship("Incident")
    entity = relationship("Entity")

    __table_args__ = (UniqueConstraint("incident_id", "entity_id", name="uq_incident_entity"),)