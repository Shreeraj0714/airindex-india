from collections import defaultdict
from datetime import date
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AirfareObservation
from .weights import route_weights


def valid_available(db: Session) -> list[AirfareObservation]:
    return list(db.scalars(select(AirfareObservation).where(
        AirfareObservation.validation_status == "valid",
        AirfareObservation.availability == "AVAILABLE",
    )))


def _bucket(day: date, period: str) -> str:
    if period == "weekly":
        iso = day.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if period == "monthly":
        return day.strftime("%Y-%m")
    return day.isoformat()


def _daily_route_prices(rows: list[AirfareObservation]) -> dict[date, dict[str, float]]:
    grouped: dict[date, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row.collection_timestamp.date()][row.route].append(row.total_fare)
    return {day: {route: mean(prices) for route, prices in routes.items()} for day, routes in grouped.items()}


def baseline_prices(rows: list[AirfareObservation]) -> dict[str, float]:
    daily = _daily_route_prices(rows)
    base_days = sorted(daily)[:5]
    result: dict[str, list[float]] = defaultdict(list)
    for day in base_days:
        for route, fare in daily[day].items():
            result[route].append(fare)
    return {route: mean(fares) for route, fares in result.items()}


def laspeyres_index(current: dict[str, float], base: dict[str, float], weights: dict[str, float]) -> float | None:
    """Return base-100 weighted relative-price index for covered basket items."""
    covered = [(route, weight) for route, weight in weights.items() if route in current and route in base and base[route] > 0]
    weight_total = sum(weight for _, weight in covered)
    if not weight_total:
        return None
    return 100 * sum(weight * current[route] / base[route] for route, weight in covered) / weight_total


def index_series(db: Session, period: str = "daily") -> list[dict]:
    rows = valid_available(db)
    if not rows:
        return []
    daily = _daily_route_prices(rows)
    base = baseline_prices(rows)
    weights = route_weights()
    daily_values = []
    for day in sorted(daily):
        value = laspeyres_index(daily[day], base, weights)
        if value is None:
            continue
        daily_values.append({"date": day.isoformat(), "index": round(value, 2)})
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in daily_values:
        grouped[_bucket(date.fromisoformat(row["date"]), period)].append(row["index"])
    return [{"date": period_key, "index": round(mean(values), 2)} for period_key, values in sorted(grouped.items())]


def latest_route_indices(db: Session) -> list[dict]:
    rows = valid_available(db)
    if not rows:
        return []
    daily = _daily_route_prices(rows)
    latest_day = max(daily)
    base = baseline_prices(rows)
    weights = route_weights()
    result = []
    for route, weight in weights.items():
        if route in daily[latest_day] and route in base:
            route_index = 100 * daily[latest_day][route] / base[route]
            result.append({"route": route, "index": round(route_index, 2), "current_fare": round(daily[latest_day][route], 2), "base_fare": round(base[route], 2), "weight": weight})
    return sorted(result, key=lambda item: item["route"])


def contributions(db: Session) -> list[dict]:
    result = []
    for item in latest_route_indices(db):
        points = item["weight"] * (item["index"] - 100)
        result.append({**item, "contribution_points": round(points, 2)})
    return sorted(result, key=lambda item: abs(item["contribution_points"]), reverse=True)
