#
# Verification Suite: Deduplication Module Functionality
#

import sys
import unittest
from pathlib import Path

# Configure module search path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import dedupe, schema


class TextStandardizationVerification(unittest.TestCase):
    def test_converts_to_lowercase(self):
        computed_result = dedupe.normalize_text("HELLO World")
        self.assertEqual(computed_result, "hello world")

    def test_strips_punctuation(self):
        computed_result = dedupe.normalize_text("Hello, World!")
        # Punctuation replaced with space, then whitespace collapsed
        self.assertEqual(computed_result, "hello world")

    def test_consolidates_whitespace(self):
        computed_result = dedupe.normalize_text("hello    world")
        self.assertEqual(computed_result, "hello world")


class NgramExtractionVerification(unittest.TestCase):
    def test_handles_short_text(self):
        computed_result = dedupe.get_ngrams("ab", gram_size=3)
        self.assertEqual(computed_result, {"ab"})

    def test_extracts_overlapping_segments(self):
        computed_result = dedupe.get_ngrams("hello", gram_size=3)
        self.assertIn("hel", computed_result)
        self.assertIn("ell", computed_result)
        self.assertIn("llo", computed_result)


class JaccardCoefficientVerification(unittest.TestCase):
    def test_identical_sets_equal_one(self):
        test_set = {"a", "b", "c"}
        computed_result = dedupe.jaccard_similarity(test_set, test_set)
        self.assertEqual(computed_result, 1.0)

    def test_disjoint_sets_equal_zero(self):
        first_set = {"a", "b", "c"}
        second_set = {"d", "e", "f"}
        computed_result = dedupe.jaccard_similarity(first_set, second_set)
        self.assertEqual(computed_result, 0.0)

    def test_partial_overlap_computes_correctly(self):
        first_set = {"a", "b", "c"}
        second_set = {"b", "c", "d"}
        computed_result = dedupe.jaccard_similarity(first_set, second_set)
        self.assertEqual(computed_result, 0.5)  # 2 overlap / 4 union

    def test_empty_sets_equal_zero(self):
        computed_result = dedupe.jaccard_similarity(set(), set())
        self.assertEqual(computed_result, 0.0)


class DuplicatePairDetectionVerification(unittest.TestCase):
    def test_no_duplicates_returns_empty(self):
        test_items = [
            schema.RedditItem(id="R1", title="Completely different topic A", url="", subreddit=""),
            schema.RedditItem(id="R2", title="Another unrelated subject B", url="", subreddit=""),
        ]
        computed_result = dedupe.find_duplicates(test_items)
        self.assertEqual(computed_result, [])

    def test_identifies_similar_pairs(self):
        test_items = [
            schema.RedditItem(id="R1", title="Best practices for Claude Code skills", url="", subreddit=""),
            schema.RedditItem(id="R2", title="Best practices for Claude Code skills guide", url="", subreddit=""),
        ]
        computed_result = dedupe.find_duplicates(test_items, similarity_threshold=0.7)
        self.assertEqual(len(computed_result), 1)
        self.assertEqual(computed_result[0], (0, 1))


class DeduplicationVerification(unittest.TestCase):
    def test_retains_higher_scored_item(self):
        test_items = [
            schema.RedditItem(id="R1", title="Best practices for skills", url="", subreddit="", score=90),
            schema.RedditItem(id="R2", title="Best practices for skills guide", url="", subreddit="", score=50),
        ]
        computed_result = dedupe.dedupe_items(test_items, similarity_threshold=0.6)
        self.assertEqual(len(computed_result), 1)
        self.assertEqual(computed_result[0].id, "R1")

    def test_preserves_distinct_items(self):
        test_items = [
            schema.RedditItem(id="R1", title="Topic about apples", url="", subreddit="", score=90),
            schema.RedditItem(id="R2", title="Discussion of oranges", url="", subreddit="", score=50),
        ]
        computed_result = dedupe.dedupe_items(test_items)
        self.assertEqual(len(computed_result), 2)

    def test_handles_empty_list(self):
        computed_result = dedupe.dedupe_items([])
        self.assertEqual(computed_result, [])

    def test_handles_single_item(self):
        test_items = [schema.RedditItem(id="R1", title="Test", url="", subreddit="")]
        computed_result = dedupe.dedupe_items(test_items)
        self.assertEqual(len(computed_result), 1)


if __name__ == "__main__":
    unittest.main()
