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
class ScoreBreakdown:
    """Score breakdown per dimension."""

    relevance: int = 0
    timeliness: int = 0
    traction: int = 0
    credibility: int = 0

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
    date_confidence: str = "weak"
    engagement: Optional[Engagement] = None
    relevance: float = 0.5
    reason: str = ""
    score: int = 0
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
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
            "date_confidence": self.date_confidence,
            "engagement": self.engagement.to_dict() if self.engagement else None,
            "relevance": self.relevance,
            "reason": self.reason,
            "score": self.score,
            "breakdown": self.breakdown.to_dict(),
            "comments": [c.to_dict() for c in self.comments],
            "comment_highlights": self.comment_highlights,
            "meta": self.meta,
        }


@dataclass
class Window:
    start: str
    end: str


@dataclass
class ModelUsage:
    openai: Optional[str] = None
    xai: Optional[str] = None


@dataclass
class InsightBundle:
    practice_notes: List[str] = field(default_factory=list)
    prompt_samples: List[str] = field(default_factory=list)
    context_md: str = ""


@dataclass
class CacheState:
    enabled: bool = False
    age_hours: Optional[float] = None


@dataclass
class RunMetrics:
    search_seconds: Optional[float] = None
    item_count: int = 0


@dataclass
class ErrorBag:
    by_source: Dict[str, str] = field(default_factory=dict)

    def get(self, source: str) -> Optional[str]:
        return self.by_source.get(source)

    def set(self, source: str, message: Optional[str]) -> None:
        if message is not None:
            self.by_source[source] = message

    def to_dict(self) -> Dict[str, str]:
        return dict(self.by_source)


@dataclass
class Report:
    """Aggregated research output with metadata."""

    topic: str
    window: Window
    generated_at: str
    mode: str
    models: ModelUsage = field(default_factory=ModelUsage)
    items: List[ContentItem] = field(default_factory=list)
    insights: InsightBundle = field(default_factory=InsightBundle)
    errors: ErrorBag = field(default_factory=ErrorBag)
    cache: CacheState = field(default_factory=CacheState)
    metrics: RunMetrics = field(default_factory=RunMetrics)

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
        self.errors.set("reddit", value)

    @property
    def x_error(self) -> Optional[str]:
        return self.errors.get("x")

    @x_error.setter
    def x_error(self, value: Optional[str]):
        self.errors.set("x", value)

    @property
    def youtube_error(self) -> Optional[str]:
        return self.errors.get("youtube")

    @youtube_error.setter
    def youtube_error(self, value: Optional[str]):
        self.errors.set("youtube", value)

    @property
    def linkedin_error(self) -> Optional[str]:
        return self.errors.get("linkedin")

    @linkedin_error.setter
    def linkedin_error(self, value: Optional[str]):
        self.errors.set("linkedin", value)

    @property
    def web_error(self) -> Optional[str]:
        return self.errors.get("web")

    @web_error.setter
    def web_error(self, value: Optional[str]):
        self.errors.set("web", value)

    @property
    def context_snippet_md(self) -> str:
        return self.insights.context_md

    @context_snippet_md.setter
    def context_snippet_md(self, value: str):
        self.insights.context_md = value

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "topic": self.topic,
            "window": {"start": self.window.start, "end": self.window.end},
            "generated_at": self.generated_at,
            "mode": self.mode,
            "models": {"openai": self.models.openai, "xai": self.models.xai},
            "items": {
                "reddit": [item.to_dict() for item in self.reddit],
                "x": [item.to_dict() for item in self.x],
                "youtube": [item.to_dict() for item in self.youtube],
                "linkedin": [item.to_dict() for item in self.linkedin],
                "web": [item.to_dict() for item in self.web],
            },
            "insights": {
                "practice_notes": list(self.insights.practice_notes),
                "prompt_samples": list(self.insights.prompt_samples),
                "context_md": self.insights.context_md,
            },
        }
        if self.errors.by_source:
            payload["errors"] = self.errors.to_dict()
        if self.cache.enabled:
            payload["cache"] = {
                "enabled": True,
                "age_hours": self.cache.age_hours,
            }
        metrics = {}
        if self.metrics.search_seconds is not None:
            metrics["search_seconds"] = self.metrics.search_seconds
        if self.metrics.item_count:
            metrics["item_count"] = self.metrics.item_count
        if metrics:
            payload["metrics"] = metrics
        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        window_data = data.get("window") or {}
        range_section = data.get("range", {}) if not window_data else {}
        start = (
            window_data.get("start")
            or window_data.get("from")
            or range_section.get("from")
            or data.get("range_start", "")
        )
        end = (
            window_data.get("end")
            or window_data.get("to")
            or range_section.get("to")
            or data.get("range_end", "")
        )

        items: List[ContentItem] = []
        item_block = data.get("items", {}) if isinstance(data.get("items"), dict) else {}

        for platform, source_enum in [
            ("reddit", Source.REDDIT),
            ("x", Source.X),
            ("youtube", Source.YOUTUBE),
            ("linkedin", Source.LINKEDIN),
            ("web", Source.WEB),
        ]:
            raw_list = item_block.get(platform)
            if raw_list is None:
                raw_list = data.get(platform, [])
            for item_data in raw_list or []:
                items.append(_item_from_dict(item_data, source_enum))

        errors = ErrorBag()
        error_block = data.get("errors")
        if isinstance(error_block, dict):
            for key, val in error_block.items():
                if val:
                    errors.set(key, str(val))
        else:
            for platform in ("reddit", "x", "youtube", "linkedin", "web"):
                err = data.get(f"{platform}_error")
                if err:
                    errors.set(platform, err)

        insights_block = data.get("insights", {}) if isinstance(data.get("insights"), dict) else {}
        insights = InsightBundle(
            practice_notes=insights_block.get("practice_notes", data.get("best_practices", [])),
            prompt_samples=insights_block.get("prompt_samples", data.get("prompt_pack", [])),
            context_md=insights_block.get("context_md", data.get("context_snippet_md", "")),
        )

        cache_block = data.get("cache", {}) if isinstance(data.get("cache"), dict) else {}
        cache = CacheState(
            enabled=bool(cache_block.get("enabled") or data.get("from_cache", False)),
            age_hours=cache_block.get("age_hours", data.get("cache_age_hours")),
        )

        metrics_block = data.get("metrics", {}) if isinstance(data.get("metrics"), dict) else {}
        metrics = RunMetrics(
            search_seconds=metrics_block.get("search_seconds", data.get("search_duration_seconds")),
            item_count=metrics_block.get("item_count", data.get("item_count", 0)),
        )
        if not metrics.item_count:
            metrics.item_count = sum(
                len(item_block.get(k, data.get(k, [])) or [])
                for k in ("reddit", "x", "youtube", "linkedin", "web")
            )

        models_block = data.get("models", {}) if isinstance(data.get("models"), dict) else {}
        models = ModelUsage(
            openai=models_block.get("openai", data.get("openai_model_used")),
            xai=models_block.get("xai", data.get("xai_model_used")),
        )

        return cls(
            topic=data["topic"],
            window=Window(start=start, end=end),
            generated_at=data["generated_at"],
            mode=data["mode"],
            models=models,
            items=items,
            insights=insights,
            errors=errors,
            cache=cache,
            metrics=metrics,
        )


def _item_from_dict(d: Dict[str, Any], source: Source) -> ContentItem:
    eng = Engagement(**d["engagement"]) if d.get("engagement") else None
    comments = [CommentNote(**comment) for comment in d.get("comments", [])]
    parts = d.get("breakdown") or d.get("score_parts", {})
    breakdown = ScoreBreakdown(**parts) if parts else ScoreBreakdown()

    return ContentItem(
        uid=d.get("uid", ""),
        source=source,
        title=d.get("title", ""),
        link=d.get("link", ""),
        author=d.get("author", ""),
        summary=d.get("summary", ""),
        published=d.get("published"),
        date_confidence=d.get("date_confidence", d.get("date_quality", "weak")),
        engagement=eng,
        relevance=d.get("relevance", d.get("signal", 0.5)),
        reason=d.get("reason", ""),
        score=d.get("score", 0),
        breakdown=breakdown,
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
        window=Window(start=start, end=end),
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
        models=ModelUsage(openai=openai_model, xai=xai_model),
        **kwargs,
    )


def _scale_count(value: Optional[int]) -> float:
    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric <= 0:
        return 0.0
    return math.sqrt(numeric)


def _weighted_sum(components: List[tuple]) -> float:
    return sum(weight * value for weight, value in components)


def _reddit_composite(sig: Engagement) -> float:
    ratio = sig.vote_ratio if sig.vote_ratio is not None else 0.5
    ratio = max(0.0, min(1.0, ratio))
    return _weighted_sum(
        [
            (0.35, _scale_count(sig.upvotes)),
            (0.45, _scale_count(sig.comments)),
            (0.20, ratio * 10),
        ]
    )


def _x_composite(sig: Engagement) -> float:
    return _weighted_sum(
        [
            (0.50, _scale_count(sig.likes)),
            (0.25, _scale_count(sig.replies)),
            (0.15, _scale_count(sig.reposts)),
            (0.10, _scale_count(sig.quotes)),
        ]
    )


def _youtube_composite(sig: Engagement) -> float:
    return _weighted_sum(
        [
            (0.70, _scale_count(sig.views)),
            (0.30, _scale_count(sig.likes)),
        ]
    )


def _linkedin_composite(sig: Engagement) -> float:
    return _weighted_sum(
        [
            (0.60, _scale_count(sig.reactions)),
            (0.40, _scale_count(sig.comments)),
        ]
    )


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
        date_confidence=trust,
        engagement=sig,
        comments=comments,
        comment_highlights=entry.get("comment_highlights", []),
        relevance=entry.get("signal", 0.5),
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
        date_confidence=trust,
        engagement=sig,
        relevance=entry.get("signal", 0.5),
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
        date_confidence=trust,
        engagement=sig,
        relevance=entry.get("signal", 0.5),
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
        date_confidence=trust,
        engagement=sig,
        relevance=entry.get("signal", 0.5),
        reason=entry.get("reason", ""),
        meta={
            "author_title": entry.get("role"),
        },
    )


def from_web_raw(entry: Dict[str, Any], start: str, end: str) -> ContentItem:
    item_date = entry.get("posted")
    trust = entry.get("date_confidence", entry.get("date_quality", "weak"))

    return ContentItem(
        uid=entry.get("uid", ""),
        source=Source.WEB,
        title=entry.get("title", ""),
        link=entry.get("link", ""),
        author=entry.get("domain", ""),
        summary=entry.get("snippet", ""),
        published=item_date,
        date_confidence=trust,
        relevance=entry.get("signal", 0.45),
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
