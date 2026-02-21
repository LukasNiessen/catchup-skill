"""Ranking and near-duplicate suppression for aggregated items."""

from datetime import datetime
from typing import List, Optional

from . import temporal
from .content import ContentItem, ScoreParts, Source


# ---------------------------------------------------------------------------
# Scoring weights and penalties
# ---------------------------------------------------------------------------

PLATFORM_WEIGHTS = {"signal": 0.42, "freshness": 0.31, "engagement": 0.27}
WEB_WEIGHTS = {"signal": 0.64, "freshness": 0.36}

MISSING_ENGAGEMENT_FALLBACK = 48
MISSING_ENGAGEMENT_PENALTY = 6
WEB_SOURCE_PENALTY = 7
WEB_DATE_BONUS = 9
WEB_DATE_PENALTY = 10


# ---------------------------------------------------------------------------
# Percentile conversion
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Harmonic mean combiner
# ---------------------------------------------------------------------------

def _weighted_harmonic_mean(values: List[float], weights: List[float], epsilon: float = 1.0) -> float:
    """Compute a weighted harmonic mean, floored by epsilon to avoid division by zero."""
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    denominator = sum(weight / max(value, epsilon) for weight, value in zip(weights, values))
    return total_weight / denominator if denominator > 0 else 0.0


# ---------------------------------------------------------------------------
# Main ranking function
# ---------------------------------------------------------------------------

def rank_items(items: List[ContentItem]) -> List[ContentItem]:
    """Assign scores then return globally sorted items."""
    if not items:
        return items

    platform_items = [item for item in items if item.source != Source.WEB]
    web_items = [item for item in items if item.source == Source.WEB]

    _score_platform_items(platform_items)
    _score_web_items(web_items)

    return _sort_by_score([*platform_items, *web_items])


def _score_platform_items(items: List[ContentItem]) -> None:
    """Score non-web items via percentile normalization + harmonic blend."""
    if not items:
        return

    raw_signal = [item.signal * 100 for item in items]
    raw_recency = [temporal.freshness_score(item.published) for item in items]
    raw_engagement = [item.engagement.composite if item.engagement else None for item in items]

    pct_signal = _percentile_ranks([float(v) for v in raw_signal])
    pct_recency = _percentile_ranks([float(v) for v in raw_recency])
    pct_engagement = _percentile_ranks(raw_engagement, fallback=MISSING_ENGAGEMENT_FALLBACK)

    weights = [PLATFORM_WEIGHTS["signal"], PLATFORM_WEIGHTS["freshness"], PLATFORM_WEIGHTS["engagement"]]

    for idx, item in enumerate(items):
        rel_pct = pct_signal[idx]
        rec_pct = pct_recency[idx]
        eng_pct = pct_engagement[idx] if pct_engagement[idx] is not None else MISSING_ENGAGEMENT_FALLBACK

        item.score_parts = ScoreParts(
            signal=int(rel_pct),
            freshness=int(rec_pct),
            engagement=int(eng_pct),
        )

        score = _weighted_harmonic_mean([rel_pct, rec_pct, eng_pct], weights)
        if raw_engagement[idx] is None:
            score -= MISSING_ENGAGEMENT_PENALTY
        if item.date_quality == "low":
            score -= 7
        elif item.date_quality == "med":
            score -= 3

        item.score = max(0, min(100, round(score)))


def _score_web_items(items: List[ContentItem]) -> None:
    """Score web items using the engagement-free formula."""
    if not items:
        return

    for item in items:
        rel = int(item.signal * 100)
        rec = temporal.freshness_score(item.published)

        item.score_parts = ScoreParts(signal=rel, freshness=rec, engagement=0)

        total = WEB_WEIGHTS["signal"] * rel + WEB_WEIGHTS["freshness"] * rec
        total -= WEB_SOURCE_PENALTY

        if item.date_quality == "high":
            total += WEB_DATE_BONUS
        elif item.date_quality == "low":
            total -= WEB_DATE_PENALTY

        item.score = max(0, min(100, round(total)))


def _sort_by_score(items: List[ContentItem]) -> List[ContentItem]:
    """Sort items by score (desc), date, then source priority."""
    source_order = {
        Source.REDDIT: 0,
        Source.X: 1,
        Source.YOUTUBE: 2,
        Source.LINKEDIN: 3,
        Source.WEB: 4,
    }

    def _date_ordinal(value: Optional[str]) -> int:
        if not value:
            return -1
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().toordinal()
        except ValueError:
            return -1

    def sort_key(item: ContentItem):
        src_rank = source_order.get(item.source, 4)
        return (-item.score, -_date_ordinal(item.published), src_rank, item.title.lower())

    return sorted(items, key=sort_key)


# ---------------------------------------------------------------------------
# SimHash deduplication
# ---------------------------------------------------------------------------

_FNV_OFFSET = 0xcbf29ce484222325
_FNV_PRIME = 0x100000001b3
_MASK64 = (1 << 64) - 1


def _fnv1a_64(token: str) -> int:
    """Compute FNV-1a 64-bit hash for a string token."""
    h = _FNV_OFFSET
    for byte in token.encode("utf-8"):
        h ^= byte
        h = (h * _FNV_PRIME) & _MASK64
    return h


def _simhash(text: str) -> int:
    """Compute a 64-bit SimHash fingerprint for the given text."""
    import re

    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
        return 0

    width = min(4, max(1, len(tokens)))
    shingles = [" ".join(tokens[idx : idx + width]) for idx in range(max(1, len(tokens) - width + 1))]

    bit_counts = [0] * 64
    for shingle in shingles:
        h = _fnv1a_64(shingle)
        for bit in range(64):
            if h & (1 << bit):
                bit_counts[bit] += 1
            else:
                bit_counts[bit] -= 1

    fingerprint = 0
    for bit in range(64):
        if bit_counts[bit] > 0:
            fingerprint |= (1 << bit)
    return fingerprint


def _hamming_distance(a: int, b: int) -> int:
    """Count differing bits between two 64-bit integers."""
    xor = a ^ b
    count = 0
    while xor:
        count += xor & 1
        xor >>= 1
    return count


def _text_of(item: ContentItem) -> str:
    """Extract the primary text field from a content item."""
    return item.title


def deduplicate(
    items: List[ContentItem],
    max_hamming: int = 10,
) -> List[ContentItem]:
    """Remove near-duplicates using SimHash fingerprinting with Hamming distance.

    Items with Hamming distance <= max_hamming are considered duplicates.
    The higher-scored item is kept from each duplicate pair.
    """
    if len(items) <= 1:
        return items

    fingerprints = [_simhash(_text_of(item)) for item in items]
    discarded_indices = set()
    for left in range(len(items)):
        if left in discarded_indices:
            continue
        for right in range(left + 1, len(items)):
            if right in discarded_indices:
                continue
            if _hamming_distance(fingerprints[left], fingerprints[right]) <= max_hamming:
                if items[left].score >= items[right].score:
                    discarded_indices.add(right)
                else:
                    discarded_indices.add(left)
                    break
    return [item for idx, item in enumerate(items) if idx not in discarded_indices]
