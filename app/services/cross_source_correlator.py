import json
from datetime import datetime, timedelta
from itertools import combinations
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer, util

from app.models.event import Event
from app.models.entity import Entity
from app.models.event_entity import EventEntity
from app.models.detection import Detection, DetectionType
from app.services.detection_fingerprint import make_fingerprint

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")  
    return _model


def get_recent_located_events(db: Session, window_hours: int = 48):
    """Events from the last window_hours that have at least one location entity linked."""
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)

    rows = db.query(Event, Entity).join(
        EventEntity, EventEntity.event_id == Event.id
    ).join(
        Entity, Entity.id == EventEntity.entity_id
    ).filter(
        Entity.type == "location",
        Event.published_at >= cutoff,
    ).all()

    return [
        {"event_id": e.id, "title": e.title, "text": e.raw_text, "source_id": e.source_id,
         "published_at": e.published_at, "location_entity_id": loc.id, "location_name": loc.name}
        for e, loc in rows
    ]


def cluster_by_location_and_sources(events: list[dict], min_sources: int = 3) -> list[dict]:
    """Group events sharing a location entity; keep only groups with 3+ distinct sources."""
    groups = {}
    for e in events:
        groups.setdefault(e["location_entity_id"], []).append(e)

    clusters = []
    for location_id, group in groups.items():
        distinct_sources = {e["source_id"] for e in group}
        if len(distinct_sources) >= min_sources:
            clusters.append({"location_entity_id": location_id, "location_name": group[0]["location_name"], "events": group})
    return clusters


def score_cluster_similarity(cluster: dict) -> float:
    """Average pairwise cosine similarity of event text within a cluster — how much they're 'about the same thing'."""
    model = get_model()
    texts = [e["text"][:500] for e in cluster["events"]]
    if len(texts) < 2:
        return 1.0

    embeddings = model.encode(texts, convert_to_tensor=True)
    pairs = list(combinations(range(len(texts)), 2))
    sims = [util.cos_sim(embeddings[i], embeddings[j]).item() for i, j in pairs]
    return sum(sims) / len(sims)


def run_cross_source_correlation(db: Session, window_hours: int = 48, min_sources: int = 3, similarity_threshold: float = 0.5) -> list[Detection]:
    events = get_recent_located_events(db, window_hours)
    clusters = cluster_by_location_and_sources(events, min_sources)

    detections = []
    for cluster in clusters:
        similarity = score_cluster_similarity(cluster)
        distinct_source_count = len({e["source_id"] for e in cluster["events"]})

        confidence = min(0.95, 0.5 + 0.4 * similarity + 0.05 * (distinct_source_count - min_sources))


        event_ids_sorted = sorted(e["event_id"] for e in cluster["events"])
        fingerprint = make_fingerprint("cross_source", cluster["location_entity_id"], *event_ids_sorted)

        existing = db.query(Detection).filter(Detection.fingerprint == fingerprint).first()
        if existing:
            continue

        detection = Detection(
            type=DetectionType.cross_source,
            sector_id=None,
            confidence=round(max(0.0, confidence), 2),
            title=f"Corroborated signal: {cluster['location_name']} ({distinct_source_count} sources)",
            description=(
                f"{len(cluster['events'])} events from {distinct_source_count} independent "
                f"sources referenced '{cluster['location_name']}' within a {window_hours}-hour window "
                f"(average content similarity: {similarity:.2f})."
            ),
            fingerprint=fingerprint,
            evidence=json.dumps({
                "location": cluster["location_name"],
                "window_hours": window_hours,
                "average_text_similarity": round(similarity, 3),
                "distinct_source_count": distinct_source_count,
                "events": [
                    {"event_id": e["event_id"], "title": e["title"], "source_id": e["source_id"], "published_at": str(e["published_at"])}
                    for e in cluster["events"]
                ],
            }),
        )

        db.add(detection)
        detections.append(detection)

    db.commit()
    return detections