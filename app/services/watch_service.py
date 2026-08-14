import json
from shapely.geometry import shape, Point
from sqlalchemy.orm import Session

from app.models.watch import EntityWatch, LocationWatch
from app.models.notification import Notification, NotificationType
from app.models.entity import Entity
from app.models.event import Event
from app.services.email_service import send_email_notification


def check_entity_watches(db: Session, event: Event, entity_ids: list[int]):
    """Called once per event, right after its entities are linked."""
    if not entity_ids:
        return
    watches = db.query(EntityWatch).filter(EntityWatch.entity_id.in_(entity_ids)).all()
    for watch in watches:
        entity = db.query(Entity).filter(Entity.id == watch.entity_id).first()
        notification = Notification(
            analyst_id=watch.analyst_id,
            type=NotificationType.entity_watch,
            title=f"New event mentions watched entity: {entity.name}",
            body=f"'{event.title}' references {entity.name}, which you are watching.",
            evidence=json.dumps({"event_id": event.id, "entity_id": entity.id, "entity_name": entity.name}),
        )
        db.add(notification)
        db.flush()
        _maybe_email(db, notification)


def check_location_watches(db: Session, event: Event, location_entities: list[Entity]):
    """Called once per event, for each location entity it links to."""
    if not location_entities:
        return
    watches = db.query(LocationWatch).all()
    for watch in watches:
        for loc in location_entities:
            if loc.latitude is None or loc.longitude is None:
                continue
            matched = False
            if watch.sector_id and watch.sector.polygon_geojson:
                polygon = shape(json.loads(watch.sector.polygon_geojson))
                matched = polygon.contains(Point(loc.longitude, loc.latitude))
            elif watch.polygon_geojson:
                polygon = shape(json.loads(watch.polygon_geojson))
                matched = polygon.contains(Point(loc.longitude, loc.latitude))

            if matched:
                notification = Notification(
                    analyst_id=watch.analyst_id,
                    type=NotificationType.location_watch,
                    title=f"New event in watched area: {watch.name}",
                    body=f"'{event.title}' occurred at {loc.name}, inside your '{watch.name}' watch area.",
                    evidence=json.dumps({"event_id": event.id, "location_name": loc.name, "watch_name": watch.name}),
                )
                db.add(notification)
                db.flush()
                _maybe_email(db, notification)


def _maybe_email(db: Session, notification: Notification):
    analyst = notification.analyst
    if analyst.email_alerts_enabled and analyst.email:
        sent = send_email_notification(analyst.email, notification.title, notification.body)
        notification.email_sent = sent
        db.commit()