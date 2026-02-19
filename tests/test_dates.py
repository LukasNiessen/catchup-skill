import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import dates


class TestDateWindow(unittest.TestCase):
    def test_produces_string_tuple(self):
        result = dates.date_window(30)
        period_start, period_end = result
        self.assertIsInstance(period_start, str)
        self.assertIsInstance(period_end, str)

    def test_conforms_to_iso_format(self):
        period_start, period_end = dates.date_window(30)
        # Expected format: YYYY-MM-DD
        self.assertRegex(period_start, r'^\d{4}-\d{2}-\d{2}$')
        self.assertRegex(period_end, r'^\d{4}-\d{2}-\d{2}$')

    def test_span_matches_requested_days(self):
        period_start, period_end = dates.date_window(30)
        start_dt = datetime.strptime(period_start, "%Y-%m-%d")
        end_dt = datetime.strptime(period_end, "%Y-%m-%d")
        day_difference = end_dt - start_dt
        self.assertEqual(day_difference.days, 30)


class DateParsingGroup(unittest.TestCase):
    def test_interprets_iso_format(self):
        result = dates.parse_date("2026-01-15")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_interprets_unix_timestamp(self):
        # Unix timestamp for 2026-01-15 00:00:00 UTC
        result = dates.parse_date("1768435200")
        self.assertIsNotNone(result)

    def test_handles_none_input(self):
        result = dates.parse_date(None)
        self.assertIsNone(result)

    def test_handles_empty_string(self):
        result = dates.parse_date("")
        self.assertIsNone(result)


# --- Standalone pytest functions for timestamp conversion ---

def test_converts_valid_timestamp():
    # 2026-01-15 00:00:00 UTC
    result = dates.timestamp_to_date(1768435200)
    assert result == "2026-01-15"


def test_timestamp_handles_none_input():
    result = dates.timestamp_to_date(None)
    assert result is None


# --- Standalone pytest functions for date confidence ---

def test_high_confidence_within_range():
    result = dates.date_confidence("2026-01-15", "2026-01-01", "2026-01-31")
    assert result == "high"


def test_low_confidence_before_range():
    result = dates.date_confidence("2025-12-15", "2026-01-01", "2026-01-31")
    assert result == "low"


def test_low_confidence_for_absent_date():
    result = dates.date_confidence(None, "2026-01-01", "2026-01-31")
    assert result == "low"


class TestAgeCalculation(unittest.TestCase):
    def test_today_is_zero(self):
        current_date = datetime.now(timezone.utc).date().isoformat()
        result = dates.days_ago(current_date)
        self.assertEqual(result, 0)

    def test_handles_none_input(self):
        result = dates.days_ago(None)
        self.assertIsNone(result)


# --- Standalone pytest functions for recency score ---

def test_today_scores_maximum():
    current_date = datetime.now(timezone.utc).date().isoformat()
    result = dates.recency_score(current_date)
    assert result == 100


def test_thirty_days_ago_scores_minimum():
    old_date = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()
    result = dates.recency_score(old_date)
    assert result == 0


def test_fifteen_days_ago_scores_midpoint():
    mid_date = (datetime.now(timezone.utc).date() - timedelta(days=15)).isoformat()
    result = dates.recency_score(mid_date)
    assert result == 50


def test_absent_date_scores_minimum():
    result = dates.recency_score(None)
    assert result == 0


if __name__ == "__main__":
    unittest.main()
