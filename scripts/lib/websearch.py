"""Process and normalize web search results with date extraction."""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from . import schema


# Month name to number lookup for date parsing
MONTHS = {
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


def _date_from_url(url: str) -> Optional[str]:
    """Try to extract a YYYY-MM-DD date embedded in the URL path."""
    # /YYYY/MM/DD/
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if m:
        y, mo, d = m.groups()
        if 2020 <= int(y) <= 2030 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"

    # /YYYY-MM-DD/ or /YYYY-MM-DD-
    m = re.search(r'/(\d{4})-(\d{2})-(\d{2})[-/]', url)
    if m:
        y, mo, d = m.groups()
        if 2020 <= int(y) <= 2030 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"

    # /YYYYMMDD/ (compact)
    m = re.search(r'/(\d{4})(\d{2})(\d{2})/', url)
    if m:
        y, mo, d = m.groups()
        if 2020 <= int(y) <= 2030 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"

    return None


def _date_from_text(text: str) -> Optional[str]:
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
        if month_num and 2020 <= int(year_str) <= 2030 and 1 <= int(day_str) <= 31:
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
        if month_num and 2020 <= int(year_str) <= 2030 and 1 <= int(day_str) <= 31:
            return f"{year_str}-{month_num:02d}-{int(day_str):02d}"

    # YYYY-MM-DD (ISO format)
    m = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if m:
        y, mo, d = m.groups()
        if 2020 <= int(y) <= 2030 and 1 <= int(mo) <= 12 and 1 <= int(d) <= 31:
            return f"{y}-{mo}-{d}"

    # Relative dates
    now = datetime.now()

    if "yesterday" in lower:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")

    if "today" in lower:
        return now.strftime("%Y-%m-%d")

    # "N days ago"
    m = re.search(r'\b(\d+)\s*days?\s*ago\b', lower)
    if m:
        n = int(m.group(1))
        if n <= 60:
            return (now - timedelta(days=n)).strftime("%Y-%m-%d")

    # "N hours ago" -> today
    m = re.search(r'\b(\d+)\s*hours?\s*ago\b', lower)
    if m:
        return now.strftime("%Y-%m-%d")

    # "last week" -> ~7 days ago
    if "last week" in lower:
        return (now - timedelta(days=7)).strftime("%Y-%m-%d")

    # "this week" -> ~3 days ago (midpoint)
    if "this week" in lower:
        return (now - timedelta(days=3)).strftime("%Y-%m-%d")

    return None


def _detect_date(
    url: str,
    snippet: str,
    title: str,
) -> Tuple[Optional[str], str]:
    """Extract a date from any available signal, returning (date, confidence)."""
    # URL is the most trustworthy source
    url_date = _date_from_url(url)
    if url_date:
        return url_date, "high"

    # Snippet next
    snippet_date = _date_from_text(snippet)
    if snippet_date:
        return snippet_date, "med"

    # Title as last resort
    title_date = _date_from_text(title)
    if title_date:
        return title_date, "med"

    return None, "low"


# Reddit and X are searched separately -- exclude them here
EXCLUDED_DOMAINS = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "mobile.twitter.com",
}


def _domain(url: str) -> str:
    """Extract the bare domain from a URL, stripping www prefix."""
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def _is_excluded(url: str) -> bool:
    """Return True if the URL belongs to an excluded domain."""
    try:
        host = urlparse(url).netloc.lower()
        return host in EXCLUDED_DOMAINS
    except Exception:
        return False


def process_results(
    raw_results: List[Dict[str, Any]],
    topic: str,
    start: str = "",
    end: str = "",
) -> List[Dict[str, Any]]:
    """Transform raw WebSearch results into normalised, date-filtered items."""
    processed = []

    for raw in raw_results:
        if not isinstance(raw, dict):
            continue

        url = raw.get("url", "")
        if not url:
            continue

        if _is_excluded(url):
            continue

        title = str(raw.get("title", "")).strip()
        snippet = str(raw.get("snippet", raw.get("description", ""))).strip()

        if not title and not snippet:
            continue

        # Date detection
        result_date = raw.get("date")
        confidence = "low"

        if result_date and re.match(r'^\d{4}-\d{2}-\d{2}$', str(result_date)):
            confidence = "med"
        else:
            detected, det_conf = _detect_date(url, snippet, title)
            if detected:
                result_date = detected
                confidence = det_conf

        # Hard filter: verified old content
        if result_date and start and result_date < start:
            continue

        # Hard filter: future dates (likely parse errors)
        if result_date and end and result_date > end:
            continue

        # Relevance
        relevance = raw.get("relevance", 0.5)
        try:
            relevance = min(1.0, max(0.0, float(relevance)))
        except (TypeError, ValueError):
            relevance = 0.5

        processed.append({
            "id": f"W{len(processed) + 1}",
            "title": title[:200],
            "url": url,
            "source_domain": _domain(url),
            "snippet": snippet[:500],
            "date": result_date,
            "date_confidence": confidence,
            "relevance": relevance,
            "why_relevant": str(raw.get("why_relevant", "")).strip(),
        })

    return processed


def to_items(
    items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[schema.WebSearchItem]:
    """Convert parsed dicts to WebSearchItem objects."""
    converted = []

    for item_data in items:
        converted.append(schema.WebSearchItem(
            id=item_data["id"],
            title=item_data["title"],
            url=item_data["url"],
            source_domain=item_data["source_domain"],
            snippet=item_data["snippet"],
            date=item_data.get("date"),
            date_confidence=item_data.get("date_confidence", "low"),
            relevance=item_data.get("relevance", 0.5),
            why_relevant=item_data.get("why_relevant", ""),
        ))

    return converted


def dedup_urls(items: List[schema.WebSearchItem]) -> List[schema.WebSearchItem]:
    """Remove duplicate WebSearch items by normalised URL."""
    seen = set()
    unique = []

    for item in items:
        normalised = item.url.lower().rstrip("/")
        if normalised not in seen:
            seen.add(normalised)
            unique.append(item)

    return unique
