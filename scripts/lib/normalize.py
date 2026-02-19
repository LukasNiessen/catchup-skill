"""Normalize raw API responses into canonical schema objects."""

from typing import Any, Dict, List, TypeVar

from . import dates, schema

ItemT = TypeVar("ItemT", schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem, schema.WebSearchItem)


def filter_dates(
    items: List[ItemT],
    start: str,
    end: str,
    exclude_undated: bool = False,
) -> List[ItemT]:
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

    for entry in raw_items:
        eng = None
        raw_eng = entry.get("engagement")
        if isinstance(raw_eng, dict):
            eng = schema.Engagement(
                score=raw_eng.get("score"),
                num_comments=raw_eng.get("num_comments"),
                upvote_ratio=raw_eng.get("upvote_ratio"),
            )

        comments = []
        for rc in entry.get("top_comments", []):
            comments.append(schema.Comment(
                score=rc.get("score", 0),
                date=rc.get("date"),
                author=rc.get("author", ""),
                excerpt=rc.get("excerpt", ""),
                url=rc.get("url", ""),
            ))

        item_date = entry.get("date")
        confidence = dates.date_confidence(item_date, start, end)

        item = schema.RedditItem(
            id=entry.get("id", ""),
            title=entry.get("title", ""),
            url=entry.get("url", ""),
            subreddit=entry.get("subreddit", ""),
            date=item_date,
            date_confidence=confidence,
            engagement=eng,
            top_comments=comments,
            comment_insights=entry.get("comment_insights", []),
            relevance=entry.get("relevance", 0.5),
            why_relevant=entry.get("why_relevant", ""),
            flair=entry.get("flair", ""),
        )
        result.append(item)

    return result


def to_x(
    raw_items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[schema.XItem]:
    """Transform raw X/Twitter API data into XItem objects."""
    result = []

    for post in raw_items:
        eng = None
        raw_eng = post.get("engagement")
        if isinstance(raw_eng, dict):
            eng = schema.Engagement(
                likes=raw_eng.get("likes"),
                reposts=raw_eng.get("reposts"),
                replies=raw_eng.get("replies"),
                quotes=raw_eng.get("quotes"),
            )

        item_date = post.get("date")
        confidence = dates.date_confidence(item_date, start, end)

        item = schema.XItem(
            id=post.get("id", ""),
            text=post.get("text", ""),
            url=post.get("url", ""),
            author_handle=post.get("author_handle", ""),
            date=item_date,
            date_confidence=confidence,
            engagement=eng,
            relevance=post.get("relevance", 0.5),
            why_relevant=post.get("why_relevant", ""),
            is_repost=bool(post.get("is_repost", False)),
        )
        result.append(item)

    return result


def to_youtube(
    raw_items: List[Dict[str, Any]],
    start: str,
    end: str,
) -> List[schema.YouTubeItem]:
    """Transform raw YouTube API data into YouTubeItem objects."""
    result = []

    for vid in raw_items:
        eng = None
        view_count = vid.get("views")
        like_count = vid.get("likes")
        if view_count is not None or like_count is not None:
            eng = schema.Engagement(
                views=view_count,
                likes=like_count,
            )

        item_date = vid.get("date")
        confidence = dates.date_confidence(item_date, start, end)

        result.append(schema.YouTubeItem(
            id=vid.get("id", ""),
            title=vid.get("title", ""),
            url=vid.get("url", ""),
            channel_name=vid.get("channel_name", ""),
            date=item_date,
            date_confidence=confidence,
            engagement=eng,
            description=vid.get("description"),
            relevance=vid.get("relevance", 0.5),
            why_relevant=vid.get("why_relevant", ""),
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
