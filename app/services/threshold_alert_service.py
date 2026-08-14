import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.watch import ThresholdAlert
from app.models.notification import Notification, NotificationType
from app.services.map_service import get_events_with_locations, filter_events_by_polygon


def evaluate_threshold_alerts(db: Session):
    alerts = db.query(ThresholdAlert).filter(ThresholdAlert.is_active == "active").all()

    for alert in alerts:
        window_start = datetime.utcnow() - timedelta(days=alert.window_days)
        events = get_events_with_locations(db, window_start, datetime.utcnow())
        in_sector = filter_events_by_polygon(events, json.loads(alert.sector.polygon_geojson))

        if alert.event_category != "all":
            in_sector = [e for e in in_sector if e["category"] == alert.event_category]

        if len(in_sector) > alert.threshold_count:
            notification = Notification(
                analyst_id=alert.analyst_id,
                type=NotificationType.threshold_alert,
                title=f"Threshold breached: {alert.name}",
                body=(
                    f"{len(in_sector)} '{alert.event_category}' events occurred in {alert.sector.name} "
                    f"over the last {alert.window_days} days — exceeds your threshold of {alert.threshold_count}."
                ),
                evidence=json.dumps({
                    "alert_id": alert.id, "actual_count": len(in_sector),
                    "threshold": alert.threshold_count, "window_days": alert.window_days,
                    "event_ids": [e["event_id"] for e in in_sector],
                }),
            )
            db.add(notification)
    db.commit()