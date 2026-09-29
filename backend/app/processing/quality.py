from statistics import median


def mad_outliers(values: list[float], threshold: float = 5.0) -> set[int]:
    """Robust MAD detector; flags values without removing valid high fares."""
    if len(values) < 5:
        return set()
    middle = median(values)
    mad = median([abs(v - middle) for v in values])
    if mad == 0:
        return set()
    return {i for i, value in enumerate(values) if abs(0.6745 * (value - middle) / mad) > threshold}


def iqr_outliers(values: list[float], multiplier: float = 2.0) -> set[int]:
    if len(values) < 8:
        return set()
    ordered = sorted(values)
    q1 = ordered[len(ordered) // 4]
    q3 = ordered[(len(ordered) * 3) // 4]
    spread = q3 - q1
    if spread == 0:
        return set()
    return {i for i, value in enumerate(values) if value < q1 - multiplier * spread or value > q3 + multiplier * spread}


def quality_score(status: str, outlier: bool) -> float:
    if status == "invalid":
        return 0.0
    return 75.0 if outlier else 100.0
