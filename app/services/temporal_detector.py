import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.sector import Sector
from app.models.sector_baseline import SectorBaseline
from app.models.detection import Detection, DetectionType
from app.services.detection_fingerprint import make_fingerprint
from app.services.map_service import get_events_with_locations, filter_events_by_polygon


def get_current_month_counts(db: Session, sector: Sector) -> dict:
    """Event counts by category for the current calendar month so far."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    events = get_events_with_locations(db, month_start, now)
    in_sector = filter_events_by_polygon(events, json.loads(sector.polygon_geojson))

    counts = {"all": len(in_sector)}
    for e in in_sector:
        cat = e["category"] or "uncategorized"
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def run_temporal_detection(db: Session, sector: Sector, min_prior_years: int = 1) -> list[Detection]:
    """
    Compares current month's activity to this sector's historical baseline for the SAME month
    in prior years — surfaces cyclical/seasonal recurrence, not just recent deviation.
    """
    current_month = datetime.utcnow().month
    current_counts = get_current_month_counts(db, sector)

    baselines = db.query(SectorBaseline).filter(
        SectorBaseline.sector_id == sector.id,
        SectorBaseline.month == current_month,
    ).all()

    detections = []

    for baseline in baselines:
        if baseline.sample_years < min_prior_years:
            continue  

        actual = current_counts.get(baseline.category, 0)

        recurrence_strength = min(1.0, baseline.sample_years / 3)  

        if baseline.std_count > 0:
            deviation = abs(actual - baseline.mean_count) / baseline.std_count
            tracking_score = max(0.0, 1 - deviation / 3)  
        else:
            tracking_score = 1.0 if actual > 0 else 0.5

        confidence = round(min(0.95, 0.3 + 0.4 * recurrence_strength + 0.3 * tracking_score), 2)

        if confidence < 0.5 or baseline.mean_count < 0.5:
            continue

        month_name = datetime(2000, current_month, 1).strftime("%B")

        current_year = datetime.utcnow().year
        fingerprint = make_fingerprint("temporal", sector.id, baseline.category, current_month, current_year)

        existing = db.query(Detection).filter(Detection.fingerprint == fingerprint).first()
        if existing:
            continue

        detection = Detection(
            type=DetectionType.temporal,
            sector_id=sector.id,
            confidence=confidence,
            title=f"Seasonal pattern: {baseline.category} activity in {sector.name} recurs in {month_name}",
            description=(
                f"'{baseline.category}' events in {sector.name} have historically averaged "
                f"{baseline.mean_count:.1f} occurrences in {month_name} across {baseline.sample_years} "
                f"prior year(s). Current month shows {actual} so far, "
                f"{'in line with' if tracking_score > 0.6 else 'diverging from'} the seasonal pattern."
            ),
            fingerprint=fingerprint,
            evidence=json.dumps({
                "category": baseline.category,
                "month": month_name,
                "historical_mean": baseline.mean_count,
                "historical_std": baseline.std_count,
                "sample_years": baseline.sample_years,
                "current_month_actual": actual,
                "recurrence_strength": round(recurrence_strength, 2),
                "tracking_score": round(tracking_score, 2),
            }),
        )
        db.add(detection)
        detections.append(detection)

    db.commit()
    return detections