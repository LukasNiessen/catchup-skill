"""Tests for briefbot_engine.ranking: percentile-power scoring and SimHash deduplication.

Uses "Kubernetes service mesh adoption" items for scoring tests and
"Quantum error correction breakthrough at IBM" near-duplicates for dedup tests.
"""

from datetime import datetime, timedelta, timezone

import pytest

from briefbot_engine.content import ContentItem, ScoreBreakdown, Engagement, Source
from briefbot_engine import ranking, temporal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc).date() - timedelta(days=n)).isoformat()


def _make_reddit_item(uid, title, signal, engagement, published, date_confidence=None):
    return ContentItem(
        uid=uid,
        source=Source.REDDIT,
        title=title,
        link=f"https://reddit.com/r/kubernetes/{uid}",
        author="r/kubernetes",
        published=published,
        date_confidence=date_confidence or temporal.CONFIDENCE_SOLID,
        engagement=engagement,
        relevance=signal,
    )


def _make_web_item(uid, title, signal, published, date_confidence=None):
    return ContentItem(
        uid=uid,
        source=Source.WEB,
        title=title,
        link=f"https://example.com/{uid}",
        author="example.com",
        published=published,
        date_confidence=date_confidence or temporal.CONFIDENCE_SOLID,
        relevance=signal,
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
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Internal helpers: _weighted_power_mean
# ---------------------------------------------------------------------------

class TestWeightedPowerMean:
    def test_equal_values_returns_that_value(self):
        result = ranking._weighted_power_mean([50.0, 50.0, 50.0], [1.0, 1.0, 1.0])
        assert abs(result - 50.0) < 0.01

    def test_zero_weights_returns_zero(self):
        result = ranking._weighted_power_mean([50.0, 60.0], [0.0, 0.0])
        assert result == 0.0

    def test_one_dimension_near_zero_drags_mean_down(self):
        result = ranking._weighted_power_mean([90.0, 1.0], [0.5, 0.5])
        assert result < 50.0

    def test_higher_weight_on_higher_value_increases_mean(self):
        heavy_high = ranking._weighted_power_mean([80.0, 20.0], [0.8, 0.2])
        heavy_low = ranking._weighted_power_mean([80.0, 20.0], [0.2, 0.8])
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
        assert dist <= 10

    def test_different_text_distant_hashes(self):
        h1 = ranking._simhash("Quantum error correction breakthrough at IBM")
        h2 = ranking._simhash("Kubernetes service mesh adoption trends in 2026")
        dist = ranking._hamming_distance(h1, h2)
        assert dist > 10

    def test_empty_text_returns_zero(self):
        assert ranking._simhash("") == 0


class TestHammingDistance:
    def test_identical_hashes_zero_distance(self):
        assert ranking._hamming_distance(0xDEADBEEF, 0xDEADBEEF) == 0

    def test_single_bit_difference(self):
        assert ranking._hamming_distance(0b1000, 0b0000) == 1

    def test_all_bits_different(self):
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
                signal=0.95,
                engagement=Engagement(upvotes=340, comments=87, vote_ratio=0.92, composite=6.5),
                published=_today(),
            ),
            _make_reddit_item(
                "k8s-2",
                "Kubernetes service mesh performance benchmarks released",
                signal=0.70,
                engagement=Engagement(upvotes=120, comments=34, vote_ratio=0.88, composite=4.8),
                published=_days_ago(5),
            ),
            _make_reddit_item(
                "k8s-3",
                "Older Kubernetes mesh discussion thread",
                signal=0.45,
                engagement=Engagement(upvotes=25, comments=8, vote_ratio=0.75, composite=2.1),
                published=_days_ago(20),
            ),
        ]

        result = ranking.rank_items(items)

        assert len(result) == 3
        assert result[0].score >= result[1].score
        assert result[1].score >= result[2].score
        assert result[0].uid == "k8s-1"

    def test_items_get_score_breakdown_populated(self):
        items = [
            _make_reddit_item(
                "k8s-bd",
                "Kubernetes service mesh adoption in healthcare",
                signal=0.85,
                engagement=Engagement(upvotes=340, comments=87, vote_ratio=0.92, composite=6.5),
                published=_today(),
            ),
        ]

        result = ranking.rank_items(items)

        assert len(result) == 1
        bd = result[0].breakdown
        assert isinstance(bd, ScoreBreakdown)
        assert isinstance(bd.relevance, int)
        assert isinstance(bd.timeliness, int)
        assert isinstance(bd.traction, int)
        assert isinstance(bd.credibility, int)

    def test_scores_are_bounded_0_to_100(self):
        items = [
            _make_reddit_item(
                "k8s-bound",
                "Kubernetes service mesh edge cases",
                signal=0.99,
                engagement=Engagement(upvotes=5000, comments=500, vote_ratio=0.99, composite=10.0),
                published=_today(),
            ),
            _make_reddit_item(
                "k8s-low",
                "Ancient Kubernetes mesh post",
                signal=0.10,
                engagement=Engagement(upvotes=1, comments=0, vote_ratio=0.50, composite=0.1),
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
            signal=0.88,
            published=_today(),
            date_confidence=temporal.CONFIDENCE_SOLID,
        )

        result = ranking.rank_items([web_item])

        assert len(result) == 1
        assert result[0].score > 0
        assert result[0].breakdown.traction == 0

    def test_mixed_platform_and_web_items(self):
        items = [
            _make_reddit_item(
                "k8s-mix-r",
                "Kubernetes service mesh adoption on Reddit",
                signal=0.90,
                engagement=Engagement(upvotes=340, comments=87, vote_ratio=0.92, composite=6.5),
                published=_today(),
            ),
            _make_web_item(
                "k8s-mix-w",
                "Kubernetes service mesh adoption web article",
                signal=0.90,
                published=_today(),
                date_confidence=temporal.CONFIDENCE_SOLID,
            ),
        ]

        result = ranking.rank_items(items)

        assert len(result) == 2
        assert all(item.score > 0 for item in result)

    def test_four_reddit_items_ranking_order(self):
        items = [
            _make_reddit_item(
                "k8s-a",
                "Kubernetes service mesh adoption in fintech sector",
                signal=0.92,
                engagement=Engagement(upvotes=340, comments=87, vote_ratio=0.92, composite=6.5),
                published=_today(),
            ),
            _make_reddit_item(
                "k8s-b",
                "Kubernetes service mesh latency improvements",
                signal=0.80,
                engagement=Engagement(upvotes=200, comments=55, vote_ratio=0.90, composite=5.2),
                published=_days_ago(3),
            ),
            _make_reddit_item(
                "k8s-c",
                "Kubernetes service mesh vs traditional proxies",
                signal=0.60,
                engagement=Engagement(upvotes=80, comments=20, vote_ratio=0.85, composite=3.5),
                published=_days_ago(10),
            ),
            _make_reddit_item(
                "k8s-d",
                "Old Kubernetes mesh migration story",
                signal=0.35,
                engagement=Engagement(upvotes=15, comments=3, vote_ratio=0.70, composite=1.5),
                published=_days_ago(25),
            ),
        ]

        result = ranking.rank_items(items)

        assert len(result) == 4
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
            uid="qec-solo",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM",
            link="https://reddit.com/r/quantum/1",
            score=75,
        )
        result = ranking.deduplicate([item])
        assert len(result) == 1
        assert result[0].uid == "qec-solo"

    def test_near_duplicate_titles_deduplicated(self):
        item_a = ContentItem(
            uid="qec-1",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM",
            link="https://reddit.com/r/quantum/1",
            score=80,
        )
        item_b = ContentItem(
            uid="qec-2",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM labs",
            link="https://reddit.com/r/quantum/2",
            score=65,
        )

        result = ranking.deduplicate([item_a, item_b])

        assert len(result) == 1

    def test_higher_scored_duplicate_is_kept(self):
        item_high = ContentItem(
            uid="qec-high",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM",
            link="https://reddit.com/r/quantum/high",
            score=90,
        )
        item_low = ContentItem(
            uid="qec-low",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM labs",
            link="https://reddit.com/r/quantum/low",
            score=45,
        )

        result = ranking.deduplicate([item_high, item_low])

        assert len(result) == 1
        assert result[0].uid == "qec-high"

    def test_lower_first_still_keeps_higher(self):
        item_low = ContentItem(
            uid="qec-low",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM labs",
            link="https://reddit.com/r/quantum/low",
            score=30,
        )
        item_high = ContentItem(
            uid="qec-high",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM",
            link="https://reddit.com/r/quantum/high",
            score=85,
        )

        result = ranking.deduplicate([item_low, item_high])

        assert len(result) == 1
        assert result[0].uid == "qec-high"

    def test_completely_different_items_preserved(self):
        items = [
            ContentItem(
                uid="qec-diff-1",
                source=Source.REDDIT,
                title="Quantum error correction breakthrough at IBM",
                link="https://reddit.com/r/quantum/1",
                score=80,
            ),
            ContentItem(
                uid="k8s-diff-2",
                source=Source.REDDIT,
                title="Kubernetes service mesh adoption surges in enterprise",
                link="https://reddit.com/r/kubernetes/2",
                score=75,
            ),
            ContentItem(
                uid="rust-diff-3",
                source=Source.REDDIT,
                title="Rust memory safety guarantees in production systems",
                link="https://reddit.com/r/rust/3",
                score=70,
            ),
        ]

        result = ranking.deduplicate(items)

        assert len(result) == 3

    def test_three_way_near_duplicates_collapse(self):
        items = [
            ContentItem(
                uid="qec-v1",
                source=Source.REDDIT,
                title="Quantum error correction breakthrough at IBM",
                link="https://reddit.com/r/quantum/v1",
                score=60,
            ),
            ContentItem(
                uid="qec-v2",
                source=Source.REDDIT,
                title="Quantum error correction breakthrough at IBM labs",
                link="https://reddit.com/r/quantum/v2",
                score=85,
            ),
            ContentItem(
                uid="qec-v3",
                source=Source.REDDIT,
                title="Quantum error correction breakthrough at IBM research",
                link="https://reddit.com/r/quantum/v3",
                score=50,
            ),
        ]

        result = ranking.deduplicate(items)

        assert len(result) <= 2
        kept_ids = {item.uid for item in result}
        assert "qec-v2" in kept_ids

    def test_custom_max_hamming(self):
        item_a = ContentItem(
            uid="qec-strict-1",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM",
            link="https://reddit.com/r/quantum/strict1",
            score=80,
        )
        item_b = ContentItem(
            uid="qec-strict-2",
            source=Source.REDDIT,
            title="Quantum error correction breakthrough at IBM labs",
            link="https://reddit.com/r/quantum/strict2",
            score=65,
        )

        result = ranking.deduplicate([item_a, item_b], max_hamming=0)
        assert len(result) == 2
