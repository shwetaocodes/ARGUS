import json
from datetime import timedelta
from sqlalchemy.orm import Session

from app.models.pattern_template import PatternTemplate
from app.models.event_classification import EventClassification
from app.models.event import Event
from app.models.sector import Sector
from app.models.detection import Detection, DetectionType
from app.services.map_service import get_events_with_locations, filter_events_by_polygon


def get_classified_sector_events(db: Session, sector: Sector, days_back: int = 90):
    """Events in this sector with a classification, chronological."""
    import json as j
    from datetime import datetime
    end = datetime.utcnow()
    start = end - timedelta(days=days_back)

    events = get_events_with_locations(db, start, end)
    in_sector = filter_events_by_polygon(events, j.loads(sector.polygon_geojson))
    in_sector = [e for e in in_sector if e["category"]]  
    in_sector.sort(key=lambda e: e["published_at"])
    return in_sector


def match_template(events: list[dict], template: PatternTemplate) -> dict | None:
    """
    Sliding window match: walk events chronologically, try to advance through
    template.steps in order, respecting each step's max_days_after_previous window.
    Returns the best (most-complete, most-recent) match found, or None.
    """
    steps = template.steps
    if not steps:
        return None

    best_match = None

    
    for start_idx, start_event in enumerate(events):
        if start_event["category"] != steps[0].category:
            continue

        matched_events = [start_event]
        last_matched_time = start_event["published_at"]
        step_cursor = 1

        for event in events[start_idx + 1:]:
            if step_cursor >= len(steps):
                break
            current_step = steps[step_cursor]

            time_gap_days = (event["published_at"] - last_matched_time).days
            if time_gap_days > current_step.max_days_after_previous:
                break  

            if event["category"] == current_step.category:
                matched_events.append(event)
                last_matched_time = event["published_at"]
                step_cursor += 1

        match_ratio = step_cursor / len(steps)

        if best_match is None or match_ratio > best_match["match_ratio"]:
            best_match = {
                "match_ratio": match_ratio,
                "matched_events": matched_events,
                "steps_matched": step_cursor,
                "total_steps": len(steps),
            }

    return best_match


def run_sequence_detection(db: Session, sector: Sector, min_confidence: float = 0.6) -> list[Detection]:
    events = get_classified_sector_events(db, sector)
    templates = db.query(PatternTemplate).filter(PatternTemplate.is_active == True).all()

    detections = []
    for template in templates:
        match = match_template(events, template)
        if not match or match["match_ratio"] < min_confidence:
            continue

        detection = Detection(
            type=DetectionType.sequence,
            sector_id=sector.id,
            confidence=round(match["match_ratio"], 2),
            title=f"Sequence match: '{template.name}' in {sector.name} ({match['steps_matched']}/{match['total_steps']} steps)",
            description=(
                f"Live event sequence in {sector.name} matches the '{template.name}' pattern template "
                f"at {match['match_ratio']*100:.0f}% confidence — {match['steps_matched']} of "
                f"{match['total_steps']} defined steps observed in order within their configured time windows."
            ),
            evidence=json.dumps({
                "template_name": template.name,
                "template_id": template.id,
                "matched_events": [
                    {"event_id": e["event_id"], "title": e["title"], "category": e["category"], "date": str(e["published_at"])}
                    for e in match["matched_events"]
                ],
                "steps_matched": match["steps_matched"],
                "total_steps": match["total_steps"],
            }),
        )
        db.add(detection)
        detections.append(detection)

    db.commit()
    return detections