"""Enrich Reddit items with real engagement data from thread JSON."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .. import net, temporal

_NON_SUBSTANTIVE = (
    r"^(yep|nope|same|agreed|this|exactly|thanks|thank\s*you|yes|no|ok|okay)\.?!?$",
    r"^(lol|lmao|rofl|haha|heh)+$",
    r"^\[(deleted|removed)\]$",
)
_REMOVED_AUTHORS = {"[deleted]", "[removed]"}


def _parse_url(url: str) -> Optional[str]:
    """Extract a fetchable Reddit path from URL input."""
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    host = parsed.netloc.lower()
    if "reddit.com" not in host:
        return None
    return parsed.path or None


def _fetch_thread(url: str, mock_data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    """Fetch the JSON representation of a Reddit thread."""
    if mock_data is not None:
        return mock_data
    thread_path = _parse_url(url)
    if not thread_path:
        return None
    try:
        return net.reddit_json(thread_path)
    except net.HTTPError:
        return None


def _listing_children(raw_listing: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_listing, dict):
        return []
    data = raw_listing.get("data", {})
    if not isinstance(data, dict):
        return []
    children = data.get("children", [])
    return children if isinstance(children, list) else []


def _parse_submission(raw_data: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_data, list) or not raw_data:
        return None
    for child in _listing_children(raw_data[0]):
        payload = child.get("data", {})
        if not isinstance(payload, dict):
            continue
        return {
            "score": payload.get("score"),
            "num_comments": payload.get("num_comments"),
            "upvote_ratio": payload.get("upvote_ratio"),
            "created_utc": payload.get("created_utc"),
            "permalink": payload.get("permalink"),
            "title": payload.get("title"),
            "selftext": str(payload.get("selftext") or "")[:640],
        }
    return None


def _parse_comments(raw_data: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_data, list) or len(raw_data) < 2:
        return []
    parsed: List[Dict[str, Any]] = []
    for child in _listing_children(raw_data[1]):
        if not isinstance(child, dict) or child.get("kind") != "t1":
            continue
        payload = child.get("data", {})
        if not isinstance(payload, dict):
            continue
        body = str(payload.get("body") or "").strip()
        if not body:
            continue
        parsed.append(
            {
                "score": payload.get("score", 0),
                "created_utc": payload.get("created_utc"),
                "author": payload.get("author", "[deleted]"),
                "body": body[:360],
                "permalink": payload.get("permalink"),
            }
        )
    return parsed


def _parse_thread(raw_data: Any) -> Dict[str, Any]:
    """Parse Reddit's JSON array into submission + comments."""
    return {"submission": _parse_submission(raw_data), "comments": _parse_comments(raw_data)}


def _top_comments(comments: List[Dict], limit: int = 12) -> List[Dict[str, Any]]:
    """Return the highest-scoring comments, excluding deleted authors."""
    ranked = sorted(
        (c for c in comments if c.get("author") not in _REMOVED_AUTHORS),
        key=lambda c: int(c.get("score") or 0),
        reverse=True,
    )
    return ranked[: max(0, limit)]


def _excerpt(text: str, hard_limit: int = 180, min_boundary_index: int = 60) -> str:
    snippet = text[:hard_limit]
    if len(text) <= hard_limit:
        return snippet
    boundary = max(snippet.rfind("."), snippet.rfind("!"), snippet.rfind("?"), snippet.rfind(";"))
    if boundary >= min_boundary_index:
        return snippet[: boundary + 1]
    return snippet.rstrip() + "..."


def _extract_insights(comments: List[Dict], limit: int = 6) -> List[str]:
    """Pull substantive insights from top comments, skipping low-value noise."""
    insights: List[str] = []
    for comment in comments[: limit * 3]:
        body = str(comment.get("body") or "").strip()
        if len(body) < 25:
            continue
        lowered = body.lower()
        if any(re.match(pattern, lowered) for pattern in _NON_SUBSTANTIVE):
            continue
        insights.append(_excerpt(body, hard_limit=190, min_boundary_index=70))
        if len(insights) >= limit:
            break
    return insights


def enrich(
    item: Dict[str, Any],
    mock_json: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Augment a Reddit item with real engagement data from the thread."""
    thread_data = _fetch_thread(item.get("url", ""), mock_json)
    if thread_data is None:
        return item

    parsed = _parse_thread(thread_data)
    submission = parsed["submission"]
    comment_list = parsed["comments"]

    if submission is not None:
        item["engagement"] = {
            "score": submission.get("score"),
            "num_comments": submission.get("num_comments"),
            "upvote_ratio": submission.get("upvote_ratio"),
        }
        created_utc = submission.get("created_utc")
        if created_utc is not None:
            item["date"] = temporal.to_date_str(created_utc)

    top = _top_comments(comment_list)
    item["top_comments"] = [
        {
            "score": c.get("score", 0),
            "date": temporal.to_date_str(c.get("created_utc")),
            "author": c.get("author", ""),
            "excerpt": str(c.get("body", ""))[:250],
            "url": f"https://www.reddit.com{c.get('permalink', '')}" if c.get("permalink") else "",
        }
        for c in top
    ]
    item["comment_insights"] = _extract_insights(top)

    return item
