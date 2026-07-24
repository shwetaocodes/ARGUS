import sys
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.source import Source, SourceType
from app.models.event import Event, EventStatus
from app.services.dedupe import make_dedupe_hash


def get_or_create_import_source(db, name: str) -> Source:
    source = db.query(Source).filter(Source.name == name).first()
    if source:
        return source

    source = Source(
        name=name,
        type=SourceType.news,
        identifier=f"csv-import:{name}",
        is_active=False,  
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def import_csv(filepath: str):
    df = pd.read_csv(filepath)

    required_cols = {"title", "summary", "raw_text", "published_at", "source_name"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    db = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        for idx, row in df.iterrows():
            source = get_or_create_import_source(db, str(row["source_name"]))

            
            external_id = f"csv-row-{idx}-{row['title']}"
            dedupe_hash = make_dedupe_hash(source.id, external_id)

            exists = db.query(Event).filter(Event.dedupe_hash == dedupe_hash).first()
            if exists:
                skipped += 1
                continue

            published_at = None
            if pd.notna(row["published_at"]):
                published_at = pd.to_datetime(row["published_at"]).to_pydatetime()
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)

            event = Event(
                title=str(row["title"])[:500],
                summary=str(row["summary"]) if pd.notna(row["summary"]) else None,
                raw_text=str(row["raw_text"]),
                source_id=source.id,
                published_at=published_at,
                status=EventStatus.raw,
                dedupe_hash=dedupe_hash,
            )
            db.add(event)
            inserted += 1

        db.commit()
        print(f"Import complete: {inserted} inserted, {skipped} skipped as duplicates")

    except Exception as e:
        db.rollback()
        print(f"Import failed, rolled back: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_csv.py <path_to_csv>")
        sys.exit(1)

    import_csv(sys.argv[1])