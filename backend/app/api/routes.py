from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean, median, pstdev

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..collectors.demo_collector import DemoReplayCollector, ROUTE_BASKET
from ..database import get_db
from ..index_engine.index import contributions, index_series, latest_route_indices, valid_available
from ..index_engine.weights import PROTOTYPE_WEIGHT_LABEL
from ..intelligence.anomalies import market_shocks
from ..intelligence.decision_support import travel_recommendation
from ..intelligence.explanations import explain_route
from ..intelligence.forecast import national_forecast
from ..models import AirfareObservation
from ..processing.quality import iqr_outliers, mad_outliers, quality_score
from ..schemas import DecisionRequest, ScenarioRequest

router = APIRouter(tags=["AirIndex India"])


def _empty(message: str) -> dict:
    return {"available": False, "message": message, "data": []}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return {"status": "ok", "service": "AirIndex India", "database": "connected", "observations": db.scalar(select(func.count(AirfareObservation.id)))}


@router.post("/seed")
def seed(reset: bool = Query(default=False), db: Session = Depends(get_db)):
    existing = db.scalar(select(func.count(AirfareObservation.id))) or 0
    if existing and not reset:
        return {"created": 0, "total": existing, "message": "Dataset already initialized. Use POST /seed?reset=true to recreate development / replay data."}
    if reset:
        db.query(AirfareObservation).delete()
        db.commit()
    collector = DemoReplayCollector()
    rows = [collector.normalize(row) for row in collector.collect()]
    grouped = defaultdict(list)
    for index, row in enumerate(rows):
        grouped[(row["route"], row["advance_days"])].append((index, row["total_fare"]))
    outliers: set[int] = set()
    for values in grouped.values():
        amounts = [value for _, value in values]
        flagged = mad_outliers(amounts) | iqr_outliers(amounts)
        outliers.update(values[position][0] for position in flagged)
    invalid, flagged = 0, 0
    for index, row in enumerate(rows):
        status, _ = collector.validate(row)
        outlier = index in outliers
        invalid += status == "invalid"
        flagged += outlier
        row["validation_status"] = status
        row["is_outlier"] = outlier
        row["quality_score"] = quality_score(status, outlier)
        db.add(AirfareObservation(**row))
    db.commit()
    return {"created": len(rows), "total": len(rows), "invalid": invalid, "outliers_flagged": flagged, "source": "Development / replay data", "message": "Development / replay data initialized. High outliers are retained and flagged, not deleted."}


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    removed = db.query(AirfareObservation).delete()
    db.commit()
    return {"removed": removed, "message": "Local development database reset."}


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    series = index_series(db)
    if not series:
        return _empty("No observations yet. Initialize the development / replay dataset.")
    latest = series[-1]["index"]
    daily = latest - series[-2]["index"] if len(series) > 1 else 0
    weekly = latest - series[-8]["index"] if len(series) > 7 else 0
    monthly = latest - series[0]["index"]
    total = db.scalar(select(func.count(AirfareObservation.id))) or 0
    available = db.scalar(select(func.count(AirfareObservation.id)).where(AirfareObservation.availability == "AVAILABLE")) or 0
    quality = db.scalar(select(func.avg(AirfareObservation.quality_score))) or 0
    latest_timestamp = db.scalar(select(func.max(AirfareObservation.collection_timestamp)))
    return {"available": True, "national_index": round(latest, 2), "base_period": 100, "daily_change": round(daily, 2), "weekly_change": round(weekly, 2), "monthly_change": round(monthly, 2), "observations": total, "available_observations": available, "data_quality": round(quality, 1), "last_updated": latest_timestamp, "source": "Development / replay data", "weight_note": PROTOTYPE_WEIGHT_LABEL}


@router.get("/observations")
def observations(route: str | None = None, limit: int = Query(default=100, le=500), db: Session = Depends(get_db)):
    statement = select(AirfareObservation).order_by(AirfareObservation.collection_timestamp.desc()).limit(limit)
    if route:
        statement = statement.where(AirfareObservation.route == route.upper())
    data = []
    for row in db.scalars(statement):
        data.append({"id": row.id, "timestamp": row.collection_timestamp, "route": row.route, "airline": row.airline, "travel_date": row.travel_date, "advance_days": row.advance_days, "total_fare": row.total_fare, "availability": row.availability, "quality_score": row.quality_score, "status": row.validation_status, "outlier": row.is_outlier, "source": row.source})
    return {"available": bool(data), "data": data, "source": "Development / replay data"}


@router.get("/observations/latest")
def latest_observations(db: Session = Depends(get_db)):
    latest = db.scalar(select(func.max(AirfareObservation.collection_timestamp)))
    if not latest:
        return _empty("No observations yet. Initialize the dataset.")
    latest_day_start = latest.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = list(db.scalars(select(AirfareObservation).where(AirfareObservation.collection_timestamp >= latest_day_start, AirfareObservation.collection_timestamp < latest_day_start + timedelta(days=1)).order_by(AirfareObservation.route, AirfareObservation.airline)))
    return {"available": bool(rows), "data": [{"id": row.id, "timestamp": row.collection_timestamp, "route": row.route, "airline": row.airline, "travel_date": row.travel_date, "advance_days": row.advance_days, "total_fare": row.total_fare, "availability": row.availability, "quality_score": row.quality_score, "status": row.validation_status, "outlier": row.is_outlier, "source": row.source} for row in rows], "source": "Development / replay data"}


@router.get("/index")
@router.get("/index/national")
def national_index(period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"), db: Session = Depends(get_db)):
    data = index_series(db, period)
    return {"available": bool(data), "data": data, "period": period, "base_period": 100, "method": "Laspeyres-style weighted relative price index", "weight_note": PROTOTYPE_WEIGHT_LABEL}


@router.get("/index/routes")
def route_index(db: Session = Depends(get_db)):
    data = latest_route_indices(db)
    return {"available": bool(data), "data": data, "weight_note": PROTOTYPE_WEIGHT_LABEL}


@router.get("/index/contribution")
def index_contribution(db: Session = Depends(get_db)):
    data = contributions(db)
    return {"available": bool(data), "data": data, "description": "Contribution in national prototype index points since the base period."}


@router.get("/lead-time")
def lead_time(route: str | None = None, db: Session = Depends(get_db)):
    rows = valid_available(db)
    if route:
        rows = [row for row in rows if row.route == route.upper()]
    if not rows:
        return _empty("No valid available observations for this selection.")
    latest_day = max(row.collection_timestamp.date() for row in rows)
    current = defaultdict(list)
    historical = defaultdict(list)
    for row in rows:
        (current if row.collection_timestamp.date() == latest_day else historical)[row.advance_days].append(row.total_fare)
    data = []
    for lead in sorted(current):
        current_fare = mean(current[lead])
        baseline = median(historical[lead]) if historical[lead] else current_fare
        data.append({"lead_days": lead, "label": f"T+{lead}", "current_fare": round(current_fare, 2), "historical_median": round(baseline, 2), "change_pct": round((current_fare / baseline - 1) * 100, 2) if baseline else 0})
    return {"available": True, "route": route or "NATIONAL BASKET", "data": data, "observation": "Shows observed replay relationship; it does not assume earlier booking is always cheaper."}


@router.get("/airlines")
def airlines(db: Session = Depends(get_db)):
    rows = valid_available(db)
    if not rows:
        return _empty("No valid observations yet.")
    latest = max(row.collection_timestamp.date() for row in rows)
    grouped = defaultdict(list)
    for row in rows:
        if row.collection_timestamp.date() == latest:
            grouped[row.airline].append(row.total_fare)
    return {"available": True, "data": [{"airline": airline, "average_fare": round(mean(values), 2), "observations": len(values)} for airline, values in sorted(grouped.items())], "source": "Development / replay data"}


@router.get("/analytics/dispersion")
def dispersion(db: Session = Depends(get_db)):
    rows = valid_available(db)
    if not rows:
        return _empty("No valid available observations yet.")
    latest = max(row.collection_timestamp.date() for row in rows)
    groups = defaultdict(list)
    for row in rows:
        if row.collection_timestamp.date() == latest:
            groups[row.route].append(row.total_fare)
    data = []
    for route, values in groups.items():
        ordered = sorted(values)
        avg = mean(values)
        std = pstdev(values) if len(values) > 1 else 0
        data.append({"route": route, "mean": round(avg, 2), "median": round(median(values), 2), "minimum": round(min(values), 2), "maximum": round(max(values), 2), "p25": round(ordered[len(ordered)//4], 2), "p75": round(ordered[(len(ordered)*3)//4], 2), "std_dev": round(std, 2), "coefficient_variation": round(std / avg * 100, 2) if avg else 0})
    return {"available": True, "data": sorted(data, key=lambda item: item["route"])}


@router.get("/analytics/anomalies")
def anomalies(db: Session = Depends(get_db)):
    data = market_shocks(db)
    return {"available": bool(data), "data": data, "method": "Robust median historical movement thresholds. Data-quality outliers remain separate from market shocks."}


@router.get("/analytics/explanations")
def explanations(route: str | None = None, db: Session = Depends(get_db)):
    return explain_route(db, route.upper() if route else None)


@router.get("/forecast")
def forecast(db: Session = Depends(get_db)):
    return national_forecast(db)


@router.post("/decision-support")
def decision_support(request: DecisionRequest, db: Session = Depends(get_db)):
    return travel_recommendation(db, request.route, request.advance_days, request.current_fare)


@router.post("/scenario")
def scenario(request: ScenarioRequest, db: Session = Depends(get_db)):
    routes = latest_route_indices(db)
    current = next((row for row in routes if row["route"] == request.route), None)
    if not current:
        raise HTTPException(status_code=404, detail="Route has no index observations. Initialize the dataset first.")
    before_national = index_series(db)[-1]["index"]
    route_after = current["index"] * (1 + request.fare_change_pct / 100)
    national_after = before_national + current["weight"] * (route_after - current["index"])
    return {"scenario": "Scenario simulation", "route": request.route, "fare_change_pct": request.fare_change_pct, "route_index_before": current["index"], "route_index_after": round(route_after, 2), "national_index_before": before_national, "national_index_after": round(national_after, 2), "national_index_impact_points": round(national_after - before_national, 2), "disclaimer": "What-if calculation using prototype configurable weights; not a forecast or official CPI statistic."}


@router.get("/quality")
def quality(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(AirfareObservation.id))) or 0
    if not total:
        return _empty("No observations yet. Initialize the development / replay dataset.")
    valid = db.scalar(select(func.count(AirfareObservation.id)).where(AirfareObservation.validation_status == "valid")) or 0
    invalid = total - valid
    duplicate = db.scalar(select(func.count(AirfareObservation.id)).where(AirfareObservation.validation_status == "duplicate")) or 0
    outliers = db.scalar(select(func.count(AirfareObservation.id)).where(AirfareObservation.is_outlier.is_(True))) or 0
    score = db.scalar(select(func.avg(AirfareObservation.quality_score))) or 0
    return {"available": True, "total": total, "valid": valid, "invalid": invalid, "duplicate": duplicate, "outliers": outliers, "average_quality_score": round(score, 1), "checks": ["required route / airline / date", "INR currency", "positive and internally consistent core fare", "duplicate payload hash", "IQR and MAD outlier flagging"], "note": "Outliers are retained for review. Sold-out flights are availability states, never zero-price fares."}


@router.get("/metadata")
def metadata():
    return {"routes": list(ROUTE_BASKET), "weights": ROUTE_BASKET, "lead_windows": [1, 7, 15, 30, 45], "weight_note": PROTOTYPE_WEIGHT_LABEL, "source_note": "Development / replay data — not live airline prices."}
