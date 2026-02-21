"""Content domain models and normalization helpers."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from . import temporal


class Source(Enum):
    REDDIT = "reddit"
    X = "x"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    WEB = "web"


@dataclass
class Engagement:
    """Platform-neutral engagement stats."""

    composite: Optional[float] = None
    upvotes: Optional[int] = None
    comments: Optional[int] = None
    vote_ratio: Optional[float] = None
    likes: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    quotes: Optional[int] = None
    views: Optional[int] = None
    reactions: Optional[int] = None
    bookmarks: Optional[int] = None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        payload = {}
        for key in (
            "composite",
            "upvotes",
            "comments",
            "vote_ratio",
            "likes",
            "reposts",
            "replies",
            "quotes",
            "views",
            "reactions",
            "bookmarks",
        ):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload or None


@dataclass
class CommentNote:
    """A notable thread comment."""

    score: int
    posted: Optional[str]
    author: str
    excerpt: str
    link: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["score"] = int(payload.get("score", 0))
        return payload


@dataclass
class ScoreParts:
    """Score breakdown per dimension."""

    signal: int = 0
    freshness: int = 0
    engagement: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class ContentItem:
    """Unified content item spanning all sources."""

    uid: str
    source: Source
    title: str
    link: str
    author: str = ""
    summary: str = ""
    published: Optional[str] = None
    date_quality: str = "low"
    engagement: Optional[Engagement] = None
    signal: float = 0.5
    reason: str = ""
    score: int = 0
    score_parts: ScoreParts = field(default_factory=ScoreParts)
    comments: List[CommentNote] = field(default_factory=list)
    comment_highlights: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "source": self.source.value,
            "title": self.title,
            "link": self.link,
            "author": self.author,
            "summary": self.summary,
            "published": self.published,
            "date_quality": self.date_quality,
            "engagement": self.engagement.to_dict() if self.engagement else None,
            "signal": self.signal,
            "reason": self.reason,
            "score": self.score,
            "score_parts": self.score_parts.to_dict(),
            "comments": [c.to_dict() for c in self.comments],
            "comment_highlights": self.comment_highlights,
            "meta": self.meta,
        }


@dataclass
class Report:
    """Aggregated research output with metadata."""

    topic: str
    range_start: str
    range_end: str
    generated_at: str
    mode: str
    openai_model_used: Optional[str] = None
    xai_model_used: Optional[str] = None
    items: List[ContentItem] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    prompt_pack: List[str] = field(default_factory=list)
    context_snippet_md: str = ""
    errors: Dict[str, str] = field(default_factory=dict)
    from_cache: bool = False
    cache_age_hours: Optional[float] = None
    search_duration_seconds: Optional[float] = None
    item_count: int = 0

    @property
    def reddit(self) -> List[ContentItem]:
        return [i for i in self.items if i.source == Source.REDDIT]

    @property
    def x(self) -> List[ContentItem]:
        return [i for i in self.items if i.source == Source.X]

    @property
    def youtube(self) -> List[ContentItem]:
        return [i for i in self.items if i.source == Source.YOUTUBE]

    @property
    def linkedin(self) -> List[ContentItem]:
        return [i for i in self.items if i.source == Source.LINKEDIN]

    @property
    def web(self) -> List[ContentItem]:
        return [i for i in self.items if i.source == Source.WEB]

    @property
    def reddit_error(self) -> Optional[str]:
        return self.errors.get("reddit")

    @reddit_error.setter
    def reddit_error(self, value: Optional[str]):
        if value is not None:
            self.errors["reddit"] = value

    @property
    def x_error(self) -> Optional[str]:
        return self.errors.get("x")

    @x_error.setter
    def x_error(self, value: Optional[str]):
        if value is not None:
            self.errors["x"] = value

    @property
    def youtube_error(self) -> Optional[str]:
        return self.errors.get("youtube")

    @youtube_error.setter
    def youtube_error(self, value: Optional[str]):
        if value is not None:
            self.errors["youtube"] = value

    @property
    def linkedin_error(self) -> Optional[str]:
        return self.errors.get("linkedin")

    @linkedin_error.setter
    def linkedin_error(self, value: Optional[str]):
        if value is not None:
            self.errors["linkedin"] = value

    @property
    def web_error(self) -> Optional[str]:
        return self.errors.get("web")

    @web_error.setter
    def web_error(self, value: Optional[str]):
        if value is not None:
            self.errors["web"] = value

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "topic": self.topic,
            "range": {"from": self.range_start, "to": self.range_end},
            "generated_at": self.generated_at,
            "mode": self.mode,
            "openai_model_used": self.openai_model_used,
            "xai_model_used": self.xai_model_used,
            "reddit": [item.to_dict() for item in self.reddit],
            "x": [item.to_dict() for item in self.x],
            "youtube": [item.to_dict() for item in self.youtube],
            "linkedin": [item.to_dict() for item in self.linkedin],
            "web": [item.to_dict() for item in self.web],
            "best_practices": self.best_practices,
            "prompt_pack": self.prompt_pack,
            "context_snippet_md": self.context_snippet_md,
        }
        for platform, msg in self.errors.items():
            payload[f"{platform}_error"] = msg
        if self.from_cache:
            payload["from_cache"] = self.from_cache
        if self.cache_age_hours is not None:
            payload["cache_age_hours"] = self.cache_age_hours
        if self.search_duration_seconds is not None:
            payload["search_duration_seconds"] = self.search_duration_seconds
        if self.item_count:
            payload["item_count"] = self.item_count
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        range_section = data.get("range", {})
        start = range_section.get("from", data.get("range_start", ""))
        end = range_section.get("to", data.get("range_end", ""))

        items: List[ContentItem] = []
        for platform, source_enum in [
            ("reddit", Source.REDDIT),
            ("x", Source.X),
            ("youtube", Source.YOUTUBE),
            ("linkedin", Source.LINKEDIN),
            ("web", Source.WEB),
        ]:
            for item_data in data.get(platform, []):
                items.append(_item_from_dict(item_data, source_enum))

        errors = {}
        for platform in ("reddit", "x", "youtube", "linkedin", "web"):
            err = data.get(f"{platform}_error")
            if err:
                errors[platform] = err

        item_count = data.get("item_count", 0)
        if not item_count:
            item_count = sum(
                len(data.get(k, []))
                for k in ("reddit", "x", "youtube", "linkedin", "web")
            )

        return cls(
            topic=data["topic"],
            range_start=start,
            range_end=end,
            generated_at=data["generated_at"],
            mode=data["mode"],
            openai_model_used=data.get("openai_model_used"),
            xai_model_used=data.get("xai_model_used"),
            items=items,
            best_practices=data.get("best_practices", []),
            prompt_pack=data.get("prompt_pack", []),
            context_snippet_md=data.get("context_snippet_md", ""),
            errors=errors,
            from_cache=data.get("from_cache", False),
            cache_age_hours=data.get("cache_age_hours"),
            search_duration_seconds=data.get("search_duration_seconds"),
            item_count=item_count,
        )


def _item_from_dict(d: Dict[str, Any], source: Source) -> ContentItem:
    eng = Engagement(**d["engagement"]) if d.get("engagement") else None
    comments = [CommentNote(**comment) for comment in d.get("comments", [])]
    parts = d.get("score_parts", {})
    score_parts = ScoreParts(**parts) if parts else ScoreParts()

    return ContentItem(
        uid=d.get("uid", ""),
        source=source,
        title=d.get("title", ""),
        link=d.get("link", ""),
        author=d.get("author", ""),
        summary=d.get("summary", ""),
        published=d.get("published"),
        date_quality=d.get("date_quality", "low"),
        engagement=eng,
        signal=d.get("signal", 0.5),
        reason=d.get("reason", ""),
        score=d.get("score", 0),
        score_parts=score_parts,
        comments=comments,
        comment_highlights=d.get("comment_highlights", []),
        meta=d.get("meta", {}),
    )


def build_report(
    topic: str,
    start: str,
    end: str,
    mode: str,
    openai_model: Optional[str] = None,
    xai_model: Optional[str] = None,
    **kwargs,
) -> Report:
    return Report(
        topic=topic,
        range_start=start,
        range_end=end,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
        openai_model_used=openai_model,
        xai_model_used=xai_model,
        **kwargs,
    )


def _safe_log1p(value: Optional[int]) -> float:
    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric < 0:
        return 0.0
    return math.log1p(numeric)


def _weighted_sum(components: List[tuple]) -> float:
    return sum(weight * value for weight, value in components)


def _reddit_composite(sig: Engagement) -> float:
    return _weighted_sum(
        [
            (0.48, _safe_log1p(sig.upvotes)),
            (0.37, _safe_log1p(sig.comments)),
            (0.15, (sig.vote_ratio or 0.5) * 12),
        ]
    )


def _x_composite(sig: Engagement) -> float:
    return _weighted_sum(
        [
            (0.45, _safe_log1p(sig.likes)),
            (0.28, _safe_log1p(sig.reposts)),
            (0.17, _safe_log1p(sig.replies)),
            (0.10, _safe_log1p(sig.quotes)),
        ]
    )


def _youtube_composite(sig: Engagement) -> float:
    return _weighted_sum([(0.62, _safe_log1p(sig.views)), (0.38, _safe_log1p(sig.likes))])


def _linkedin_composite(sig: Engagement) -> float:
    return _weighted_sum([(0.55, _safe_log1p(sig.reactions)), (0.45, _safe_log1p(sig.comments))])


def from_reddit_raw(entry: Dict[str, Any], start: str, end: str) -> ContentItem:
    sig = None
    metrics = entry.get("metrics")
    if isinstance(metrics, dict):
        sig = Engagement(
            upvotes=metrics.get("upvotes"),
            comments=metrics.get("comments"),
            vote_ratio=metrics.get("vote_ratio"),
        )
        if sig.upvotes is not None or sig.comments is not None:
            sig.composite = _reddit_composite(sig)

    comments = [
        CommentNote(
            score=comment.get("score", 0),
            posted=comment.get("posted"),
            author=comment.get("author", ""),
            excerpt=comment.get("excerpt", ""),
            link=comment.get("link", ""),
        )
        for comment in entry.get("comment_cards", [])
    ]

    item_date = entry.get("posted")
    trust = temporal.trust_level(item_date, start, end)

    return ContentItem(
        uid=entry.get("uid", ""),
        source=Source.REDDIT,
        title=entry.get("title", ""),
        link=entry.get("link", ""),
        author=entry.get("community", ""),
        published=item_date,
        date_quality=trust,
        engagement=sig,
        comments=comments,
        comment_highlights=entry.get("comment_highlights", []),
        signal=entry.get("signal", 0.5),
        reason=entry.get("reason", ""),
        meta={
            "subreddit": entry.get("community", ""),
            "flair": entry.get("flair", ""),
        },
    )


def from_x_raw(entry: Dict[str, Any], start: str, end: str) -> ContentItem:
    sig = None
    metrics = entry.get("metrics")
    if isinstance(metrics, dict):
        sig = Engagement(
            likes=metrics.get("likes"),
            reposts=metrics.get("reposts"),
            replies=metrics.get("replies"),
            quotes=metrics.get("quotes"),
        )
        if sig.likes is not None or sig.reposts is not None:
            sig.composite = _x_composite(sig)

    item_date = entry.get("posted")
    trust = temporal.trust_level(item_date, start, end)

    return ContentItem(
        uid=entry.get("uid", ""),
        source=Source.X,
        title=entry.get("excerpt", ""),
        link=entry.get("link", ""),
        author=entry.get("handle", ""),
        published=item_date,
        date_quality=trust,
        engagement=sig,
        signal=entry.get("signal", 0.5),
        reason=entry.get("reason", ""),
        meta={
            "is_repost": bool(entry.get("is_repost", False)),
            "language": entry.get("language", "en"),
        },
    )


def from_youtube_raw(entry: Dict[str, Any], start: str, end: str) -> ContentItem:
    sig = None
    metrics = entry.get("metrics")
    if isinstance(metrics, dict):
        sig = Engagement(views=metrics.get("views"), likes=metrics.get("likes"))
        sig.composite = _youtube_composite(sig)

    item_date = entry.get("posted")
    trust = temporal.trust_level(item_date, start, end)

    return ContentItem(
        uid=entry.get("uid", ""),
        source=Source.YOUTUBE,
        title=entry.get("title", ""),
        link=entry.get("link", ""),
        author=entry.get("channel", ""),
        summary=entry.get("summary") or "",
        published=item_date,
        date_quality=trust,
        engagement=sig,
        signal=entry.get("signal", 0.5),
        reason=entry.get("reason", ""),
        meta={
            "duration_seconds": entry.get("duration_seconds"),
        },
    )


def from_linkedin_raw(entry: Dict[str, Any], start: str, end: str) -> ContentItem:
    sig = None
    metrics = entry.get("metrics")
    if isinstance(metrics, dict):
        sig = Engagement(reactions=metrics.get("reactions"), comments=metrics.get("comments"))
        sig.composite = _linkedin_composite(sig)

    item_date = entry.get("posted")
    trust = temporal.trust_level(item_date, start, end)

    return ContentItem(
        uid=entry.get("uid", ""),
        source=Source.LINKEDIN,
        title=entry.get("excerpt", ""),
        link=entry.get("link", ""),
        author=entry.get("author", ""),
        published=item_date,
        date_quality=trust,
        engagement=sig,
        signal=entry.get("signal", 0.5),
        reason=entry.get("reason", ""),
        meta={
            "author_title": entry.get("role"),
        },
    )


def from_web_raw(entry: Dict[str, Any], start: str, end: str) -> ContentItem:
    item_date = entry.get("posted")
    trust = entry.get("date_quality", "low")

    return ContentItem(
        uid=entry.get("uid", ""),
        source=Source.WEB,
        title=entry.get("title", ""),
        link=entry.get("link", ""),
        author=entry.get("domain", ""),
        summary=entry.get("snippet", ""),
        published=item_date,
        date_quality=trust,
        signal=entry.get("signal", 0.45),
        reason=entry.get("reason", ""),
        meta={
            "source_domain": entry.get("domain", ""),
            "language": entry.get("language", "en"),
        },
    )


_FACTORY = {
    Source.REDDIT: from_reddit_raw,
    Source.X: from_x_raw,
    Source.YOUTUBE: from_youtube_raw,
    Source.LINKEDIN: from_linkedin_raw,
    Source.WEB: from_web_raw,
}


def items_from_raw(raw_items: List[Dict[str, Any]], source: Source, start: str, end: str) -> List[ContentItem]:
    converter: Callable[[Dict[str, Any], str, str], ContentItem] = _FACTORY[source]
    return [converter(entry, start, end) for entry in raw_items]


def filter_by_date(
    items: List[ContentItem],
    start: str,
    end: str,
    exclude_undated: bool = False,
) -> List[ContentItem]:
    selected: List[ContentItem] = []
    for item in items:
        if item.published is None:
            if not exclude_undated:
                selected.append(item)
            continue
        if item.published < start:
            continue
        if item.published > end:
            continue
        selected.append(item)
    return selected


def as_dicts(items: List[ContentItem]) -> List[Dict[str, Any]]:
    return [item.to_dict() for item in items]
