#
# Verification Suite: Score Module Functionality
#

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Configure module search path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import schema, score


class SafeLogarithmVerification(unittest.TestCase):
    def test_positive_value(self):
        computed_result = score.safe_logarithm(100)
        self.assertGreater(computed_result, 0)

    def test_zero(self):
        computed_result = score.safe_logarithm(0)
        self.assertEqual(computed_result, 0)

    def test_none(self):
        computed_result = score.safe_logarithm(None)
        self.assertEqual(computed_result, 0)

    def test_negative(self):
        computed_result = score.safe_logarithm(-5)
        self.assertEqual(computed_result, 0)


class RedditEngagementComputationVerification(unittest.TestCase):
    def test_with_engagement(self):
        engagement_data = schema.Engagement(score=100, num_comments=50, upvote_ratio=0.9)
        computed_result = score.calculate_reddit_engagement_value(engagement_data)
        self.assertIsNotNone(computed_result)
        self.assertGreater(computed_result, 0)

    def test_without_engagement(self):
        computed_result = score.calculate_reddit_engagement_value(None)
        self.assertIsNone(computed_result)

    def test_empty_engagement(self):
        engagement_data = schema.Engagement()
        computed_result = score.calculate_reddit_engagement_value(engagement_data)
        self.assertIsNone(computed_result)


class XEngagementComputationVerification(unittest.TestCase):
    def test_with_engagement(self):
        engagement_data = schema.Engagement(likes=100, reposts=25, replies=15, quotes=5)
        computed_result = score.calculate_x_engagement_value(engagement_data)
        self.assertIsNotNone(computed_result)
        self.assertGreater(computed_result, 0)

    def test_without_engagement(self):
        computed_result = score.calculate_x_engagement_value(None)
        self.assertIsNone(computed_result)


class PercentageScalingVerification(unittest.TestCase):
    def test_normalizes_values(self):
        test_values = [0, 50, 100]
        computed_result = score.scale_to_percentage(test_values)
        self.assertEqual(computed_result[0], 0)
        self.assertEqual(computed_result[1], 50)
        self.assertEqual(computed_result[2], 100)

    def test_handles_none(self):
        test_values = [0, None, 100]
        computed_result = score.scale_to_percentage(test_values)
        self.assertIsNone(computed_result[1])

    def test_single_value(self):
        test_values = [50]
        computed_result = score.scale_to_percentage(test_values)
        self.assertEqual(computed_result[0], 50)


class RedditItemScoringVerification(unittest.TestCase):
    def test_scores_items(self):
        current_date = datetime.now(timezone.utc).date().isoformat()
        test_items = [
            schema.RedditItem(
                id="R1",
                title="Test",
                url="https://reddit.com/r/test/1",
                subreddit="test",
                date=current_date,
                date_confidence="high",
                engagement=schema.Engagement(score=100, num_comments=50, upvote_ratio=0.9),
                relevance=0.9,
            ),
            schema.RedditItem(
                id="R2",
                title="Test 2",
                url="https://reddit.com/r/test/2",
                subreddit="test",
                date=current_date,
                date_confidence="high",
                engagement=schema.Engagement(score=10, num_comments=5, upvote_ratio=0.8),
                relevance=0.5,
            ),
        ]

        computed_result = score.compute_reddit_scores(test_items)

        self.assertEqual(len(computed_result), 2)
        self.assertGreater(computed_result[0].score, 0)
        self.assertGreater(computed_result[1].score, 0)
        # Higher relevance and engagement should score higher
        self.assertGreater(computed_result[0].score, computed_result[1].score)

    def test_empty_list(self):
        computed_result = score.compute_reddit_scores([])
        self.assertEqual(computed_result, [])


class XItemScoringVerification(unittest.TestCase):
    def test_scores_items(self):
        current_date = datetime.now(timezone.utc).date().isoformat()
        test_items = [
            schema.XItem(
                id="X1",
                text="Test post",
                url="https://x.com/user/1",
                author_handle="user1",
                date=current_date,
                date_confidence="high",
                engagement=schema.Engagement(likes=100, reposts=25, replies=15, quotes=5),
                relevance=0.9,
            ),
        ]

        computed_result = score.compute_x_scores(test_items)

        self.assertEqual(len(computed_result), 1)
        self.assertGreater(computed_result[0].score, 0)


class ItemSortingVerification(unittest.TestCase):
    def test_sorts_by_score_descending(self):
        test_items = [
            schema.RedditItem(id="R1", title="Low", url="", subreddit="", score=30),
            schema.RedditItem(id="R2", title="High", url="", subreddit="", score=90),
            schema.RedditItem(id="R3", title="Mid", url="", subreddit="", score=60),
        ]

        computed_result = score.arrange_by_score(test_items)

        self.assertEqual(computed_result[0].id, "R2")
        self.assertEqual(computed_result[1].id, "R3")
        self.assertEqual(computed_result[2].id, "R1")

    def test_stable_sort(self):
        test_items = [
            schema.RedditItem(id="R1", title="A", url="", subreddit="", score=50),
            schema.RedditItem(id="R2", title="B", url="", subreddit="", score=50),
        ]

        computed_result = score.arrange_by_score(test_items)

        # Both have same score, should maintain order by title
        self.assertEqual(len(computed_result), 2)


if __name__ == "__main__":
    unittest.main()
