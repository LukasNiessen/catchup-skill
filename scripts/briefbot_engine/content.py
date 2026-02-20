"""Unified content model and factory functions for all platform sources."""

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar


class Source(Enum):
    REDDIT = "reddit"
    X = "x"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    WEB = "web"


@dataclass
class Signals:
    """Platform-agnostic engagement metrics."""

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
        d = {}
        for fld in (
            "composite", "upvotes", "comments", "vote_ratio", "likes",
            "reposts", "replies", "quotes", "views", "reactions", "bookmarks",
        ):
            val = getattr(self, fld)
            if val is not None:
                d[fld] = val
        return d if d else None


@dataclass
class ThreadComment:
    """Comment extracted from a discussion thread."""

    score: int
    date: Optional[str]
    author: str
    excerpt: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["score"] = int(payload.get("score", 0))
        return payload


@dataclass
class ScoreBreakdown:
    """Breakdown of scoring components."""

    relevance: int = 0
    recency: int = 0
    engagement: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class ContentItem:
    """Unified content item spanning all platform sources."""

    item_id: str
    source: Source
    headline: str
    permalink: str
    author: str = ""
    body: str = ""
    published: Optional[str] = None
    date_trust: str = "low"
    signals: Optional[Signals] = None
    relevance: float = 0.5
    rationale: str = ""
    score: int = 0
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    thread_comments: List[ThreadComment] = field(default_factory=list)
    thread_insights: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.item_id,
            "source": self.source.value,
            "headline": self.headline,
            "permalink": self.permalink,
            "author": self.author,
            "body": self.body,
            "published": self.published,
            "date_trust": self.date_trust,
            "signals": self.signals.to_dict() if self.signals else None,
            "relevance": self.relevance,
            "rationale": self.rationale,
            "score": self.score,
            "breakdown": self.breakdown.to_dict(),
            "thread_comments": [c.to_dict() for c in self.thread_comments],
            "thread_insights": self.thread_insights,
            "meta": self.meta,
        }
        return d


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

    # Compat shims for render.py field access
    @property
    def range_from(self) -> str:
        return self.range_start

    @property
    def range_to(self) -> str:
        return self.range_end

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "topic": self.topic,
            "range": {
                "from": self.range_start,
                "to": self.range_end,
            },
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
            d[f"{platform}_error"] = msg
        if self.from_cache:
            d["from_cache"] = self.from_cache
        if self.cache_age_hours is not None:
            d["cache_age_hours"] = self.cache_age_hours
        if self.search_duration_seconds is not None:
            d["search_duration_seconds"] = self.search_duration_seconds
        if self.item_count:
            d["item_count"] = self.item_count
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        """Reconstruct a Report from its serialized dict."""
        range_section = data.get("range", {})
        start = range_section.get("from", data.get("range_start", ""))
        end = range_section.get("to", data.get("range_end", ""))

        items = []
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
    """Reconstruct a ContentItem from a serialized dict."""
    sig = None
    if d.get("signals"):
        sig = Signals(**d["signals"])

    comments = []
    for c in d.get("thread_comments", []):
        comments.append(ThreadComment(**c))

    bd = d.get("breakdown", {})
    breakdown = ScoreBreakdown(**bd) if bd else ScoreBreakdown()

    return ContentItem(
        item_id=d.get("id", ""),
        source=source,
        headline=d.get("headline", ""),
        permalink=d.get("permalink", ""),
        author=d.get("author", ""),
        body=d.get("body", ""),
        published=d.get("published"),
        date_trust=d.get("date_trust", "low"),
        signals=sig,
        relevance=d.get("relevance", 0.5),
        rationale=d.get("rationale", ""),
        score=d.get("score", 0),
        breakdown=breakdown,
        thread_comments=comments,
        thread_insights=d.get("thread_insights", []),
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
    """Create a new report with metadata and optional extra fields."""
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


# ---------------------------------------------------------------------------
# Factory functions: raw API dicts -> ContentItem
# ---------------------------------------------------------------------------

def _safe_log1p(val: Optional[int]) -> float:
    """Safe log1p, returns 0.0 for None or negative inputs."""
    if val is None:
        return 0.0
    try:
        number = float(val)
    except (TypeError, ValueError):
        return 0.0
    if number < 0:
        return 0.0
    return math.log1p(number)


def _compute_composite_reddit(sig: Signals) -> float:
    """Compute composite engagement for Reddit: 0.48*score + 0.37*comments + 0.15*ratio."""
    sc = _safe_log1p(sig.upvotes)
    cm = _safe_log1p(sig.comments)
    ra = (sig.vote_ratio or 0.5) * 12
    return 0.48 * sc + 0.37 * cm + 0.15 * ra


def _compute_composite_x(sig: Signals) -> float:
    """Compute composite engagement for X: 0.45*likes + 0.28*reposts + 0.17*replies + 0.10*quotes."""
    lk = _safe_log1p(sig.likes)
    rp = _safe_log1p(sig.reposts)
    rl = _safe_log1p(sig.replies)
    qu = _safe_log1p(sig.quotes)
    return 0.45 * lk + 0.28 * rp + 0.17 * rl + 0.10 * qu


def _compute_composite_youtube(sig: Signals) -> float:
    """Compute composite engagement for YouTube: 0.62*views + 0.38*likes."""
    vw = _safe_log1p(sig.views)
    lk = _safe_log1p(sig.likes)
    return 0.62 * vw + 0.38 * lk


def _compute_composite_linkedin(sig: Signals) -> float:
    """Compute composite engagement for LinkedIn: 0.55*reactions + 0.45*comments."""
    rx = _safe_log1p(sig.reactions)
    cm = _safe_log1p(sig.comments)
    return 0.55 * rx + 0.45 * cm


def _trust_level(date_input: Optional[str], range_start: str, range_end: str) -> str:
    """Return 'high' if date falls within [range_start, range_end], else 'low'."""
    if not date_input:
        return "low"
    try:
        from datetime import datetime as _dt
        parsed = _dt.strptime(date_input, "%Y-%m-%d").date()
        s = _dt.strptime(range_start, "%Y-%m-%d").date()
        e = _dt.strptime(range_end, "%Y-%m-%d").date()
        return "high" if s <= parsed <= e else "low"
    except ValueError:
        return "low"


def from_reddit_raw(
    entry: Dict[str, Any],
    start: str,
    end: str,
) -> ContentItem:
    """Transform a single raw Reddit API dict into a ContentItem."""
    sig = None
    raw_eng = entry.get("engagement")
    if isinstance(raw_eng, dict):
        sig = Signals(
            upvotes=raw_eng.get("score"),
            comments=raw_eng.get("num_comments"),
            vote_ratio=raw_eng.get("upvote_ratio"),
        )
        if sig.upvotes is not None or sig.comments is not None:
            sig.composite = _compute_composite_reddit(sig)

    comments = []
    for rc in entry.get("top_comments", []):
        comments.append(ThreadComment(
            score=rc.get("score", 0),
            date=rc.get("date"),
            author=rc.get("author", ""),
            excerpt=rc.get("excerpt", ""),
            url=rc.get("url", ""),
        ))

    item_date = entry.get("date")
    trust = _trust_level(item_date, start, end)

    return ContentItem(
        item_id=entry.get("id", ""),
        source=Source.REDDIT,
        headline=entry.get("title", ""),
        permalink=entry.get("url", ""),
        author=entry.get("subreddit", ""),
        published=item_date,
        date_trust=trust,
        signals=sig,
        thread_comments=comments,
        thread_insights=entry.get("comment_insights", []),
        relevance=entry.get("relevance", 0.5),
        rationale=entry.get("why_relevant", ""),
        meta={
            "subreddit": entry.get("subreddit", ""),
            "flair": entry.get("flair", ""),
        },
    )


def from_x_raw(
    entry: Dict[str, Any],
    start: str,
    end: str,
) -> ContentItem:
    """Transform a single raw X/Twitter API dict into a ContentItem."""
    sig = None
    raw_eng = entry.get("engagement")
    if isinstance(raw_eng, dict):
        sig = Signals(
            likes=raw_eng.get("likes"),
            reposts=raw_eng.get("reposts"),
            replies=raw_eng.get("replies"),
            quotes=raw_eng.get("quotes"),
        )
        if sig.likes is not None or sig.reposts is not None:
            sig.composite = _compute_composite_x(sig)

    item_date = entry.get("date")
    trust = _trust_level(item_date, start, end)

    return ContentItem(
        item_id=entry.get("id", ""),
        source=Source.X,
        headline=entry.get("text", ""),
        permalink=entry.get("url", ""),
        author=entry.get("author_handle", ""),
        published=item_date,
        date_trust=trust,
        signals=sig,
        relevance=entry.get("relevance", 0.5),
        rationale=entry.get("why_relevant", ""),
        meta={
            "is_repost": bool(entry.get("is_repost", False)),
            "language": entry.get("language", "en"),
        },
    )


def from_youtube_raw(
    entry: Dict[str, Any],
    start: str,
    end: str,
) -> ContentItem:
    """Transform a single raw YouTube API dict into a ContentItem."""
    sig = None
    view_count = entry.get("views")
    like_count = entry.get("likes")
    if view_count is not None or like_count is not None:
        sig = Signals(views=view_count, likes=like_count)
        sig.composite = _compute_composite_youtube(sig)

    item_date = entry.get("date")
    trust = _trust_level(item_date, start, end)

    return ContentItem(
        item_id=entry.get("id", ""),
        source=Source.YOUTUBE,
        headline=entry.get("title", ""),
        permalink=entry.get("url", ""),
        author=entry.get("channel_name", ""),
        body=entry.get("description") or "",
        published=item_date,
        date_trust=trust,
        signals=sig,
        relevance=entry.get("relevance", 0.5),
        rationale=entry.get("why_relevant", ""),
        meta={
            "duration_seconds": entry.get("duration_seconds"),
        },
    )


def from_linkedin_raw(
    entry: Dict[str, Any],
    start: str,
    end: str,
) -> ContentItem:
    """Transform a single raw LinkedIn API dict into a ContentItem."""
    sig = None
    reaction_count = entry.get("reactions")
    comment_count = entry.get("comments")
    if reaction_count is not None or comment_count is not None:
        sig = Signals(reactions=reaction_count, comments=comment_count)
        sig.composite = _compute_composite_linkedin(sig)

    item_date = entry.get("date")
    trust = _trust_level(item_date, start, end)

    return ContentItem(
        item_id=entry.get("id", ""),
        source=Source.LINKEDIN,
        headline=entry.get("text", ""),
        permalink=entry.get("url", ""),
        author=entry.get("author_name", ""),
        published=item_date,
        date_trust=trust,
        signals=sig,
        relevance=entry.get("relevance", 0.5),
        rationale=entry.get("why_relevant", ""),
        meta={
            "author_title": entry.get("author_title"),
        },
    )


def from_web_raw(
    entry: Dict[str, Any],
    start: str,
    end: str,
) -> ContentItem:
    """Transform a single raw web search dict into a ContentItem."""
    item_date = entry.get("date")
    trust = entry.get("date_confidence", "low")

    return ContentItem(
        item_id=entry.get("id", ""),
        source=Source.WEB,
        headline=entry.get("title", ""),
        permalink=entry.get("url", ""),
        author=entry.get("source_domain", ""),
        body=entry.get("snippet", ""),
        published=item_date,
        date_trust=trust,
        relevance=entry.get("relevance", 0.45),
        rationale=entry.get("why_relevant", ""),
        meta={
            "source_domain": entry.get("source_domain", ""),
            "language": entry.get("language", "en"),
        },
    )


# ---------------------------------------------------------------------------
# Batch factory functions (list wrappers)
# ---------------------------------------------------------------------------

_FACTORY = {
    Source.REDDIT: from_reddit_raw,
    Source.X: from_x_raw,
    Source.YOUTUBE: from_youtube_raw,
    Source.LINKEDIN: from_linkedin_raw,
    Source.WEB: from_web_raw,
}


def items_from_raw(
    raw_items: List[Dict[str, Any]],
    source: Source,
    start: str,
    end: str,
) -> List[ContentItem]:
    """Convert a list of raw dicts into ContentItems for the given source."""
    factory = _FACTORY[source]
    return [factory(entry, start, end) for entry in raw_items]


def filter_by_date(
    items: List[ContentItem],
    start: str,
    end: str,
    exclude_undated: bool = False,
) -> List[ContentItem]:
    """Remove items with verified dates outside the acceptable range."""
    filtered = []
    for item in items:
        if item.published is None:
            if not exclude_undated:
                filtered.append(item)
            continue
        if item.published < start:
            continue
        if item.published > end:
            continue
        filtered.append(item)
    return filtered


def as_dicts(items: List[ContentItem]) -> List[Dict[str, Any]]:
    """Convert ContentItem objects to dicts for JSON serialization."""
    return [item.to_dict() for item in items]
