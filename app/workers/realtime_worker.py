"""
Consumes processed-events immediately — this is where entity/location watch
notifications and cross-source correlation move OFF the 6-hour batch schedule
and become genuinely real-time, since they're naturally per-event triggers,
unlike anomaly/temporal detection which need an aggregate window.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal
from app.models.event import Event
from app.models.event_entity import EventEntity
from app.models.entity import Entity, EntityType
from app.core.kafka_config import get_consumer, TOPIC_PROCESSED_EVENTS
from app.services.watch_service import check_entity_watches, check_location_watches

def run():
    consumer = get_consumer(TOPIC_PROCESSED_EVENTS, group_id="realtime-workers")
    print("[realtime_worker] listening on", TOPIC_PROCESSED_EVENTS)

    for message in consumer:
        event_id = message.value["event_id"]
        db = SessionLocal()
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            links = db.query(EventEntity).filter(EventEntity.event_id == event_id).all()
            entities = [db.query(Entity).filter(Entity.id == l.entity_id).first() for l in links]

            check_entity_watches(db, event, [e.id for e in entities if e])
            location_entities = [e for e in entities if e and e.type == EntityType.location]
            check_location_watches(db, event, location_entities)

            consumer.commit()
        except Exception as e:
            print(f"[realtime_worker] FAILED event {event_id}: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    run()