from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.services.rss_ingest import poll_all_news_sources
from app.models.sector import Sector
from app.services.anomaly_detector import run_anomaly_detection
from app.services.temporal_detector import run_temporal_detection
from app.services.sequence_matcher import run_sequence_detection
from app.services.cross_source_correlator import run_cross_source_correlation
from app.services.baseline_service import compute_sector_baseline
from app.services.digest_service import run_daily_digest
from app.services.threshold_alert_service import evaluate_threshold_alerts



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

def scheduled_detection_run():
    db = SessionLocal()
    try:
        sectors = db.query(Sector).all()
        for sector in sectors:
            compute_sector_baseline(db, sector)
            run_anomaly_detection(db, sector)
            run_temporal_detection(db, sector)
            run_sequence_detection(db, sector)
        run_cross_source_correlation(db)
    finally:
        db.close()

def scheduled_digest_job():
    db = SessionLocal()
    try:
        run_daily_digest(db)
    finally:
        db.close()

def scheduled_threshold_check():
    db = SessionLocal()
    try:
        evaluate_threshold_alerts(db)
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(scheduled_rss_poll, "interval", minutes=15, id="rss_poll")
    scheduler.add_job(scheduled_detection_run, "interval", hours=6, id="detection_run")  
    scheduler.add_job(scheduled_digest_job, "cron", hour=5, minute=30, id="daily_digest")
    scheduler.add_job(scheduled_threshold_check, "interval", minutes=15, id="threshold_alerts")
    scheduler.start()