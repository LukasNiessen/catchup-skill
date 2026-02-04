#
# Data Transformation: Normalizes raw API responses into canonical schema format
# Handles cross-platform data format differences and date validation
#

from typing import Any, Dict, List, TypeVar, Union

from . import dates, schema

ContentItem = TypeVar("ContentItem", schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem, schema.WebSearchItem)


def filter_by_date_range(
    content_items: List[ContentItem],
    range_start: str,
    range_end: str,
    exclude_undated: bool = False,
) -> List[ContentItem]:
    """
    Removes items with verified dates outside the acceptable range.

    This serves as a safety net to ensure no outdated content survives
    even if the upstream API returns items outside the requested window.

    Args:
        content_items: Items to filter
        range_start: Earliest acceptable date (YYYY-MM-DD)
        range_end: Latest acceptable date (YYYY-MM-DD)
        exclude_undated: If True, also removes items without dates

    Returns:
        Filtered list containing only in-range items
    """
    filtered_items = []

    for item in content_items:
        # Handle items without dates
        if item.date is None:
            if not exclude_undated:
                filtered_items.append(item)
            continue

        # Exclude items dated before the range start
        if item.date < range_start:
            continue

        # Exclude items dated after the range end (likely parsing errors)
        if item.date > range_end:
            continue

        filtered_items.append(item)

    return filtered_items


def normalize_reddit_items(
    raw_items: List[Dict[str, Any]],
    range_start: str,
    range_end: str,
) -> List[schema.RedditItem]:
    """
    Transforms raw Reddit API data into normalized RedditItem objects.

    Processes engagement metrics, comment data, and date confidence levels.
    """
    transformed_items = []

    for raw_item in raw_items:
        # Extract and transform engagement metrics
        engagement_metrics = None
        raw_engagement = raw_item.get("engagement")

        if isinstance(raw_engagement, dict):
            engagement_metrics = schema.Engagement(
                score=raw_engagement.get("score"),
                num_comments=raw_engagement.get("num_comments"),
                upvote_ratio=raw_engagement.get("upvote_ratio"),
            )

        # Extract and transform comment data
        comment_list = []
        raw_comments = raw_item.get("top_comments", [])

        for raw_comment in raw_comments:
            transformed_comment = schema.Comment(
                score=raw_comment.get("score", 0),
                date=raw_comment.get("date"),
                author=raw_comment.get("author", ""),
                excerpt=raw_comment.get("excerpt", ""),
                url=raw_comment.get("url", ""),
            )
            comment_list.append(transformed_comment)

        # Assess date reliability
        item_date = raw_item.get("date")
        date_reliability = dates.get_date_confidence(item_date, range_start, range_end)

        # Construct normalized item
        normalized_item = schema.RedditItem(
            id=raw_item.get("id", ""),
            title=raw_item.get("title", ""),
            url=raw_item.get("url", ""),
            subreddit=raw_item.get("subreddit", ""),
            date=item_date,
            date_confidence=date_reliability,
            engagement=engagement_metrics,
            top_comments=comment_list,
            comment_insights=raw_item.get("comment_insights", []),
            relevance=raw_item.get("relevance", 0.5),
            why_relevant=raw_item.get("why_relevant", ""),
        )

        transformed_items.append(normalized_item)

    return transformed_items


def normalize_x_items(
    raw_items: List[Dict[str, Any]],
    range_start: str,
    range_end: str,
) -> List[schema.XItem]:
    """
    Transforms raw X/Twitter API data into normalized XItem objects.

    Processes engagement metrics and date confidence levels.
    """
    transformed_items = []

    for raw_item in raw_items:
        # Extract and transform engagement metrics
        engagement_metrics = None
        raw_engagement = raw_item.get("engagement")

        if isinstance(raw_engagement, dict):
            engagement_metrics = schema.Engagement(
                likes=raw_engagement.get("likes"),
                reposts=raw_engagement.get("reposts"),
                replies=raw_engagement.get("replies"),
                quotes=raw_engagement.get("quotes"),
            )

        # Assess date reliability
        item_date = raw_item.get("date")
        date_reliability = dates.get_date_confidence(item_date, range_start, range_end)

        # Construct normalized item
        normalized_item = schema.XItem(
            id=raw_item.get("id", ""),
            text=raw_item.get("text", ""),
            url=raw_item.get("url", ""),
            author_handle=raw_item.get("author_handle", ""),
            date=item_date,
            date_confidence=date_reliability,
            engagement=engagement_metrics,
            relevance=raw_item.get("relevance", 0.5),
            why_relevant=raw_item.get("why_relevant", ""),
        )

        transformed_items.append(normalized_item)

    return transformed_items


def normalize_youtube_items(
    raw_items: List[Dict[str, Any]],
    range_start: str,
    range_end: str,
) -> List[schema.YouTubeItem]:
    """
    Transforms raw YouTube API data into normalized YouTubeItem objects.

    Processes view counts, likes, and date confidence levels.
    """
    transformed_items = []

    for raw_item in raw_items:
        # Extract and transform engagement metrics
        engagement_metrics = None
        view_count = raw_item.get("views")
        like_count = raw_item.get("likes")

        if view_count is not None or like_count is not None:
            engagement_metrics = schema.Engagement(
                views=view_count,
                likes=like_count,
            )

        # Assess date reliability
        item_date = raw_item.get("date")
        date_reliability = dates.get_date_confidence(item_date, range_start, range_end)

        # Construct normalized item
        normalized_item = schema.YouTubeItem(
            id=raw_item.get("id", ""),
            title=raw_item.get("title", ""),
            url=raw_item.get("url", ""),
            channel_name=raw_item.get("channel_name", ""),
            date=item_date,
            date_confidence=date_reliability,
            engagement=engagement_metrics,
            description=raw_item.get("description"),
            relevance=raw_item.get("relevance", 0.5),
            why_relevant=raw_item.get("why_relevant", ""),
        )

        transformed_items.append(normalized_item)

    return transformed_items


def normalize_linkedin_items(
    raw_items: List[Dict[str, Any]],
    range_start: str,
    range_end: str,
) -> List[schema.LinkedInItem]:
    """
    Transforms raw LinkedIn API data into normalized LinkedInItem objects.

    Processes reaction counts, comments, and date confidence levels.
    """
    transformed_items = []

    for raw_item in raw_items:
        # Extract and transform engagement metrics
        engagement_metrics = None
        reaction_count = raw_item.get("reactions")
        comment_count = raw_item.get("comments")

        if reaction_count is not None or comment_count is not None:
            engagement_metrics = schema.Engagement(
                reactions=reaction_count,
                comments=comment_count,
            )

        # Assess date reliability
        item_date = raw_item.get("date")
        date_reliability = dates.get_date_confidence(item_date, range_start, range_end)

        # Construct normalized item
        normalized_item = schema.LinkedInItem(
            id=raw_item.get("id", ""),
            text=raw_item.get("text", ""),
            url=raw_item.get("url", ""),
            author_name=raw_item.get("author_name", ""),
            author_title=raw_item.get("author_title"),
            date=item_date,
            date_confidence=date_reliability,
            engagement=engagement_metrics,
            relevance=raw_item.get("relevance", 0.5),
            why_relevant=raw_item.get("why_relevant", ""),
        )

        transformed_items.append(normalized_item)

    return transformed_items


def items_to_dicts(content_items: List) -> List[Dict[str, Any]]:
    """Converts schema objects to dictionaries for JSON serialization."""
    return [item.to_dict() for item in content_items]
