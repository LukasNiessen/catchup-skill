"""Date manipulation and recency scoring utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%B %d, %Y",
    "%d/%m/%Y",
]


def date_window(days: int = 30) -> Tuple[str, str]:
    """Return (start, end) ISO date strings for a rolling window of N calendar days."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days)
    return start.isoformat(), today.isoformat()


def parse_date(date_input: Optional[str]) -> Optional[datetime]:
    """Parse a date string or numeric timestamp into a UTC datetime."""
    if not date_input:
        return None

    # Try Unix timestamp first (common from Reddit API)
    try:
        return datetime.fromtimestamp(float(date_input), tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    # Try ISO format variants
    for fmt in FORMATS:
        try:
            parsed = datetime.strptime(date_input, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def timestamp_to_date(unix_timestamp: Optional[float]) -> Optional[str]:
    """Convert a Unix timestamp to an ISO date string (YYYY-MM-DD)."""
    if unix_timestamp is None:
        return None

    try:
        dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        return dt.date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def date_confidence(
    date_input: Optional[str],
    range_start: str,
    range_end: str,
) -> str:
    """Return 'high' if date falls within [range_start, range_end], else 'low'."""
    if not date_input:
        return 'low'

    try:
        parsed = datetime.strptime(date_input, "%Y-%m-%d").date()
        start = datetime.strptime(range_start, "%Y-%m-%d").date()
        end = datetime.strptime(range_end, "%Y-%m-%d").date()
        return 'high' if start <= parsed <= end else 'low'
    except ValueError:
        return 'low'


def days_ago(date_input: Optional[str]) -> Optional[int]:
    """Return number of days elapsed since the given YYYY-MM-DD date."""
    if not date_input:
        return None

    try:
        parsed = datetime.strptime(date_input, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        return (today - parsed).days
    except ValueError:
        return None


def recency_score(date_input: Optional[str], max_days: int = 30) -> int:
    """Score from 0-100 based on freshness (100 = today, 0 = max_days old or unknown)."""
    age = days_ago(date_input)

    if age is None:
        return 0

    if age < 0:
        return 100  # Future date, likely today's content

    if age >= max_days:
        return 0

    return int(100 * ((max_days - age) / max_days) ** 0.95)
