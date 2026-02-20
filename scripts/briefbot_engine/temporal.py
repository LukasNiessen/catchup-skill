"""Unified time utilities: date windowing, parsing, freshness scoring, date extraction."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from urllib.parse import urlparse

PARSE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%B %d, %Y",
    "%d/%m/%Y",
]

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


# ---------------------------------------------------------------------------
# Core date operations
# ---------------------------------------------------------------------------

def _utc_today():
    return datetime.now(timezone.utc).date()


def window(days: int = 30) -> Tuple[str, str]:
    """Return (start, end) ISO date strings for a rolling window of N calendar days."""
    end_date = _utc_today()
    span_days = max(0, int(days))
    begin_date = end_date - timedelta(days=span_days)
    return begin_date.isoformat(), end_date.isoformat()


def interpret(date_input: Optional[str]) -> Optional[datetime]:
    """Parse a date string or numeric timestamp into a UTC datetime."""
    if not date_input:
        return None

    try:
        return datetime.fromtimestamp(float(date_input), tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    for fmt in PARSE_FORMATS:
        try:
            parsed = datetime.strptime(date_input, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def to_date_str(unix_timestamp: Optional[float]) -> Optional[str]:
    """Convert a Unix timestamp to an ISO date string (YYYY-MM-DD)."""
    if unix_timestamp is None:
        return None
    try:
        dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        return dt.date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def trust_level(
    date_input: Optional[str],
    range_start: str,
    range_end: str,
) -> str:
    """Return 'high' if date falls within [range_start, range_end], else 'low'."""
    if not date_input:
        return "low"
    try:
        parsed = datetime.strptime(date_input, "%Y-%m-%d").date()
        start = datetime.strptime(range_start, "%Y-%m-%d").date()
        end = datetime.strptime(range_end, "%Y-%m-%d").date()
        return "high" if start <= parsed <= end else "low"
    except ValueError:
        return "low"


def elapsed_days(date_input: Optional[str]) -> Optional[int]:
    """Return number of days elapsed since the given YYYY-MM-DD date."""
    if not date_input:
        return None
    try:
        parsed = datetime.strptime(date_input, "%Y-%m-%d").date()
        today = _utc_today()
        return (today - parsed).days
    except ValueError:
        return None


def freshness_score(date_input: Optional[str], max_days: int = 30) -> int:
    """Score from 0-100 based on freshness (100 = today, 0 = max_days old or unknown)."""
    age = elapsed_days(date_input)
    if age is None:
        return 0
    if age < 0:
        return 100
    if age >= max_days:
        return 0
    return int(100 * ((max_days - age) / max_days) ** 0.95)


# ---------------------------------------------------------------------------
# Date extraction from URLs and text (merged from websearch.py date logic)
# ---------------------------------------------------------------------------

def extract_from_url(url: str) -> Optional[str]:
    """Try to extract a YYYY-MM-DD date embedded in the URL path."""
    # /YYYYMMDD/ (compact)
    m = re.search(r'/(\d{4})(\d{2})(\d{2})/', url)
    if m:
        y, mo, d = m.groups()
        if 2019 <= int(y) <= 2032 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"

    # /YYYY/MM/DD/
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if m:
        y, mo, d = m.groups()
        if 2019 <= int(y) <= 2032 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"

    # /YYYY-MM-DD/ or /YYYY-MM-DD-
    m = re.search(r'/(\d{4})-(\d{2})-(\d{2})[-/]', url)
    if m:
        y, mo, d = m.groups()
        if 2019 <= int(y) <= 2032 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"

    return None


def extract_from_text(text: str) -> Optional[str]:
    """Try to extract a date from free-form text content."""
    if not text:
        return None

    lower = text.lower()

    # Month DD, YYYY (e.g. "January 24, 2026")
    m = re.search(
        r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})\b',
        lower,
    )
    if m:
        month_str, day_str, year_str = m.groups()
        month_num = MONTHS.get(month_str[:3])
        if month_num and 2019 <= int(year_str) <= 2032 and 1 <= int(day_str) <= 31:
            return f"{year_str}-{month_num:02d}-{int(day_str):02d}"

    # DD Month YYYY (e.g. "24 January 2026")
    m = re.search(
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s+'
        r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'\s+(\d{4})\b',
        lower,
    )
    if m:
        day_str, month_str, year_str = m.groups()
        month_num = MONTHS.get(month_str[:3])
        if month_num and 2019 <= int(year_str) <= 2032 and 1 <= int(day_str) <= 31:
            return f"{year_str}-{month_num:02d}-{int(day_str):02d}"

    # YYYY-MM-DD (ISO format)
    m = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if m:
        y, mo, d = m.groups()
        if 2019 <= int(y) <= 2032 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"

    # Relative dates
    now = datetime.now()

    if "yesterday" in lower:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")

    if "today" in lower:
        return now.strftime("%Y-%m-%d")

    m = re.search(r'\b(\d+)\s*days?\s*ago\b', lower)
    if m:
        n = int(m.group(1))
        if n <= 90:
            return (now - timedelta(days=n)).strftime("%Y-%m-%d")

    m = re.search(r'\b(\d+)\s*hours?\s*ago\b', lower)
    if m:
        return now.strftime("%Y-%m-%d")

    if "last week" in lower:
        return (now - timedelta(days=7)).strftime("%Y-%m-%d")

    if "this week" in lower:
        return (now - timedelta(days=4)).strftime("%Y-%m-%d")

    if "last month" in lower:
        return (now - timedelta(days=30)).strftime("%Y-%m-%d")

    return None


def detect(
    url: str,
    snippet: str,
    title: str,
) -> Tuple[Optional[str], str]:
    """Extract a date from any available signal, returning (date, confidence)."""
    url_date = extract_from_url(url)
    if url_date:
        return url_date, "high"

    title_date = extract_from_text(title)
    if title_date:
        return title_date, "low"

    snippet_date = extract_from_text(snippet)
    if snippet_date:
        return snippet_date, "med"

    return None, "low"
