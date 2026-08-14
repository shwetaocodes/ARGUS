import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ReportStatus(str, enum.Enum):
    draft = "draft"
    published = "published"

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    polygon_geojson = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    event_types = Column(String, nullable=True)   

    situation = Column(Text, nullable=False)
    analysis = Column(Text, nullable=False)
    implications = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)

    status = Column(Enum(ReportStatus), default=ReportStatus.draft, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    created_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    published_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("Analyst", foreign_keys=[created_by_id])
    publisher = relationship("Analyst", foreign_keys=[published_by_id])


class ReportVersion(Base):
    """Append-only snapshot history — same pattern as ExtractionCorrection: never overwrite, always log."""
    __tablename__ = "report_versions"
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    version = Column(Integer, nullable=False)
    situation = Column(Text, nullable=False)
    analysis = Column(Text, nullable=False)
    implications = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    edited_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("Report")
    editor = relationship("Analyst")