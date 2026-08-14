from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.dependencies import require_senior_analyst, get_current_user
from app.core.database import get_db
from app.models.pattern_template import PatternTemplate, PatternTemplateStep

router = APIRouter(prefix="/patterns", tags=["patterns"])

class StepInput(BaseModel):
    category: str
    max_days_after_previous: int

class TemplateCreate(BaseModel):
    name: str
    steps: list[StepInput]

@router.post("/templates")
def create_template(payload: TemplateCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    
    template = PatternTemplate(name=payload.name, created_by_id=current_user.id)
    db.add(template)
    db.flush()

    for i, step in enumerate(payload.steps):
        db.add(PatternTemplateStep(
            template_id=template.id, step_order=i,
            category=step.category, max_days_after_previous=step.max_days_after_previous,
        ))
    db.commit()
    return {"id": template.id, "name": template.name, "steps": len(payload.steps)}

@router.get("/templates")
def list_templates(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    templates = db.query(PatternTemplate).all()
    return [{"id": t.id, "name": t.name, "is_active": t.is_active, "steps": len(t.steps)} for t in templates]

@router.post("/templates")
def create_template(payload: TemplateCreate, db: Session = Depends(get_db), current_user=Depends(require_senior_analyst)):
    template = PatternTemplate(name=payload.name, created_by_id=current_user.id)
    