#
# Web Search Module: Processes results from Claude's built-in WebSearch tool
# Handles date extraction, domain filtering, and normalization of web results
#
# NOTE: WebSearch uses Claude's built-in WebSearch tool, which runs INSIDE Claude Code.
# Unlike Reddit/X which use external APIs, WebSearch results are obtained by Claude
# directly and passed to this module for normalization and scoring.
#
# The typical flow is:
# 1. Claude invokes WebSearch tool with the topic
# 2. Claude passes results to parse_websearch_results()
# 3. Results are normalized into WebSearchItem objects
#

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from . import schema


# Month name to number mappings for date parsing
MONTH_NAME_MAPPING = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def detect_date_in_url(page_url: str) -> Optional[str]:
    """
    Attempts to extract a date embedded in the URL path.

    Many sites embed dates in URLs like:
    - /2026/01/24/article-title
    - /2026-01-24/article
    - /blog/20260124/title

    Args:
        page_url: URL to analyze

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    # Pattern 1: /YYYY/MM/DD/ (most common)
    pattern_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', page_url)
    if pattern_match:
        year_val, month_val, day_val = pattern_match.groups()
        if 2020 <= int(year_val) <= 2030 and 1 <= int(month_val) <= 12 and 1 <= int(day_val) <= 31:
            return "{}-{}-{}".format(year_val, month_val, day_val)

    # Pattern 2: /YYYY-MM-DD/ or /YYYY-MM-DD-
    pattern_match = re.search(r'/(\d{4})-(\d{2})-(\d{2})[-/]', page_url)
    if pattern_match:
        year_val, month_val, day_val = pattern_match.groups()
        if 2020 <= int(year_val) <= 2030 and 1 <= int(month_val) <= 12 and 1 <= int(day_val) <= 31:
            return "{}-{}-{}".format(year_val, month_val, day_val)

    # Pattern 3: /YYYYMMDD/ (compact format)
    pattern_match = re.search(r'/(\d{4})(\d{2})(\d{2})/', page_url)
    if pattern_match:
        year_val, month_val, day_val = pattern_match.groups()
        if 2020 <= int(year_val) <= 2030 and 1 <= int(month_val) <= 12 and 1 <= int(day_val) <= 31:
            return "{}-{}-{}".format(year_val, month_val, day_val)

    return None


def detect_date_in_text(content_text: str) -> Optional[str]:
    """
    Attempts to extract a date from text content.

    Looks for patterns like:
    - January 24, 2026 or Jan 24, 2026
    - 24 January 2026
    - 2026-01-24
    - "3 days ago", "yesterday", "last week"

    Args:
        content_text: Text to analyze

    Returns:
        Date string in YYYY-MM-DD format, or None if not found
    """
    if not content_text:
        return None

    lowercase_text = content_text.lower()

    # Pattern 1: Month DD, YYYY (e.g., "January 24, 2026")
    pattern_match = re.search(
        r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})\b',
        lowercase_text
    )
    if pattern_match:
        month_text, day_text, year_text = pattern_match.groups()
        month_number = MONTH_NAME_MAPPING.get(month_text[:3])
        if month_number and 2020 <= int(year_text) <= 2030 and 1 <= int(day_text) <= 31:
            return "{}-{:02d}-{:02d}".format(year_text, month_number, int(day_text))

    # Pattern 2: DD Month YYYY (e.g., "24 January 2026")
    pattern_match = re.search(
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s+'
        r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
        r'\s+(\d{4})\b',
        lowercase_text
    )
    if pattern_match:
        day_text, month_text, year_text = pattern_match.groups()
        month_number = MONTH_NAME_MAPPING.get(month_text[:3])
        if month_number and 2020 <= int(year_text) <= 2030 and 1 <= int(day_text) <= 31:
            return "{}-{:02d}-{:02d}".format(year_text, month_number, int(day_text))

    # Pattern 3: YYYY-MM-DD (ISO format)
    pattern_match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', content_text)
    if pattern_match:
        year_val, month_val, day_val = pattern_match.groups()
        if 2020 <= int(year_val) <= 2030 and 1 <= int(month_val) <= 12 and 1 <= int(day_val) <= 31:
            return "{}-{}-{}".format(year_val, month_val, day_val)

    # Pattern 4: Relative dates
    current_date = datetime.now()

    if "yesterday" in lowercase_text:
        computed_date = current_date - timedelta(days=1)
        return computed_date.strftime("%Y-%m-%d")

    if "today" in lowercase_text:
        return current_date.strftime("%Y-%m-%d")

    # "N days ago"
    pattern_match = re.search(r'\b(\d+)\s*days?\s*ago\b', lowercase_text)
    if pattern_match:
        days_count = int(pattern_match.group(1))
        if days_count <= 60:
            computed_date = current_date - timedelta(days=days_count)
            return computed_date.strftime("%Y-%m-%d")

    # "N hours ago" -> today
    pattern_match = re.search(r'\b(\d+)\s*hours?\s*ago\b', lowercase_text)
    if pattern_match:
        return current_date.strftime("%Y-%m-%d")

    # "last week" -> approximately 7 days ago
    if "last week" in lowercase_text:
        computed_date = current_date - timedelta(days=7)
        return computed_date.strftime("%Y-%m-%d")

    # "this week" -> approximately 3 days ago (middle of week)
    if "this week" in lowercase_text:
        computed_date = current_date - timedelta(days=3)
        return computed_date.strftime("%Y-%m-%d")

    return None


def analyze_date_signals(
    page_url: str,
    snippet_text: str,
    title_text: str,
) -> Tuple[Optional[str], str]:
    """
    Extracts date from any available signal source.

    Prioritizes URL (most reliable), then snippet, then title.

    Args:
        page_url: Page URL
        snippet_text: Page snippet/description
        title_text: Page title

    Returns:
        Tuple of (date_string, confidence_level)
        - date from URL: 'high' confidence
        - date from snippet/title: 'med' confidence
        - no date found: None, 'low' confidence
    """
    # URL is most reliable source
    url_date = detect_date_in_url(page_url)
    if url_date:
        return url_date, "high"

    # Try snippet next
    snippet_date = detect_date_in_text(snippet_text)
    if snippet_date:
        return snippet_date, "med"

    # Try title as fallback
    title_date = detect_date_in_text(title_text)
    if title_date:
        return title_date, "med"

    return None, "low"


# Domains to exclude (Reddit and X are handled separately)
BLOCKED_DOMAINS = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "mobile.twitter.com",
}


def isolate_domain(full_url: str) -> str:
    """
    Extracts the domain from a URL.

    Args:
        full_url: Complete URL

    Returns:
        Domain string (e.g., "medium.com")
    """
    try:
        parsed = urlparse(full_url)
        domain_name = parsed.netloc.lower()
        # Remove www. prefix for cleaner display
        if domain_name.startswith("www."):
            domain_name = domain_name[4:]
        return domain_name
    except Exception:
        return ""


def domain_is_blocked(full_url: str) -> bool:
    """
    Checks if URL is from a blocked domain (Reddit/X).

    Args:
        full_url: URL to check

    Returns:
        True if URL should be excluded
    """
    try:
        parsed = urlparse(full_url)
        domain_name = parsed.netloc.lower()
        return domain_name in BLOCKED_DOMAINS
    except Exception:
        return False


def process_websearch_output(
    raw_results: List[Dict[str, Any]],
    subject_matter: str,
    period_start: str = "",
    period_end: str = "",
) -> List[Dict[str, Any]]:
    """
    Transforms WebSearch results into normalized format.

    This function expects results from Claude's WebSearch tool.
    Each result should have: title, url, snippet, and optionally date/relevance.

    Uses "Date Detective" approach:
    1. Extract dates from URLs (high confidence)
    2. Extract dates from snippets/titles (med confidence)
    3. Hard filter: exclude items with verified old dates
    4. Keep items with no date signals (with low confidence penalty)

    Args:
        raw_results: List of WebSearch result dicts
        subject_matter: Original search topic (for context)
        period_start: Start date for filtering (YYYY-MM-DD)
        period_end: End date for filtering (YYYY-MM-DD)

    Returns:
        List of normalized item dicts ready for WebSearchItem creation
    """
    processed_items = []

    result_index = 0
    while result_index < len(raw_results):
        raw_result = raw_results[result_index]
        result_index += 1

        if not isinstance(raw_result, dict):
            continue

        result_url = raw_result.get("url", "")
        if not result_url:
            continue

        # Skip Reddit/X URLs (handled separately)
        if domain_is_blocked(result_url):
            continue

        result_title = str(raw_result.get("title", "")).strip()
        result_snippet = str(raw_result.get("snippet", raw_result.get("description", ""))).strip()

        if not result_title and not result_snippet:
            continue

        # Use Date Detective to extract date signals
        result_date = raw_result.get("date")
        confidence_level = "low"

        if result_date and re.match(r'^\d{4}-\d{2}-\d{2}$', str(result_date)):
            # Provided date is valid
            confidence_level = "med"
        else:
            # Try to extract date from URL/snippet/title
            detected_date, detected_confidence = analyze_date_signals(result_url, result_snippet, result_title)
            if detected_date:
                result_date = detected_date
                confidence_level = detected_confidence

        # Hard filter: if we found a date and it's too old, skip
        if result_date and period_start and result_date < period_start:
            continue  # DROP - verified old content

        # Hard filter: if date is in the future, skip (parsing error)
        if result_date and period_end and result_date > period_end:
            continue  # DROP - future date

        # Get relevance if provided, default to 0.5
        relevance_value = raw_result.get("relevance", 0.5)
        try:
            relevance_value = min(1.0, max(0.0, float(relevance_value)))
        except (TypeError, ValueError):
            relevance_value = 0.5

        processed_item = {
            "id": "W{}".format(len(processed_items) + 1),
            "title": result_title[:200],  # Truncate long titles
            "url": result_url,
            "source_domain": isolate_domain(result_url),
            "snippet": result_snippet[:500],  # Truncate long snippets
            "date": result_date,
            "date_confidence": confidence_level,
            "relevance": relevance_value,
            "why_relevant": str(raw_result.get("why_relevant", "")).strip(),
        }

        processed_items.append(processed_item)

    return processed_items


def transform_to_websearch_items(
    processed_items: List[Dict[str, Any]],
    period_start: str,
    period_end: str,
) -> List[schema.WebSearchItem]:
    """
    Converts parsed dicts to WebSearchItem objects.

    Args:
        processed_items: List of parsed item dicts
        period_start: Start of date range (YYYY-MM-DD)
        period_end: End of date range (YYYY-MM-DD)

    Returns:
        List of WebSearchItem objects
    """
    converted_items = []

    item_index = 0
    while item_index < len(processed_items):
        item_data = processed_items[item_index]
        web_item = schema.WebSearchItem(
            id=item_data["id"],
            title=item_data["title"],
            url=item_data["url"],
            source_domain=item_data["source_domain"],
            snippet=item_data["snippet"],
            date=item_data.get("date"),
            date_confidence=item_data.get("date_confidence", "low"),
            relevance=item_data.get("relevance", 0.5),
            why_relevant=item_data.get("why_relevant", ""),
        )
        converted_items.append(web_item)
        item_index += 1

    return converted_items


def eliminate_duplicates(item_collection: List[schema.WebSearchItem]) -> List[schema.WebSearchItem]:
    """
    Removes duplicate WebSearch items.

    Deduplication is based on URL.

    Args:
        item_collection: List of WebSearchItem objects

    Returns:
        Deduplicated list
    """
    encountered_urls = set()
    unique_items = []

    item_index = 0
    while item_index < len(item_collection):
        current_item = item_collection[item_index]
        # Normalize URL for comparison
        normalized_url = current_item.url.lower().rstrip("/")
        if normalized_url not in encountered_urls:
            encountered_urls.add(normalized_url)
            unique_items.append(current_item)
        item_index += 1

    return unique_items
