"""Time-window and publication-date utilities."""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

_STRPTIME_PATTERNS = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%B %d, %Y",
    "%d/%m/%Y",
)

_MONTH_TO_INT = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


# ---------------------------------------------------------------------------
# Core date operations
# ---------------------------------------------------------------------------

def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _as_iso_date(value: date) -> str:
    return value.isoformat()


def window(days: int = 30) -> Tuple[str, str]:
    """Return `from,to` bounds for a rolling UTC calendar window."""
    end_day = _today_utc()
    back_days = max(0, int(days or 0))
    start_day = end_day - timedelta(days=back_days)
    return _as_iso_date(start_day), _as_iso_date(end_day)


def interpret(date_input: Optional[str]) -> Optional[datetime]:
    """Parse known date shapes into a UTC datetime."""
    if not date_input:
        return None

    text = str(date_input).strip()
    if not text:
        return None

    # Fast path: Python ISO parser handles timezone offsets well.
    iso_candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    for fmt in _STRPTIME_PATTERNS:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        return datetime.fromtimestamp(float(text), tz=timezone.utc)
    except (ValueError, TypeError):
        return None


def to_date_str(unix_timestamp: Optional[float]) -> Optional[str]:
    """Convert unix seconds into `YYYY-MM-DD`."""
    if unix_timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def trust_level(
    date_input: Optional[str],
    range_start: str,
    range_end: str,
) -> str:
    """Return confidence of date against the target range."""
    if not date_input:
        return "low"
    try:
        parsed = datetime.strptime(date_input, "%Y-%m-%d").date()
        start_day = datetime.strptime(range_start, "%Y-%m-%d").date()
        end_day = datetime.strptime(range_end, "%Y-%m-%d").date()
        return "high" if start_day <= parsed <= end_day else "low"
    except ValueError:
        return "low"


def elapsed_days(date_input: Optional[str]) -> Optional[int]:
    """Return full days elapsed since date_input."""
    if not date_input:
        return None
    try:
        parsed = datetime.strptime(date_input, "%Y-%m-%d").date()
        return (_today_utc() - parsed).days
    except ValueError:
        return None


def freshness_score(date_input: Optional[str], max_days: int = 30) -> int:
    """Return curved freshness score in [0,100]."""
    age = elapsed_days(date_input)
    if age is None:
        return 0
    if age < 0:
        return 100
    cap = max(1, int(max_days))
    if age >= cap:
        return 0
    remaining = (cap - age) / cap
    return int(100 * (remaining ** 0.93))


# ---------------------------------------------------------------------------
# Date extraction from URLs and text (merged from websearch.py date logic)
# ---------------------------------------------------------------------------

def extract_from_url(url: str) -> Optional[str]:
    """Extract a plausible publish date from URL patterns."""
    patterns = (
        r"/(\d{4})(\d{2})(\d{2})/",
        r"/(\d{4})/(\d{2})/(\d{2})/",
        r"/(\d{4})-(\d{2})-(\d{2})[-/]",
    )
    for pattern in patterns:
        match = re.search(pattern, url)
        if not match:
            continue
        year, month, day = match.groups()
        if 2019 <= int(year) <= 2032 and 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            return f"{year}-{month}-{day}"
    return None


def extract_from_text(text: str) -> Optional[str]:
    """Extract a date-like value from natural language."""
    if not text:
        return None

    lowered = text.lower()

    month_first = re.search(
        r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})\b',
        lowered,
    )
    if month_first:
        month_str, day_str, year_str = month_first.groups()
        month_num = _MONTH_TO_INT.get(month_str[:3])
        if month_num and 2019 <= int(year_str) <= 2032 and 1 <= int(day_str) <= 31:
            return f"{year_str}-{month_num:02d}-{int(day_str):02d}"

    day_first = re.search(
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s+'
        r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'\s+(\d{4})\b',
        lowered,
    )
    if day_first:
        day_str, month_str, year_str = day_first.groups()
        month_num = _MONTH_TO_INT.get(month_str[:3])
        if month_num and 2019 <= int(year_str) <= 2032 and 1 <= int(day_str) <= 31:
            return f"{year_str}-{month_num:02d}-{int(day_str):02d}"

    iso = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if iso:
        year, month, day = iso.groups()
        if 2019 <= int(year) <= 2032 and 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            return f"{year}-{month}-{day}"

    now = datetime.now()
    if "yesterday" in lowered:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in lowered:
        return now.strftime("%Y-%m-%d")

    ago_days = re.search(r"\b(\d+)\s*days?\s*ago\b", lowered)
    if ago_days:
        span = int(ago_days.group(1))
        if span <= 90:
            return (now - timedelta(days=span)).strftime("%Y-%m-%d")

    ago_hours = re.search(r"\b(\d+)\s*hours?\s*ago\b", lowered)
    if ago_hours:
        return now.strftime("%Y-%m-%d")

    relative_map = {
        "last week": 7,
        "this week": 4,
        "last month": 30,
    }
    for label, days_back in relative_map.items():
        if label in lowered:
            return (now - timedelta(days=days_back)).strftime("%Y-%m-%d")

    return None


def detect(
    url: str,
    snippet: str,
    title: str,
) -> Tuple[Optional[str], str]:
    """Choose best available date signal from URL/title/snippet."""
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
