import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class SourceType(str, enum.Enum):
    news = "news"
    telegram = "telegram"

class Language(str, enum.Enum):
    en = "en"
    ur = "ur"
    zh = "zh"

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(Enum(SourceType), nullable=False)
    identifier = Column(String, nullable=False)
    language = Column(Enum(Language), nullable=True)   
    topic = Column(String, nullable=True)              
    is_active = Column(Boolean, default=True)

    events = relationship("Event", back_populates="source")

    correct_extractions = Column(Integer, default=0)
    total_reviewed_extractions = Column(Integer, default=0)