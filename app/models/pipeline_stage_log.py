import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, func
from app.core.database import Base

class StageStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    skipped = "skipped"

class PipelineStageLog(Base):
    __tablename__ = "pipeline_stage_log"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    stage = Column(String, nullable=False)  
    status = Column(Enum(StageStatus), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())