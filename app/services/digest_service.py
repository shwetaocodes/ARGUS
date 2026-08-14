import json
import ollama
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.detection import Detection
from app.models.analyst import Analyst
from app.models.notification import Notification, NotificationType
from app.services.email_service import send_email_notification

ollama_client = ollama.Client(host=settings.OLLAMA_HOST)

DIGEST_PROMPT = """Summarize the following intelligence detections from the last 24 hours into a short morning briefing, 2-3 sentences per item. Be factual and concise, no speculation beyond what's stated.

Detections:
{detections}

Return ONLY valid JSON: {{"summary": "one paragraph overview", "items": ["item 1 summary", "item 2 summary", ...]}}
"""


def generate_daily_digest(db: Session) -> dict:
    since = datetime.utcnow() - timedelta(hours=24)
    top_detections = db.query(Detection).filter(
        Detection.created_at >= since
    ).order_by(Detection.confidence.desc()).limit(5).all()

    if not top_detections:
        return {"summary": "No anomalies or pattern matches detected in the last 24 hours.", "items": []}

    detections_text = "\n".join(
        f"- [{d.type.value}, {d.confidence*100:.0f}% confidence] {d.title}: {d.description}"
        for d in top_detections
    )

    try:
        response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": DIGEST_PROMPT.format(detections=detections_text)}],
            format="json",
        )
        result = json.loads(response["message"]["content"])
    except Exception as e:
        print(f"[Digest] LLM summarization failed, falling back to raw list: {e}")
        result = {
            "summary": f"{len(top_detections)} detections in the last 24 hours (summary generation failed).",
            "items": [d.title for d in top_detections],
        }

    result["detection_ids"] = [d.id for d in top_detections]
    return result


def run_daily_digest(db: Session):
    digest = generate_daily_digest(db)
    body = digest["summary"] + "\n\n" + "\n".join(f"- {i}" for i in digest["items"])

    analysts = db.query(Analyst).all()
    for analyst in analysts:
        notification = Notification(
            analyst_id=analyst.id, type=NotificationType.daily_digest,
            title="Daily morning digest — 05:30",
            body=body, evidence=json.dumps(digest),
        )
        db.add(notification)
        db.flush()
        if analyst.email_alerts_enabled and analyst.email:
            sent = send_email_notification(analyst.email, notification.title, body)
            notification.email_sent = sent
    db.commit()