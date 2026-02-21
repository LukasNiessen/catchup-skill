"""Tests for scheduling modules (briefbot_engine.scheduling.cron and .jobs)."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from briefbot_engine.scheduling.cron import (
    parse_cron_expression,
    describe_schedule,
    cron_to_schtasks_args,
    next_occurrence,
)
from briefbot_engine.scheduling.jobs import (
    create_job,
    list_jobs,
    get_job,
    delete_job,
    update_job_run_status,
)


# ===========================================================================
# Cron parsing: parse_cron_expression()
# ===========================================================================

def test_parse_daily_6am():
    parsed = parse_cron_expression("0 6 * * *")
    assert parsed["minute"] == [0]
    assert parsed["hour"] == [6]
    assert parsed["day_of_month"] == "*"
    assert parsed["month"] == "*"
    assert parsed["day_of_week"] == "*"


def test_parse_named_weekdays():
    parsed = parse_cron_expression("0 9 * * MON,WED,FRI")
    assert 1 in parsed["day_of_week"]  # MON
    assert 3 in parsed["day_of_week"]  # WED
    assert 5 in parsed["day_of_week"]  # FRI


def test_parse_ranges():
    parsed = parse_cron_expression("0 8 * * 1-5")
    assert parsed["day_of_week"] == [1, 2, 3, 4, 5]


def test_parse_invalid_raises_valueerror():
    with pytest.raises(ValueError):
        parse_cron_expression("not a cron")


def test_parse_too_few_fields_raises_valueerror():
    with pytest.raises(ValueError):
        parse_cron_expression("0 6 *")


# ===========================================================================
# describe_schedule()
# ===========================================================================

def test_describe_daily():
    parsed = parse_cron_expression("0 6 * * *")
    desc = describe_schedule(parsed)
    assert "Daily" in desc
    assert "06:00" in desc


def test_describe_weekdays():
    parsed = parse_cron_expression("30 8 * * 1-5")
    desc = describe_schedule(parsed)
    assert "Weekdays" in desc
    assert "08:30" in desc


def test_describe_weekends():
    parsed = parse_cron_expression("0 10 * * 0,6")
    desc = describe_schedule(parsed)
    assert "Weekends" in desc
    assert "10:00" in desc


def test_describe_specific_days():
    parsed = parse_cron_expression("0 9 * * MON,FRI")
    desc = describe_schedule(parsed)
    assert "MON" in desc
    assert "FRI" in desc
    assert "09:00" in desc


def test_describe_monthly():
    parsed = parse_cron_expression("0 9 1 * *")
    desc = describe_schedule(parsed)
    assert "month" in desc.lower()
    assert "09:00" in desc


# ===========================================================================
# cron_to_schtasks_args()
# ===========================================================================

def test_schtasks_daily():
    parsed = parse_cron_expression("0 6 * * *")
    args = cron_to_schtasks_args(parsed)
    assert "/SC" in args
    assert "DAILY" in args
    assert "06:00" in args


def test_schtasks_weekly():
    parsed = parse_cron_expression("0 8 * * MON,WED,FRI")
    args = cron_to_schtasks_args(parsed)
    assert "WEEKLY" in args
    assert "/D" in args
    # MON, WED, FRI should appear in the day list
    day_index = args.index("/D") + 1
    day_str = args[day_index]
    assert "MON" in day_str
    assert "WED" in day_str
    assert "FRI" in day_str


def test_schtasks_monthly():
    parsed = parse_cron_expression("0 9 15 * *")
    args = cron_to_schtasks_args(parsed)
    assert "MONTHLY" in args
    assert "/D" in args
    day_index = args.index("/D") + 1
    assert "15" in args[day_index]


# ===========================================================================
# next_occurrence()
# ===========================================================================

def test_next_occurrence_future_today():
    # Use a reference time of 05:00; schedule is 06:00 daily => should fire same day
    ref = datetime(2026, 2, 18, 5, 0, 0)
    parsed = parse_cron_expression("0 6 * * *")
    nxt = next_occurrence(parsed, after=ref)
    assert nxt.hour == 6
    assert nxt.minute == 0
    assert nxt.day == 18  # same day


def test_next_occurrence_past_today_goes_tomorrow():
    # Reference time is 07:00; schedule is 06:00 daily => should fire next day
    ref = datetime(2026, 2, 18, 7, 0, 0)
    parsed = parse_cron_expression("0 6 * * *")
    nxt = next_occurrence(parsed, after=ref)
    assert nxt.hour == 6
    assert nxt.minute == 0
    assert nxt.day == 19  # next day


def test_next_occurrence_weekday_skips_weekend():
    # Friday 2026-02-20, 7am. Weekday-only schedule at 06:00 => should skip to Monday
    ref = datetime(2026, 2, 20, 7, 0, 0)  # Friday
    parsed = parse_cron_expression("0 6 * * 1-5")
    nxt = next_occurrence(parsed, after=ref)
    assert nxt.weekday() == 0  # Monday
    assert nxt.hour == 6


# ===========================================================================
# Jobs CRUD (uses tmp_path fixture)
# ===========================================================================

def test_create_job_has_required_fields(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    job = create_job(
        topic="AI news",
        schedule="0 6 * * *",
        email="test@example.com",
        args_dict={"sampling": "lite"},
        filepath=jobs_file,
    )
    assert "id" in job
    assert job["topic"] == "AI news"
    assert job["schedule"] == "0 6 * * *"
    assert job["email"] == "test@example.com"
    assert job["run_count"] == 0


def test_list_jobs_returns_created(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    create_job("Topic A", "0 6 * * *", "a@test.com", {}, filepath=jobs_file)
    create_job("Topic B", "0 7 * * *", "b@test.com", {}, filepath=jobs_file)
    jobs = list_jobs(filepath=jobs_file)
    assert len(jobs) == 2


def test_get_job_returns_matching(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    created = create_job("Topic", "0 6 * * *", "x@test.com", {}, filepath=jobs_file)
    found = get_job(created["id"], filepath=jobs_file)
    assert found is not None
    assert found["id"] == created["id"]


def test_get_job_returns_none_for_missing(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    found = get_job("nonexistent_id", filepath=jobs_file)
    assert found is None


def test_delete_job_removes_it(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    created = create_job("Topic", "0 6 * * *", "x@test.com", {}, filepath=jobs_file)
    result = delete_job(created["id"], filepath=jobs_file)
    assert result is True
    assert get_job(created["id"], filepath=jobs_file) is None


def test_delete_job_returns_false_for_missing(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    result = delete_job("nonexistent_id", filepath=jobs_file)
    assert result is False


def test_update_job_run_status_increments_count(tmp_path):
    jobs_file = tmp_path / "jobs.json"
    created = create_job("Topic", "0 6 * * *", "x@test.com", {}, filepath=jobs_file)
    job_id = created["id"]

    update_job_run_status(job_id, "success", filepath=jobs_file)
    job = get_job(job_id, filepath=jobs_file)
    assert job["run_count"] == 1
    assert job["last_status"] == "success"

    update_job_run_status(job_id, "error", error="timeout", filepath=jobs_file)
    job = get_job(job_id, filepath=jobs_file)
    assert job["run_count"] == 2
    assert job["last_status"] == "error"
    assert job["last_error"] == "timeout"
