"""Process and normalize web search results with date extraction."""

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .. import temporal
from ..content import ContentItem, Source, from_web_raw


# Reddit and X are searched separately -- exclude them here
EXCLUDED_DOMAINS = {
    "reddit.com",
    "www.reddit.com",
    "old.reddit.com",
    "m.reddit.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "nitter.net",
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

        link = raw.get("url", "")
        if not link:
            continue

        if _is_excluded(link):
            continue

        title = str(raw.get("title", "")).strip()
        snippet = str(raw.get("snippet", raw.get("description", ""))).strip()

        if not title and not snippet:
            continue

        # Date detection
        result_date = raw.get("date")
        confidence = temporal.CONFIDENCE_WEAK

        if result_date and re.match(r'^\d{4}-\d{2}-\d{2}$', str(result_date)):
            confidence = temporal.CONFIDENCE_SOFT
        else:
            detected, det_conf = temporal.detect(link, snippet, title)
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
        relevance = raw.get("relevance", 0.45)
        try:
            relevance = min(1.0, max(0.0, float(relevance)))
        except (TypeError, ValueError):
            relevance = 0.45

        processed.append({
            "uid": f"W{len(processed) + 1}",
            "title": title[:250],
            "link": link,
            "domain": _domain(link),
            "snippet": snippet[:400],
            "posted": result_date,
            "date_confidence": confidence,
            "signal": relevance,
            "reason": str(raw.get("why_relevant", "")).strip(),
        })

    return processed


def to_items(
    items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[ContentItem]:
    """Convert parsed dicts to ContentItem objects."""
    converted = []

    for item_data in items:
        converted.append(from_web_raw(item_data, start, end))

    return converted


def dedup_urls(items: List[ContentItem]) -> List[ContentItem]:
    """Remove duplicate ContentItems by normalised URL."""
    seen = set()
    unique = []

    for item in items:
        normalised = item.link.lower().rstrip("/")
        # Strip www. prefix for more aggressive dedup
        normalised = re.sub(r'^(https?://)www\.', r'\1', normalised)
        # Remove query parameters
        normalised = normalised.split("?")[0]
        if normalised not in seen:
            seen.add(normalised)
            unique.append(item)

    return unique
