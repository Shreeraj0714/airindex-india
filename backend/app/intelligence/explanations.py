from collections import defaultdict
from statistics import median

from sqlalchemy.orm import Session

from ..index_engine.index import valid_available


def explain_route(db: Session, route: str | None = None) -> dict:
    rows = valid_available(db)
    if not rows:
        return {"route": route, "message": "Insufficient evidence to determine the primary driver.", "evidence": []}
    latest_day = max(row.collection_timestamp.date() for row in rows)
    target = route or "DEL-BOM"
    route_rows = [row for row in rows if row.route == target]
    latest = [row for row in route_rows if row.collection_timestamp.date() == latest_day]
    historical = [row for row in route_rows if row.collection_timestamp.date() < latest_day]
    if not latest or len(historical) < 20:
        return {"route": target, "message": "Insufficient evidence to determine the primary driver.", "evidence": []}
    current = median([r.total_fare for r in latest])
    baseline = median([r.total_fare for r in historical[-120:]])
    pct = (current / baseline - 1) * 100
    by_lead = defaultdict(list)
    historical_lead = defaultdict(list)
    for row in latest: by_lead[row.advance_days].append(row.total_fare)
    for row in historical: historical_lead[row.advance_days].append(row.total_fare)
    pressured = [f"T+{lead}" for lead, fares in by_lead.items() if median(fares) > median(historical_lead[lead]) * 1.06]
    sold_out = sum(1 for row in db.query(type(route_rows[0])).filter_by(route=target).all() if row.availability == "SOLD_OUT")
    if abs(pct) < 2:
        message = f"{target} fares are broadly stable versus the recent baseline. No primary driver is supported by the replay observations."
    elif pressured:
        direction = "increased" if pct > 0 else "decreased"
        message = f"{target} fares {direction} {abs(pct):.1f}% versus the recent baseline. The movement is concentrated in {', '.join(pressured)}, while longer lead-time observations are comparatively steadier. This indicates lead-time-specific market pressure in the replay data."
    else:
        message = "Insufficient evidence to determine the primary driver. The observed route movement is not concentrated in a measurable lead-time pattern."
    return {"route": target, "message": message, "evidence": [{"metric": "latest median fare", "value": round(current, 2)}, {"metric": "recent baseline", "value": round(baseline, 2)}, {"metric": "change", "value": round(pct, 2)}, {"metric": "sold-out replay observations", "value": sold_out}]}
