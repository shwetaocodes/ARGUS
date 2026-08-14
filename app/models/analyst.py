from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class Analyst(Base):
    __tablename__ = "analysts"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="analyst")
    email = Column(String, nullable=True)
    email_alerts_enabled = Column(Boolean, default=False)

    sitreps = relationship("Sitrep", back_populates="analyst")