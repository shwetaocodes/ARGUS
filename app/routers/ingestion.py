from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.rss_ingest import poll_all_news_sources
from app.services.telegram_ingest import poll_all_telegram_sources

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/news/run")
def run_news_poll(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    count = poll_all_news_sources(db)
    return {"new_events": count}

@router.post("/telegram/run")
def run_telegram_poll(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    count = poll_all_telegram_sources(db)
    return {"new_events": count}