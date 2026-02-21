"""Reddit thread hydration and comment-signal extraction."""

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .. import net, temporal

_TRIVIAL_REPLIES = (
    r"^(yep|nope|same|agreed|this|exactly|yes|no|ok|okay|got it|\+1)\.?!?$",
    r"^(lol|lmao|rofl|haha|heh|lmfao|based)+$",
    r"^\[(deleted|removed)\]$",
)
_SKIP_AUTHORS = {"[deleted]", "[removed]"}


def _thread_path_from_url(url: str) -> Optional[str]:
    """Extract a fetchable Reddit path from a URL."""
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    host = parsed.netloc.lower()
    if "reddit.com" not in host:
        return None
    return parsed.path or None


def _load_thread_json(
    url: str, mock_data: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """Fetch the JSON representation of a Reddit thread."""
    if mock_data is not None:
        return mock_data
    thread_path = _thread_path_from_url(url)
    if not thread_path:
        return None
    try:
        return net.reddit_json(thread_path)
    except net.HTTPError:
        return None


def _children(raw_listing: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_listing, dict):
        return []
    data = raw_listing.get("data", {})
    if not isinstance(data, dict):
        return []
    children = data.get("children", [])
    return children if isinstance(children, list) else []


def _read_submission(raw_data: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_data, list) or not raw_data:
        return None
    submission_listing = raw_data[0]
    for child in _children(submission_listing):
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


def _read_comments(raw_data: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_data, list) or len(raw_data) < 2:
        return []
    comments: List[Dict[str, Any]] = []
    for child in _children(raw_data[1]):
        if not isinstance(child, dict) or child.get("kind") != "t1":
            continue
        payload = child.get("data", {})
        if not isinstance(payload, dict):
            continue
        body = str(payload.get("body") or "").strip()
        if not body:
            continue
        comments.append(
            {
                "score": payload.get("score", 0),
                "created_utc": payload.get("created_utc"),
                "author": payload.get("author", "[deleted]"),
                "body": body[:360],
                "permalink": payload.get("permalink"),
            }
        )
    return comments


def _decode_thread_payload(raw_data: Any) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Decode Reddit listing JSON into submission + comments."""
    submission = _read_submission(raw_data)
    comments = _read_comments(raw_data)
    return submission, comments


def _top_comments(comments: List[Dict], limit: int = 10) -> List[Dict[str, Any]]:
    """Return highest-scoring comments from non-removed authors."""
    ranked = [row for row in comments if row.get("author") not in _SKIP_AUTHORS]
    ranked.sort(key=lambda row: int(row.get("score") or 0), reverse=True)
    return ranked[: max(limit, 0)]


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
    for comment in comments[: limit * 4]:
        body = str(comment.get("body") or "").strip()
        if len(body) < 28:
            continue
        lowered = body.lower()
        if any(re.match(pattern, lowered) for pattern in _TRIVIAL_REPLIES):
            continue
        insights.append(_excerpt(body, hard_limit=190, min_boundary_index=70))
        if len(insights) >= limit:
            break
    return insights


def enrich(
    item: Dict[str, Any],
    mock_json: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Augment a Reddit item with thread-derived engagement metadata."""
    thread_data = _load_thread_json(item.get("link", ""), mock_json)
    if thread_data is None:
        return item

    submission, comment_list = _decode_thread_payload(thread_data)

    if submission is not None:
        item["metrics"] = {
            "upvotes": submission.get("score"),
            "comments": submission.get("num_comments"),
            "vote_ratio": submission.get("upvote_ratio"),
        }
        created_utc = submission.get("created_utc")
        if created_utc is not None:
            item["posted"] = temporal.to_date_str(created_utc)

    top = _top_comments(comment_list, limit=10)
    item["comment_cards"] = [
        {
            "score": c.get("score", 0),
            "posted": temporal.to_date_str(c.get("created_utc")),
            "author": c.get("author", ""),
            "excerpt": str(c.get("body", ""))[:250],
            "link": f"https://www.reddit.com{c.get('permalink', '')}" if c.get("permalink") else "",
        }
        for c in top
    ]
    item["comment_highlights"] = _extract_insights(top)

    return item
