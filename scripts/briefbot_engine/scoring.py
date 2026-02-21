"""Scoring and near-duplicate suppression for aggregated items."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from . import timeframe
from .records import Channel, Scorecard, Signal


PLATFORM_WEIGHTS = {
    "topicality": 0.38,
    "freshness": 0.27,
    "traction": 0.23,
    "trust": 0.12,
}
WEB_WEIGHTS = {
    "topicality": 0.52,
    "freshness": 0.33,
    "trust": 0.15,
}

MISSING_INTERACTION_FALLBACK = 42
MISSING_INTERACTION_PENALTY = 7
WEB_SOURCE_PENALTY = 6
WEB_DATE_BONUS = 5
WEB_DATE_PENALTY = 9

SOURCE_TRUST_BASE = {
    Channel.REDDIT: 61,
    Channel.X: 53,
    Channel.YOUTUBE: 59,
    Channel.LINKEDIN: 66,
    Channel.WEB: 49,
}


def _percentile_ranks(values: List[Optional[float]], fallback: float = 50) -> List[float]:
    """Convert raw values to percentile ranks (0-100) across the batch."""
    valid = [(idx, value) for idx, value in enumerate(values) if value is not None]
    if not valid:
        return [fallback if v is None else 50.0 for v in values]

    sorted_valid = sorted(valid, key=lambda pair: pair[1])
    n = len(sorted_valid)

    rank_by_index = {}
    for rank_idx, (item_idx, _value) in enumerate(sorted_valid):
        rank_by_index[item_idx] = (rank_idx / max(1, n - 1)) * 100

    return [None if value is None else rank_by_index[idx] for idx, value in enumerate(values)]


def _weighted_geometric(values: List[float], weights: List[float]) -> float:
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    product = 1.0
    for value, weight in zip(values, weights):
        adjusted = max(1.0, value)
        product *= adjusted ** weight
    return product ** (1.0 / total_weight)


def _trust(item: Signal) -> int:
    base = SOURCE_TRUST_BASE.get(item.channel, 50)
    if item.time_confidence == timeframe.CONFIDENCE_SOLID:
        base += 5
    elif item.time_confidence == timeframe.CONFIDENCE_WEAK:
        base -= 7
    return max(0, min(100, int(base)))


def rank_items(items: List[Signal], source_weights: Optional[dict] = None) -> List[Signal]:
    """Assign scores then return globally sorted items."""
    if not items:
        return items

    platform_items = [item for item in items if item.channel != Channel.WEB]
    web_items = [item for item in items if item.channel == Channel.WEB]

    _score_platform_items(platform_items)
    _score_web_items(web_items)
    _apply_source_weights([*platform_items, *web_items], source_weights or {})

    return _sort_by_score([*platform_items, *web_items])


def _apply_source_weights(items: List[Signal], source_weights: dict) -> None:
    if not items or not source_weights:
        return
    for item in items:
        weight = float(source_weights.get(item.channel.value, 1.0))
        if weight == 1.0:
            continue
        adjusted = max(0, min(100, round(item.rank * weight)))
        item.rank = adjusted
        item.extras["stance_weight"] = weight


def _score_platform_items(items: List[Signal]) -> None:
    if not items:
        return

    raw_topical = [item.topicality * 100 for item in items]
    raw_fresh = [timeframe.recency_score(item.dated) for item in items]
    raw_interaction = [
        item.interaction.pulse if item.interaction else None for item in items
    ]
    raw_trust = [_trust(item) for item in items]

    pct_topical = _percentile_ranks([float(v) for v in raw_topical])
    pct_fresh = _percentile_ranks([float(v) for v in raw_fresh])
    pct_interaction = _percentile_ranks(raw_interaction, fallback=MISSING_INTERACTION_FALLBACK)

    weights = [
        PLATFORM_WEIGHTS["topicality"],
        PLATFORM_WEIGHTS["freshness"],
        PLATFORM_WEIGHTS["traction"],
        PLATFORM_WEIGHTS["trust"],
    ]

    for idx, item in enumerate(items):
        topical = pct_topical[idx]
        fresh = pct_fresh[idx]
        traction = pct_interaction[idx] if pct_interaction[idx] is not None else MISSING_INTERACTION_FALLBACK
        trust = raw_trust[idx]

        item.scorecard = Scorecard(
            topicality=int(topical),
            freshness=int(fresh),
            traction=int(traction),
            trust=int(trust),
        )

        score = _weighted_geometric([topical, fresh, traction, trust], weights)
        if raw_interaction[idx] is None:
            score -= MISSING_INTERACTION_PENALTY
        if item.time_confidence == timeframe.CONFIDENCE_WEAK:
            score -= 5

        item.rank = max(0, min(100, round(score)))


def _score_web_items(items: List[Signal]) -> None:
    if not items:
        return

    for item in items:
        topical = int(item.topicality * 100)
        fresh = timeframe.recency_score(item.dated)
        trust = _trust(item)

        item.scorecard = Scorecard(
            topicality=topical,
            freshness=fresh,
            traction=0,
            trust=trust,
        )

        total = (
            WEB_WEIGHTS["topicality"] * topical
            + WEB_WEIGHTS["freshness"] * fresh
            + WEB_WEIGHTS["trust"] * trust
        )
        total -= WEB_SOURCE_PENALTY

        if item.time_confidence == timeframe.CONFIDENCE_SOLID:
            total += WEB_DATE_BONUS
        elif item.time_confidence == timeframe.CONFIDENCE_WEAK:
            total -= WEB_DATE_PENALTY

        item.rank = max(0, min(100, round(total)))


def _sort_by_score(items: List[Signal]) -> List[Signal]:
    """Sort items by rank (desc), trust, then date."""

    def _date_ordinal(value: Optional[str]) -> int:
        if not value:
            return -1
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().toordinal()
        except ValueError:
            return -1

    def sort_key(item: Signal):
        trust = item.scorecard.trust if item.scorecard else 0
        title = (item.headline or "").lower()
        return (-item.rank, -trust, -_date_ordinal(item.dated), title)

    return sorted(items, key=sort_key)


def _tokenize(text: str) -> List[str]:
    import re

    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _shingles(tokens: List[str], width: int = 3) -> Iterable[str]:
    if not tokens:
        return []
    width = min(width, max(1, len(tokens)))
    return [" ".join(tokens[idx : idx + width]) for idx in range(max(1, len(tokens) - width + 1))]


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _text_of(item: Signal) -> str:
    """Extract the primary text field from a signal."""
    return " ".join([item.headline or "", item.byline or "", item.url or ""]).strip()


def deduplicate(
    items: List[Signal],
    similarity_threshold: float = 0.88,
) -> List[Signal]:
    """Remove near-duplicates using shingled Jaccard similarity."""
    if len(items) <= 1:
        return items

    shingles = [
        list(_shingles(_tokenize(_text_of(item)), width=3))
        for item in items
    ]
    discarded_indices = set()
    for left in range(len(items)):
        if left in discarded_indices:
            continue
        for right in range(left + 1, len(items)):
            if right in discarded_indices:
                continue
            if _jaccard(shingles[left], shingles[right]) >= similarity_threshold:
                if items[left].rank >= items[right].rank:
                    discarded_indices.add(right)
                else:
                    discarded_indices.add(left)
                    break
    return [item for idx, item in enumerate(items) if idx not in discarded_indices]
