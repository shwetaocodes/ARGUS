from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, func
from app.core.database import Base

class EntityAliasDictionary(Base):
    __tablename__ = "entity_alias_dictionary"
    id = Column(Integer, primary_key=True)
    canonical_name = Column(String, nullable=False, index=True)
    alias_normalized = Column(String, nullable=False)  
    language = Column(String, nullable=True)  
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("alias_normalized", name="uq_alias_normalized"),
    )