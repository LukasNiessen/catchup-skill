#
# Ranking Engine: Computes popularity-aware scores for discovered content
# Implements weighted scoring based on relevance, recency, and engagement
#

import math
from typing import List, Optional, Union

from . import dates, schema

# Weight distribution for platforms with engagement data (Reddit/X)
RELEVANCE_COEFFICIENT = 0.45
RECENCY_COEFFICIENT = 0.25
ENGAGEMENT_COEFFICIENT = 0.30

# Weight distribution for web search (no engagement, redistributed to 100%)
WEB_RELEVANCE_COEFFICIENT = 0.55
WEB_RECENCY_COEFFICIENT = 0.45
WEB_SOURCE_DEDUCTION = 15  # Points subtracted for lacking engagement data

# Web search date confidence modifiers
WEB_VERIFIED_DATE_BONUS = 10   # Reward for URL-verified recent date (high confidence)
WEB_MISSING_DATE_PENALTY = 20  # Penalty for no date signals (low confidence)

# Fallback engagement score
BASELINE_ENGAGEMENT = 35
MISSING_ENGAGEMENT_PENALTY = 10


def safe_logarithm(metric_value: Optional[int]) -> float:
    """Computes log1p safely, handling None and negative inputs."""
    if metric_value is None or metric_value < 0:
        return 0.0
    return math.log1p(metric_value)


# Preserve the original function name for API compatibility
log1p_safe = safe_logarithm


def calculate_reddit_engagement_value(engagement_metrics: Optional[schema.Engagement]) -> Optional[float]:
    """
    Derives raw engagement value for Reddit content.

    Formula: 0.55*log1p(score) + 0.40*log1p(num_comments) + 0.05*(upvote_ratio*10)
    """
    if engagement_metrics is None:
        return None

    if engagement_metrics.score is None and engagement_metrics.num_comments is None:
        return None

    score_component = safe_logarithm(engagement_metrics.score)
    comments_component = safe_logarithm(engagement_metrics.num_comments)
    ratio_component = (engagement_metrics.upvote_ratio or 0.5) * 10

    return 0.55 * score_component + 0.40 * comments_component + 0.05 * ratio_component


# Preserve the original function name for API compatibility
compute_reddit_engagement_raw = calculate_reddit_engagement_value


def calculate_x_engagement_value(engagement_metrics: Optional[schema.Engagement]) -> Optional[float]:
    """
    Derives raw engagement value for X content.

    Formula: 0.55*log1p(likes) + 0.25*log1p(reposts) + 0.15*log1p(replies) + 0.05*log1p(quotes)
    """
    if engagement_metrics is None:
        return None

    if engagement_metrics.likes is None and engagement_metrics.reposts is None:
        return None

    likes_component = safe_logarithm(engagement_metrics.likes)
    reposts_component = safe_logarithm(engagement_metrics.reposts)
    replies_component = safe_logarithm(engagement_metrics.replies)
    quotes_component = safe_logarithm(engagement_metrics.quotes)

    return 0.55 * likes_component + 0.25 * reposts_component + 0.15 * replies_component + 0.05 * quotes_component


# Preserve the original function name for API compatibility
compute_x_engagement_raw = calculate_x_engagement_value


def calculate_youtube_engagement_value(engagement_metrics: Optional[schema.Engagement]) -> Optional[float]:
    """
    Derives raw engagement value for YouTube content.

    Formula: 0.70*log1p(views) + 0.30*log1p(likes)
    Views receive heavy weighting as the primary engagement signal for video content.
    """
    if engagement_metrics is None:
        return None

    if engagement_metrics.views is None and engagement_metrics.likes is None:
        return None

    views_component = safe_logarithm(engagement_metrics.views)
    likes_component = safe_logarithm(engagement_metrics.likes)

    return 0.70 * views_component + 0.30 * likes_component


# Preserve the original function name for API compatibility
compute_youtube_engagement_raw = calculate_youtube_engagement_value


def calculate_linkedin_engagement_value(engagement_metrics: Optional[schema.Engagement]) -> Optional[float]:
    """
    Derives raw engagement value for LinkedIn content.

    Formula: 0.60*log1p(reactions) + 0.40*log1p(comments)
    """
    if engagement_metrics is None:
        return None

    if engagement_metrics.reactions is None and engagement_metrics.comments is None:
        return None

    reactions_component = safe_logarithm(engagement_metrics.reactions)
    comments_component = safe_logarithm(engagement_metrics.comments)

    return 0.60 * reactions_component + 0.40 * comments_component


# Preserve the original function name for API compatibility
compute_linkedin_engagement_raw = calculate_linkedin_engagement_value


def scale_to_percentage(raw_values: List[float], fallback: float = 50) -> List[float]:
    """
    Rescales a collection of values to the 0-100 range.

    Args:
        raw_values: Unscaled values (None values are preserved)
        fallback: Default value assigned to None entries

    Returns:
        Rescaled values
    """
    # Extract non-None values
    valid_entries = [entry for entry in raw_values if entry is not None]
    if not valid_entries:
        return [fallback if entry is None else 50 for entry in raw_values]

    minimum_value = min(valid_entries)
    maximum_value = max(valid_entries)
    value_span = maximum_value - minimum_value

    if value_span == 0:
        return [50 if entry is None else 50 for entry in raw_values]

    scaled_results = []
    entry_index = 0
    while entry_index < len(raw_values):
        entry = raw_values[entry_index]
        if entry is None:
            scaled_results.append(None)
        else:
            scaled_value = ((entry - minimum_value) / value_span) * 100
            scaled_results.append(scaled_value)
        entry_index += 1

    return scaled_results


# Preserve the original function name for API compatibility
normalize_to_100 = scale_to_percentage


def compute_reddit_scores(item_collection: List[schema.RedditItem]) -> List[schema.RedditItem]:
    """
    Assigns scores to Reddit items based on the weighted formula.

    Args:
        item_collection: Reddit items to score

    Returns:
        Items with populated score fields
    """
    if not item_collection:
        return item_collection

    # Calculate raw engagement values
    raw_engagement_values = []
    item_index = 0
    while item_index < len(item_collection):
        raw_engagement_values.append(calculate_reddit_engagement_value(item_collection[item_index].engagement))
        item_index += 1

    # Scale engagement to percentage
    scaled_engagement = scale_to_percentage(raw_engagement_values)

    item_index = 0
    while item_index < len(item_collection):
        current_item = item_collection[item_index]

        # Relevance component (model-provided, scale to 0-100)
        relevance_component = int(current_item.relevance * 100)

        # Recency component
        recency_component = dates.recency_score(current_item.date)

        # Engagement component
        if scaled_engagement[item_index] is not None:
            engagement_component = int(scaled_engagement[item_index])
        else:
            engagement_component = BASELINE_ENGAGEMENT

        # Record component scores
        current_item.subs = schema.SubScores(
            relevance=relevance_component,
            recency=recency_component,
            engagement=engagement_component,
        )

        # Calculate weighted total
        weighted_total = (
            RELEVANCE_COEFFICIENT * relevance_component +
            RECENCY_COEFFICIENT * recency_component +
            ENGAGEMENT_COEFFICIENT * engagement_component
        )

        # Apply penalty for missing engagement
        if raw_engagement_values[item_index] is None:
            weighted_total -= MISSING_ENGAGEMENT_PENALTY

        # Apply penalty for uncertain dates
        if current_item.date_confidence == "low":
            weighted_total -= 10
        elif current_item.date_confidence == "med":
            weighted_total -= 5

        current_item.score = max(0, min(100, int(weighted_total)))
        item_index += 1

    return item_collection


# Preserve the original function name for API compatibility
score_reddit_items = compute_reddit_scores


def compute_x_scores(item_collection: List[schema.XItem]) -> List[schema.XItem]:
    """
    Assigns scores to X items based on the weighted formula.

    Args:
        item_collection: X items to score

    Returns:
        Items with populated score fields
    """
    if not item_collection:
        return item_collection

    # Calculate raw engagement values
    raw_engagement_values = []
    item_index = 0
    while item_index < len(item_collection):
        raw_engagement_values.append(calculate_x_engagement_value(item_collection[item_index].engagement))
        item_index += 1

    # Scale engagement to percentage
    scaled_engagement = scale_to_percentage(raw_engagement_values)

    item_index = 0
    while item_index < len(item_collection):
        current_item = item_collection[item_index]

        # Relevance component
        relevance_component = int(current_item.relevance * 100)

        # Recency component
        recency_component = dates.recency_score(current_item.date)

        # Engagement component
        if scaled_engagement[item_index] is not None:
            engagement_component = int(scaled_engagement[item_index])
        else:
            engagement_component = BASELINE_ENGAGEMENT

        # Record component scores
        current_item.subs = schema.SubScores(
            relevance=relevance_component,
            recency=recency_component,
            engagement=engagement_component,
        )

        # Calculate weighted total
        weighted_total = (
            RELEVANCE_COEFFICIENT * relevance_component +
            RECENCY_COEFFICIENT * recency_component +
            ENGAGEMENT_COEFFICIENT * engagement_component
        )

        # Apply penalty for missing engagement
        if raw_engagement_values[item_index] is None:
            weighted_total -= MISSING_ENGAGEMENT_PENALTY

        # Apply penalty for uncertain dates
        if current_item.date_confidence == "low":
            weighted_total -= 10
        elif current_item.date_confidence == "med":
            weighted_total -= 5

        current_item.score = max(0, min(100, int(weighted_total)))
        item_index += 1

    return item_collection


# Preserve the original function name for API compatibility
score_x_items = compute_x_scores


def compute_youtube_scores(item_collection: List[schema.YouTubeItem]) -> List[schema.YouTubeItem]:
    """
    Assigns scores to YouTube items based on the weighted formula.

    Args:
        item_collection: YouTube items to score

    Returns:
        Items with populated score fields
    """
    if not item_collection:
        return item_collection

    # Calculate raw engagement values
    raw_engagement_values = []
    item_index = 0
    while item_index < len(item_collection):
        raw_engagement_values.append(calculate_youtube_engagement_value(item_collection[item_index].engagement))
        item_index += 1

    # Scale engagement to percentage
    scaled_engagement = scale_to_percentage(raw_engagement_values)

    item_index = 0
    while item_index < len(item_collection):
        current_item = item_collection[item_index]

        # Relevance component
        relevance_component = int(current_item.relevance * 100)

        # Recency component
        recency_component = dates.recency_score(current_item.date)

        # Engagement component
        if scaled_engagement[item_index] is not None:
            engagement_component = int(scaled_engagement[item_index])
        else:
            engagement_component = BASELINE_ENGAGEMENT

        # Record component scores
        current_item.subs = schema.SubScores(
            relevance=relevance_component,
            recency=recency_component,
            engagement=engagement_component,
        )

        # Calculate weighted total
        weighted_total = (
            RELEVANCE_COEFFICIENT * relevance_component +
            RECENCY_COEFFICIENT * recency_component +
            ENGAGEMENT_COEFFICIENT * engagement_component
        )

        # Apply penalty for missing engagement
        if raw_engagement_values[item_index] is None:
            weighted_total -= MISSING_ENGAGEMENT_PENALTY

        # Apply penalty for uncertain dates
        if current_item.date_confidence == "low":
            weighted_total -= 10
        elif current_item.date_confidence == "med":
            weighted_total -= 5

        current_item.score = max(0, min(100, int(weighted_total)))
        item_index += 1

    return item_collection


# Preserve the original function name for API compatibility
score_youtube_items = compute_youtube_scores


def compute_linkedin_scores(item_collection: List[schema.LinkedInItem]) -> List[schema.LinkedInItem]:
    """
    Assigns scores to LinkedIn items based on the weighted formula.

    Args:
        item_collection: LinkedIn items to score

    Returns:
        Items with populated score fields
    """
    if not item_collection:
        return item_collection

    # Calculate raw engagement values
    raw_engagement_values = []
    item_index = 0
    while item_index < len(item_collection):
        raw_engagement_values.append(calculate_linkedin_engagement_value(item_collection[item_index].engagement))
        item_index += 1

    # Scale engagement to percentage
    scaled_engagement = scale_to_percentage(raw_engagement_values)

    item_index = 0
    while item_index < len(item_collection):
        current_item = item_collection[item_index]

        # Relevance component
        relevance_component = int(current_item.relevance * 100)

        # Recency component
        recency_component = dates.recency_score(current_item.date)

        # Engagement component
        if scaled_engagement[item_index] is not None:
            engagement_component = int(scaled_engagement[item_index])
        else:
            engagement_component = BASELINE_ENGAGEMENT

        # Record component scores
        current_item.subs = schema.SubScores(
            relevance=relevance_component,
            recency=recency_component,
            engagement=engagement_component,
        )

        # Calculate weighted total
        weighted_total = (
            RELEVANCE_COEFFICIENT * relevance_component +
            RECENCY_COEFFICIENT * recency_component +
            ENGAGEMENT_COEFFICIENT * engagement_component
        )

        # Apply penalty for missing engagement
        if raw_engagement_values[item_index] is None:
            weighted_total -= MISSING_ENGAGEMENT_PENALTY

        # Apply penalty for uncertain dates
        if current_item.date_confidence == "low":
            weighted_total -= 10
        elif current_item.date_confidence == "med":
            weighted_total -= 5

        current_item.score = max(0, min(100, int(weighted_total)))
        item_index += 1

    return item_collection


# Preserve the original function name for API compatibility
score_linkedin_items = compute_linkedin_scores


def compute_websearch_scores(item_collection: List[schema.WebSearchItem]) -> List[schema.WebSearchItem]:
    """
    Assigns scores to WebSearch items using the engagement-free formula.

    Uses redistributed weights: 55% relevance + 45% recency - 15pt source penalty.
    This ensures web results rank below comparable Reddit/X items.

    Date confidence modifiers:
    - High confidence (URL-verified date): +10 bonus
    - Med confidence (snippet-extracted date): neutral
    - Low confidence (no date signals): -20 penalty

    Args:
        item_collection: WebSearch items to score

    Returns:
        Items with populated score fields
    """
    if not item_collection:
        return item_collection

    item_index = 0
    while item_index < len(item_collection):
        current_item = item_collection[item_index]

        # Relevance component
        relevance_component = int(current_item.relevance * 100)

        # Recency component
        recency_component = dates.recency_score(current_item.date)

        # Record component scores (engagement is 0 - no data available)
        current_item.subs = schema.SubScores(
            relevance=relevance_component,
            recency=recency_component,
            engagement=0,  # Explicitly zero - no engagement data available
        )

        # Calculate weighted total using web-specific coefficients
        weighted_total = (
            WEB_RELEVANCE_COEFFICIENT * relevance_component +
            WEB_RECENCY_COEFFICIENT * recency_component
        )

        # Apply source penalty (web results < Reddit/X for equivalent relevance/recency)
        weighted_total -= WEB_SOURCE_DEDUCTION

        # Apply date confidence modifiers
        # High confidence (URL-verified): bonus
        # Med confidence (snippet-extracted): neutral
        # Low confidence (no date signals): heavy penalty
        if current_item.date_confidence == "high":
            weighted_total += WEB_VERIFIED_DATE_BONUS
        elif current_item.date_confidence == "low":
            weighted_total -= WEB_MISSING_DATE_PENALTY

        current_item.score = max(0, min(100, int(weighted_total)))
        item_index += 1

    return item_collection


# Preserve the original function name for API compatibility
score_websearch_items = compute_websearch_scores


def arrange_by_score(item_collection: List[Union[schema.RedditItem, schema.XItem, schema.YouTubeItem, schema.LinkedInItem, schema.WebSearchItem]]) -> List:
    """
    Orders items by score (descending), then date, then source priority.

    Args:
        item_collection: Items to arrange

    Returns:
        Arranged items
    """
    def ordering_key(item):
        # Primary: score descending (negate for descending order)
        score_key = -item.score

        # Secondary: date descending (most recent first)
        date_value = item.date or "0000-00-00"
        date_key = -int(date_value.replace("-", ""))

        # Tertiary: source priority (Reddit > X > YouTube > LinkedIn > WebSearch)
        if isinstance(item, schema.RedditItem):
            source_rank = 0
        elif isinstance(item, schema.XItem):
            source_rank = 1
        elif isinstance(item, schema.YouTubeItem):
            source_rank = 2
        elif isinstance(item, schema.LinkedInItem):
            source_rank = 3
        else:  # WebSearchItem
            source_rank = 4

        # Quaternary: content text for stability
        content_text = getattr(item, "title", "") or getattr(item, "text", "")

        return (score_key, date_key, source_rank, content_text)

    return sorted(item_collection, key=ordering_key)


# Preserve the original function name for API compatibility
sort_items = arrange_by_score
