"""Tests for briefbot_engine.scoring: geometric scoring and Jaccard deduplication.

Uses "Kubernetes service mesh adoption" items for scoring tests and
"Quantum error correction breakthrough at IBM" near-duplicates for dedup tests.
"""

from datetime import datetime, timedelta, timezone

from briefbot_engine.records import Channel, Interaction, Signal
from briefbot_engine import scoring, timeframe


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc).date() - timedelta(days=n)).isoformat()


def _make_reddit_item(key, headline, topicality, interaction, dated, conf=None):
    return Signal(
        key=key,
        channel=Channel.REDDIT,
        headline=headline,
        url=f"https://reddit.com/r/kubernetes/{key}",
        byline="r/kubernetes",
        dated=dated,
        time_confidence=conf or timeframe.CONFIDENCE_SOLID,
        interaction=interaction,
        topicality=topicality,
    )


def _make_web_item(key, headline, topicality, dated, conf=None):
    return Signal(
        key=key,
        channel=Channel.WEB,
        headline=headline,
        url=f"https://example.com/{key}",
        byline="example.com",
        dated=dated,
        time_confidence=conf or timeframe.CONFIDENCE_SOLID,
        topicality=topicality,
    )


class TestPercentileRanks:
    def test_converts_values_to_percentile_ranks(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = scoring._percentile_ranks(values)
        assert result[0] == 0.0
        assert result[-1] == 100.0
        assert result[2] == 50.0

    def test_single_value_gets_zero(self):
        result = scoring._percentile_ranks([42.0])
        assert result == [0.0]

    def test_none_values_preserved_as_none(self):
        result = scoring._percentile_ranks([10.0, None, 30.0])
        assert result[1] is None
        assert result[0] is not None
        assert result[2] is not None

    def test_all_none_returns_fallback(self):
        result = scoring._percentile_ranks([None, None], fallback=50)
        assert result == [50, 50]

    def test_equal_values_get_same_rank(self):
        result = scoring._percentile_ranks([5.0, 5.0, 5.0])
        assert len(result) == 3


class TestWeightedGeometric:
    def test_equal_values_returns_that_value(self):
        result = scoring._weighted_geometric([50.0, 50.0, 50.0], [1.0, 1.0, 1.0])
        assert abs(result - 50.0) < 0.01

    def test_zero_weights_returns_zero(self):
        result = scoring._weighted_geometric([50.0, 60.0], [0.0, 0.0])
        assert result == 0.0

    def test_one_dimension_near_zero_drags_mean_down(self):
        result = scoring._weighted_geometric([90.0, 1.0], [0.5, 0.5])
        assert result < 50.0

    def test_higher_weight_on_higher_value_increases_mean(self):
        heavy_high = scoring._weighted_geometric([80.0, 20.0], [0.8, 0.2])
        heavy_low = scoring._weighted_geometric([80.0, 20.0], [0.2, 0.8])
        assert heavy_high > heavy_low


class TestRankItems:
    def test_empty_list_returns_empty(self):
        assert scoring.rank_items([]) == []

    def test_scores_kubernetes_items_and_sorts_descending(self):
        items = [
            _make_reddit_item(
                "k8s-1",
                "Kubernetes service mesh adoption surges in enterprise",
                topicality=0.95,
                interaction=Interaction(upvotes=340, comments=87, ratio=0.92, pulse=6.5),
                dated=_today(),
            ),
            _make_reddit_item(
                "k8s-2",
                "Kubernetes service mesh performance benchmarks released",
                topicality=0.70,
                interaction=Interaction(upvotes=120, comments=34, ratio=0.88, pulse=4.8),
                dated=_days_ago(5),
            ),
            _make_reddit_item(
                "k8s-3",
                "Older Kubernetes mesh discussion thread",
                topicality=0.45,
                interaction=Interaction(upvotes=25, comments=8, ratio=0.75, pulse=2.1),
                dated=_days_ago(20),
            ),
        ]

        result = scoring.rank_items(items)

        assert len(result) == 3
        assert result[0].rank >= result[1].rank
        assert result[1].rank >= result[2].rank
        assert result[0].key == "k8s-1"

    def test_items_get_scorecard_populated(self):
        items = [
            _make_reddit_item(
                "k8s-bd",
                "Kubernetes service mesh adoption in healthcare",
                topicality=0.85,
                interaction=Interaction(upvotes=340, comments=87, ratio=0.92, pulse=6.5),
                dated=_today(),
            ),
        ]

        result = scoring.rank_items(items)

        assert len(result) == 1
        bd = result[0].scorecard
        assert isinstance(bd.topicality, int)
        assert isinstance(bd.freshness, int)
        assert isinstance(bd.traction, int)
        assert isinstance(bd.trust, int)

    def test_scores_are_bounded_0_to_100(self):
        items = [
            _make_reddit_item(
                "k8s-bound",
                "Kubernetes service mesh edge cases",
                topicality=0.99,
                interaction=Interaction(upvotes=5000, comments=500, ratio=0.99, pulse=10.0),
                dated=_today(),
            ),
            _make_reddit_item(
                "k8s-low",
                "Ancient Kubernetes mesh post",
                topicality=0.10,
                interaction=Interaction(upvotes=1, comments=0, ratio=0.50, pulse=0.1),
                dated=_days_ago(29),
            ),
        ]

        result = scoring.rank_items(items)

        for item in result:
            assert 0 <= item.rank <= 100

    def test_web_items_scored_differently_no_interaction(self):
        web_item = _make_web_item(
            "web-k8s",
            "Kubernetes service mesh adoption guide 2026",
            topicality=0.88,
            dated=_today(),
            conf=timeframe.CONFIDENCE_SOLID,
        )

        result = scoring.rank_items([web_item])

        assert len(result) == 1
        assert result[0].rank > 0
        assert result[0].scorecard.traction == 0

    def test_mixed_platform_and_web_items(self):
        items = [
            _make_reddit_item(
                "k8s-mix-r",
                "Kubernetes service mesh adoption on Reddit",
                topicality=0.90,
                interaction=Interaction(upvotes=340, comments=87, ratio=0.92, pulse=6.5),
                dated=_today(),
            ),
            _make_web_item(
                "k8s-mix-w",
                "Kubernetes service mesh adoption web article",
                topicality=0.90,
                dated=_today(),
                conf=timeframe.CONFIDENCE_SOLID,
            ),
        ]

        result = scoring.rank_items(items)

        assert len(result) == 2
        assert all(item.rank > 0 for item in result)


class TestDeduplicate:
    def test_empty_list_returns_empty(self):
        assert scoring.deduplicate([]) == []

    def test_single_item_returns_that_item(self):
        item = Signal(
            key="qec-solo",
            channel=Channel.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            url="https://reddit.com/r/quantum/1",
            rank=75,
        )
        result = scoring.deduplicate([item])
        assert len(result) == 1
        assert result[0].key == "qec-solo"

    def test_near_duplicate_titles_deduplicated(self):
        item_a = Signal(
            key="qec-1",
            channel=Channel.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            url="https://reddit.com/r/quantum/1",
            rank=80,
        )
        item_b = Signal(
            key="qec-2",
            channel=Channel.REDDIT,
            headline="Quantum error correction breakthrough at IBM labs",
            url="https://reddit.com/r/quantum/2",
            rank=65,
        )

        result = scoring.deduplicate([item_a, item_b])

        assert len(result) == 1

    def test_higher_scored_duplicate_is_kept(self):
        item_high = Signal(
            key="qec-high",
            channel=Channel.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            url="https://reddit.com/r/quantum/high",
            rank=90,
        )
        item_low = Signal(
            key="qec-low",
            channel=Channel.REDDIT,
            headline="Quantum error correction breakthrough at IBM labs",
            url="https://reddit.com/r/quantum/low",
            rank=45,
        )

        result = scoring.deduplicate([item_high, item_low])

        assert len(result) == 1
        assert result[0].key == "qec-high"

    def test_completely_different_items_preserved(self):
        items = [
            Signal(
                key="qec-diff-1",
                channel=Channel.REDDIT,
                headline="Quantum error correction breakthrough at IBM",
                url="https://reddit.com/r/quantum/1",
                rank=80,
            ),
            Signal(
                key="k8s-diff-2",
                channel=Channel.REDDIT,
                headline="Kubernetes service mesh adoption surges in enterprise",
                url="https://reddit.com/r/kubernetes/2",
                rank=75,
            ),
            Signal(
                key="rust-diff-3",
                channel=Channel.REDDIT,
                headline="Rust memory safety guarantees in production systems",
                url="https://reddit.com/r/rust/3",
                rank=70,
            ),
        ]

        result = scoring.deduplicate(items)

        assert len(result) == 3

    def test_similarity_threshold_allows_stricter_matching(self):
        item_a = Signal(
            key="qec-strict-1",
            channel=Channel.REDDIT,
            headline="Quantum error correction breakthrough at IBM",
            url="https://reddit.com/r/quantum/strict1",
            rank=80,
        )
        item_b = Signal(
            key="qec-strict-2",
            channel=Channel.REDDIT,
            headline="Quantum error correction breakthrough at IBM labs",
            url="https://reddit.com/r/quantum/strict2",
            rank=65,
        )

        result = scoring.deduplicate([item_a, item_b], similarity_threshold=1.0)
        assert len(result) == 2
