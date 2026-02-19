import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import dedupe, schema


class NormalizeTests(unittest.TestCase):
    def test_converts_to_lowercase(self):
        out = dedupe.normalize("HELLO World")
        self.assertEqual(out, "hello world")

    def test_strips_punctuation(self):
        out = dedupe.normalize("Hello, World!")
        # Punctuation replaced with space, then whitespace collapsed
        self.assertEqual(out, "hello world")

    def test_consolidates_whitespace(self):
        out = dedupe.normalize("hello    world")
        self.assertEqual(out, "hello world")


class NgramTests(unittest.TestCase):
    def test_handles_short_text(self):
        out = dedupe.ngrams("ab", n=3)
        self.assertEqual(out, {"ab"})

    def test_extracts_overlapping_segments(self):
        out = dedupe.ngrams("hello", n=3)
        self.assertIn("hel", out)
        self.assertIn("ell", out)
        self.assertIn("llo", out)


class JaccardTests(unittest.TestCase):
    def test_identical_sets_equal_one(self):
        test_set = {"a", "b", "c"}
        out = dedupe.jaccard(test_set, test_set)
        self.assertEqual(out, 1.0)

    def test_disjoint_sets_equal_zero(self):
        first_set = {"a", "b", "c"}
        second_set = {"d", "e", "f"}
        out = dedupe.jaccard(first_set, second_set)
        self.assertEqual(out, 0.0)

    def test_partial_overlap_computes_correctly(self):
        first_set = {"a", "b", "c"}
        second_set = {"b", "c", "d"}
        out = dedupe.jaccard(first_set, second_set)
        self.assertEqual(out, 0.5)  # 2 overlap / 4 union

    def test_empty_sets_equal_zero(self):
        out = dedupe.jaccard(set(), set())
        self.assertEqual(out, 0.0)


class DupePairTests(unittest.TestCase):
    def test_no_duplicates_returns_empty(self):
        test_items = [
            schema.RedditItem(id="R1", title="Completely different topic A", url="", subreddit=""),
            schema.RedditItem(id="R2", title="Another unrelated subject B", url="", subreddit=""),
        ]
        out = dedupe.find_dupes(test_items)
        self.assertEqual(out, [])

    def test_identifies_similar_pairs(self):
        test_items = [
            schema.RedditItem(id="R1", title="Best practices for Claude Code skills", url="", subreddit=""),
            schema.RedditItem(id="R2", title="Best practices for Claude Code skills guide", url="", subreddit=""),
        ]
        out = dedupe.find_dupes(test_items, threshold=0.7)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0], (0, 1))


class DeduplicateTests(unittest.TestCase):
    def test_retains_higher_scored_item(self):
        test_items = [
            schema.RedditItem(id="R1", title="Best practices for skills", url="", subreddit="", score=90),
            schema.RedditItem(id="R2", title="Best practices for skills guide", url="", subreddit="", score=50),
        ]
        out = dedupe.deduplicate(test_items, threshold=0.6)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, "R1")

    def test_preserves_distinct_items(self):
        test_items = [
            schema.RedditItem(id="R1", title="Topic about apples", url="", subreddit="", score=90),
            schema.RedditItem(id="R2", title="Discussion of oranges", url="", subreddit="", score=50),
        ]
        out = dedupe.deduplicate(test_items)
        self.assertEqual(len(out), 2)

    def test_handles_empty_list(self):
        out = dedupe.deduplicate([])
        self.assertEqual(out, [])

    def test_handles_single_item(self):
        test_items = [schema.RedditItem(id="R1", title="Test", url="", subreddit="")]
        out = dedupe.deduplicate(test_items)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
