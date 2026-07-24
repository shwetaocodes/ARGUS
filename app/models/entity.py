import enum
from sqlalchemy import Column, Integer, String, Enum, ARRAY
from sqlalchemy.orm import relationship
from app.core.database import Base


class EntityType(str, enum.Enum):
    person = "person"
    org = "org"
    location = "location"
    topic = "topic"


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(Enum(EntityType), nullable=False)
    aliases = Column(ARRAY(String), nullable=True)

    event_links = relationship("EventEntity", back_populates="entity")
    alerts = relationship("Alert", back_populates="entity")