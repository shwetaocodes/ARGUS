from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Sitrep(Base):
    __tablename__ = "sitreps"

    id = Column(Integer, primary_key=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    analyst = relationship("Analyst", back_populates="sitreps")
    event = relationship("Event", back_populates="sitreps")