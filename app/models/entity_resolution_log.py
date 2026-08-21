from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, func
from app.core.database import Base

class EntityResolutionLog(Base):
    __tablename__ = "entity_resolution_log"
    id = Column(Integer, primary_key=True)
    input_name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False)
    resolved_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    method = Column(String, nullable=False)  
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())