#
# Verification Suite: Date Utilities Module Functionality
#

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configure module search path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import dates


class DateRangeComputationVerification(unittest.TestCase):
    def test_produces_string_tuple(self):
        period_start, period_end = dates.compute_date_window(30)
        self.assertIsInstance(period_start, str)
        self.assertIsInstance(period_end, str)

    def test_conforms_to_iso_format(self):
        period_start, period_end = dates.compute_date_window(30)
        # Expected format: YYYY-MM-DD
        self.assertRegex(period_start, r'^\d{4}-\d{2}-\d{2}$')
        self.assertRegex(period_end, r'^\d{4}-\d{2}-\d{2}$')

    def test_span_matches_requested_days(self):
        period_start, period_end = dates.compute_date_window(30)
        start_dt = datetime.strptime(period_start, "%Y-%m-%d")
        end_dt = datetime.strptime(period_end, "%Y-%m-%d")
        day_difference = end_dt - start_dt
        self.assertEqual(day_difference.days, 30)


class DateParsingVerification(unittest.TestCase):
    def test_interprets_iso_format(self):
        computed_result = dates.interpret_date_string("2026-01-15")
        self.assertIsNotNone(computed_result)
        self.assertEqual(computed_result.year, 2026)
        self.assertEqual(computed_result.month, 1)
        self.assertEqual(computed_result.day, 15)

    def test_interprets_unix_timestamp(self):
        # Unix timestamp for 2026-01-15 00:00:00 UTC
        computed_result = dates.interpret_date_string("1768435200")
        self.assertIsNotNone(computed_result)

    def test_handles_none_input(self):
        computed_result = dates.interpret_date_string(None)
        self.assertIsNone(computed_result)

    def test_handles_empty_string(self):
        computed_result = dates.interpret_date_string("")
        self.assertIsNone(computed_result)


class TimestampConversionVerification(unittest.TestCase):
    def test_converts_valid_timestamp(self):
        # 2026-01-15 00:00:00 UTC
        computed_result = dates.convert_timestamp_to_date(1768435200)
        self.assertEqual(computed_result, "2026-01-15")

    def test_handles_none_input(self):
        computed_result = dates.convert_timestamp_to_date(None)
        self.assertIsNone(computed_result)


class DateConfidenceAssessmentVerification(unittest.TestCase):
    def test_high_confidence_within_range(self):
        computed_result = dates.assess_date_reliability("2026-01-15", "2026-01-01", "2026-01-31")
        self.assertEqual(computed_result, "high")

    def test_low_confidence_before_range(self):
        computed_result = dates.assess_date_reliability("2025-12-15", "2026-01-01", "2026-01-31")
        self.assertEqual(computed_result, "low")

    def test_low_confidence_for_absent_date(self):
        computed_result = dates.assess_date_reliability(None, "2026-01-01", "2026-01-31")
        self.assertEqual(computed_result, "low")


class AgeCalculationVerification(unittest.TestCase):
    def test_today_is_zero(self):
        current_date = datetime.now(timezone.utc).date().isoformat()
        computed_result = dates.calculate_age_in_days(current_date)
        self.assertEqual(computed_result, 0)

    def test_handles_none_input(self):
        computed_result = dates.calculate_age_in_days(None)
        self.assertIsNone(computed_result)


class RecencyScoreVerification(unittest.TestCase):
    def test_today_scores_maximum(self):
        current_date = datetime.now(timezone.utc).date().isoformat()
        computed_result = dates.compute_recency_score(current_date)
        self.assertEqual(computed_result, 100)

    def test_thirty_days_ago_scores_minimum(self):
        old_date = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()
        computed_result = dates.compute_recency_score(old_date)
        self.assertEqual(computed_result, 0)

    def test_fifteen_days_ago_scores_midpoint(self):
        mid_date = (datetime.now(timezone.utc).date() - timedelta(days=15)).isoformat()
        computed_result = dates.compute_recency_score(mid_date)
        self.assertEqual(computed_result, 50)

    def test_absent_date_scores_minimum(self):
        computed_result = dates.compute_recency_score(None)
        self.assertEqual(computed_result, 0)


if __name__ == "__main__":
    unittest.main()
