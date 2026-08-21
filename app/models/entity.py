import enum
from sqlalchemy import Column, Integer, String, Enum, ARRAY, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy import ARRAY, Float

class EntityType(str, enum.Enum):
    person = "person"
    org = "org"
    location = "location"
    topic = "topic"
    military_unit = "military_unit"
    weapon = "weapon"

class ThreatLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    type = Column(Enum(EntityType), nullable=False)
    aliases = Column(ARRAY(String), default=list)

    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geocode_confidence = Column(String, nullable=True)  

    threat_level = Column(Enum(ThreatLevel), nullable=True)

    event_links = relationship("EventEntity", back_populates="entity")

    alerts = relationship("Alert", back_populates="entity")

    name_embedding = Column(ARRAY(Float), nullable=True)
