from collections import defaultdict
from statistics import median

from sqlalchemy.orm import Session

from ..index_engine.index import valid_available


def market_shocks(db: Session) -> list[dict]:
    rows = valid_available(db)
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row.route][row.collection_timestamp.date()].append(row.total_fare)
    feed = []
    for route, days in grouped.items():
        ordered = sorted(days)
        if len(ordered) < 8:
            continue
        latest = ordered[-1]
        current = median(days[latest])
        baseline_days = ordered[-15:-1]
        reference = median([value for d in baseline_days for value in days[d]])
        change = (current / reference - 1) * 100 if reference else 0
        historical_changes = []
        for position in range(7, len(ordered)):
            today = median(days[ordered[position]])
            prior = median([v for d in ordered[max(0, position-7):position] for v in days[d]])
            if prior:
                historical_changes.append(abs((today / prior - 1) * 100))
        threshold = max(7.5, median(historical_changes) * 2.5) if historical_changes else 7.5
        severity = "SHOCK" if abs(change) >= max(15, threshold * 1.6) else "ELEVATED" if abs(change) >= threshold else "NORMAL"
        feed.append({"route": route, "current_fare": round(current, 2), "historical_reference": round(reference, 2), "change_pct": round(change, 2), "severity": severity, "timestamp": latest.isoformat(), "threshold_pct": round(threshold, 2)})
    return sorted(feed, key=lambda item: abs(item["change_pct"]), reverse=True)
