"""Tests for cron expression parser."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Ensure library modules are discoverable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.cron_parse import (
    cron_to_schtasks_args,
    describe_schedule,
    next_occurrence,
    parse_cron_expression,
)


class TestParseCronExpression:
    """Tests for parse_cron_expression()."""

    def test_daily_at_six(self):
        result = parse_cron_expression("0 6 * * *")
        assert result["minute"] == [0]
        assert result["hour"] == [6]
        assert result["day_of_month"] == "*"
        assert result["month"] == "*"
        assert result["day_of_week"] == "*"

    def test_specific_weekdays(self):
        result = parse_cron_expression("30 8 * * 1,3,5")
        assert result["minute"] == [30]
        assert result["hour"] == [8]
        assert result["day_of_week"] == [1, 3, 5]

    def test_named_weekdays(self):
        result = parse_cron_expression("0 9 * * MON,WED,FRI")
        assert result["day_of_week"] == [1, 3, 5]

    def test_day_of_month(self):
        result = parse_cron_expression("0 12 1 * *")
        assert result["day_of_month"] == [1]

    def test_sunday_normalization(self):
        """Both 0 and 7 should map to Sunday (0)."""
        result = parse_cron_expression("0 6 * * 7")
        assert result["day_of_week"] == [0]

    def test_range_in_dow(self):
        result = parse_cron_expression("0 6 * * 1-5")
        assert result["day_of_week"] == [1, 2, 3, 4, 5]

    def test_wrong_field_count(self):
        with pytest.raises(ValueError, match="exactly 5 fields"):
            parse_cron_expression("0 6 * *")

    def test_step_values_rejected(self):
        with pytest.raises(ValueError, match="Step values"):
            parse_cron_expression("*/15 6 * * *")

    def test_wildcard_minute_rejected(self):
        with pytest.raises(ValueError, match="every minute"):
            parse_cron_expression("* 6 * * *")

    def test_wildcard_hour_accepted(self):
        result = parse_cron_expression("0 * * * *")
        assert result["hour"] == "*"
        assert result["minute"] == [0]

    def test_out_of_range_minute(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_cron_expression("60 6 * * *")

    def test_out_of_range_hour(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_cron_expression("0 25 * * *")

    def test_multiple_minutes_rejected(self):
        with pytest.raises(ValueError, match="Multiple minute"):
            parse_cron_expression("0,30 6 * * *")

    def test_multiple_hours_rejected(self):
        with pytest.raises(ValueError, match="Multiple hour"):
            parse_cron_expression("0 6,12 * * *")


class TestDescribeSchedule:
    """Tests for describe_schedule()."""

    def test_daily(self):
        parsed = parse_cron_expression("0 6 * * *")
        assert describe_schedule(parsed) == "Daily at 06:00"

    def test_weekdays(self):
        parsed = parse_cron_expression("0 8 * * 1-5")
        assert describe_schedule(parsed) == "Weekdays at 08:00"

    def test_weekends(self):
        parsed = parse_cron_expression("0 10 * * 0,6")
        assert describe_schedule(parsed) == "Weekends at 10:00"

    def test_specific_days(self):
        parsed = parse_cron_expression("30 8 * * 1,3,5")
        assert describe_schedule(parsed) == "MON, WED, FRI at 08:30"

    def test_monthly(self):
        parsed = parse_cron_expression("0 9 1 * *")
        assert describe_schedule(parsed) == "1st of every month at 09:00"

    def test_monthly_15th(self):
        parsed = parse_cron_expression("0 9 15 * *")
        assert describe_schedule(parsed) == "15th of every month at 09:00"

    def test_all_dow_is_daily(self):
        parsed = parse_cron_expression("0 6 * * 0,1,2,3,4,5,6")
        assert describe_schedule(parsed) == "Daily at 06:00"


class TestCronToSchtasksArgs:
    """Tests for cron_to_schtasks_args()."""

    def test_daily(self):
        parsed = parse_cron_expression("0 6 * * *")
        args = cron_to_schtasks_args(parsed)
        assert args == ["/SC", "DAILY", "/ST", "06:00"]

    def test_weekly(self):
        parsed = parse_cron_expression("30 8 * * 1,3,5")
        args = cron_to_schtasks_args(parsed)
        assert args == ["/SC", "WEEKLY", "/D", "MON,WED,FRI", "/ST", "08:30"]

    def test_monthly(self):
        parsed = parse_cron_expression("0 12 1 * *")
        args = cron_to_schtasks_args(parsed)
        assert args == ["/SC", "MONTHLY", "/D", "1", "/ST", "12:00"]

    def test_all_dow_becomes_daily(self):
        parsed = parse_cron_expression("0 6 * * 0,1,2,3,4,5,6")
        args = cron_to_schtasks_args(parsed)
        assert args == ["/SC", "DAILY", "/ST", "06:00"]

    def test_specific_month_rejected(self):
        parsed = parse_cron_expression("0 6 * * *")
        parsed["month"] = [1, 6]  # Force specific months
        with pytest.raises(ValueError, match="month restrictions"):
            cron_to_schtasks_args(parsed)


class TestNextOccurrence:
    """Tests for next_occurrence()."""

    def test_daily_future_today(self):
        parsed = parse_cron_expression("0 23 * * *")
        after = datetime(2025, 6, 15, 8, 0, 0)
        result = next_occurrence(parsed, after)
        assert result == datetime(2025, 6, 15, 23, 0, 0)

    def test_daily_past_today_goes_tomorrow(self):
        parsed = parse_cron_expression("0 6 * * *")
        after = datetime(2025, 6, 15, 12, 0, 0)
        result = next_occurrence(parsed, after)
        assert result == datetime(2025, 6, 16, 6, 0, 0)

    def test_weekday_skips_weekend(self):
        parsed = parse_cron_expression("0 9 * * 1-5")
        # Saturday June 14, 2025
        after = datetime(2025, 6, 14, 10, 0, 0)
        result = next_occurrence(parsed, after)
        # Should be Monday June 16
        assert result.weekday() == 0  # Monday
        assert result.day == 16

    def test_monthly_first(self):
        parsed = parse_cron_expression("0 9 1 * *")
        after = datetime(2025, 6, 5, 10, 0, 0)
        result = next_occurrence(parsed, after)
        assert result.day == 1
        assert result.month == 7
