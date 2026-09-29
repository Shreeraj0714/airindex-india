from statistics import median
from sqlalchemy.orm import Session
from ..index_engine.index import valid_available


def travel_recommendation(db: Session, route: str, advance_days: int, current_fare: float | None) -> dict:
    rows = valid_available(db)
    selected = [row for row in rows if row.route == route]
    if not selected:
        return {"recommendation": "MONITOR", "message": "Insufficient replay observations for this route.", "evidence": []}
    nearest = min({row.advance_days for row in selected}, key=lambda lead: abs(lead - advance_days))
    relevant = [row for row in selected if row.advance_days == nearest]
    current = current_fare or median([row.total_fare for row in relevant[-20:]])
    recent_median = median([row.total_fare for row in relevant[-60:]])
    latest_date = max(row.collection_timestamp.date() for row in selected)
    total_latest = [row for row in db.query(type(selected[0])).filter_by(route=route).all() if row.collection_timestamp.date() == latest_date]
    availability = sum(row.availability == "AVAILABLE" for row in total_latest) / len(total_latest) if total_latest else 1
    ratio = current / recent_median
    if ratio <= 0.95 or (ratio <= 1.03 and availability < 0.82):
        recommendation = "FAVOUR BOOKING"
        message = "Favour booking because the current fare is at or below the recent comparable lead-time median, with availability monitored as a supporting signal."
    elif ratio >= 1.12 and availability > 0.88:
        recommendation = "FAVOUR WAITING"
        message = "Favour waiting because the current fare is materially above the recent comparable lead-time median while replay availability remains broad."
    else:
        recommendation = "MONITOR"
        message = "Monitor: the current fare is close to its comparable historical range or evidence is mixed."
    return {"recommendation": recommendation, "message": message, "evidence": [{"metric": "current fare", "value": round(current, 2)}, {"metric": f"T+{nearest} median", "value": round(recent_median, 2)}, {"metric": "latest availability rate", "value": round(availability * 100, 1)}], "disclaimer": "Decision support only, not a price guarantee. Based on development / replay data."}
