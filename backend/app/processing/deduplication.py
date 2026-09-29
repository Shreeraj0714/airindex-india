def duplicate_key(item: dict) -> str:
    return "|".join(str(item.get(k, "")) for k in ("route", "airline", "travel_date", "advance_days", "total_fare", "flight_number"))
