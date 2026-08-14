import json
from datetime import datetime
from anthropic import Anthropic
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.map_service import get_events_with_locations, filter_events_by_polygon
from app.services.entity_profile import get_entity_relationships

client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

REPORT_PROMPT = """You are drafting a military-format intelligence report from the structured data below. Follow this exact four-section structure. Write factually — do not invent details not present in the data.

DATA:
Time period: {start_date} to {end_date}
Area: {area_description}
Total events: {event_count}
Event category breakdown: {category_breakdown}
Key entities involved: {entities_summary}
Detections/anomalies in this period: {detections_summary}
Sample event summaries: {sample_events}

Write four sections:
1. SITUATION — factual summary of events observed, no interpretation
2. ANALYSIS — patterns, trends, and anomalies detected in the data above
3. IMPLICATIONS — what this suggests for the next 72 hours, grounded in the data, not speculation beyond it
4. RECOMMENDATION — suggested actions or watch priorities for analysts

Return ONLY valid JSON: {{"situation": "...", "analysis": "...", "implications": "...", "recommendation": "..."}}
"""


def build_report_context(db: Session, sector=None, polygon_geojson=None, start_date=None, end_date=None, event_types=None) -> dict:
    """Gathers real underlying data — this IS the 'structured context injection' the spec names."""
    events = get_events_with_locations(db, start_date, end_date)

    if sector:
        events = filter_events_by_polygon(events, json.loads(sector.polygon_geojson))
    elif polygon_geojson:
        events = filter_events_by_polygon(events, polygon_geojson)

    if event_types:
        allowed = set(event_types.split(","))
        events = [e for e in events if e["category"] in allowed]

    category_counts = {}
    for e in events:
        cat = e["category"] or "uncategorized"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    from app.models.detection import Detection
    detections = db.query(Detection).filter(
        Detection.created_at >= start_date, Detection.created_at <= end_date,
    ).order_by(Detection.confidence.desc()).limit(10).all()

    return {
        "start_date": start_date.isoformat() if start_date else "unspecified",
        "end_date": end_date.isoformat() if end_date else "unspecified",
        "area_description": sector.name if sector else "custom drawn area",
        "event_count": len(events),
        "category_breakdown": category_counts,
        "sample_events": [{"title": e["title"], "category": e["category"], "date": str(e["published_at"])} for e in events[:15]],
        "detections_summary": [{"title": d.title, "confidence": d.confidence, "type": d.type.value} for d in detections],
    }


def generate_report_draft(context: dict) -> dict:
    prompt = REPORT_PROMPT.format(
        start_date=context["start_date"], end_date=context["end_date"],
        area_description=context["area_description"], event_count=context["event_count"],
        category_breakdown=json.dumps(context["category_breakdown"]),
        entities_summary="see sample events", detections_summary=json.dumps(context["detections_summary"]),
        sample_events=json.dumps(context["sample_events"]),
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    cleaned = raw_text.strip().strip("```json").strip("```").strip()
    return json.loads(cleaned)