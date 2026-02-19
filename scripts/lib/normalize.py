"""Normalize raw API responses into canonical schema objects."""

from typing import Any, Dict, List, TypeVar

from . import dates, schema

ContentItem = TypeVar("ContentItem", schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem, schema.WebSearchItem)


def filter_dates(
    items: List[ContentItem],
    start: str,
    end: str,
    exclude_undated: bool = False,
) -> List[ContentItem]:
    """Remove items with verified dates outside the acceptable range."""
    filtered = []

    for item in items:
        if item.date is None:
            if not exclude_undated:
                filtered.append(item)
            continue

        if item.date < start:
            continue
        if item.date > end:
            continue

        filtered.append(item)

    return filtered


def to_reddit(
    raw_items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[schema.RedditItem]:
    """Transform raw Reddit API data into RedditItem objects."""
    result = []

    for raw in raw_items:
        eng = None
        raw_eng = raw.get("engagement")
        if isinstance(raw_eng, dict):
            eng = schema.Engagement(
                score=raw_eng.get("score"),
                num_comments=raw_eng.get("num_comments"),
                upvote_ratio=raw_eng.get("upvote_ratio"),
            )

        comments = []
        for rc in raw.get("top_comments", []):
            comments.append(schema.Comment(
                score=rc.get("score", 0),
                date=rc.get("date"),
                author=rc.get("author", ""),
                excerpt=rc.get("excerpt", ""),
                url=rc.get("url", ""),
            ))

        item_date = raw.get("date")
        confidence = dates.date_confidence(item_date, start, end)

        result.append(schema.RedditItem(
            id=raw.get("id", ""),
            title=raw.get("title", ""),
            url=raw.get("url", ""),
            subreddit=raw.get("subreddit", ""),
            date=item_date,
            date_confidence=confidence,
            engagement=eng,
            top_comments=comments,
            comment_insights=raw.get("comment_insights", []),
            relevance=raw.get("relevance", 0.5),
            why_relevant=raw.get("why_relevant", ""),
        ))

    return result


def to_x(
    raw_items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[schema.XItem]:
    """Transform raw X/Twitter API data into XItem objects."""
    result = []

    for raw in raw_items:
        eng = None
        raw_eng = raw.get("engagement")
        if isinstance(raw_eng, dict):
            eng = schema.Engagement(
                likes=raw_eng.get("likes"),
                reposts=raw_eng.get("reposts"),
                replies=raw_eng.get("replies"),
                quotes=raw_eng.get("quotes"),
            )

        item_date = raw.get("date")
        confidence = dates.date_confidence(item_date, start, end)

        result.append(schema.XItem(
            id=raw.get("id", ""),
            text=raw.get("text", ""),
            url=raw.get("url", ""),
            author_handle=raw.get("author_handle", ""),
            date=item_date,
            date_confidence=confidence,
            engagement=eng,
            relevance=raw.get("relevance", 0.5),
            why_relevant=raw.get("why_relevant", ""),
        ))

    return result


def to_youtube(
    raw_items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[schema.YouTubeItem]:
    """Transform raw YouTube API data into YouTubeItem objects."""
    result = []

    for raw in raw_items:
        eng = None
        view_count = raw.get("views")
        like_count = raw.get("likes")
        if view_count is not None or like_count is not None:
            eng = schema.Engagement(
                views=view_count,
                likes=like_count,
            )

        item_date = raw.get("date")
        confidence = dates.date_confidence(item_date, start, end)

        result.append(schema.YouTubeItem(
            id=raw.get("id", ""),
            title=raw.get("title", ""),
            url=raw.get("url", ""),
            channel_name=raw.get("channel_name", ""),
            date=item_date,
            date_confidence=confidence,
            engagement=eng,
            description=raw.get("description"),
            relevance=raw.get("relevance", 0.5),
            why_relevant=raw.get("why_relevant", ""),
        ))

    return result


def to_linkedin(
    raw_items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[schema.LinkedInItem]:
    """Transform raw LinkedIn API data into LinkedInItem objects."""
    result = []

    for raw in raw_items:
        eng = None
        reaction_count = raw.get("reactions")
        comment_count = raw.get("comments")
        if reaction_count is not None or comment_count is not None:
            eng = schema.Engagement(
                reactions=reaction_count,
                comments=comment_count,
            )

        item_date = raw.get("date")
        confidence = dates.date_confidence(item_date, start, end)

        result.append(schema.LinkedInItem(
            id=raw.get("id", ""),
            text=raw.get("text", ""),
            url=raw.get("url", ""),
            author_name=raw.get("author_name", ""),
            author_title=raw.get("author_title"),
            date=item_date,
            date_confidence=confidence,
            engagement=eng,
            relevance=raw.get("relevance", 0.5),
            why_relevant=raw.get("why_relevant", ""),
        ))

    return result


def as_dicts(items: List) -> List[Dict[str, Any]]:
    """Convert schema objects to dicts for JSON serialization."""
    return [item.to_dict() for item in items]
