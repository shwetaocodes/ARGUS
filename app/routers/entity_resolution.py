from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.entity_merge_candidate import EntityMergeCandidate, MergeCandidateStatus

router = APIRouter(prefix="/entity-resolution", tags=["entity-resolution"])

@router.get("/merge-candidates")
def list_merge_candidates(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    rows = db.query(EntityMergeCandidate).filter(EntityMergeCandidate.status == MergeCandidateStatus.pending).all()
    return [
        {"id": c.id, "new_entity": c.new_entity.name, "matched_entity": c.matched_entity.name,
         "method": c.method, "score": round(c.score, 3)}
        for c in rows
    ]

@router.post("/merge-candidates/{candidate_id}/confirm")
def confirm_merge(candidate_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Analyst confirms two entities are the same — this is the ONLY path
    by which a probabilistic match becomes a permanent merge."""
    c = db.query(EntityMergeCandidate).filter(EntityMergeCandidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")

    new_entity, target = c.new_entity, c.matched_entity
    if new_entity.name not in (target.aliases or []):
        target.aliases = (target.aliases or []) + [new_entity.name]

    c.status = MergeCandidateStatus.confirmed
    c.reviewed_by_id = current_user.id
    db.commit()
    return {"status": "confirmed", "merged_into": target.name}

@router.post("/merge-candidates/{candidate_id}/reject")
def reject_merge(candidate_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    c = db.query(EntityMergeCandidate).filter(EntityMergeCandidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    c.status = MergeCandidateStatus.rejected
    c.reviewed_by_id = current_user.id
    db.commit()
    return {"status": "rejected"}