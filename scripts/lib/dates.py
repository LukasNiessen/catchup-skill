#
# Temporal Utilities: Date manipulation and validation for the catchup skill
# Provides date parsing, range calculation, and recency scoring
#

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


def compute_date_window(day_count: int = 30) -> Tuple[str, str]:
    """
    Calculates a date range spanning the last N days from today.

    Returns a tuple of (start_date, end_date) formatted as YYYY-MM-DD strings.
    """
    current_date = datetime.now(timezone.utc).date()
    window_start = current_date - timedelta(days=day_count)
    return window_start.isoformat(), current_date.isoformat()


# Preserve the original function name for API compatibility
get_date_range = compute_date_window


def interpret_date_string(date_input: Optional[str]) -> Optional[datetime]:
    """
    Parses a date string from various formats into a datetime object.

    Supported formats include:
    - ISO 8601 variants (YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, etc.)
    - Unix timestamps (as strings)
    """
    if date_input is None or date_input == "":
        return None

    # Attempt to parse as Unix timestamp (common from Reddit API)
    try:
        timestamp_value = float(date_input)
        return datetime.fromtimestamp(timestamp_value, tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    # Attempt ISO format variants
    format_patterns = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ]

    pattern_index = 0
    while pattern_index < len(format_patterns):
        try:
            parsed = datetime.strptime(date_input, format_patterns[pattern_index])
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pattern_index += 1

    return None


# Preserve the original function name for API compatibility
parse_date = interpret_date_string


def convert_timestamp_to_date(unix_timestamp: Optional[float]) -> Optional[str]:
    """
    Transforms a Unix timestamp into an ISO date string (YYYY-MM-DD).

    Returns None for invalid or missing input.
    """
    if unix_timestamp is None:
        return None

    try:
        converted_datetime = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        return converted_datetime.date().isoformat()
    except (ValueError, TypeError, OSError):
        return None


# Preserve the original function name for API compatibility
timestamp_to_date = convert_timestamp_to_date


def assess_date_reliability(
    date_input: Optional[str],
    range_start: str,
    range_end: str
) -> str:
    """
    Evaluates how confident we can be about a date's accuracy.

    Confidence levels:
    - 'high': Date falls within the expected range
    - 'med': Not used by this function (reserved for intermediate confidence)
    - 'low': Date is missing, outside range, or invalid
    """
    if date_input is None or date_input == "":
        return 'low'

    try:
        parsed_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        boundary_start = datetime.strptime(range_start, "%Y-%m-%d").date()
        boundary_end = datetime.strptime(range_end, "%Y-%m-%d").date()

        # Check if date falls within acceptable window
        date_in_range = boundary_start <= parsed_date <= boundary_end

        if date_in_range:
            return 'high'

        # Date is either too old or suspiciously in the future
        return 'low'

    except ValueError:
        return 'low'


# Preserve the original function name for API compatibility
get_date_confidence = assess_date_reliability


def calculate_age_in_days(date_input: Optional[str]) -> Optional[int]:
    """
    Determines how many days have elapsed since the given date.

    Returns None if the date is missing or malformed.
    """
    if date_input is None or date_input == "":
        return None

    try:
        parsed_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        current_date = datetime.now(timezone.utc).date()
        difference = current_date - parsed_date
        return difference.days
    except ValueError:
        return None


# Preserve the original function name for API compatibility
days_ago = calculate_age_in_days


def compute_recency_score(date_input: Optional[str], maximum_age_days: int = 30) -> int:
    """
    Calculates a freshness score from 0 to 100.

    Scoring logic:
    - Today's content: 100 points
    - Content at maximum_age_days: 0 points
    - Unknown dates: 0 points (worst case assumption)
    - Future dates: 100 points (treated as today)
    """
    age_days = calculate_age_in_days(date_input)

    if age_days is None:
        return 0

    if age_days < 0:
        return 100  # Future date, likely today's content

    if age_days >= maximum_age_days:
        return 0

    freshness_ratio = 1 - (age_days / maximum_age_days)
    return int(100 * freshness_ratio)


# Preserve the original function name for API compatibility
recency_score = compute_recency_score
