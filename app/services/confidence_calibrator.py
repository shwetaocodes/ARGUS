from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.source import Source
from app.models.entity import Entity
from app.models.event import Event
from app.models.event_entity import EventEntity
from app.models.confidence_score import ConfidenceScore

CONFIDENCE_TO_FLOAT = {"high": 0.9, "medium": 0.6, "low": 0.3}

# Weights sum to 1.0 — tune these based on real calibration data once you have
# enough analyst review outcomes to check predicted-vs-actual accuracy.
WEIGHTS = {
    "ner_confidence": 0.15,
    "embedding_similarity": 0.15,
    "source_reliability": 0.25,
    "cross_source_agreement": 0.25,
    "llm_confidence": 0.20,
}


def get_source_reliability(db: Session, source_id: int) -> float:
    """
    Historical accuracy of this source, from actual analyst review outcomes —
    NOT from anything the LLM says. A brand-new source with no review history
    gets a neutral 0.5, not an assumed-good 0.9 — new sources have to earn trust.
    """
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source or source.total_reviewed_extractions == 0:
        return 0.5
    return source.correct_extractions / source.total_reviewed_extractions


def get_embedding_similarity_score(entity: Entity, matched_score: float | None) -> float:
    """
    matched_score comes from entity_resolver.py's own embedding stage — this
    function doesn't recompute anything, it just normalizes what resolution
    already calculated into the 0-1 range this calibrator expects.
    If this entity was a brand-new creation (no match), similarity is neutral,
    not penalized — a genuinely new entity isn't 'less confident', it's just new.
    """
    if matched_score is None:
        return 0.5
    return matched_score


def get_cross_source_agreement(db: Session, entity_id: int, event_id: int, window_hours: int = 48) -> float:
    """
    Real signal, not a guess: how many DISTINCT sources mention this same
    entity within the time window. Reuses the same distinct-source-counting
    logic as Phase 3's cross-source correlator, applied here per-entity
    instead of per-location-cluster.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or not event.published_at:
        return 0.5

    window_start = event.published_at - timedelta(hours=window_hours)
    window_end = event.published_at + timedelta(hours=window_hours)

    rows = db.query(EventEntity, Event).join(Event, Event.id == EventEntity.event_id).filter(
        EventEntity.entity_id == entity_id,
        Event.published_at >= window_start,
        Event.published_at <= window_end,
    ).all()

    distinct_sources = {e.source_id for _, e in rows}
    if len(distinct_sources) <= 1:
        return 0.3
    return min(1.0, 0.3 + (len(distinct_sources) - 1) * 0.35)


def compute_weighted_confidence(
    ner_confidence: str | None,
    embedding_similarity: float | None,
    source_reliability: float,
    cross_source_agreement: float,
    llm_confidence: str | None,
) -> dict:
    """
    Pure function — no DB access, easy to unit test in isolation.
    Any missing signal is excluded and the remaining weights are
    renormalized, rather than treating a missing signal as a 0 (which
    would unfairly punish, say, a brand-new entity with no cross-source
    history yet).
    """
    ner_val = CONFIDENCE_TO_FLOAT.get(ner_confidence)
    llm_val = CONFIDENCE_TO_FLOAT.get(llm_confidence)

    components = {
        "ner_confidence": ner_val,
        "embedding_similarity": embedding_similarity,
        "source_reliability": source_reliability,
        "cross_source_agreement": cross_source_agreement,
        "llm_confidence": llm_val,
    }

    present = {k: v for k, v in components.items() if v is not None}
    if not present:
        return {"weighted_score": 0.5, "components": components, "confidence_level": "low"}

    total_weight = sum(WEIGHTS[k] for k in present)
    weighted_score = sum(v * WEIGHTS[k] for k, v in present.items()) / total_weight

    if weighted_score >= 0.75:
        level = "high"
    elif weighted_score >= 0.5:
        level = "medium"
    else:
        level = "low"

    return {"weighted_score": round(weighted_score, 3), "components": components, "confidence_level": level}