from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id = Column(Integer, primary_key=True)
    entity_a_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    entity_b_id = Column(Integer, ForeignKey("entities.id"), nullable=False)

    co_occurrence_count = Column(Integer, default=1, nullable=False)
    first_co_occurred_at = Column(DateTime(timezone=True), nullable=True)
    last_co_occurred_at = Column(DateTime(timezone=True), nullable=True)

    entity_a = relationship("Entity", foreign_keys=[entity_a_id])
    entity_b = relationship("Entity", foreign_keys=[entity_b_id])

    __table_args__ = (
        UniqueConstraint("entity_a_id", "entity_b_id", name="uq_entity_pair"),
        CheckConstraint("entity_a_id < entity_b_id", name="ck_entity_order"),
    )