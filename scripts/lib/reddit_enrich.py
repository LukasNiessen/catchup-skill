"""Enrich Reddit items with real engagement data from thread JSON."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import http, dates


def _parse_url(url: str) -> Optional[str]:
    """Extract the path from a Reddit URL, or None if not reddit.com."""
    try:
        parsed = urlparse(url)
        if "reddit.com" not in parsed.netloc:
            return None
        return parsed.path
    except:
        return None


def _fetch_thread(url: str, mock_data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    """Fetch the JSON representation of a Reddit thread."""
    if mock_data is not None:
        return mock_data

    path = _parse_url(url)
    if path is None:
        return None

    try:
        return http.reddit_json(path)
    except http.HTTPError:
        return None


def _parse_thread(raw_data: Any) -> Dict[str, Any]:
    """Parse Reddit's JSON array into submission + comments."""
    components = {
        "submission": None,
        "comments": [],
    }

    if not isinstance(raw_data, list) or len(raw_data) < 1:
        return components

    # Submission lives in the first listing
    listing = raw_data[0]
    if isinstance(listing, dict):
        children = listing.get("data", {}).get("children", [])
        if children:
            sub = children[0].get("data", {})
            components["submission"] = {
                "score": sub.get("score"),
                "num_comments": sub.get("num_comments"),
                "upvote_ratio": sub.get("upvote_ratio"),
                "created_utc": sub.get("created_utc"),
                "permalink": sub.get("permalink"),
                "title": sub.get("title"),
                "selftext": sub.get("selftext", "")[:600],
            }

    # Comments live in the second listing
    if len(raw_data) >= 2:
        comment_listing = raw_data[1]
        if isinstance(comment_listing, dict):
            for child in comment_listing.get("data", {}).get("children", []):
                if child.get("kind") != "t1":
                    continue

                cdata = child.get("data", {})
                body = cdata.get("body")
                if not body:
                    continue

                components["comments"].append({
                    "score": cdata.get("score", 0),
                    "created_utc": cdata.get("created_utc"),
                    "author": cdata.get("author", "[deleted]"),  # Reddit's default for deleted accounts
                    "body": cdata.get("body", "")[:350],
                    "permalink": cdata.get("permalink"),
                })

    return components


def _top_comments(comments: List[Dict], limit: int = 12) -> List[Dict[str, Any]]:
    """Return the highest-scoring comments, excluding deleted authors."""
    excluded = {"[deleted]", "[removed]"}
    valid = [c for c in comments if c.get("author") not in excluded]
    ranked = sorted(valid, key=lambda c: c.get("score", 0), reverse=True)
    return ranked[:limit]


def _extract_insights(comments: List[Dict], limit: int = 6) -> List[str]:
    """Pull substantive insights from top comments, skipping low-value noise."""
    insights = []
    candidates = comments[:limit * 3]

    low_value_patterns = [
        r'^(yep|nope|same|agreed|this|exactly|thanks|thank\s*you|yes|no|ok|okay)\.?!?$',
        r'^(lol|lmao|rofl|haha|heh)+$',
        r'^\[(deleted|removed)\]$',
    ]

    for comment in candidates:
        body = comment.get("body", "").strip()

        if len(body) < 25:
            continue

        body_lower = body.lower()
        if any(re.match(pat, body_lower) for pat in low_value_patterns):
            continue

        # Truncate to a meaningful excerpt
        excerpt = body[:180]

        if len(body) > 180:
            found_boundary = False
            for i, ch in enumerate(excerpt):
                if ch in '.!?;' and i > 65:
                    excerpt = excerpt[:i + 1]
                    found_boundary = True
                    break

            if not found_boundary:
                excerpt = excerpt.rstrip() + "..."

        insights.append(excerpt)

        if len(insights) >= limit:
            break

    return insights


def enrich(
    item: Dict[str, Any],
    mock_json: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Augment a Reddit item with real engagement data from the thread."""
    thread_url = item.get("url", "")

    thread_data = _fetch_thread(thread_url, mock_json)
    if thread_data is None:
        return item

    parsed = _parse_thread(thread_data)
    submission = parsed.get("submission")
    comment_list = parsed.get("comments", [])

    # Populate engagement from the actual submission
    if submission is not None:
        item["engagement"] = {
            "score": submission.get("score"),
            "num_comments": submission.get("num_comments"),
            "upvote_ratio": submission.get("upvote_ratio"),
        }

        created = submission.get("created_utc")
        if created is not None:
            item["date"] = dates.timestamp_to_date(created)

    # Attach top comments
    best = _top_comments(comment_list)
    item["top_comments"] = []

    for comment in best:
        permalink = comment.get("permalink", "")
        comment_url = f"https://www.reddit.com{permalink}" if permalink else ""

        item["top_comments"].append({
            "score": comment.get("score", 0),
            "date": dates.timestamp_to_date(comment.get("created_utc")),
            "author": comment.get("author", ""),
            "excerpt": comment.get("body", "")[:250],
            "url": comment_url,
        })

    # Distil discussion insights
    item["comment_insights"] = _extract_insights(best)

    return item
