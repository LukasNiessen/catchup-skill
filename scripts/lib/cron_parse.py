#
# Cron Expression Parser: Parses cron expressions and translates to schtasks
# Supports daily, specific weekdays, and monthly patterns
#

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


# Day-of-week mapping (cron uses 0=Sunday or 7=Sunday)
DOW_NAMES = {
    0: "SUN",
    1: "MON",
    2: "TUE",
    3: "WED",
    4: "THU",
    5: "FRI",
    6: "SAT",
    7: "SUN",
}

DOW_FROM_NAME = {
    "SUN": 0,
    "MON": 1,
    "TUE": 2,
    "WED": 3,
    "THU": 4,
    "FRI": 5,
    "SAT": 6,
}

# schtasks day abbreviations
SCHTASKS_DOW = {
    0: "SUN",
    1: "MON",
    2: "TUE",
    3: "WED",
    4: "THU",
    5: "FRI",
    6: "SAT",
}


def parse_cron_expression(expression: str) -> Dict[str, Any]:
    """
    Parses a standard 5-field cron expression into a structured dict.

    Fields: minute hour day-of-month month day-of-week

    Returns:
        {
            "raw": original expression,
            "minute": list of ints or "*",
            "hour": list of ints or "*",
            "day_of_month": list of ints or "*",
            "month": list of ints or "*",
            "day_of_week": list of ints or "*",
        }

    Raises:
        ValueError: If the expression is malformed or uses unsupported syntax.
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(
            "Cron expression must have exactly 5 fields (minute hour day-of-month month day-of-week), got {}: '{}'".format(
                len(parts), expression
            )
        )

    field_names = ["minute", "hour", "day_of_month", "month", "day_of_week"]
    field_ranges = {
        "minute": (0, 59),
        "hour": (0, 23),
        "day_of_month": (1, 31),
        "month": (1, 12),
        "day_of_week": (0, 7),
    }

    parsed = {"raw": expression.strip()}

    for i, field_name in enumerate(field_names):
        raw_field = parts[i]
        low, high = field_ranges[field_name]
        parsed[field_name] = _parse_field(raw_field, low, high, field_name)

    # Normalize day_of_week: convert 7 (Sunday) to 0
    if parsed["day_of_week"] != "*":
        parsed["day_of_week"] = sorted(
            set(0 if d == 7 else d for d in parsed["day_of_week"])
        )

    _validate_parsed(parsed)
    return parsed


def _parse_field(raw: str, low: int, high: int, field_name: str) -> Any:
    """Parses a single cron field into a list of ints or '*'."""
    if raw == "*":
        return "*"

    # Handle step values like */5 or 1-30/2
    if "/" in raw:
        raise ValueError(
            "Step values (e.g., '{}') are not supported. Use explicit lists instead.".format(
                raw
            )
        )

    values = set()

    for segment in raw.split(","):
        segment = segment.strip()

        # Named day-of-week (e.g., MON, TUE)
        if field_name == "day_of_week" and segment.upper() in DOW_FROM_NAME:
            values.add(DOW_FROM_NAME[segment.upper()])
            continue

        # Range (e.g., 1-5)
        range_match = re.match(r"^(\d+)-(\d+)$", segment)
        if range_match:
            range_start = int(range_match.group(1))
            range_end = int(range_match.group(2))
            if range_start < low or range_end > high or range_start > range_end:
                raise ValueError(
                    "Invalid range {}-{} for field '{}' (allowed {}-{})".format(
                        range_start, range_end, field_name, low, high
                    )
                )
            values.update(range(range_start, range_end + 1))
            continue

        # Single value
        if not segment.isdigit():
            raise ValueError(
                "Invalid value '{}' in field '{}'".format(segment, field_name)
            )
        val = int(segment)
        if val < low or val > high:
            raise ValueError(
                "Value {} out of range for field '{}' (allowed {}-{})".format(
                    val, field_name, low, high
                )
            )
        values.add(val)

    return sorted(values)


def _validate_parsed(parsed: Dict[str, Any]) -> None:
    """Validates that the parsed expression represents a supportable schedule."""
    minute = parsed["minute"]
    hour = parsed["hour"]

    # Must specify at least a fixed minute
    if minute == "*":
        raise ValueError(
            "Wildcard minute ('* ...') would run every minute. Specify a minute value."
        )

    # TURNED OFF! IT IS ALLOWED TO RUN EVERY HOUR!
    # Must specify at least a fixed hour
    # if hour == "*":
    #   raise ValueError(
    #      "Wildcard hour ('{} * ...') would run every hour. Specify an hour value.".format(
    #         parsed["raw"].split()[0]
    #    )
    # )

    # Multiple minutes or hours not supported for schtasks simplicity
    if len(minute) > 1:
        raise ValueError("Multiple minute values are not supported for scheduled jobs.")
    if len(hour) > 1:
        raise ValueError("Multiple hour values are not supported for scheduled jobs.")


def describe_schedule(parsed: Dict[str, Any]) -> str:
    """
    Generates a human-readable description of a parsed cron schedule.

    Examples:
        "Daily at 06:00"
        "Mon, Wed, Fri at 08:30"
        "1st of every month at 09:00"
        "Every hour at :00"
    """
    minute = parsed["minute"][0]
    hour = parsed["hour"]

    # Handle wildcard hour (e.g., "0 * * * *" = every hour)
    if hour == "*":
        time_str = "every hour at :{:02d}".format(minute)

        dom = parsed["day_of_month"]
        dow = parsed["day_of_week"]

        if dow != "*" and dom == "*":
            if sorted(dow) == list(range(0, 7)):
                return "Every hour at :{:02d}".format(minute)
            if sorted(dow) == [1, 2, 3, 4, 5]:
                return "Weekdays, every hour at :{:02d}".format(minute)
            day_names = [DOW_NAMES[d] for d in dow]
            return "{}, every hour at :{:02d}".format(", ".join(day_names), minute)

        return "Every hour at :{:02d}".format(minute)

    hour = hour[0]
    time_str = "{:02d}:{:02d}".format(hour, minute)

    dom = parsed["day_of_month"]
    dow = parsed["day_of_week"]

    # Specific days of week
    if dow != "*" and dom == "*":
        if sorted(dow) == list(range(0, 7)):
            return "Daily at {}".format(time_str)
        if sorted(dow) == [1, 2, 3, 4, 5]:
            return "Weekdays at {}".format(time_str)
        if sorted(dow) == [0, 6]:
            return "Weekends at {}".format(time_str)
        day_names = [DOW_NAMES[d] for d in dow]
        return "{} at {}".format(", ".join(day_names), time_str)

    # Specific days of month
    if dom != "*" and dow == "*":
        if len(dom) == 1:
            suffix = _ordinal_suffix(dom[0])
            return "{}{} of every month at {}".format(dom[0], suffix, time_str)
        day_list = ", ".join(str(d) for d in dom)
        return "Days {} of every month at {}".format(day_list, time_str)

    # Both wildcards = daily
    if dom == "*" and dow == "*":
        return "Daily at {}".format(time_str)

    return "Custom schedule at {}".format(time_str)


def _ordinal_suffix(n: int) -> str:
    """Returns the ordinal suffix for a number (1st, 2nd, 3rd, 4th, etc.)."""
    if 11 <= n <= 13:
        return "th"
    remainder = n % 10
    if remainder == 1:
        return "st"
    if remainder == 2:
        return "nd"
    if remainder == 3:
        return "rd"
    return "th"


def cron_to_schtasks_args(parsed: Dict[str, Any]) -> List[str]:
    """
    Translates a parsed cron expression into Windows schtasks arguments.

    Returns a list of strings like ["/SC", "DAILY", "/ST", "06:00"].

    Raises:
        ValueError: If the schedule cannot be represented in schtasks.
    """
    minute = parsed["minute"][0]
    hour = parsed["hour"]

    dom = parsed["day_of_month"]
    dow = parsed["day_of_week"]
    month = parsed["month"]

    # Check for unsupported month restrictions
    if month != "*":
        raise ValueError(
            "Specific month restrictions are not supported for Windows scheduled tasks."
        )

    # Hourly: hour is wildcard
    if hour == "*":
        start_time = "00:{:02d}".format(minute)
        return ["/SC", "HOURLY", "/ST", start_time]

    hour = hour[0]
    time_str = "{:02d}:{:02d}".format(hour, minute)

    # Daily: both dom and dow are wildcards
    if dom == "*" and dow == "*":
        return ["/SC", "DAILY", "/ST", time_str]

    # Weekly: specific days of week
    if dow != "*" and dom == "*":
        if sorted(dow) == list(range(0, 7)):
            return ["/SC", "DAILY", "/ST", time_str]
        day_names = [SCHTASKS_DOW[d] for d in dow]
        return ["/SC", "WEEKLY", "/D", ",".join(day_names), "/ST", time_str]

    # Monthly: specific days of month
    if dom != "*" and dow == "*":
        day_list = ",".join(str(d) for d in dom)
        return ["/SC", "MONTHLY", "/D", day_list, "/ST", time_str]

    raise ValueError(
        "Cannot translate schedule with both day-of-month and day-of-week to schtasks."
    )


def next_occurrence(
    parsed: Dict[str, Any], after: Optional[datetime] = None
) -> datetime:
    """
    Computes the next fire time for a parsed cron schedule.

    Args:
        parsed: A parsed cron expression dict.
        after: The reference time (defaults to now).

    Returns:
        The next datetime when this schedule would fire.
    """
    if after is None:
        after = datetime.now()

    minute = parsed["minute"][0]
    hour = parsed["hour"]
    dom = parsed["day_of_month"]
    dow = parsed["day_of_week"]

    # Handle wildcard hour (every hour)
    if hour == "*":
        candidate = after.replace(minute=minute, second=0, microsecond=0)
        if candidate <= after:
            candidate += timedelta(hours=1)
        # Search forward up to 48 hours
        for _ in range(48):
            matches_dom = dom == "*" or candidate.day in dom
            cron_dow = (candidate.weekday() + 1) % 7
            matches_dow = dow == "*" or cron_dow in dow
            if matches_dom and matches_dow:
                return candidate
            candidate += timedelta(hours=1)
        raise ValueError("Could not find next occurrence within 48 hours.")

    hour = hour[0]

    # Start from the target time today
    candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If the candidate is in the past, start from tomorrow
    if candidate <= after:
        candidate += timedelta(days=1)

    # Search forward up to 366 days
    for _ in range(366):
        matches_dom = dom == "*" or candidate.day in dom
        # Python weekday: Monday=0, Sunday=6. Cron: Sunday=0, Saturday=6
        cron_dow = (candidate.weekday() + 1) % 7
        matches_dow = dow == "*" or cron_dow in dow

        if matches_dom and matches_dow:
            return candidate

        candidate += timedelta(days=1)

    raise ValueError("Could not find next occurrence within 366 days.")
