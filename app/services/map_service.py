import json
from datetime import datetime
from sqlalchemy.orm import Session
from shapely.geometry import shape, Point

from app.models.event import Event
from app.models.entity import Entity
from app.models.event_entity import EventEntity
from app.models.event_classification import EventClassification


def get_events_with_locations(db: Session, start_date: datetime = None, end_date: datetime = None, category: str = None):
    """Base query: events joined to their location entities, with lat/long."""
    query = db.query(Event, Entity, EventClassification).join(
        EventEntity, EventEntity.event_id == Event.id
    ).join(
        Entity, Entity.id == EventEntity.entity_id
    ).outerjoin(
        EventClassification, EventClassification.event_id == Event.id
    ).filter(
        Entity.type == "location",
        Entity.latitude.isnot(None),
        Entity.longitude.isnot(None),
    )

    if start_date:
        query = query.filter(Event.published_at >= start_date)
    if end_date:
        query = query.filter(Event.published_at <= end_date)
    if category:
        query = query.filter(EventClassification.category == category)

    rows = query.all()
    return [
        {
            "event_id": e.id,
            "title": e.title,
            "published_at": e.published_at,
            "lat": loc.latitude,
            "lon": loc.longitude,
            "category": cls.category.value if cls else None,
        }
        for e, loc, cls in rows
    ]


def filter_events_by_polygon(events: list[dict], polygon_geojson: dict) -> list[dict]:
    polygon = shape(polygon_geojson)  
    return [e for e in events if polygon.contains(Point(e["lon"], e["lat"]))]


def build_heatmap_data(events: list[dict]) -> list[dict]:
    """Simple density: group by rounded coordinate, count occurrences."""
    from collections import defaultdict
    buckets = defaultdict(int)
    for e in events:
        key = (round(e["lat"], 2), round(e["lon"], 2))  
        buckets[key] += 1
    return [{"lat": lat, "lon": lon, "weight": count} for (lat, lon), count in buckets.items()]