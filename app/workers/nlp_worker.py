"""
NLP extraction worker — consumes raw-events, processes via the staged
pipeline (NER -> entity linking -> classification -> geocoding -> sentiment,
each independently retried and validated), persists, publishes
processed-events.

Run as its own long-lived process:
    python -m app.workers.nlp_worker
    
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal
from app.models.event import Event
from app.core.kafka_config import get_consumer, get_producer, TOPIC_RAW_EVENTS, TOPIC_PROCESSED_EVENTS
from app.services.pipeline.orchestrator import process_event_pipeline

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

            result = process_event_pipeline(db, event)  

            producer.send(TOPIC_PROCESSED_EVENTS, {"event_id": event_id})
            producer.flush()

            consumer.commit()  
            if result["failed_stages"]:
                print(f"[nlp_worker] event {event_id} processed with partial failures: {result['failed_stages']}")
            else:
                print(f"[nlp_worker] processed event {event_id}")
                
        except Exception as e:
            print(f"[nlp_worker] FAILED event {event_id}: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    run()