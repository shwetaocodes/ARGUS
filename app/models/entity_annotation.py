from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class EntityAnnotation(Base):
    __tablename__ = "entity_annotations"

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    note = Column(Text, nullable=False)
    tag = Column(String, nullable=True)  
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entity = relationship("Entity")
    analyst = relationship("Analyst")