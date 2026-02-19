import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import cache


class TestCacheKey(unittest.TestCase):
    def test_produces_string_value(self):
        got = cache.cache_key("test topic", "2026-01-01", "2026-01-31", "both")
        self.assertIsInstance(got, str)

    def test_deterministic_for_identical_inputs(self):
        first_key = cache.cache_key("test topic", "2026-01-01", "2026-01-31", "both")
        second_key = cache.cache_key("test topic", "2026-01-01", "2026-01-31", "both")
        self.assertEqual(first_key, second_key)

    def test_varies_for_distinct_inputs(self):
        first_key = cache.cache_key("topic a", "2026-01-01", "2026-01-31", "both")
        second_key = cache.cache_key("topic b", "2026-01-01", "2026-01-31", "both")
        self.assertNotEqual(first_key, second_key)

    def test_identifier_length(self):
        got = cache.cache_key("test", "2026-01-01", "2026-01-31", "both")
        self.assertEqual(len(got), 20)


class TestCachePath(unittest.TestCase):
    def test_produces_path_object(self):
        got = cache.cache_path("abc123")
        self.assertIsInstance(got, Path)

    def test_includes_json_suffix(self):
        got = cache.cache_path("abc123")
        self.assertEqual(got.suffix, ".json")


class TestCacheValidity(unittest.TestCase):
    def test_absent_file_is_invalid(self):
        nonexistent_path = Path("/nonexistent/path/file.json")
        got = cache.is_valid(nonexistent_path)
        self.assertFalse(got)


class TestModelCache(unittest.TestCase):
    def test_absent_provider_returns_none(self):
        # Query a provider that should not exist
        got = cache.get_cached_model("nonexistent_provider")
        # May return None or cached value, but must not raise exception
        self.assertTrue(got is None or isinstance(got, str))


if __name__ == "__main__":
    unittest.main()
