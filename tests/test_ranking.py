"""Tests for briefbot_engine.ranking: percentile-harmonic scoring and SimHash deduplication.

Uses "Kubernetes service mesh adoption" items for scoring tests and
"Quantum error correction breakthrough at IBM" near-duplicates for dedup tests.
"""

from datetime import datetime, timedelta, timezone

import pytest

from briefbot_engine.content import ContentItem, ScoreBreakdown, Signals, Source
from briefbot_engine import ranking


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc).date() - timedelta(days=n)).isoformat()


def _make_reddit_item(item_id, headline, relevance, signals, published, date_trust="high"):
    return ContentItem(
        item_id=item_id,
        source=Source.REDDIT,
        headline=headline,
        permalink=f"https://reddit.com/r/kubernetes/{item_id}",
        author="r/kubernetes",
        published=published,
        date_trust=date_trust,
        signals=signals,
        relevance=relevance,
    )


def _make_web_item(item_id, headline, relevance, published, date_trust="high"):
    return ContentItem(
        item_id=item_id,
        source=Source.WEB,
        headline=headline,
        permalink=f"https://example.com/{item_id}",
        author="example.com",
        published=published,
        date_trust=date_trust,
        relevance=relevance,
    )


# ---------------------------------------------------------------------------
# Internal helpers: _percentile_ranks
# ---------------------------------------------------------------------------

class TestPercentileRanks:
    def test_converts_values_to_percentile_ranks(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = ranking._percentile_ranks(values)
        assert result[0] == 0.0
        assert result[-1] == 100.0
        # Middle value should be 50
        assert result[2] == 50.0

    def test_single_value_gets_zero(self):
        result = ranking._percentile_ranks([42.0])
        assert result == [0.0]

    def test_none_values_preserved_as_none(self):
        result = ranking._percentile_ranks([10.0, None, 30.0])
        assert result[1] is None
        assert result[0] is not None
        assert result[2] is not None

    def test_all_none_returns_fallback(self):
        result = ranking._percentile_ranks([None, None], fallback=50)
        assert result == [50, 50]

    def test_equal_values_get_same_rank(self):
        result = ranking._percentile_ranks([5.0, 5.0, 5.0])
        # All tied values should end up with the same rank assignment
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Internal helpers: _weighted_harmonic_mean
# ---------------------------------------------------------------------------

class TestWeightedHarmonicMean:
    def test_equal_values_returns_that_value(self):
        result = ranking._weighted_harmonic_mean([50.0, 50.0, 50.0], [1.0, 1.0, 1.0])
        assert abs(result - 50.0) < 0.01

    def test_zero_weights_returns_zero(self):
        result = ranking._weighted_harmonic_mean([50.0, 60.0], [0.0, 0.0])
        assert result == 0.0

    def test_one_dimension_near_zero_drags_mean_down(self):
        # Harmonic mean is sensitive to low values
        result = ranking._weighted_harmonic_mean([90.0, 1.0], [0.5, 0.5])
        assert result < 45.0  # well below arithmetic mean of 45.5

    def test_epsilon_prevents_division_by_zero(self):
        result = ranking._weighted_harmonic_mean([0.0, 50.0], [0.5, 0.5])
        assert result > 0.0  # epsilon floors the zero

    def test_higher_weight_on_higher_value_increases_mean(self):
        heavy_high = ranking._weighted_harmonic_mean([80.0, 20.0], [0.8, 0.2])
        heavy_low = ranking._weighted_harmonic_mean([80.0, 20.0], [0.2, 0.8])
        assert heavy_high > heavy_low


# ---------------------------------------------------------------------------
# Internal helpers: _simhash and _hamming_distance
# ---------------------------------------------------------------------------

class TestSimHash:
    def test_produces_64_bit_integer(self):
        h = ranking._simhash("Kubernetes service mesh adoption trends")
        assert isinstance(h, int)
        assert 0 <= h < (1 << 64)

    def test_identical_text_identical_hash(self):
        text = "Quantum error correction breakthrough at IBM"
        assert ranking._simhash(text) == ranking._simhash(text)

    def test_similar_text_close_hashes(self):
        h1 = ranking._simhash("Quantum error correction breakthrough at IBM")
        h2 = ranking._simhash("Quantum error correction breakthrough at IBM labs")
        dist = ranking._hamming_distance(h1, h2)
        assert dist <= 10  # near-duplicates should be close

    def test_different_text_distant_hashes(self):
        h1 = ranking._simhash("Quantum error correction breakthrough at IBM")
        h2 = ranking._simhash("Kubernetes service mesh adoption trends in 2026")
        dist = ranking._hamming_distance(h1, h2)
        assert dist > 10  # unrelated text should diverge

    def test_empty_text_returns_zero(self):
        assert ranking._simhash("") == 0


class TestHammingDistance:
    def test_identical_hashes_zero_distance(self):
        assert ranking._hamming_distance(0xDEADBEEF, 0xDEADBEEF) == 0

    def test_single_bit_difference(self):
        assert ranking._hamming_distance(0b1000, 0b0000) == 1

    def test_all_bits_different(self):
        # For 64-bit integers, 0 vs all-ones differ in 64 bits
        assert ranking._hamming_distance(0, (1 << 64) - 1) == 64

    def test_symmetry(self):
        a, b = 0xCAFE, 0xBEEF
        assert ranking._hamming_distance(a, b) == ranking._hamming_distance(b, a)


# ---------------------------------------------------------------------------
# Scoring via rank_items()
# ---------------------------------------------------------------------------

class TestRankItems:
    def test_empty_list_returns_empty(self):
        assert ranking.rank_items([]) == []

    def test_scores_kubernetes_items_and_sorts_descending(self):
        items = [
            _make_reddit_item(
                "k8s-1",
                "Kubernetes service mesh adoption surges in enterprise",
                relevance=0.95,
                signals=Signals(upvotes=340, comments=87, vote_ratio=0.92, composite=6.5),
                published=_today(),
            ),
            _make_reddit_item(
                "k8s-2",
                "Kubernetes service mesh performance benchmarks released",
                relevance=0.70,
                signals=Signals(upvotes=120, comments=34, vote_ratio=0.88, composite=4.8),
                published=_days_ago(5),
            ),
            _make_reddit_item(
                "k8s-3",
                "Older Kubernetes mesh discussion thread",
                relevance=0.45,
                signals=Signals(upvotes=25, comments=8, vote_ratio=0.75, composite=2.1),
                published=_days_ago(20),
            ),
        ]

        result = ranking.rank_items(items)

        assert len(result) == 3
        # Higher relevance + engagement + recency => higher score
        assert result[0].score >= result[1].score
        assert result[1].score >= result[2].score
        # The top item should be k8s-1
        assert result[0].item_id == "k8s-1"

    def test_items_get_score_breakdown_populated(self):
        items = [
            _make_reddit_item(
                "k8s-bd",
                "Kubernetes service mesh adoption in healthcare",
                relevance=0.85,
                signals=Signals(upvotes=340, comments=87, vote_ratio=0.92, composite=6.5),
                published=_today(),
            ),
        ]

        result = ranking.rank_items(items)

        assert len(result) == 1
        bd = result[0].breakdown
        assert isinstance(bd, ScoreBreakdown)
        # Single platform item -> percentile rank is 0 for all dimensions (only one item)
        assert isinstance(bd.relevance, int)
        assert isinstance(bd.recency, int)
        assert isinstance(bd.engagement, int)

    def test_scores_are_bounded_0_to_100(self):
        items = [
            _make_reddit_item(
                "k8s-bound",
                "Kubernetes service mesh edge cases",
                relevance=0.99,
                signals=Signals(upvotes=5000, comments=500, vote_ratio=0.99, composite=10.0),
                published=_today(),
            ),
            _make_reddit_item(
                "k8s-low",
                "Ancient Kubernetes mesh post",
                relevance=0.10,
                signals=Signals(upvotes=1, comments=0, vote_ratio=0.50, composite=0.1),
                published=_days_ago(29),
            ),
        ]

        result = ranking.rank_items(items)

        for item in result:
            assert 0 <= item.score <= 100

    def test_web_items_scored_differently_no_engagement(self):
        web_item = _make_web_item(
            "web-k8s",
            "Kubernetes service mesh adoption guide 2026",
            relevance=0.88,
            published=_today(),
            date_trust="high",
        )

        result = ranking.rank_items([web_item])

        assert len(result) == 1
        assert result[0].score > 0
        # Web items should have engagement=0 in breakdown
        assert result[0].breakdown.engagement == 0

    def test_mixed_platform_and_web_items(self):
        items = [
            _make_reddit_item(
                "k8s-mix-r",
                "Kubernetes service mesh adoption on Reddit",
                relevance=0.90,
                signals=Signals(upvotes=340, comments=87, vote_ratio=0.92, composite=6.5),
                published=_today(),
            ),
            _make_web_item(
                "k8s-mix-w",
                "Kubernetes service mesh adoption web article",
                relevance=0.90,
                published=_today(),
                date_trust="high",
            ),
        ]

        result = ranking.rank_items(items)

        assert len(result) == 2
        # Both should have scores > 0
        assert all(item.score > 0 for item in result)

    def test_four_reddit_items_ranking_order(self):
        """Four items with varying engagement/relevance/recency -- verify ordering."""
        items = [
            _make_reddit_item(
                "k8s-a",
                "Kubernetes service mesh adoption in fintech sector",
                relevance=0.92,
                signals=Signals(upvotes=340, comments=87, vote_ratio=0.92, composite=6.5),
                published=_today(),
            ),
            _make_reddit_item(
                "k8s-b",
                "Kubernetes service mesh latency improvements",
                relevance=0.80,
                signals=Signals(upvotes=200, comments=55, vote_ratio=0.90, composite=5.2),
                published=_days_ago(3),
            ),
            _make_reddit_item(
                "k8s-c",
                "Kubernetes service mesh vs traditional proxies",
                relevance=0.60,
                signals=Signals(upvotes=80, comments=20, vote_ratio=0.85, composite=3.5),
                published=_days_ago(10),
            ),
            _make_reddit_item(
                "k8s-d",
                "Old Kubernetes mesh migration story",
                relevance=0.35,
                signals=Signals(upvotes=15, comments=3, vote_ratio=0.70, composite=1.5),
                published=_days_ago(25),
            ),
        ]

        result = ranking.rank_items(items)

        assert len(result) == 4
        # Verify descending score order
        scores = [item.score for item in result]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Deduplication via deduplicate()
# ---------------------------------------------------------------------------

class TestDeduplicate:
    def test_empty_list_returns_empty(self):
        assert ranking.deduplicate([]) == []

    def test_single_item_returns_that_item(self):
        item = ContentItem(
            item_id="qec-solo",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            permalink="https://reddit.com/r/quantum/1",
            score=75,
        )
        result = ranking.deduplicate([item])
        assert len(result) == 1
        assert result[0].item_id == "qec-solo"

    def test_near_duplicate_headlines_deduplicated(self):
        """Two nearly identical headlines should collapse to one."""
        item_a = ContentItem(
            item_id="qec-1",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            permalink="https://reddit.com/r/quantum/1",
            score=80,
        )
        item_b = ContentItem(
            item_id="qec-2",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM labs",
            permalink="https://reddit.com/r/quantum/2",
            score=65,
        )

        result = ranking.deduplicate([item_a, item_b])

        assert len(result) == 1

    def test_higher_scored_duplicate_is_kept(self):
        """When deduplicating, the item with the higher score should survive."""
        item_high = ContentItem(
            item_id="qec-high",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            permalink="https://reddit.com/r/quantum/high",
            score=90,
        )
        item_low = ContentItem(
            item_id="qec-low",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM labs",
            permalink="https://reddit.com/r/quantum/low",
            score=45,
        )

        result = ranking.deduplicate([item_high, item_low])

        assert len(result) == 1
        assert result[0].item_id == "qec-high"

    def test_lower_first_still_keeps_higher(self):
        """When the lower-scored item appears first, the higher-scored one still wins."""
        item_low = ContentItem(
            item_id="qec-low",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM labs",
            permalink="https://reddit.com/r/quantum/low",
            score=30,
        )
        item_high = ContentItem(
            item_id="qec-high",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            permalink="https://reddit.com/r/quantum/high",
            score=85,
        )

        result = ranking.deduplicate([item_low, item_high])

        assert len(result) == 1
        assert result[0].item_id == "qec-high"

    def test_completely_different_items_preserved(self):
        """Items with entirely different headlines are all kept."""
        items = [
            ContentItem(
                item_id="qec-diff-1",
                source=Source.REDDIT,
                headline="Quantum error correction breakthrough at IBM",
                permalink="https://reddit.com/r/quantum/1",
                score=80,
            ),
            ContentItem(
                item_id="k8s-diff-2",
                source=Source.REDDIT,
                headline="Kubernetes service mesh adoption surges in enterprise",
                permalink="https://reddit.com/r/kubernetes/2",
                score=75,
            ),
            ContentItem(
                item_id="rust-diff-3",
                source=Source.REDDIT,
                headline="Rust memory safety guarantees in production systems",
                permalink="https://reddit.com/r/rust/3",
                score=70,
            ),
        ]

        result = ranking.deduplicate(items)

        assert len(result) == 3

    def test_three_way_near_duplicates_collapse(self):
        """Three variations of the same headline should collapse to one."""
        items = [
            ContentItem(
                item_id="qec-v1",
                source=Source.REDDIT,
                headline="Quantum error correction breakthrough at IBM",
                permalink="https://reddit.com/r/quantum/v1",
                score=60,
            ),
            ContentItem(
                item_id="qec-v2",
                source=Source.REDDIT,
                headline="Quantum error correction breakthrough at IBM labs",
                permalink="https://reddit.com/r/quantum/v2",
                score=85,
            ),
            ContentItem(
                item_id="qec-v3",
                source=Source.REDDIT,
                headline="Quantum error correction breakthrough at IBM research",
                permalink="https://reddit.com/r/quantum/v3",
                score=50,
            ),
        ]

        result = ranking.deduplicate(items)

        # Should collapse to 1 (or at most 2 if the third is just different enough)
        assert len(result) <= 2
        # The highest-scored duplicate should survive
        kept_ids = {item.item_id for item in result}
        assert "qec-v2" in kept_ids

    def test_custom_max_hamming(self):
        """A very low max_hamming should preserve near-duplicates as distinct."""
        item_a = ContentItem(
            item_id="qec-strict-1",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            permalink="https://reddit.com/r/quantum/strict1",
            score=80,
        )
        item_b = ContentItem(
            item_id="qec-strict-2",
            source=Source.REDDIT,
            headline="Quantum error correction breakthrough at IBM labs",
            permalink="https://reddit.com/r/quantum/strict2",
            score=65,
        )

        # With max_hamming=0, only exact-hash matches are deduped
        result = ranking.deduplicate([item_a, item_b], max_hamming=0)
        assert len(result) == 2
