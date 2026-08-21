from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ExtractionCorrection(Base):
    __tablename__ = "extraction_corrections"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)

    extraction_type = Column(String, nullable=False)  
    original_value = Column(Text, nullable=False)      
    corrected_value = Column(Text, nullable=True)       
    action = Column(String, nullable=False)             

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("Event")
    analyst = relationship("Analyst")

    source_table = Column(String, nullable=False, default="event") 
    source_record_id = Column(Integer, nullable=True)