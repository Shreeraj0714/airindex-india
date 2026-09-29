from .cleaning import clean_currency, clean_text


def normalize_observation(item: dict) -> dict:
    normalized = dict(item)
    for key in ("origin", "destination", "airline", "cabin", "fare_class", "currency", "availability"):
        normalized[key] = clean_text(normalized.get(key))
    normalized["route"] = f"{normalized['origin']}-{normalized['destination']}"
    for key in ("base_fare", "taxes", "mandatory_fees", "total_fare"):
        normalized[key] = clean_currency(normalized[key])
    normalized["total_fare"] = round(normalized["base_fare"] + normalized["taxes"] + normalized["mandatory_fees"], 2)
    return normalized
