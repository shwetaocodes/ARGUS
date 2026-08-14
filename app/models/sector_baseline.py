from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class SectorBaseline(Base):
    __tablename__ = "sector_baselines"

    id = Column(Integer, primary_key=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    category = Column(String, nullable=False)   
    month = Column(Integer, nullable=False)      

    mean_count = Column(Float, nullable=False)
    std_count = Column(Float, nullable=False)
    sample_years = Column(Integer, nullable=False)  
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sector = relationship("Sector")

    __table_args__ = (
        UniqueConstraint("sector_id", "category", "month", name="uq_sector_category_month"),
    )