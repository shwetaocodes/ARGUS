from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.entity_profile import get_entity_profile, get_entity_timeline, get_entity_relationships
from app.models.entity import Entity, ThreatLevel
from app.models.entity_annotation import EntityAnnotation
from app.services.graph_analysis import compute_centrality, get_entity_neighborhood

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("/{entity_id}/profile")
def entity_profile(entity_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    profile = get_entity_profile(db, entity_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Entity not found")
    return profile


@router.get("/{entity_id}/timeline")
def entity_timeline(entity_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_entity_timeline(db, entity_id)


@router.get("/{entity_id}/relationships")
def entity_relationships(entity_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_entity_relationships(db, entity_id)


class ThreatLevelUpdate(BaseModel):
    threat_level: str

@router.patch("/{entity_id}/threat-level")
def set_threat_level(entity_id: int, payload: ThreatLevelUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    if payload.threat_level not in [t.value for t in ThreatLevel]:
        raise HTTPException(status_code=400, detail="Invalid threat level")
    entity.threat_level = ThreatLevel(payload.threat_level)
    db.commit()
    return {"id": entity.id, "threat_level": entity.threat_level.value}


class AnnotationCreate(BaseModel):
    note: str
    tag: Optional[str] = None

@router.post("/{entity_id}/annotations")
def add_annotation(entity_id: int, payload: AnnotationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    annotation = EntityAnnotation(entity_id=entity_id, analyst_id=current_user.id, note=payload.note, tag=payload.tag)
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return {"id": annotation.id, "note": annotation.note, "tag": annotation.tag, "analyst_id": annotation.analyst_id}


@router.get("/{entity_id}/annotations")
def list_annotations(entity_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(EntityAnnotation).filter(EntityAnnotation.entity_id == entity_id).order_by(EntityAnnotation.created_at.desc()).all()
    return [{"id": a.id, "note": a.note, "tag": a.tag, "analyst_id": a.analyst_id, "created_at": a.created_at} for a in rows]

@router.get("/graph/centrality")
def entity_centrality(top_n: int = 20, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return compute_centrality(db, top_n)

@router.get("/{entity_id}/graph")
def entity_graph(entity_id: int, depth: int = 1, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return get_entity_neighborhood(db, entity_id, depth)

@router.get("/")
def list_entities(
    type: Optional[str] = None, q: Optional[str] = None,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
):
    query = db.query(Entity)
    if type:
        query = query.filter(Entity.type == type)
    if q:
        query = query.filter(Entity.name.ilike(f"%{q}%"))
    rows = query.limit(100).all()
    return [{"id": e.id, "name": e.name, "type": e.type.value, "threat_level": e.threat_level.value if e.threat_level else None} for e in rows]