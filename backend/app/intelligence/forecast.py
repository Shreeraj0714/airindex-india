from sqlalchemy.orm import Session
from ..index_engine.index import index_series


def national_forecast(db: Session) -> dict:
    series = index_series(db)
    if len(series) < 7:
        return {"available": False, "message": "Forecast unavailable: seed at least seven days of valid observations."}
    values = [point["index"] for point in series[-14:]]
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    trend = sum(changes) / len(changes)
    expected = values[-1] + trend * 7
    pct = (expected / values[-1] - 1) * 100
    mae = sum(abs(c) for c in changes) / len(changes)
    return {"available": True, "model": "7-day linear trend baseline", "current_index": round(values[-1], 2), "forecast_index": round(expected, 2), "expected_change_pct": round(pct, 2), "direction": "INCREASE" if pct > 0.2 else "DECREASE" if pct < -0.2 else "STABLE", "confidence": "Moderate" if mae < 1.5 else "Low", "model_error_mae": round(mae, 2), "uncertainty_band": round(mae * 2, 2), "message": "Explainable baseline forecast; it is not a guarantee."}
