import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class MergeCandidateStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"

class EntityMergeCandidate(Base):
    __tablename__ = "entity_merge_candidates"
    id = Column(Integer, primary_key=True)
    new_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)  
    matched_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)  
    method = Column(String, nullable=False)   
    score = Column(Float, nullable=False)
    status = Column(Enum(MergeCandidateStatus), default=MergeCandidateStatus.pending, nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    new_entity = relationship("Entity", foreign_keys=[new_entity_id])
    matched_entity = relationship("Entity", foreign_keys=[matched_entity_id])
    reviewer = relationship("Analyst")