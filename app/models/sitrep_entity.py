from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class SitrepEntity(Base):
    __tablename__ = "sitrep_entities"
    id = Column(Integer, primary_key=True)
    sitrep_id = Column(Integer, ForeignKey("sitreps.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    confidence = Column(String, nullable=True)
    review_status = Column(String, default="pending")
    reviewed_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    sitrep = relationship("Sitrep")
    entity = relationship("Entity")

    __table_args__ = (UniqueConstraint("sitrep_id", "entity_id", name="uq_sitrep_entity"),)