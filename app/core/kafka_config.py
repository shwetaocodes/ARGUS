from kafka import KafkaProducer, KafkaConsumer
import json

KAFKA_BOOTSTRAP = "localhost:9092"

TOPIC_RAW_EVENTS = "argus.raw-events"
TOPIC_PROCESSED_EVENTS = "argus.processed-events"

_producer = None

def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all", 
        )
    return _producer

def get_consumer(topic: str, group_id: str) -> KafkaConsumer:
    return KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=group_id,          
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,  
    )