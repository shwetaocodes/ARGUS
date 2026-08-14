import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class EntityWatch(Base):
    __tablename__ = "entity_watches"
    id = Column(Integer, primary_key=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyst = relationship("Analyst")
    entity = relationship("Entity")


class LocationWatch(Base):
    __tablename__ = "location_watches"
    id = Column(Integer, primary_key=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)   
    polygon_geojson = Column(Text, nullable=True)                          
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyst = relationship("Analyst")
    sector = relationship("Sector")


class ThresholdAlert(Base):
    __tablename__ = "threshold_alerts"
    id = Column(Integer, primary_key=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    name = Column(String, nullable=False)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    event_category = Column(String, nullable=False)   
    threshold_count = Column(Integer, nullable=False)  
    window_days = Column(Integer, nullable=False)       
    is_active = Column(String, default="active")        
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyst = relationship("Analyst")
    sector = relationship("Sector")