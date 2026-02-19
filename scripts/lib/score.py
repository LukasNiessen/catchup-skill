"""Weighted scoring engine for multi-platform content ranking."""

import math
from typing import List, Optional, Union

from . import dates, schema

WEIGHTS = {"relevance": 0.38, "recency": 0.34, "engagement": 0.28}
WEB_WEIGHTS = {"relevance": 0.58, "recency": 0.42}
WEB_SOURCE_PENALTY = 9
WEB_DATE_BONUS = 11
WEB_DATE_PENALTY = 14

BASELINE_ENGAGEMENT = 45
MISSING_ENGAGEMENT_PENALTY = 8


def _log1p(val: Optional[int]) -> float:
    """Safe log1p, returns 0.0 for None or negative inputs."""
    if val is None or val < 0:
        return 0.0
    return math.log1p(val)


def _reddit_engagement(eng: Optional[schema.Engagement]) -> Optional[float]:
    """Raw engagement value for Reddit: 0.48*score + 0.37*comments + 0.15*ratio."""
    if eng is None:
        return None
    if eng.score is None and eng.num_comments is None:
        return None
    sc = _log1p(eng.score)
    cm = _log1p(eng.num_comments)
    ra = (eng.upvote_ratio or 0.5) * 12
    return 0.48 * sc + 0.37 * cm + 0.15 * ra


def _x_engagement(eng: Optional[schema.Engagement]) -> Optional[float]:
    """Raw engagement value for X: 0.45*likes + 0.28*reposts + 0.17*replies + 0.10*quotes."""
    if eng is None:
        return None
    if eng.likes is None and eng.reposts is None:
        return None
    lk = _log1p(eng.likes)
    rp = _log1p(eng.reposts)
    re = _log1p(eng.replies)
    qu = _log1p(eng.quotes)
    return 0.45 * lk + 0.28 * rp + 0.17 * re + 0.10 * qu


def _youtube_engagement(eng: Optional[schema.Engagement]) -> Optional[float]:
    """Raw engagement value for YouTube: 0.62*views + 0.38*likes."""
    if eng is None:
        return None
    if eng.views is None and eng.likes is None:
        return None
    vw = _log1p(eng.views)
    lk = _log1p(eng.likes)
    return 0.62 * vw + 0.38 * lk


def _linkedin_engagement(eng: Optional[schema.Engagement]) -> Optional[float]:
    """Raw engagement value for LinkedIn: 0.55*reactions + 0.45*comments."""
    if eng is None:
        return None
    if eng.reactions is None and eng.comments is None:
        return None
    rx = _log1p(eng.reactions)
    cm = _log1p(eng.comments)
    return 0.55 * rx + 0.45 * cm


def _to_pct(values: List[float], fallback: float = 50) -> List[float]:
    """Rescale values to 0-100 range, preserving None entries."""
    valid = [v for v in values if v is not None]
    if not valid:
        return [fallback if v is None else 50 for v in values]

    lo = min(valid)
    hi = max(valid)
    span = hi - lo

    if span == 0:
        return [50 if v is None else 50 for v in values]

    result = []
    for v in values:
        if v is None:
            result.append(None)
        else:
            result.append(((v - lo + 0.1) / (span + 0.1)) * 100)
    return result


def score_reddit(items: List[schema.RedditItem]) -> List[schema.RedditItem]:
    """Assign weighted scores to Reddit items."""
    if not items:
        return items

    raw_eng = [_reddit_engagement(item.engagement) for item in items]
    scaled_eng = _to_pct(raw_eng)

    for i, item in enumerate(items):
        rel = int(item.relevance * 100)
        rec = dates.recency_score(item.date)
        eng_score = int(scaled_eng[i]) if scaled_eng[i] is not None else BASELINE_ENGAGEMENT

        item.subs = schema.SubScores(relevance=rel, recency=rec, engagement=eng_score)

        total = (
            WEIGHTS["relevance"] * rel
            + WEIGHTS["recency"] * rec
            + WEIGHTS["engagement"] * eng_score
        )

        if raw_eng[i] is None:
            total -= MISSING_ENGAGEMENT_PENALTY
        if item.date_confidence == "low":
            total -= 7
        elif item.date_confidence == "med":
            total -= 3

        item.score = max(0, min(100, round(total)))

    return items


def score_x(items: List[schema.XItem]) -> List[schema.XItem]:
    """Assign weighted scores to X items."""
    if not items:
        return items

    raw_eng = [_x_engagement(item.engagement) for item in items]
    scaled_eng = _to_pct(raw_eng)

    for i, item in enumerate(items):
        rel = int(item.relevance * 100)
        rec = dates.recency_score(item.date)
        eng_score = int(scaled_eng[i]) if scaled_eng[i] is not None else BASELINE_ENGAGEMENT

        item.subs = schema.SubScores(relevance=rel, recency=rec, engagement=eng_score)

        total = (
            WEIGHTS["relevance"] * rel
            + WEIGHTS["recency"] * rec
            + WEIGHTS["engagement"] * eng_score
        )

        if raw_eng[i] is None:
            total -= MISSING_ENGAGEMENT_PENALTY
        if item.date_confidence == "low":
            total -= 7
        elif item.date_confidence == "med":
            total -= 3

        item.score = max(0, min(100, round(total)))

    return items


def score_youtube(items: List[schema.YouTubeItem]) -> List[schema.YouTubeItem]:
    """Assign weighted scores to YouTube items."""
    if not items:
        return items

    raw_eng = [_youtube_engagement(item.engagement) for item in items]
    scaled_eng = _to_pct(raw_eng)

    for i, item in enumerate(items):
        rel = int(item.relevance * 100)
        rec = dates.recency_score(item.date)
        eng_score = int(scaled_eng[i]) if scaled_eng[i] is not None else BASELINE_ENGAGEMENT

        item.subs = schema.SubScores(relevance=rel, recency=rec, engagement=eng_score)

        total = (
            WEIGHTS["relevance"] * rel
            + WEIGHTS["recency"] * rec
            + WEIGHTS["engagement"] * eng_score
        )

        if raw_eng[i] is None:
            total -= MISSING_ENGAGEMENT_PENALTY
        if item.date_confidence == "low":
            total -= 7
        elif item.date_confidence == "med":
            total -= 3

        item.score = max(0, min(100, round(total)))

    return items


def score_linkedin(items: List[schema.LinkedInItem]) -> List[schema.LinkedInItem]:
    """Assign weighted scores to LinkedIn items."""
    if not items:
        return items

    raw_eng = [_linkedin_engagement(item.engagement) for item in items]
    scaled_eng = _to_pct(raw_eng)

    for i, item in enumerate(items):
        rel = int(item.relevance * 100)
        rec = dates.recency_score(item.date)
        eng_score = int(scaled_eng[i]) if scaled_eng[i] is not None else BASELINE_ENGAGEMENT

        item.subs = schema.SubScores(relevance=rel, recency=rec, engagement=eng_score)

        total = (
            WEIGHTS["relevance"] * rel
            + WEIGHTS["recency"] * rec
            + WEIGHTS["engagement"] * eng_score
        )

        if raw_eng[i] is None:
            total -= MISSING_ENGAGEMENT_PENALTY
        if item.date_confidence == "low":
            total -= 7
        elif item.date_confidence == "med":
            total -= 3

        item.score = max(0, min(100, round(total)))

    return items


def score_web(items: List[schema.WebSearchItem]) -> List[schema.WebSearchItem]:
    """Assign scores to web items using the engagement-free formula."""
    if not items:
        return items

    for i, item in enumerate(items):
        rel = int(item.relevance * 100)
        rec = dates.recency_score(item.date)

        item.subs = schema.SubScores(relevance=rel, recency=rec, engagement=0)

        total = (
            WEB_WEIGHTS["relevance"] * rel
            + WEB_WEIGHTS["recency"] * rec
        )

        total -= WEB_SOURCE_PENALTY

        if item.date_confidence == "high":
            total += WEB_DATE_BONUS
        elif item.date_confidence == "low":
            total -= WEB_DATE_PENALTY

        item.score = max(0, min(100, round(total)))

    return items


def rank(items: List[Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem, schema.WebSearchItem]]) -> List:
    """Sort items by score (desc), date, then source priority."""
    def sort_key(item):
        score_key = -item.score
        date_val = item.date or "0000-00-00"
        date_key = -int(date_val.replace("-", ""))

        if isinstance(item, schema.RedditItem):
            src = 0
        elif isinstance(item, schema.XItem):
            src = 1
        elif isinstance(item, schema.YouTubeItem):
            src = 2
        elif isinstance(item, schema.LinkedInItem):
            src = 3
        else:
            src = 4

        text = getattr(item, "title", "") or getattr(item, "text", "")
        return (score_key, date_key, src, text)

    return sorted(items, key=sort_key)
