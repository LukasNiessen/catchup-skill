"""Tests for briefbot_engine.timeframe -- date windowing, parsing, freshness, extraction."""

from datetime import datetime, timedelta, timezone

from briefbot_engine.timeframe import (
    CONFIDENCE_SOLID,
    CONFIDENCE_SOFT,
    CONFIDENCE_WEAK,
    date_confidence,
    days_since,
    detect_date,
    parse_moment,
    recency_score,
    scan_text_date,
    scan_url_date,
    span,
    to_iso_date,
)


# ---------------------------------------------------------------------------
# span()
# ---------------------------------------------------------------------------

def test_span_returns_string_tuple():
    start, end = span(30)

    assert isinstance(start, str)
    assert isinstance(end, str)


def test_span_strings_are_iso_format():
    start, end = span(14)

    assert len(start) == 10
    assert start[4] == "-" and start[7] == "-"
    assert len(end) == 10
    assert end[4] == "-" and end[7] == "-"


def test_span_length_matches_requested_days():
    start, end = span(45)

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    delta = (end_dt - start_dt).days

    assert delta == 45


def test_span_end_is_today():
    _, end = span(7)

    today = datetime.now(timezone.utc).date().isoformat()
    assert end == today


# ---------------------------------------------------------------------------
# parse_moment()
# ---------------------------------------------------------------------------

def test_parse_moment_iso_date():
    result = parse_moment("2026-02-14")

    assert result is not None
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 14


def test_parse_moment_iso_datetime_with_z():
    result = parse_moment("2026-02-14T09:30:00Z")

    assert result is not None
    assert result.year == 2026
    assert result.hour == 9
    assert result.minute == 30


def test_parse_moment_unix_timestamp():
    # 2026-06-15 00:00:00 UTC = 1781481600
    result = parse_moment("1781481600")

    assert result is not None
    assert result.year == 2026
    assert result.month == 6
    assert result.day == 15


def test_parse_moment_none_returns_none():
    result = parse_moment(None)

    assert result is None


def test_parse_moment_empty_string_returns_none():
    result = parse_moment("")

    assert result is None


def test_parse_moment_natural_month_day_year():
    result = parse_moment("February 14, 2026")

    assert result is not None
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 14


# ---------------------------------------------------------------------------
# to_iso_date()
# ---------------------------------------------------------------------------

def test_to_iso_date_valid_timestamp():
    # 2026-02-14 00:00:00 UTC = 1771027200
    result = to_iso_date(1771027200)

    assert result == "2026-02-14"


def test_to_iso_date_none_returns_none():
    result = to_iso_date(None)

    assert result is None


# ---------------------------------------------------------------------------
# date_confidence()
# ---------------------------------------------------------------------------

def test_date_confidence_solid_within_range():
    result = date_confidence("2026-02-10", "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_SOLID


def test_date_confidence_soft_near_range():
    result = date_confidence("2026-02-22", "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_SOFT


def test_date_confidence_weak_before_range():
    result = date_confidence("2025-11-30", "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_WEAK


def test_date_confidence_weak_after_range():
    result = date_confidence("2026-04-01", "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_WEAK


def test_date_confidence_weak_for_none():
    result = date_confidence(None, "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_WEAK


def test_date_confidence_solid_at_boundaries():
    assert date_confidence("2026-01-20", "2026-01-20", "2026-02-19") == CONFIDENCE_SOLID
    assert date_confidence("2026-02-19", "2026-01-20", "2026-02-19") == CONFIDENCE_SOLID


# ---------------------------------------------------------------------------
# days_since()
# ---------------------------------------------------------------------------

def test_days_since_today_is_zero():
    today = datetime.now(timezone.utc).date().isoformat()

    result = days_since(today)

    assert result == 0


def test_days_since_none_returns_none():
    result = days_since(None)

    assert result is None


def test_days_since_past_date():
    seven_ago = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()

    result = days_since(seven_ago)

    assert result == 7


# ---------------------------------------------------------------------------
# recency_score()
# ---------------------------------------------------------------------------

def test_recency_score_today_is_100():
    today = datetime.now(timezone.utc).date().isoformat()

    result = recency_score(today)

    assert result == 100


def test_recency_score_30_days_ago_is_0():
    old = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()

    result = recency_score(old)

    assert result == 0


def test_recency_score_15_days_ago_near_45():
    mid = (datetime.now(timezone.utc).date() - timedelta(days=15)).isoformat()

    result = recency_score(mid)

    assert 44 <= result <= 50


def test_recency_score_none_is_0():
    result = recency_score(None)

    assert result == 0


def test_recency_score_beyond_max_days_is_0():
    ancient = (datetime.now(timezone.utc).date() - timedelta(days=60)).isoformat()

    result = recency_score(ancient)

    assert result == 0


# ---------------------------------------------------------------------------
# scan_url_date()
# ---------------------------------------------------------------------------

def test_scan_url_date_yyyymmdd_compact():
    url = "https://news.example.com/articles/20260207/solar-tandem-record"

    result = scan_url_date(url)

    assert result == "2026-02-07"


def test_scan_url_date_yyyy_mm_dd_slashes():
    url = "https://blog.example.com/2026/02/14/perovskite-update/"

    result = scan_url_date(url)

    assert result == "2026-02-14"


def test_scan_url_date_yyyy_mm_dd_dashes():
    url = "https://pv-magazine.com/2026-01-28-solar-efficiency/"

    result = scan_url_date(url)

    assert result == "2026-01-28"


def test_scan_url_date_no_date_returns_none():
    url = "https://en.wikipedia.org/wiki/Perovskite_solar_cell"

    result = scan_url_date(url)

    assert result is None


# ---------------------------------------------------------------------------
# scan_text_date()
# ---------------------------------------------------------------------------

def test_scan_text_date_month_day_year():
    text = "Published on February 7, 2026 -- new perovskite tandem efficiency record."

    result = scan_text_date(text)

    assert result == "2026-02-07"


def test_scan_text_date_day_month_year():
    text = "14 February 2026: Researchers confirm 33.7% efficiency."

    result = scan_text_date(text)

    assert result == "2026-02-14"


def test_scan_text_date_iso_format():
    text = "Data collected as of 2026-02-11 shows consistent improvement."

    result = scan_text_date(text)

    assert result == "2026-02-11"


def test_scan_text_date_relative_yesterday():
    text = "Updated yesterday with latest results."

    result = scan_text_date(text)

    expected = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert result == expected


def test_scan_text_date_relative_days_ago():
    text = "Posted 3 days ago on the research forum."

    result = scan_text_date(text)

    expected = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    assert result == expected


def test_scan_text_date_empty_returns_none():
    result = scan_text_date("")

    assert result is None


def test_scan_text_date_none_returns_none():
    result = scan_text_date(None)

    assert result is None


# ---------------------------------------------------------------------------
# detect_date() -- combines URL + text extraction
# ---------------------------------------------------------------------------

def test_detect_date_url_date_takes_priority():
    url = "https://example.com/2026/02/07/article/"
    snippet = "Published January 15, 2026."
    title = "Solar News"

    date, confidence = detect_date(url, snippet, title)

    assert date == "2026-02-07"
    assert confidence == CONFIDENCE_SOLID


def test_detect_date_falls_back_to_title():
    url = "https://example.com/article/latest"
    snippet = ""
    title = "February 12, 2026 -- Big solar update"

    date, confidence = detect_date(url, snippet, title)

    assert date == "2026-02-12"
    assert confidence == CONFIDENCE_SOFT


def test_detect_date_falls_back_to_snippet():
    url = "https://example.com/article/latest"
    snippet = "Results from February 9, 2026 show improved yields."
    title = "Solar efficiency results"

    date, confidence = detect_date(url, snippet, title)

    assert date == "2026-02-09"
    assert confidence == CONFIDENCE_SOFT


def test_detect_date_returns_none_when_no_date():
    url = "https://example.com/about"
    snippet = "We build solar panels."
    title = "About Us"

    date, confidence = detect_date(url, snippet, title)

    assert date is None
    assert confidence == CONFIDENCE_WEAK
