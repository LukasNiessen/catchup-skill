"""Process and normalize web search results with date extraction."""

import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from .. import timeframe
from ..records import Signal, from_web_raw


EXCLUDED_DOMAINS = {
    "reddit.com",
    "old.reddit.com",
    "redd.it",
    "twitter.com",
    "mobile.twitter.com",
    "x.com",
    "t.co",
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
        if host.startswith("www."):
            host = host[4:]
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

        result_date = raw.get("date")
        confidence = timeframe.CONFIDENCE_WEAK

        if result_date and re.match(r"^\d{4}-\d{2}-\d{2}$", str(result_date)):
            confidence = timeframe.CONFIDENCE_SOFT
        else:
            detected, det_conf = timeframe.detect_date(link, snippet, title)
            if detected:
                result_date = detected
                confidence = det_conf

        if result_date and start and result_date < start:
            continue

        if result_date and end and result_date > end:
            continue

        relevance = raw.get("relevance", 0.45)
        try:
            relevance = min(1.0, max(0.0, float(relevance)))
        except (TypeError, ValueError):
            relevance = 0.45

        processed.append(
            {
                "key": f"W-{len(processed) + 1:02d}",
                "headline": title[:250],
                "url": link,
                "domain": _domain(link),
                "snippet": snippet[:400],
                "dated": result_date,
                "time_confidence": confidence,
                "topicality": relevance,
                "rationale": str(raw.get("why_relevant", "")).strip(),
            }
        )

    return processed


def to_items(
    items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[Signal]:
    """Convert parsed dicts to Signal objects."""
    return [from_web_raw(item_data, start, end) for item_data in items]


def dedup_urls(items: List[Signal]) -> List[Signal]:
    """Remove duplicate Signals by normalised URL."""
    seen = set()
    unique = []

    for item in items:
        normalised = item.url.lower().rstrip("/")
        normalised = re.sub(r"^(https?://)www\.", r"\1", normalised)
        normalised = normalised.split("?")[0]
        if normalised not in seen:
            seen.add(normalised)
            unique.append(item)

    return unique
