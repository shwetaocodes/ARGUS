from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, func
from app.core.database import Base

class ConfidenceScore(Base):
    __tablename__ = "confidence_scores"
    id = Column(Integer, primary_key=True)
    event_entity_id = Column(Integer, ForeignKey("event_entities.id"), nullable=True)
    event_classification_id = Column(Integer, ForeignKey("event_classifications.id"), nullable=True)

    ner_confidence = Column(Float, nullable=True)
    embedding_similarity = Column(Float, nullable=True)
    source_reliability = Column(Float, nullable=True)
    cross_source_agreement = Column(Float, nullable=True)
    llm_confidence = Column(Float, nullable=True)

    weighted_score = Column(Float, nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())