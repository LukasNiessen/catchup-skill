#
# Thread Enrichment: Fetches real engagement metrics from Reddit's JSON API
# Augments discovered threads with upvotes, comments, and community insights
#

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import http, dates


def parse_reddit_url_path(thread_url: str) -> Optional[str]:
    """
    Extracts the path component from a Reddit URL.

    Returns None if the URL is not from reddit.com.
    """
    try:
        parsed_components = urlparse(thread_url)

        if "reddit.com" not in parsed_components.netloc:
            return None

        return parsed_components.path
    except:
        return None


# Preserve the original function name for API compatibility
extract_reddit_path = parse_reddit_url_path


def retrieve_thread_json(thread_url: str, mock_data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    """
    Fetches the JSON representation of a Reddit thread.

    Args:
        thread_url: Full Reddit thread URL
        mock_data: Optional mock data for testing

    Returns:
        Parsed JSON data or None on failure
    """
    if mock_data is not None:
        return mock_data

    url_path = parse_reddit_url_path(thread_url)

    if url_path is None:
        return None

    try:
        response_data = http.get_reddit_json(url_path)
        return response_data
    except http.HTTPError:
        return None


# Preserve the original function name for API compatibility
fetch_thread_data = retrieve_thread_json


def extract_thread_components(raw_data: Any) -> Dict[str, Any]:
    """
    Parses Reddit's JSON structure into a structured representation.

    Reddit returns an array where:
    - Element 0: The submission (post) listing
    - Element 1: The comments listing
    """
    components = {
        "submission": None,
        "comments": [],
    }

    # Validate input structure
    if not isinstance(raw_data, list):
        return components

    if len(raw_data) < 1:
        return components

    # Extract submission from first element
    submission_listing = raw_data[0]

    if isinstance(submission_listing, dict):
        child_elements = submission_listing.get("data", {}).get("children", [])

        if len(child_elements) > 0:
            submission_data = child_elements[0].get("data", {})

            components["submission"] = {
                "score": submission_data.get("score"),
                "num_comments": submission_data.get("num_comments"),
                "upvote_ratio": submission_data.get("upvote_ratio"),
                "created_utc": submission_data.get("created_utc"),
                "permalink": submission_data.get("permalink"),
                "title": submission_data.get("title"),
                "selftext": submission_data.get("selftext", "")[:500],
            }

    # Extract comments from second element
    if len(raw_data) >= 2:
        comments_listing = raw_data[1]

        if isinstance(comments_listing, dict):
            child_elements = comments_listing.get("data", {}).get("children", [])

            for child_element in child_elements:
                # Filter to actual comments (kind = t1)
                if child_element.get("kind") != "t1":
                    continue

                comment_data = child_element.get("data", {})

                # Skip comments without body text
                comment_body = comment_data.get("body")
                if not comment_body:
                    continue

                comment_record = {
                    "score": comment_data.get("score", 0),
                    "created_utc": comment_data.get("created_utc"),
                    "author": comment_data.get("author", "[deleted]"),
                    "body": comment_data.get("body", "")[:300],
                    "permalink": comment_data.get("permalink"),
                }

                components["comments"].append(comment_record)

    return components


# Preserve the original function name for API compatibility
parse_thread_data = extract_thread_components


def select_top_comments(comment_list: List[Dict], maximum_count: int = 10) -> List[Dict[str, Any]]:
    """
    Selects the highest-scored comments from a thread.

    Filters out deleted/removed comments before sorting.
    """
    # Exclude deleted or removed authors
    excluded_authors = {"[deleted]", "[removed]"}
    valid_comments = [
        comment for comment in comment_list
        if comment.get("author") not in excluded_authors
    ]

    # Sort by score in descending order
    sorted_comments = sorted(
        valid_comments,
        key=lambda c: c.get("score", 0),
        reverse=True
    )

    return sorted_comments[:maximum_count]


# Preserve the original function name for API compatibility
get_top_comments = select_top_comments


def distill_comment_insights(comment_list: List[Dict], maximum_count: int = 7) -> List[str]:
    """
    Extracts key insights from the top comments.

    Uses heuristics to identify substantive, actionable comments
    rather than simple agreement/disagreement responses.
    """
    insights_collected = []

    # Process more comments than needed to account for filtering
    comments_to_examine = comment_list[:maximum_count * 2]

    for comment in comments_to_examine:
        comment_body = comment.get("body", "").strip()

        # Skip short comments
        if len(comment_body) < 30:
            continue

        # Skip low-value response patterns
        low_value_patterns = [
            r'^(this|same|agreed|exactly|yep|nope|yes|no|thanks|thank you)\.?$',
            r'^lol|lmao|haha',
            r'^\[deleted\]',
            r'^\[removed\]',
        ]

        body_lower = comment_body.lower()
        is_low_value = any(re.match(pattern, body_lower) for pattern in low_value_patterns)

        if is_low_value:
            continue

        # Truncate to a meaningful excerpt
        insight_text = comment_body[:150]

        if len(comment_body) > 150:
            # Attempt to find a natural sentence boundary
            boundary_found = False
            char_index = 0

            while char_index < len(insight_text):
                current_char = insight_text[char_index]

                if current_char in '.!?' and char_index > 50:
                    insight_text = insight_text[:char_index + 1]
                    boundary_found = True
                    break

                char_index += 1

            if not boundary_found:
                insight_text = insight_text.rstrip() + "..."

        insights_collected.append(insight_text)

        if len(insights_collected) >= maximum_count:
            break

    return insights_collected


# Preserve the original function name for API compatibility
extract_comment_insights = distill_comment_insights


def enrich_reddit_item(
    item_data: Dict[str, Any],
    mock_thread_json: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Augments a Reddit item with real engagement metrics from the thread.

    Fetches the actual thread data and extracts:
    - Upvote score
    - Comment count
    - Upvote ratio
    - Top comments with excerpts
    - Distilled insights from discussion
    """
    thread_url = item_data.get("url", "")

    # Retrieve thread JSON
    thread_json = retrieve_thread_json(thread_url, mock_thread_json)

    if thread_json is None:
        return item_data

    # Parse the JSON structure
    parsed_components = extract_thread_components(thread_json)
    submission_data = parsed_components.get("submission")
    comment_data = parsed_components.get("comments", [])

    # Update engagement metrics from actual data
    if submission_data is not None:
        item_data["engagement"] = {
            "score": submission_data.get("score"),
            "num_comments": submission_data.get("num_comments"),
            "upvote_ratio": submission_data.get("upvote_ratio"),
        }

        # Update date from actual creation timestamp
        creation_timestamp = submission_data.get("created_utc")

        if creation_timestamp is not None:
            item_data["date"] = dates.timestamp_to_date(creation_timestamp)

    # Extract top comments
    top_comments = select_top_comments(comment_data)
    item_data["top_comments"] = []

    for comment in top_comments:
        comment_permalink = comment.get("permalink", "")
        comment_url = "https://reddit.com{}".format(comment_permalink) if comment_permalink else ""

        formatted_comment = {
            "score": comment.get("score", 0),
            "date": dates.timestamp_to_date(comment.get("created_utc")),
            "author": comment.get("author", ""),
            "excerpt": comment.get("body", "")[:200],
            "url": comment_url,
        }

        item_data["top_comments"].append(formatted_comment)

    # Extract discussion insights
    item_data["comment_insights"] = distill_comment_insights(top_comments)

    return item_data
