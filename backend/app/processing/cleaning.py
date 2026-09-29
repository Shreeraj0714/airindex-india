def clean_text(value: str | None) -> str | None:
    return value.strip().upper() if value else value


def clean_currency(value: float) -> float:
    return round(max(float(value), 0), 2)
