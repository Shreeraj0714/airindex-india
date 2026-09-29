import unittest
from datetime import date

from app.collectors.demo_collector import DemoReplayCollector, LEAD_WINDOWS
from app.index_engine.index import laspeyres_index
from app.processing.normalization import normalize_observation
from app.processing.quality import mad_outliers
from app.processing.validation import validate_observation


class CorePipelineTests(unittest.TestCase):
    def test_normalization_creates_route_and_core_total(self):
        item = normalize_observation({"origin": " del ", "destination": "bom", "airline": "Test Air", "cabin": "economy", "fare_class": "saver", "currency": "inr", "availability": "available", "base_fare": 5000, "taxes": 900, "mandatory_fees": 100, "total_fare": 0})
        self.assertEqual(item["route"], "DEL-BOM")
        self.assertEqual(item["total_fare"], 6000)

    def test_validation_rejects_zero_fare_and_invalid_currency(self):
        status, errors = validate_observation({"origin": "DEL", "destination": "BOM", "travel_date": date.today(), "airline": "Test", "currency": "USD", "base_fare": 0, "taxes": 0, "mandatory_fees": 0, "total_fare": 0})
        self.assertEqual(status, "invalid")
        self.assertIn("zero or negative fare", errors)
        self.assertIn("invalid currency", errors)

    def test_laspeyres_weighted_relative_index(self):
        value = laspeyres_index({"A": 120, "B": 100}, {"A": 100, "B": 100}, {"A": 0.6, "B": 0.4})
        self.assertAlmostEqual(value, 112)

    def test_replay_supports_required_advance_windows(self):
        sample = DemoReplayCollector().collect()
        self.assertEqual({row["advance_days"] for row in sample}, set(LEAD_WINDOWS))
        self.assertGreaterEqual(len(sample), 30 * 10 * 5)

    def test_mad_flags_extreme_value(self):
        self.assertIn(5, mad_outliers([100, 101, 99, 102, 100, 600]))


if __name__ == "__main__":
    unittest.main()
