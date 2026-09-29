from datetime import date, datetime, timedelta
from hashlib import sha256
from math import sin
from random import Random

from .base import BaseCollector
from ..processing.normalization import normalize_observation
from ..processing.validation import validate_observation

ROUTE_BASKET = {
    "DEL-BOM": 0.16, "DEL-BLR": 0.14, "BOM-BLR": 0.11, "DEL-CCU": 0.10,
    "BLR-HYD": 0.09, "MAA-DEL": 0.09, "DEL-HYD": 0.09, "BOM-DEL": 0.08,
    "BOM-GOI": 0.07, "DEL-GOI": 0.07,
}
ROUTE_BASE = {"DEL-BOM": 6200, "DEL-BLR": 7100, "BOM-BLR": 5900, "DEL-CCU": 6700, "BLR-HYD": 4400, "MAA-DEL": 6500, "DEL-HYD": 5000, "BOM-DEL": 6100, "BOM-GOI": 4200, "DEL-GOI": 7200}
AIRLINES = [("IndiGo", 0.94), ("Air India", 1.02), ("Akasa Air", 0.90), ("SpiceJet", 0.88)]
LEAD_WINDOWS = [1, 7, 15, 30, 45]


class DemoReplayCollector(BaseCollector):
    """Deterministic development/replay generator, never a claim of live prices."""
    def collect(self) -> list[dict]:
        rng = Random(26056)
        start = date.today() - timedelta(days=44)
        rows: list[dict] = []
        for offset in range(45):
            observed = start + timedelta(days=offset)
            weekly = 1 + 0.045 * sin(offset / 3.5)
            for route, base in ROUTE_BASE.items():
                origin, destination = route.split("-")
                weekend = 1.11 if observed.weekday() in (4, 5, 6) else 1.0
                route_pressure = 1 + (0.0019 * offset if route in {"DEL-BOM", "DEL-BLR", "BOM-GOI"} else 0.0006 * offset)
                for lead in LEAD_WINDOWS:
                    lead_factor = {1: 1.55, 7: 1.27, 15: 1.12, 30: 1.0, 45: 0.96}[lead]
                    for airline_index, (airline, airline_factor) in enumerate(AIRLINES[:3]):
                        available = "SOLD_OUT" if rng.random() < (0.025 + (0.045 if lead == 1 else 0)) else "AVAILABLE"
                        noise = 1 + rng.uniform(-0.065, 0.075)
                        shock = 1.20 if route == "DEL-BOM" and offset in (38, 39, 40) and lead in (1, 7) else 1.0
                        total = base * airline_factor * lead_factor * weekly * weekend * route_pressure * noise * shock
                        # Small number of high but preserved market observations.
                        if rng.random() < 0.003:
                            total *= 1.55
                        base_fare = total * 0.78
                        taxes = total * 0.17
                        fees = total - base_fare - taxes
                        key = f"{route}|{airline}|{observed}|{lead}|{airline_index}"
                        rows.append({
                            "collection_timestamp": datetime.combine(observed, datetime.min.time()) + timedelta(hours=9 + airline_index),
                            "origin": origin, "destination": destination, "airline": airline, "flight_number": f"{['6E','AI','QP'][airline_index]}{100 + (offset % 80)}",
                            "travel_date": observed + timedelta(days=lead), "advance_days": lead, "cabin": "ECONOMY", "fare_class": "SAVER",
                            "base_fare": base_fare, "taxes": taxes, "mandatory_fees": fees, "total_fare": total,
                            "availability": available, "source": "Development / replay data", "currency": "INR",
                            "departure_time": ["07:15", "12:40", "18:20"][airline_index], "arrival_time": None,
                            "duration": 125, "stops": 0, "refundable": False, "baggage": "15 kg",
                            "raw_payload_hash": sha256(key.encode()).hexdigest(),
                        })
        return rows

    def validate(self, item: dict) -> tuple[str, list[str]]:
        return validate_observation(item)

    def normalize(self, item: dict) -> dict:
        return normalize_observation(item)
