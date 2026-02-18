#
# Data Structures: Type definitions for the research aggregation system
# Defines the canonical representations for content items and reports
#

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class Engagement:
    """Container for platform-specific interaction metrics."""

    # Reddit-specific metrics
    score: Optional[int] = None
    num_comments: Optional[int] = None
    upvote_ratio: Optional[float] = None

    # X-specific metrics
    likes: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    quotes: Optional[int] = None

    # YouTube-specific metrics
    views: Optional[int] = None
    # Note: likes field is shared with X

    # LinkedIn-specific metrics
    reactions: Optional[int] = None
    comments: Optional[int] = None  # Also applicable to LinkedIn

    def to_dict(self) -> Dict[str, Any]:
        serialized = {}
        if self.score is not None:
            serialized['score'] = self.score
        if self.num_comments is not None:
            serialized['num_comments'] = self.num_comments
        if self.upvote_ratio is not None:
            serialized['upvote_ratio'] = self.upvote_ratio
        if self.likes is not None:
            serialized['likes'] = self.likes
        if self.reposts is not None:
            serialized['reposts'] = self.reposts
        if self.replies is not None:
            serialized['replies'] = self.replies
        if self.quotes is not None:
            serialized['quotes'] = self.quotes
        if self.views is not None:
            serialized['views'] = self.views
        if self.reactions is not None:
            serialized['reactions'] = self.reactions
        if self.comments is not None:
            serialized['comments'] = self.comments
        return serialized if serialized else None


@dataclass
class Comment:
    """Representation of a Reddit comment."""

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
    """Canonical representation of a Reddit thread."""

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'subreddit': self.subreddit,
            'date': self.date,
            'date_confidence': self.date_confidence,
            'engagement': self.engagement.to_dict() if self.engagement else None,
            'top_comments': [comment.to_dict() for comment in self.top_comments],
            'comment_insights': self.comment_insights,
            'relevance': self.relevance,
            'why_relevant': self.why_relevant,
            'subs': self.subs.to_dict(),
            'score': self.score,
        }


@dataclass
class XItem:
    """Canonical representation of an X post."""

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
        }


@dataclass
class YouTubeItem:
    """Canonical representation of a YouTube video."""

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
        }


@dataclass
class LinkedInItem:
    """Canonical representation of a LinkedIn post."""

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
    """Canonical representation of a web search result (lacks engagement data)."""

    id: str
    title: str
    url: str
    source_domain: str  # e.g., "medium.com", "github.com"
    snippet: str
    date: Optional[str] = None
    date_confidence: str = "low"
    relevance: float = 0.5
    why_relevant: str = ""
    subs: SubScores = field(default_factory=SubScores)
    score: int = 0

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
        }


@dataclass
class Report:
    """Complete research report container."""

    topic: str
    range_from: str
    range_to: str
    generated_at: str
    mode: str  # Values: 'reddit-only', 'x-only', 'both', 'web-only', 'all', etc.
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
    # Error tracking
    reddit_error: Optional[str] = None
    x_error: Optional[str] = None
    youtube_error: Optional[str] = None
    linkedin_error: Optional[str] = None
    web_error: Optional[str] = None
    # Cache metadata
    from_cache: bool = False
    cache_age_hours: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        serialized = {
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
            serialized['reddit_error'] = self.reddit_error
        if self.x_error:
            serialized['x_error'] = self.x_error
        if self.youtube_error:
            serialized['youtube_error'] = self.youtube_error
        if self.linkedin_error:
            serialized['linkedin_error'] = self.linkedin_error
        if self.web_error:
            serialized['web_error'] = self.web_error
        if self.from_cache:
            serialized['from_cache'] = self.from_cache
        if self.cache_age_hours is not None:
            serialized['cache_age_hours'] = self.cache_age_hours
        return serialized

    @classmethod
    def from_dict(cls, serialized_data: Dict[str, Any]) -> "Report":
        """Reconstructs a Report from its serialized dictionary form."""
        # Handle range field transformation
        range_section = serialized_data.get('range', {})
        period_start = range_section.get('from', serialized_data.get('range_from', ''))
        period_end = range_section.get('to', serialized_data.get('range_to', ''))

        # Reconstruct Reddit items
        reddit_items = []
        reddit_index = 0
        reddit_source = serialized_data.get('reddit', [])
        while reddit_index < len(reddit_source):
            item_data = reddit_source[reddit_index]
            engagement_obj = None
            if item_data.get('engagement'):
                engagement_obj = Engagement(**item_data['engagement'])
            comment_objects = []
            comment_index = 0
            comment_source = item_data.get('top_comments', [])
            while comment_index < len(comment_source):
                comment_objects.append(Comment(**comment_source[comment_index]))
                comment_index += 1
            subs_obj = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            reddit_items.append(RedditItem(
                id=item_data['id'],
                title=item_data['title'],
                url=item_data['url'],
                subreddit=item_data['subreddit'],
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                engagement=engagement_obj,
                top_comments=comment_objects,
                comment_insights=item_data.get('comment_insights', []),
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs_obj,
                score=item_data.get('score', 0),
            ))
            reddit_index += 1

        # Reconstruct X items
        x_items = []
        x_index = 0
        x_source = serialized_data.get('x', [])
        while x_index < len(x_source):
            item_data = x_source[x_index]
            engagement_obj = None
            if item_data.get('engagement'):
                engagement_obj = Engagement(**item_data['engagement'])
            subs_obj = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            x_items.append(XItem(
                id=item_data['id'],
                text=item_data['text'],
                url=item_data['url'],
                author_handle=item_data['author_handle'],
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                engagement=engagement_obj,
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs_obj,
                score=item_data.get('score', 0),
            ))
            x_index += 1

        # Reconstruct YouTube items
        youtube_items = []
        youtube_index = 0
        youtube_source = serialized_data.get('youtube', [])
        while youtube_index < len(youtube_source):
            item_data = youtube_source[youtube_index]
            engagement_obj = None
            if item_data.get('engagement'):
                engagement_obj = Engagement(**item_data['engagement'])
            subs_obj = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            youtube_items.append(YouTubeItem(
                id=item_data['id'],
                title=item_data['title'],
                url=item_data['url'],
                channel_name=item_data.get('channel_name', ''),
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                engagement=engagement_obj,
                description=item_data.get('description'),
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs_obj,
                score=item_data.get('score', 0),
            ))
            youtube_index += 1

        # Reconstruct LinkedIn items
        linkedin_items = []
        linkedin_index = 0
        linkedin_source = serialized_data.get('linkedin', [])
        while linkedin_index < len(linkedin_source):
            item_data = linkedin_source[linkedin_index]
            engagement_obj = None
            if item_data.get('engagement'):
                engagement_obj = Engagement(**item_data['engagement'])
            subs_obj = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
            linkedin_items.append(LinkedInItem(
                id=item_data['id'],
                text=item_data['text'],
                url=item_data['url'],
                author_name=item_data.get('author_name', ''),
                author_title=item_data.get('author_title'),
                date=item_data.get('date'),
                date_confidence=item_data.get('date_confidence', 'low'),
                engagement=engagement_obj,
                relevance=item_data.get('relevance', 0.5),
                why_relevant=item_data.get('why_relevant', ''),
                subs=subs_obj,
                score=item_data.get('score', 0),
            ))
            linkedin_index += 1

        # Reconstruct Web items
        web_items = []
        web_index = 0
        web_source = serialized_data.get('web', [])
        while web_index < len(web_source):
            item_data = web_source[web_index]
            subs_obj = SubScores(**item_data.get('subs', {})) if item_data.get('subs') else SubScores()
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
                subs=subs_obj,
                score=item_data.get('score', 0),
            ))
            web_index += 1

        return cls(
            topic=serialized_data['topic'],
            range_from=period_start,
            range_to=period_end,
            generated_at=serialized_data['generated_at'],
            mode=serialized_data['mode'],
            openai_model_used=serialized_data.get('openai_model_used'),
            xai_model_used=serialized_data.get('xai_model_used'),
            reddit=reddit_items,
            x=x_items,
            youtube=youtube_items,
            linkedin=linkedin_items,
            web=web_items,
            best_practices=serialized_data.get('best_practices', []),
            prompt_pack=serialized_data.get('prompt_pack', []),
            context_snippet_md=serialized_data.get('context_snippet_md', ''),
            reddit_error=serialized_data.get('reddit_error'),
            x_error=serialized_data.get('x_error'),
            youtube_error=serialized_data.get('youtube_error'),
            linkedin_error=serialized_data.get('linkedin_error'),
            web_error=serialized_data.get('web_error'),
            from_cache=serialized_data.get('from_cache', False),
            cache_age_hours=serialized_data.get('cache_age_hours'),
        )


def instantiate_report(
    subject_matter: str,
    period_start: str,
    period_end: str,
    operation_mode: str,
    openai_model: Optional[str] = None,
    xai_model: Optional[str] = None,
) -> Report:
    """Factory function to construct a new report with metadata."""
    return Report(
        topic=subject_matter,
        range_from=period_start,
        range_to=period_end,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mode=operation_mode,
        openai_model_used=openai_model,
        xai_model_used=xai_model,
    )
