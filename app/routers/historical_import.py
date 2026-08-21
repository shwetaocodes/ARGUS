from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import pandas as pd
import io

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.source import Source, SourceType
from app.models.event import Event, EventStatus
from app.models.incident import Incident, IncidentType
from app.services.dedupe import make_dedupe_hash

router = APIRouter(prefix="/historical-import", tags=["historical-import"])


def _read_upload_to_df(file: UploadFile, contents: bytes) -> pd.DataFrame:
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext == "csv":
        return pd.read_csv(io.BytesIO(contents))
    elif ext in ("xlsx", "xls"):
        return pd.read_excel(io.BytesIO(contents))
    raise HTTPException(status_code=400, detail=f"Unsupported file type '.{ext}'. Use .csv, .xlsx, or .xls.")


def _get_or_create_import_source(db: Session, name: str) -> Source:
    source = db.query(Source).filter(Source.name == name).first()
    if source:
        return source
    source = Source(name=name, type=SourceType.news, identifier=f"historical-import:{name}", is_active=False)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.post("/events")
async def import_historical_events(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    For historical NEWS/article-style data — lands in `events`, same status='raw'
    shape as RSS/Telegram, so it flows through the normal NLP pipeline afterward.
    Required columns: title, summary, raw_text, published_at, source_name
    """
    contents = await file.read()
    df = _read_upload_to_df(file, contents)

    required = {"title", "summary", "raw_text", "published_at", "source_name"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")

    inserted, skipped = 0, 0
    try:
        for idx, row in df.iterrows():
            source = _get_or_create_import_source(db, str(row["source_name"]))
            dedupe_hash = make_dedupe_hash(source.id, f"hist-row-{idx}-{row['title']}")

            if db.query(Event).filter(Event.dedupe_hash == dedupe_hash).first():
                skipped += 1
                continue

            published_at = pd.to_datetime(row["published_at"]) if pd.notna(row["published_at"]) else None

            db.add(Event(
                title=str(row["title"])[:500],
                summary=str(row["summary"]) if pd.notna(row["summary"]) else None,
                raw_text=str(row["raw_text"]),
                source_id=source.id,
                published_at=published_at,
                status=EventStatus.raw,
                dedupe_hash=dedupe_hash,
            ))
            inserted += 1
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")

    return {"inserted": inserted, "skipped_duplicates": skipped, "filename": file.filename}


@router.post("/incidents")
async def import_historical_incidents(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Imports DIRECTLY into `incidents`, not `events` — this is the gap flagged
    explicitly: 'imports to Events table; incident data would require
    additional processing.' This endpoint skips that indirection entirely.
    Required columns: incident_date, location, type, description, reliability_rating
    """
    contents = await file.read()
    df = _read_upload_to_df(file, contents)

    required = {"incident_date", "location", "type", "description", "reliability_rating"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")

    valid_types = {t.value for t in IncidentType}
    inserted, skipped_invalid = 0, []

    try:
        for idx, row in df.iterrows():
            row_type = str(row["type"]).strip()
            if row_type not in valid_types:
                skipped_invalid.append({"row": idx, "reason": f"invalid type '{row_type}'"})
                continue

            rating = int(row["reliability_rating"])
            if not (1 <= rating <= 5):
                skipped_invalid.append({"row": idx, "reason": f"reliability_rating {rating} out of range 1-5"})
                continue

            incident_date = pd.to_datetime(row["incident_date"])
            if pd.isna(incident_date):
                skipped_invalid.append({"row": idx, "reason": "unparseable incident_date"})
                continue

            db.add(Incident(
                analyst_id=current_user.id, 
                incident_date=incident_date,
                location=str(row["location"]),
                type=IncidentType(row_type),
                description=str(row["description"]),
                reliability_rating=rating,
            ))
            inserted += 1
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")

    return {"inserted": inserted, "skipped_invalid_rows": skipped_invalid, "filename": file.filename}