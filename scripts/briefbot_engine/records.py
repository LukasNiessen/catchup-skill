"""Domain models and normalization helpers for BriefBot outputs."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from . import timeframe


class Channel(Enum):
    REDDIT = "reddit"
    X = "x"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    WEB = "web"


@dataclass
class Interaction:
    """Platform-neutral interaction stats."""

    pulse: Optional[float] = None
    upvotes: Optional[int] = None
    comments: Optional[int] = None
    ratio: Optional[float] = None
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
            "pulse",
            "upvotes",
            "comments",
            "ratio",
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
class ThreadNote:
    """A notable thread comment."""

    score: int
    stamped: Optional[str]
    author: str
    excerpt: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["score"] = int(payload.get("score", 0))
        return payload


@dataclass
class Scorecard:
    """Score breakdown per dimension."""

    topicality: int = 0
    freshness: int = 0
    traction: int = 0
    trust: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class Signal:
    """Unified content item spanning all sources."""

    key: str
    channel: Channel
    headline: str
    url: str
    byline: str = ""
    blurb: str = ""
    dated: Optional[str] = None
    time_confidence: str = "low"
    interaction: Optional[Interaction] = None
    topicality: float = 0.5
    rationale: str = ""
    rank: int = 0
    scorecard: Scorecard = field(default_factory=Scorecard)
    thread_notes: List[ThreadNote] = field(default_factory=list)
    notables: List[str] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "channel": self.channel.value,
            "headline": self.headline,
            "url": self.url,
            "byline": self.byline,
            "blurb": self.blurb,
            "dated": self.dated,
            "time_confidence": self.time_confidence,
            "interaction": self.interaction.to_dict() if self.interaction else None,
            "topicality": self.topicality,
            "rationale": self.rationale,
            "rank": self.rank,
            "scorecard": self.scorecard.to_dict(),
            "thread_notes": [c.to_dict() for c in self.thread_notes],
            "notables": self.notables,
            "extras": self.extras,
        }


@dataclass
class Span:
    start: str
    end: str


@dataclass
class ModelChoices:
    openai: Optional[str] = None
    xai: Optional[str] = None


@dataclass
class InsightPack:
    notes: List[str] = field(default_factory=list)
    prompt_samples: List[str] = field(default_factory=list)
    context_md: str = ""


@dataclass
class CacheMark:
    enabled: bool = False
    age_hours: Optional[float] = None


@dataclass
class RunStats:
    search_seconds: Optional[float] = None
    item_count: int = 0


@dataclass
class SourceErrors:
    by_channel: Dict[str, str] = field(default_factory=dict)

    def get(self, channel: str) -> Optional[str]:
        return self.by_channel.get(channel)

    def set(self, channel: str, message: Optional[str]) -> None:
        if message is not None:
            self.by_channel[channel] = message

    def to_dict(self) -> Dict[str, str]:
        return dict(self.by_channel)


@dataclass
class Brief:
    """Aggregated research output with metadata."""

    topic: str
    span: Span
    generated_at: str
    mode: str
    models: ModelChoices = field(default_factory=ModelChoices)
    complexity_class: str = ""
    complexity_reason: str = ""
    epistemic_stance: str = ""
    epistemic_reason: str = ""
    decomposition: List[str] = field(default_factory=list)
    decomposition_source: str = ""
    items: List[Signal] = field(default_factory=list)
    insights: InsightPack = field(default_factory=InsightPack)
    errors: SourceErrors = field(default_factory=SourceErrors)
    cache: CacheMark = field(default_factory=CacheMark)
    metrics: RunStats = field(default_factory=RunStats)

    @property
    def reddit(self) -> List[Signal]:
        return [i for i in self.items if i.channel == Channel.REDDIT]

    @property
    def x(self) -> List[Signal]:
        return [i for i in self.items if i.channel == Channel.X]

    @property
    def youtube(self) -> List[Signal]:
        return [i for i in self.items if i.channel == Channel.YOUTUBE]

    @property
    def linkedin(self) -> List[Signal]:
        return [i for i in self.items if i.channel == Channel.LINKEDIN]

    @property
    def web(self) -> List[Signal]:
        return [i for i in self.items if i.channel == Channel.WEB]

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
            "span": {"start": self.span.start, "end": self.span.end},
            "generated_at": self.generated_at,
            "mode": self.mode,
            "models": {"openai": self.models.openai, "xai": self.models.xai},
            "intent": {
                "complexity_class": self.complexity_class,
                "complexity_reason": self.complexity_reason,
                "epistemic_stance": self.epistemic_stance,
                "epistemic_reason": self.epistemic_reason,
                "decomposition": list(self.decomposition),
                "decomposition_source": self.decomposition_source,
            },
            "items": {
                "reddit": [item.to_dict() for item in self.reddit],
                "x": [item.to_dict() for item in self.x],
                "youtube": [item.to_dict() for item in self.youtube],
                "linkedin": [item.to_dict() for item in self.linkedin],
                "web": [item.to_dict() for item in self.web],
            },
            "insights": {
                "notes": list(self.insights.notes),
                "prompt_samples": list(self.insights.prompt_samples),
                "context_md": self.insights.context_md,
            },
        }
        if self.errors.by_channel:
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
    def from_dict(cls, data: Dict[str, Any]) -> "Brief":
        span_block = data.get("span") or {}
        window_block = data.get("window", {}) if not span_block else {}
        range_section = data.get("range", {}) if not span_block and not window_block else {}
        start = (
            span_block.get("start")
            or window_block.get("start")
            or window_block.get("from")
            or range_section.get("from")
            or data.get("range_start", "")
        )
        end = (
            span_block.get("end")
            or window_block.get("end")
            or window_block.get("to")
            or range_section.get("to")
            or data.get("range_end", "")
        )

        items: List[Signal] = []
        item_block = data.get("items", {}) if isinstance(data.get("items"), dict) else {}

        for platform, channel_enum in [
            ("reddit", Channel.REDDIT),
            ("x", Channel.X),
            ("youtube", Channel.YOUTUBE),
            ("linkedin", Channel.LINKEDIN),
            ("web", Channel.WEB),
        ]:
            raw_list = item_block.get(platform)
            if raw_list is None:
                raw_list = data.get(platform, [])
            for item_data in raw_list or []:
                items.append(_signal_from_dict(item_data, channel_enum))

        errors = SourceErrors()
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
        insights = InsightPack(
            notes=insights_block.get("notes", data.get("best_practices", [])),
            prompt_samples=insights_block.get("prompt_samples", data.get("prompt_pack", [])),
            context_md=insights_block.get("context_md", data.get("context_snippet_md", "")),
        )

        cache_block = data.get("cache", {}) if isinstance(data.get("cache"), dict) else {}
        cache = CacheMark(
            enabled=bool(cache_block.get("enabled") or data.get("from_cache", False)),
            age_hours=cache_block.get("age_hours", data.get("cache_age_hours")),
        )

        metrics_block = data.get("metrics", {}) if isinstance(data.get("metrics"), dict) else {}
        metrics = RunStats(
            search_seconds=metrics_block.get("search_seconds", data.get("search_duration_seconds")),
            item_count=metrics_block.get("item_count", data.get("item_count", 0)),
        )
        if not metrics.item_count:
            metrics.item_count = sum(
                len(item_block.get(k, data.get(k, [])) or [])
                for k in ("reddit", "x", "youtube", "linkedin", "web")
            )

        models_block = data.get("models", {}) if isinstance(data.get("models"), dict) else {}
        models = ModelChoices(
            openai=models_block.get("openai", data.get("openai_model_used")),
            xai=models_block.get("xai", data.get("xai_model_used")),
        )

        intent_block = data.get("intent", {}) if isinstance(data.get("intent"), dict) else {}

        return cls(
            topic=data["topic"],
            span=Span(start=start, end=end),
            generated_at=data["generated_at"],
            mode=data["mode"],
            models=models,
            complexity_class=intent_block.get("complexity_class", ""),
            complexity_reason=intent_block.get("complexity_reason", ""),
            epistemic_stance=intent_block.get("epistemic_stance", ""),
            epistemic_reason=intent_block.get("epistemic_reason", ""),
            decomposition=intent_block.get("decomposition", []),
            decomposition_source=intent_block.get("decomposition_source", ""),
            items=items,
            insights=insights,
            errors=errors,
            cache=cache,
            metrics=metrics,
        )


def _signal_from_dict(d: Dict[str, Any], channel: Channel) -> Signal:
    interaction_payload = d.get("interaction") or d.get("engagement") or d.get("metrics")
    interaction = Interaction(**interaction_payload) if isinstance(interaction_payload, dict) else None
    thread_notes = [ThreadNote(**note) for note in d.get("thread_notes", d.get("comments", []))]
    score_part = d.get("scorecard") or d.get("breakdown") or d.get("score_parts", {})
    scorecard = Scorecard(**score_part) if score_part else Scorecard()

    return Signal(
        key=d.get("key", d.get("uid", "")),
        channel=channel,
        headline=d.get("headline", d.get("title", "")),
        url=d.get("url", d.get("link", "")),
        byline=d.get("byline", d.get("author", "")),
        blurb=d.get("blurb", d.get("summary", "")),
        dated=d.get("dated", d.get("published")),
        time_confidence=d.get("time_confidence", d.get("date_confidence", d.get("date_quality", "low"))),
        interaction=interaction,
        topicality=d.get("topicality", d.get("relevance", d.get("signal", 0.5))),
        rationale=d.get("rationale", d.get("reason", "")),
        rank=d.get("rank", d.get("score", 0)),
        scorecard=scorecard,
        thread_notes=thread_notes,
        notables=d.get("notables", d.get("comment_highlights", [])),
        extras=d.get("extras", d.get("meta", {})),
    )


def build_brief(
    topic: str,
    start: str,
    end: str,
    mode: str,
    openai_model: Optional[str] = None,
    xai_model: Optional[str] = None,
    **kwargs,
) -> Brief:
    return Brief(
        topic=topic,
        span=Span(start=start, end=end),
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
        models=ModelChoices(openai=openai_model, xai=xai_model),
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


def _reddit_pulse(sig: Interaction) -> float:
    ratio = sig.ratio if sig.ratio is not None else 0.55
    ratio = max(0.0, min(1.0, ratio))
    return _weighted_sum(
        [
            (0.40, _scale_count(sig.upvotes)),
            (0.40, _scale_count(sig.comments)),
            (0.20, ratio * 10),
        ]
    )


def _x_pulse(sig: Interaction) -> float:
    return _weighted_sum(
        [
            (0.46, _scale_count(sig.likes)),
            (0.26, _scale_count(sig.replies)),
            (0.16, _scale_count(sig.reposts)),
            (0.12, _scale_count(sig.quotes)),
        ]
    )


def _youtube_pulse(sig: Interaction) -> float:
    return _weighted_sum(
        [
            (0.68, _scale_count(sig.views)),
            (0.32, _scale_count(sig.likes)),
        ]
    )


def _linkedin_pulse(sig: Interaction) -> float:
    return _weighted_sum(
        [
            (0.62, _scale_count(sig.reactions)),
            (0.38, _scale_count(sig.comments)),
        ]
    )


def from_reddit_raw(entry: Dict[str, Any], start: str, end: str) -> Signal:
    metrics = entry.get("metrics") or entry.get("signals")
    interaction = None
    if isinstance(metrics, dict):
        interaction = Interaction(
            upvotes=metrics.get("upvotes"),
            comments=metrics.get("comments"),
            ratio=metrics.get("ratio") if metrics.get("ratio") is not None else metrics.get("vote_ratio"),
        )
        if interaction.upvotes is not None or interaction.comments is not None:
            interaction.pulse = _reddit_pulse(interaction)

    thread_notes = [
        ThreadNote(
            score=comment.get("score", 0),
            stamped=comment.get("stamped") or comment.get("posted"),
            author=comment.get("author", ""),
            excerpt=comment.get("excerpt", ""),
            url=comment.get("url", comment.get("link", "")),
        )
        for comment in entry.get("thread_notes", entry.get("comment_cards", []))
    ]

    item_date = entry.get("dated", entry.get("posted"))
    trust = timeframe.date_confidence(item_date, start, end)

    return Signal(
        key=entry.get("key", entry.get("uid", "")),
        channel=Channel.REDDIT,
        headline=entry.get("headline", entry.get("title", "")),
        url=entry.get("url", entry.get("link", "")),
        byline=entry.get("forum", entry.get("community", "")),
        dated=item_date,
        time_confidence=trust,
        interaction=interaction,
        thread_notes=thread_notes,
        notables=entry.get("notables", entry.get("comment_highlights", [])),
        topicality=entry.get("topicality", entry.get("signal", 0.5)),
        rationale=entry.get("rationale", entry.get("reason", "")),
        extras={
            "subreddit": entry.get("forum", entry.get("community", "")),
            "flair": entry.get("flair", ""),
        },
    )


def from_x_raw(entry: Dict[str, Any], start: str, end: str) -> Signal:
    metrics = entry.get("metrics") or entry.get("signals")
    interaction = None
    if isinstance(metrics, dict):
        interaction = Interaction(
            likes=metrics.get("likes"),
            reposts=metrics.get("reposts"),
            replies=metrics.get("replies"),
            quotes=metrics.get("quotes"),
        )
        if interaction.likes is not None or interaction.reposts is not None:
            interaction.pulse = _x_pulse(interaction)

    item_date = entry.get("dated", entry.get("posted"))
    trust = timeframe.date_confidence(item_date, start, end)

    return Signal(
        key=entry.get("key", entry.get("uid", "")),
        channel=Channel.X,
        headline=entry.get("snippet", entry.get("excerpt", "")),
        url=entry.get("url", entry.get("link", "")),
        byline=entry.get("handle", ""),
        dated=item_date,
        time_confidence=trust,
        interaction=interaction,
        topicality=entry.get("topicality", entry.get("signal", 0.5)),
        rationale=entry.get("rationale", entry.get("reason", "")),
        extras={
            "is_repost": bool(entry.get("is_repost", False)),
            "language": entry.get("language", "en"),
        },
    )


def from_youtube_raw(entry: Dict[str, Any], start: str, end: str) -> Signal:
    metrics = entry.get("metrics") or entry.get("signals")
    interaction = None
    if isinstance(metrics, dict):
        interaction = Interaction(views=metrics.get("views"), likes=metrics.get("likes"))
        interaction.pulse = _youtube_pulse(interaction)

    item_date = entry.get("dated", entry.get("posted"))
    trust = timeframe.date_confidence(item_date, start, end)

    return Signal(
        key=entry.get("key", entry.get("uid", "")),
        channel=Channel.YOUTUBE,
        headline=entry.get("headline", entry.get("title", "")),
        url=entry.get("url", entry.get("link", "")),
        byline=entry.get("channel", ""),
        blurb=entry.get("summary") or entry.get("blurb", ""),
        dated=item_date,
        time_confidence=trust,
        interaction=interaction,
        topicality=entry.get("topicality", entry.get("signal", 0.5)),
        rationale=entry.get("rationale", entry.get("reason", "")),
        extras={
            "duration_seconds": entry.get("duration_seconds"),
        },
    )


def from_linkedin_raw(entry: Dict[str, Any], start: str, end: str) -> Signal:
    metrics = entry.get("metrics") or entry.get("signals")
    interaction = None
    if isinstance(metrics, dict):
        interaction = Interaction(
            reactions=metrics.get("reactions"),
            comments=metrics.get("comments"),
        )
        interaction.pulse = _linkedin_pulse(interaction)

    item_date = entry.get("dated", entry.get("posted"))
    trust = timeframe.date_confidence(item_date, start, end)

    return Signal(
        key=entry.get("key", entry.get("uid", "")),
        channel=Channel.LINKEDIN,
        headline=entry.get("snippet", entry.get("excerpt", "")),
        url=entry.get("url", entry.get("link", "")),
        byline=entry.get("author", ""),
        dated=item_date,
        time_confidence=trust,
        interaction=interaction,
        topicality=entry.get("topicality", entry.get("signal", 0.5)),
        rationale=entry.get("rationale", entry.get("reason", "")),
        extras={
            "author_title": entry.get("role"),
        },
    )


def from_web_raw(entry: Dict[str, Any], start: str, end: str) -> Signal:
    item_date = entry.get("dated", entry.get("posted"))
    trust = entry.get("time_confidence", entry.get("date_confidence", entry.get("date_quality", "low")))

    return Signal(
        key=entry.get("key", entry.get("uid", "")),
        channel=Channel.WEB,
        headline=entry.get("headline", entry.get("title", "")),
        url=entry.get("url", entry.get("link", "")),
        byline=entry.get("domain", ""),
        blurb=entry.get("snippet", entry.get("blurb", "")),
        dated=item_date,
        time_confidence=trust,
        topicality=entry.get("topicality", entry.get("signal", 0.45)),
        rationale=entry.get("rationale", entry.get("reason", "")),
        extras={
            "source_domain": entry.get("domain", ""),
            "language": entry.get("language", "en"),
        },
    )


_FACTORY: Dict[Channel, Callable[[Dict[str, Any], str, str], Signal]] = {
    Channel.REDDIT: from_reddit_raw,
    Channel.X: from_x_raw,
    Channel.YOUTUBE: from_youtube_raw,
    Channel.LINKEDIN: from_linkedin_raw,
    Channel.WEB: from_web_raw,
}


def items_from_raw(raw_items: List[Dict[str, Any]], channel: Channel, start: str, end: str) -> List[Signal]:
    converter = _FACTORY[channel]
    return [converter(entry, start, end) for entry in raw_items]


def filter_by_date(
    items: List[Signal],
    start: str,
    end: str,
    exclude_undated: bool = False,
) -> List[Signal]:
    selected: List[Signal] = []
    for item in items:
        if item.dated is None:
            if not exclude_undated:
                selected.append(item)
            continue
        if item.dated < start:
            continue
        if item.dated > end:
            continue
        selected.append(item)
    return selected


def as_dicts(items: List[Signal]) -> List[Dict[str, Any]]:
    return [item.to_dict() for item in items]
