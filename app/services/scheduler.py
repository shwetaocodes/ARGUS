from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.services.rss_ingest import poll_all_news_sources

scheduler = BackgroundScheduler()

def scheduled_rss_poll():
    db = SessionLocal()
    try:
        poll_all_news_sources(db)
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(scheduled_rss_poll, "interval", minutes=15, id="rss_poll")
    scheduler.start()