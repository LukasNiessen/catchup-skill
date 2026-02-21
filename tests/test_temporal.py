"""Tests for briefbot_engine.temporal -- date windowing, parsing, freshness, extraction."""

from datetime import datetime, timedelta, timezone

from briefbot_engine.temporal import (
    CONFIDENCE_SOLID,
    CONFIDENCE_SOFT,
    CONFIDENCE_WEAK,
    detect,
    elapsed_days,
    extract_from_text,
    extract_from_url,
    freshness_score,
    interpret,
    to_date_str,
    trust_level,
    window,
)


# ---------------------------------------------------------------------------
# window()
# ---------------------------------------------------------------------------

def test_window_returns_string_tuple():
    start, end = window(30)

    assert isinstance(start, str)
    assert isinstance(end, str)


def test_window_strings_are_iso_format():
    start, end = window(14)

    # YYYY-MM-DD pattern
    assert len(start) == 10
    assert start[4] == "-" and start[7] == "-"
    assert len(end) == 10
    assert end[4] == "-" and end[7] == "-"


def test_window_span_matches_requested_days():
    start, end = window(45)

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    delta = (end_dt - start_dt).days

    assert delta == 45


def test_window_end_is_today():
    _, end = window(7)

    today = datetime.now(timezone.utc).date().isoformat()
    assert end == today


# ---------------------------------------------------------------------------
# interpret()
# ---------------------------------------------------------------------------

def test_interpret_iso_date():
    result = interpret("2026-02-14")

    assert result is not None
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 14


def test_interpret_iso_datetime_with_z():
    result = interpret("2026-02-14T09:30:00Z")

    assert result is not None
    assert result.year == 2026
    assert result.hour == 9
    assert result.minute == 30


def test_interpret_unix_timestamp():
    # 2026-06-15 00:00:00 UTC = 1781481600
    result = interpret("1781481600")

    assert result is not None
    assert result.year == 2026
    assert result.month == 6
    assert result.day == 15


def test_interpret_none_returns_none():
    result = interpret(None)

    assert result is None


def test_interpret_empty_string_returns_none():
    result = interpret("")

    assert result is None


def test_interpret_natural_month_day_year():
    result = interpret("February 14, 2026")

    assert result is not None
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 14


# ---------------------------------------------------------------------------
# to_date_str()
# ---------------------------------------------------------------------------

def test_to_date_str_valid_timestamp():
    # 2026-02-14 00:00:00 UTC = 1771027200
    result = to_date_str(1771027200)

    assert result == "2026-02-14"


def test_to_date_str_none_returns_none():
    result = to_date_str(None)

    assert result is None


# ---------------------------------------------------------------------------
# trust_level()
# ---------------------------------------------------------------------------

def test_trust_level_solid_within_range():
    result = trust_level("2026-02-10", "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_SOLID


def test_trust_level_soft_near_range():
    result = trust_level("2026-02-22", "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_SOFT


def test_trust_level_weak_before_range():
    result = trust_level("2025-11-30", "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_WEAK


def test_trust_level_weak_after_range():
    result = trust_level("2026-04-01", "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_WEAK


def test_trust_level_weak_for_none():
    result = trust_level(None, "2026-01-20", "2026-02-19")

    assert result == CONFIDENCE_WEAK


def test_trust_level_solid_at_boundaries():
    assert trust_level("2026-01-20", "2026-01-20", "2026-02-19") == CONFIDENCE_SOLID
    assert trust_level("2026-02-19", "2026-01-20", "2026-02-19") == CONFIDENCE_SOLID


# ---------------------------------------------------------------------------
# elapsed_days()
# ---------------------------------------------------------------------------

def test_elapsed_days_today_is_zero():
    today = datetime.now(timezone.utc).date().isoformat()

    result = elapsed_days(today)

    assert result == 0


def test_elapsed_days_none_returns_none():
    result = elapsed_days(None)

    assert result is None


def test_elapsed_days_past_date():
    seven_ago = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()

    result = elapsed_days(seven_ago)

    assert result == 7


# ---------------------------------------------------------------------------
# freshness_score()
# ---------------------------------------------------------------------------

def test_freshness_score_today_is_100():
    today = datetime.now(timezone.utc).date().isoformat()

    result = freshness_score(today)

    assert result == 100


def test_freshness_score_30_days_ago_is_0():
    old = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()

    result = freshness_score(old)

    assert result == 0


def test_freshness_score_15_days_ago_near_45():
    mid = (datetime.now(timezone.utc).date() - timedelta(days=15)).isoformat()

    result = freshness_score(mid)

    # Curved formula: int(100 * ((30-15)/30) ** 1.15) ~ 45
    assert 42 <= result <= 48


def test_freshness_score_none_is_0():
    result = freshness_score(None)

    assert result == 0


def test_freshness_score_beyond_max_days_is_0():
    ancient = (datetime.now(timezone.utc).date() - timedelta(days=60)).isoformat()

    result = freshness_score(ancient)

    assert result == 0


# ---------------------------------------------------------------------------
# extract_from_url()
# ---------------------------------------------------------------------------

def test_extract_from_url_yyyymmdd_compact():
    url = "https://news.example.com/articles/20260207/solar-tandem-record"

    result = extract_from_url(url)

    assert result == "2026-02-07"


def test_extract_from_url_yyyy_mm_dd_slashes():
    url = "https://blog.example.com/2026/02/14/perovskite-update/"

    result = extract_from_url(url)

    assert result == "2026-02-14"


def test_extract_from_url_yyyy_mm_dd_dashes():
    url = "https://pv-magazine.com/2026-01-28-solar-efficiency/"

    result = extract_from_url(url)

    assert result == "2026-01-28"


def test_extract_from_url_no_date_returns_none():
    url = "https://en.wikipedia.org/wiki/Perovskite_solar_cell"

    result = extract_from_url(url)

    assert result is None


# ---------------------------------------------------------------------------
# extract_from_text()
# ---------------------------------------------------------------------------

def test_extract_from_text_month_day_year():
    text = "Published on February 7, 2026 -- new perovskite tandem efficiency record."

    result = extract_from_text(text)

    assert result == "2026-02-07"


def test_extract_from_text_day_month_year():
    text = "14 February 2026: Researchers confirm 33.7% efficiency."

    result = extract_from_text(text)

    assert result == "2026-02-14"


def test_extract_from_text_iso_format():
    text = "Data collected as of 2026-02-11 shows consistent improvement."

    result = extract_from_text(text)

    assert result == "2026-02-11"


def test_extract_from_text_relative_yesterday():
    text = "Updated yesterday with latest results."

    result = extract_from_text(text)

    expected = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert result == expected


def test_extract_from_text_relative_days_ago():
    text = "Posted 3 days ago on the research forum."

    result = extract_from_text(text)

    expected = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    assert result == expected


def test_extract_from_text_empty_returns_none():
    result = extract_from_text("")

    assert result is None


def test_extract_from_text_none_returns_none():
    result = extract_from_text(None)

    assert result is None


# ---------------------------------------------------------------------------
# detect() -- combines URL + text extraction
# ---------------------------------------------------------------------------

def test_detect_url_date_takes_priority():
    url = "https://example.com/2026/02/07/article/"
    snippet = "Published January 15, 2026."
    title = "Solar News"

    date, confidence = detect(url, snippet, title)

    assert date == "2026-02-07"
    assert confidence == CONFIDENCE_SOLID


def test_detect_falls_back_to_title():
    url = "https://example.com/article/latest"
    snippet = ""
    title = "February 12, 2026 -- Big solar update"

    date, confidence = detect(url, snippet, title)

    assert date == "2026-02-12"
    assert confidence == CONFIDENCE_SOFT


def test_detect_falls_back_to_snippet():
    url = "https://example.com/article/latest"
    snippet = "Results from February 9, 2026 show improved yields."
    title = "Solar efficiency results"

    date, confidence = detect(url, snippet, title)

    assert date == "2026-02-09"
    assert confidence == CONFIDENCE_SOFT


def test_detect_returns_none_when_no_date():
    url = "https://example.com/about"
    snippet = "We build solar panels."
    title = "About Us"

    date, confidence = detect(url, snippet, title)

    assert date is None
    assert confidence == CONFIDENCE_WEAK
