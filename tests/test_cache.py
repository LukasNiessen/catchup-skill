#
# Verification Suite: Cache Module Functionality
#

import sys
import unittest
from pathlib import Path

# Configure module search path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import cache


class CacheIdentifierVerification(unittest.TestCase):
    def test_produces_string_value(self):
        computed_result = cache.get_cache_key("test topic", "2026-01-01", "2026-01-31", "both")
        self.assertIsInstance(computed_result, str)

    def test_deterministic_for_identical_inputs(self):
        first_key = cache.get_cache_key("test topic", "2026-01-01", "2026-01-31", "both")
        second_key = cache.get_cache_key("test topic", "2026-01-01", "2026-01-31", "both")
        self.assertEqual(first_key, second_key)

    def test_varies_for_distinct_inputs(self):
        first_key = cache.get_cache_key("topic a", "2026-01-01", "2026-01-31", "both")
        second_key = cache.get_cache_key("topic b", "2026-01-01", "2026-01-31", "both")
        self.assertNotEqual(first_key, second_key)

    def test_identifier_length(self):
        computed_key = cache.get_cache_key("test", "2026-01-01", "2026-01-31", "both")
        self.assertEqual(len(computed_key), 16)


class CacheFilepathVerification(unittest.TestCase):
    def test_produces_path_object(self):
        computed_result = cache.get_cache_path("abc123")
        self.assertIsInstance(computed_result, Path)

    def test_includes_json_suffix(self):
        computed_result = cache.get_cache_path("abc123")
        self.assertEqual(computed_result.suffix, ".json")


class CacheValidityVerification(unittest.TestCase):
    def test_absent_file_is_invalid(self):
        nonexistent_path = Path("/nonexistent/path/file.json")
        computed_result = cache.is_cache_valid(nonexistent_path)
        self.assertFalse(computed_result)


class ModelCacheVerification(unittest.TestCase):
    def test_absent_provider_returns_none(self):
        # Query a provider that should not exist
        computed_result = cache.get_cached_model("nonexistent_provider")
        # May return None or cached value, but must not raise exception
        self.assertTrue(computed_result is None or isinstance(computed_result, str))


if __name__ == "__main__":
    unittest.main()
