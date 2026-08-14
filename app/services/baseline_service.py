import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.sector import Sector
from app.models.sector_baseline import SectorBaseline
from app.services.map_service import get_events_with_locations, filter_events_by_polygon


def compute_sector_baseline(db: Session, sector: Sector, lookback_years: int = 3):
    """Recomputes per-category, per-month baseline stats for a sector from all available history."""
    import json
    end = datetime.utcnow()
    start = end - timedelta(days=365 * lookback_years)

    events = get_events_with_locations(db, start, end)
    in_sector = filter_events_by_polygon(events, json.loads(sector.polygon_geojson))

    if not in_sector:
        return []

    df = pd.DataFrame(in_sector)
    df["published_at"] = pd.to_datetime(df["published_at"])
    df["year"] = df["published_at"].dt.year
    df["month"] = df["published_at"].dt.month
    df["category"] = df["category"].fillna("uncategorized")

    results = []

    for category in list(df["category"].unique()) + ["all"]:
        subset = df if category == "all" else df[df["category"] == category]
        if subset.empty:
            continue

        monthly_yearly_counts = subset.groupby(["year", "month"]).size().reset_index(name="count")

        for month in range(1, 13):
            month_data = monthly_yearly_counts[monthly_yearly_counts["month"] == month]
            if month_data.empty:
                continue

            mean_count = month_data["count"].mean()
            std_count = month_data["count"].std()
            std_count = 0.0 if pd.isna(std_count) else std_count
            sample_years = month_data["year"].nunique()

            existing = db.query(SectorBaseline).filter(
                SectorBaseline.sector_id == sector.id,
                SectorBaseline.category == category,
                SectorBaseline.month == month,
            ).first()

            if existing:
                existing.mean_count = float(mean_count)
                existing.std_count = float(std_count)
                existing.sample_years = int(sample_years)
            else:
                existing = SectorBaseline(
                    sector_id=sector.id, category=category, month=month,
                    mean_count=float(mean_count), std_count=float(std_count), sample_years=int(sample_years),
                )
                db.add(existing)

            results.append(existing)

    db.commit()
    return results