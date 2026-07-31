from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class PatternTemplate(Base):
    __tablename__ = "pattern_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_by_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    steps = relationship("PatternTemplateStep", back_populates="template", order_by="PatternTemplateStep.step_order")
    creator = relationship("Analyst")


class PatternTemplateStep(Base):
    __tablename__ = "pattern_template_steps"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("pattern_templates.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    category = Column(String, nullable=False)          
    max_days_after_previous = Column(Integer, nullable=False)  

    template = relationship("PatternTemplate", back_populates="steps")