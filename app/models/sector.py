from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Sector(Base):
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    name = Column(String, nullable=False)
    polygon_geojson = Column(Text, nullable=False)  # GeoJSON polygon coordinates, stored as JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analyst = relationship("Analyst")