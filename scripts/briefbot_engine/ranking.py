"""Percentile-harmonic scoring and SimHash deduplication for content items."""

from datetime import datetime
from typing import List, Optional

from . import temporal
from .content import ContentItem, ScoreBreakdown, Source


# ---------------------------------------------------------------------------
# Scoring weights and penalties
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS = {"relevance": 0.42, "recency": 0.31, "engagement": 0.27}
WEB_DIMENSION_WEIGHTS = {"relevance": 0.64, "recency": 0.36}

BASELINE_ENGAGEMENT = 48
MISSING_ENGAGEMENT_PENALTY = 6
WEB_SOURCE_PENALTY = 7
WEB_DATE_BONUS = 9
WEB_DATE_PENALTY = 10


# ---------------------------------------------------------------------------
# Percentile conversion
# ---------------------------------------------------------------------------

def _percentile_ranks(values: List[Optional[float]], fallback: float = 50) -> List[float]:
    """Convert raw values to percentile ranks (0-100) across the batch."""
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if not valid:
        return [fallback if v is None else 50.0 for v in values]

    # Sort by value to assign percentile ranks
    sorted_valid = sorted(valid, key=lambda pair: pair[1])
    n = len(sorted_valid)

    rank_map = {}
    for rank_idx, (orig_idx, _val) in enumerate(sorted_valid):
        rank_map[orig_idx] = (rank_idx / max(n - 1, 1)) * 100

    result = []
    for i, v in enumerate(values):
        if v is None:
            result.append(None)
        else:
            result.append(rank_map[i])
    return result


# ---------------------------------------------------------------------------
# Harmonic mean combiner
# ---------------------------------------------------------------------------

def _weighted_harmonic_mean(
    values: List[float],
    weights: List[float],
    epsilon: float = 1.0,
) -> float:
    """Compute a weighted harmonic mean, floored by epsilon to avoid division by zero."""
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    denominator = sum(w / max(v, epsilon) for w, v in zip(weights, values))
    return total_weight / denominator if denominator > 0 else 0.0


# ---------------------------------------------------------------------------
# Main ranking function
# ---------------------------------------------------------------------------

def rank_items(items: List[ContentItem]) -> List[ContentItem]:
    """Score and sort a batch of ContentItems using percentile-harmonic ranking.

    - Converts raw relevance, recency, and engagement values to percentile ranks
    - Combines via weighted harmonic mean (not linear sum)
    - Applies post-harmonic confidence adjustments
    - Web items use a two-dimensional (engagement-free) formula
    """
    if not items:
        return items

    # Separate web items (no engagement dimension) from platform items
    web_items = [i for i in items if i.source == Source.WEB]
    platform_items = [i for i in items if i.source != Source.WEB]

    _score_platform_items(platform_items)
    _score_web_items(web_items)

    all_items = platform_items + web_items
    return _sort_by_score(all_items)


def _score_platform_items(items: List[ContentItem]) -> None:
    """Score items that have engagement metrics (Reddit, X, YouTube, LinkedIn)."""
    if not items:
        return

    # Extract raw values
    raw_relevance = [item.relevance * 100 for item in items]
    raw_recency = [temporal.freshness_score(item.published) for item in items]
    raw_engagement = [
        item.signals.composite if item.signals and item.signals.composite is not None else None
        for item in items
    ]

    # Convert to percentile ranks
    pct_relevance = _percentile_ranks([float(v) for v in raw_relevance])
    pct_recency = _percentile_ranks([float(v) for v in raw_recency])
    pct_engagement = _percentile_ranks(raw_engagement, fallback=BASELINE_ENGAGEMENT)

    weights = [
        DIMENSION_WEIGHTS["relevance"],
        DIMENSION_WEIGHTS["recency"],
        DIMENSION_WEIGHTS["engagement"],
    ]

    for i, item in enumerate(items):
        rel_pct = pct_relevance[i]
        rec_pct = pct_recency[i]
        eng_pct = pct_engagement[i] if pct_engagement[i] is not None else BASELINE_ENGAGEMENT

        # Store breakdown for debugging / display
        item.breakdown = ScoreBreakdown(
            relevance=int(rel_pct),
            recency=int(rec_pct),
            engagement=int(eng_pct),
        )

        # Weighted harmonic mean
        total = _weighted_harmonic_mean(
            [rel_pct, rec_pct, eng_pct],
            weights,
        )

        # Post-harmonic confidence adjustments (additive)
        if raw_engagement[i] is None:
            total -= MISSING_ENGAGEMENT_PENALTY
        if item.date_trust == "low":
            total -= 7
        elif item.date_trust == "med":
            total -= 3

        item.score = max(0, min(100, round(total)))


def _score_web_items(items: List[ContentItem]) -> None:
    """Score web items using the engagement-free formula."""
    if not items:
        return

    for item in items:
        rel = int(item.relevance * 100)
        rec = temporal.freshness_score(item.published)

        item.breakdown = ScoreBreakdown(relevance=rel, recency=rec, engagement=0)

        total = (
            WEB_DIMENSION_WEIGHTS["relevance"] * rel
            + WEB_DIMENSION_WEIGHTS["recency"] * rec
        )
        total -= WEB_SOURCE_PENALTY

        if item.date_trust == "high":
            total += WEB_DATE_BONUS
        elif item.date_trust == "low":
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
        src = source_order.get(item.source, 4)
        return (-item.score, -_date_ordinal(item.published), src, item.headline.lower())

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
    # Tokenize: lowercase, split on non-alphanumeric
    import re
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    if not tokens:
        return 0

    # Build 3-gram shingles
    shingles = []
    for i in range(max(1, len(tokens) - 2)):
        shingle = " ".join(tokens[i:i + 3])
        shingles.append(shingle)

    # Accumulate bit weights
    bit_counts = [0] * 64
    for shingle in shingles:
        h = _fnv1a_64(shingle)
        for bit in range(64):
            if h & (1 << bit):
                bit_counts[bit] += 1
            else:
                bit_counts[bit] -= 1

    # Build fingerprint
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
    return item.headline


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

    discard = set()
    for i in range(len(items)):
        if i in discard:
            continue
        for j in range(i + 1, len(items)):
            if j in discard:
                continue
            if _hamming_distance(fingerprints[i], fingerprints[j]) <= max_hamming:
                if items[i].score >= items[j].score:
                    discard.add(j)
                else:
                    discard.add(i)
                    break  # i is discarded, no need to check more pairs

    return [item for idx, item in enumerate(items) if idx not in discard]
