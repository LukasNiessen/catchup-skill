"""Data structures for normalized content items and aggregated research output."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class Engagement:
    """Engagement signals across content sources."""

    score: Optional[int] = None
    num_comments: Optional[int] = None
    upvote_ratio: Optional[float] = None
    likes: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    quotes: Optional[int] = None
    views: Optional[int] = None
    reactions: Optional[int] = None
    comments: Optional[int] = None
    bookmarks: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.score is not None:
            d['score'] = self.score
        if self.num_comments is not None:
            d['num_comments'] = self.num_comments
        if self.upvote_ratio is not None:
            d['upvote_ratio'] = self.upvote_ratio
        if self.likes is not None:
            d['likes'] = self.likes
        if self.reposts is not None:
            d['reposts'] = self.reposts
        if self.replies is not None:
            d['replies'] = self.replies
        if self.quotes is not None:
            d['quotes'] = self.quotes
        if self.views is not None:
            d['views'] = self.views
        if self.reactions is not None:
            d['reactions'] = self.reactions
        if self.comments is not None:
            d['comments'] = self.comments
        if self.bookmarks is not None:
            d['bookmarks'] = self.bookmarks
        return d if d else None


@dataclass
class Comment:
    """Comment extracted from a Reddit thread."""

    score: int
    date: Optional[str]
    author: str
    excerpt: str
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'score': self.score,
            'date': self.date,
            'author': self.author,
            'excerpt': self.excerpt,
            'url': self.url,
        }


@dataclass
class SubScores:
    """Breakdown of scoring components."""

    relevance: int = 0
    recency: int = 0
    engagement: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            'relevance': self.relevance,
            'recency': self.recency,
            'engagement': self.engagement,
        }


@dataclass
class RedditItem:
    """Canonical Reddit thread."""

    id: str
    title: str
    url: str
    subreddit: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[Engagement] = None
    top_comments: List[Comment] = field(default_factory=list)
    comment_insights: List[str] = field(default_factory=list)
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0
    flair: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'subreddit': self.subreddit,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'top_comments': [c.to_dict() for c in self.top_comments],
            'comment_insights': self.comment_insights,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
            'flair': self.flair,
        }


@dataclass
class XItem:
    """Canonical X post."""

    id: str
    text: str
    url: str
    author_handle: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[Engagement] = None
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0
    is_repost: bool = False
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text': self.text,
            'url': self.url,
            'author_handle': self.author_handle,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
            'is_repost': self.is_repost,
            'language': self.language,
        }


@dataclass
class YouTubeItem:
    """Canonical YouTube video."""

    id: str
    title: str
    url: str
    channel_name: str
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[Engagement] = None
    description: Optional[str] = None
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0
    duration_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'channel_name': self.channel_name,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'description': self.description,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
            'duration_seconds': self.duration_seconds,
        }


@dataclass
class LinkedInItem:
    """Canonical LinkedIn post."""

    id: str
    text: str
    url: str
    author_name: str
    author_title: Optional[str] = None
    date: Optional[str] = None
    date_confidence: str = "low"
    engagement: Optional[Engagement] = None
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text': self.text,
            'url': self.url,
            'author_name': self.author_name,
            'author_title': self.author_title,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class WebSearchItem:
    """Canonical web search result (no engagement data)."""

    id: str
    title: str
    url: str
    source_domain: str
    snippet: str
    date: Optional[str] = None
    date_confidence: str = "low"
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'source_domain': self.source_domain,
            'snippet': self.snippet,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
            'language': self.language,
        }


@dataclass
class Report:
    """Aggregated research output with metadata."""

    topic: str
    range_from: str
    range_to: str
    generated_at: str
    mode: str
    openai_model_used: Optional[str] = None
    xai_model_used: Optional[str] = None
    reddit: List[RedditItem] = field(default_factory=list)
    x: List[XItem] = field(default_factory=list)
    youtube: List[YouTubeItem] = field(default_factory=list)
    linkedin: List[LinkedInItem] = field(default_factory=list)
    web: List[WebSearchItem] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    prompt_pack: List[str] = field(default_factory=list)
    context_snippet_md: str = ""
    reddit_error: Optional[str] = None
    x_error: Optional[str] = None
    youtube_error: Optional[str] = None
    linkedin_error: Optional[str] = None
    web_error: Optional[str] = None
    from_cache: bool = False
    cache_age_hours: Optional[float] = None
    search_duration_seconds: Optional[float] = None
    item_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'topic': self.topic,
            'range': {
                'from': self.range_from,
                'to': self.range_to,
            },
            'generated_at': self.generated_at,
            'mode': self.mode,
            'openai_model_used': self.openai_model_used,
            'xai_model_used': self.xai_model_used,
            'reddit': [item.to_dict() for item in self.reddit],
            'x': [item.to_dict() for item in self.x],
            'youtube': [item.to_dict() for item in self.youtube],
            'linkedin': [item.to_dict() for item in self.linkedin],
            'web': [item.to_dict() for item in self.web],
            'best_practices': self.best_practices,
            'prompt_pack': self.prompt_pack,
            'context_snippet_md': self.context_snippet_md,
        }
        if self.reddit_error:
            d['reddit_error'] = self.reddit_error
        if self.x_error:
            d['x_error'] = self.x_error
        if self.youtube_error:
            d['youtube_error'] = self.youtube_error
        if self.linkedin_error:
            d['linkedin_error'] = self.linkedin_error
        if self.web_error:
            d['web_error'] = self.web_error
        if self.from_cache:
            d['from_cache'] = self.from_cache
        if self.cache_age_hours is not None:
            d['cache_age_hours'] = self.cache_age_hours
        if self.search_duration_seconds is not None:
            d['search_duration_seconds'] = self.search_duration_seconds
        if self.item_count:
            d['item_count'] = self.item_count
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Report":
        """Reconstruct a Report from its serialized dict."""
        if 'item_count' not in data:
            data['item_count'] = sum(
                len(data.get(k, [])) for k in ('reddit', 'x', 'youtube', 'linkedin', 'web')
            )
        range_section = data.get('range', {})
        start = range_section.get('from', data.get('range_from', ''))
        end = range_section.get('to', data.get('range_to', ''))

        # Reconstruct Reddit items
        reddit_items = []
        for item_data in data.get('reddit', []):
            eng = None
            if item_data.get('engagement'):
                eng = Engagement(**item_data['engagement'])
            comments = []
            for c_data in item_data.get('top_comments', []):
                comments.append(Comment(**c_data))
            subs = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            reddit_items.append(RedditItem(
                id=item_data['id'],
                title=item_data['title'],
                url=item_data['url'],
                subreddit=item_data['subreddit'],
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                engagement=eng,
                top_comments=comments,
                comment_insights=item_data.get('comment_insights', []),
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs,
                score=item_data.get('score', 0),
            ))

        # Reconstruct X items
        x_items = []
        for item_data in data.get('x', []):
            eng = None
            if item_data.get('engagement'):
                eng = Engagement(**item_data['engagement'])
            subs = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            x_items.append(XItem(
                id=item_data['id'],
                text=item_data['text'],
                url=item_data['url'],
                author_handle=item_data['author_handle'],
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                engagement=eng,
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs,
                score=item_data.get('score', 0),
            ))

        # Reconstruct YouTube items
        youtube_items = []
        for item_data in data.get('youtube', []):
            eng = None
            if item_data.get('engagement'):
                eng = Engagement(**item_data['engagement'])
            subs = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            youtube_items.append(YouTubeItem(
                id=item_data['id'],
                title=item_data['title'],
                url=item_data['url'],
                channel_name=item_data.get('channel_name', ''),
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                engagement=eng,
                description=item_data.get('description'),
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs,
                score=item_data.get('score', 0),
            ))

        # Reconstruct LinkedIn items
        linkedin_items = []
        for item_data in data.get('linkedin', []):
            eng = None
            if item_data.get('engagement'):
                eng = Engagement(**item_data['engagement'])
            subs = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            linkedin_items.append(LinkedInItem(
                id=item_data['id'],
                text=item_data['text'],
                url=item_data['url'],
                author_name=item_data.get('author_name', ''),
                author_title=item_data.get('author_title'),
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                engagement=eng,
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs,
                score=item_data.get('score', 0),
            ))

        # Reconstruct Web items
        web_items = []
        for item_data in data.get('web', []):
            subs = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            web_items.append(WebSearchItem(
                id=item_data['id'],
                title=item_data['title'],
                url=item_data['url'],
                source_domain=item_data.get('source_domain', ''),
                snippet=item_data.get('snippet', ''),
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs,
                score=item_data.get('score', 0),
            ))

        return cls(
            topic=data['topic'],
            range_from=start,
            range_to=end,
            generated_at=data['generated_at'],
            mode=data['mode'],
            openai_model_used=data.get('openai_model_used'),
            xai_model_used=data.get('xai_model_used'),
            reddit=reddit_items,
            x=x_items,
            youtube=youtube_items,
            linkedin=linkedin_items,
            web=web_items,
            best_practices=data.get('best_practices', []),
            prompt_pack=data.get('prompt_pack', []),
            context_snippet_md=data.get('context_snippet_md', ''),
            reddit_error=data.get('reddit_error'),
            x_error=data.get('x_error'),
            youtube_error=data.get('youtube_error'),
            linkedin_error=data.get('linkedin_error'),
            web_error=data.get('web_error'),
            from_cache=data.get('from_cache', False),
            cache_age_hours=data.get('cache_age_hours'),
            search_duration_seconds=data.get('search_duration_seconds'),
            item_count=data.get('item_count', 0),
        )


def make_report(
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
        range_from=start,
        range_to=end,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
        openai_model_used=openai_model,
        xai_model_used=xai_model,
        **kwargs,
    )
