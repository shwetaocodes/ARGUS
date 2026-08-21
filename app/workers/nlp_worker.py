"""
NLP extraction worker — consumes raw-events, processes, persists, publishes
processed-events. Run as its own long-lived process, separate from uvicorn:

    python -m app.workers.nlp_worker

Run multiple instances (different terminals, or containers) to scale
horizontally — Kafka's consumer group mechanics automatically split
partitions across them, no code change needed.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal
from app.models.event import Event
from app.core.kafka_config import get_consumer, get_producer, TOPIC_RAW_EVENTS, TOPIC_PROCESSED_EVENTS
from app.services.nlp_extraction import process_event

def run():
    consumer = get_consumer(TOPIC_RAW_EVENTS, group_id="nlp-workers")
    producer = get_producer()
    print("[nlp_worker] listening on", TOPIC_RAW_EVENTS)

    for message in consumer:
        event_id = message.value["event_id"]
        db = SessionLocal()
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                print(f"[nlp_worker] event {event_id} not found, skipping")
                consumer.commit()
                continue

            process_event(db, event)  

            producer.send(TOPIC_PROCESSED_EVENTS, {"event_id": event_id})
            producer.flush()

            consumer.commit()  
            print(f"[nlp_worker] processed event {event_id}")

        except Exception as e:
            print(f"[nlp_worker] FAILED event {event_id}: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    run()