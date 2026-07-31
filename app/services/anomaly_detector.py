import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from statsmodels.tsa.seasonal import STL
from sqlalchemy.orm import Session

from app.models.sector import Sector
from app.models.detection import Detection, DetectionType
from app.services.map_service import get_events_with_locations, filter_events_by_polygon


def get_sector_daily_series(db: Session, sector: Sector, days_back: int = 120) -> pd.Series:
    """Daily event counts within a sector's polygon over the lookback window."""
    import json as j
    end = datetime.utcnow()
    start = end - timedelta(days=days_back)

    events = get_events_with_locations(db, start, end)
    in_sector = filter_events_by_polygon(events, j.loads(sector.polygon_geojson))

    if not in_sector:
        return pd.Series(dtype=float)

    df = pd.DataFrame(in_sector)
    df["date"] = pd.to_datetime(df["published_at"]).dt.date
    daily_counts = df.groupby("date").size()

    full_range = pd.date_range(start=start.date(), end=end.date(), freq="D")
    daily_counts = daily_counts.reindex(full_range.date, fill_value=0)
    return daily_counts


def detect_stl_anomalies(series: pd.Series, std_threshold: float = 2.0) -> list[dict]:
    """STL decomposition — flags days where the residual exceeds N std deviations."""
    if len(series) < 14:  
        return []

    try:
        stl = STL(series, period=7, robust=True)
        result = stl.fit()
        residual = result.resid
        std = residual.std()
        mean = residual.mean()

        anomalies = []
        for date, resid_val in residual.items():
            if std > 0 and abs(resid_val - mean) > std_threshold * std:
                anomalies.append({
                    "date": str(date),
                    "actual": float(series[date]),
                    "trend": float(result.trend[date]),
                    "residual": float(resid_val),
                    "std_deviations": float(abs(resid_val - mean) / std),
                })
        return anomalies
    except Exception as e:
        print(f"[Anomaly] STL failed: {e}")
        return []


def detect_isolation_forest_anomalies(series: pd.Series, contamination: float = 0.05) -> list[dict]:
    """Isolation Forest on the raw count series — catches point anomalies STL's smooth decomposition might miss."""
    if len(series) < 14:
        return []

    X = series.values.reshape(-1, 1)
    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(X)
    scores = model.decision_function(X)

    anomalies = []
    for i, (date, pred, score) in enumerate(zip(series.index, predictions, scores)):
        if pred == -1:  
            anomalies.append({
                "date": str(date),
                "actual": float(series.iloc[i]),
                "anomaly_score": float(score),  
            })
    return anomalies


def run_anomaly_detection(db: Session, sector: Sector) -> list[Detection]:
    series = get_sector_daily_series(db, sector)
    if series.empty:
        return []

    stl_anomalies = detect_stl_anomalies(series)
    if_anomalies = detect_isolation_forest_anomalies(series)

    
    if_dates = {a["date"] for a in if_anomalies}
    detections = []

    for anomaly in stl_anomalies:
        confirmed_by_isolation_forest = anomaly["date"] in if_dates
        confidence = min(0.95, 0.55 + 0.15 * anomaly["std_deviations"] + (0.2 if confirmed_by_isolation_forest else 0))

        detection = Detection(
            type=DetectionType.anomaly,
            sector_id=sector.id,
            confidence=round(confidence, 2),
            title=f"Activity anomaly in {sector.name} on {anomaly['date']}",
            description=(
                f"Event count of {int(anomaly['actual'])} on {anomaly['date']} deviates "
                f"{anomaly['std_deviations']:.1f} standard deviations from the sector's seasonal baseline "
                f"(expected trend: {anomaly['trend']:.1f})."
                + (" Confirmed independently by Isolation Forest." if confirmed_by_isolation_forest else "")
            ),
            evidence=json.dumps({
                "method": "STL decomposition + Isolation Forest cross-check" if confirmed_by_isolation_forest else "STL decomposition",
                "date": anomaly["date"],
                "actual_count": anomaly["actual"],
                "trend_baseline": anomaly["trend"],
                "std_deviations_from_baseline": anomaly["std_deviations"],
                "confirmed_by_isolation_forest": confirmed_by_isolation_forest,
                "full_series": {str(k): float(v) for k, v in series.items()},
            }),
        )
        db.add(detection)
        detections.append(detection)

    db.commit()
    return detections