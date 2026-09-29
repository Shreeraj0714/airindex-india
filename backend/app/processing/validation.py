from datetime import date


VALID_CURRENCIES = {"INR"}


def validate_observation(item: dict) -> tuple[str, list[str]]:
    errors = []
    if not item.get("origin") or not item.get("destination") or item.get("origin") == item.get("destination"):
        errors.append("missing or invalid route")
    if not isinstance(item.get("travel_date"), date):
        errors.append("invalid travel date")
    if not item.get("airline"):
        errors.append("missing airline")
    if item.get("currency") not in VALID_CURRENCIES:
        errors.append("invalid currency")
    fare = item.get("total_fare", 0)
    if fare <= 0:
        errors.append("zero or negative fare")
    if fare > 150000:
        errors.append("unreasonable fare value")
    expected = round(item.get("base_fare", 0) + item.get("taxes", 0) + item.get("mandatory_fees", 0), 2)
    if abs(expected - fare) > 1:
        errors.append("inconsistent total fare")
    return ("valid" if not errors else "invalid", errors)
