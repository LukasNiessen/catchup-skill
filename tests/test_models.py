#
# Verification Suite: Model Selection Module Functionality
#

import sys
import unittest
from pathlib import Path

# Configure module search path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import models


class VersionExtractionVerification(unittest.TestCase):
    def test_extracts_major_version(self):
        computed_result = models.parse_version("gpt-5")
        self.assertEqual(computed_result, (5,))

    def test_extracts_minor_version(self):
        computed_result = models.parse_version("gpt-5.2")
        self.assertEqual(computed_result, (5, 2))

    def test_extracts_patch_version(self):
        computed_result = models.parse_version("gpt-5.2.1")
        self.assertEqual(computed_result, (5, 2, 1))

    def test_handles_unversioned_model(self):
        computed_result = models.parse_version("custom-model")
        self.assertIsNone(computed_result)


class MainlineModelDetectionVerification(unittest.TestCase):
    def test_gpt5_is_mainline(self):
        self.assertTrue(models.is_mainline_openai_model("gpt-5"))

    def test_gpt52_is_mainline(self):
        self.assertTrue(models.is_mainline_openai_model("gpt-5.2"))

    def test_gpt5_mini_is_not_mainline(self):
        self.assertFalse(models.is_mainline_openai_model("gpt-5-mini"))

    def test_gpt4_is_not_mainline(self):
        self.assertFalse(models.is_mainline_openai_model("gpt-4"))


class OpenAIModelSelectionVerification(unittest.TestCase):
    def test_pinned_policy_returns_pin(self):
        computed_result = models.select_openai_model(
            "fake-key",
            selection_policy="pinned",
            pinned_model="gpt-5.1"
        )
        self.assertEqual(computed_result, "gpt-5.1")

    def test_auto_selects_latest(self):
        mock_model_list = [
            {"id": "gpt-5.2", "created": 1704067200},
            {"id": "gpt-5.1", "created": 1701388800},
            {"id": "gpt-5", "created": 1698710400},
        ]
        computed_result = models.select_openai_model(
            "fake-key",
            selection_policy="auto",
            mock_model_list=mock_model_list
        )
        self.assertEqual(computed_result, "gpt-5.2")

    def test_auto_excludes_variants(self):
        mock_model_list = [
            {"id": "gpt-5.2", "created": 1704067200},
            {"id": "gpt-5-mini", "created": 1704067200},
            {"id": "gpt-5.1", "created": 1701388800},
        ]
        computed_result = models.select_openai_model(
            "fake-key",
            selection_policy="auto",
            mock_model_list=mock_model_list
        )
        self.assertEqual(computed_result, "gpt-5.2")


class XAIModelSelectionVerification(unittest.TestCase):
    def test_latest_policy_returns_latest(self):
        computed_result = models.select_xai_model(
            "fake-key",
            selection_policy="latest"
        )
        self.assertEqual(computed_result, "grok-4-1-fast")

    def test_stable_policy_returns_stable(self):
        # Clear cache to avoid interference
        from lib import cache
        cache.MODEL_CACHE_FILE.unlink(missing_ok=True)
        computed_result = models.select_xai_model(
            "fake-key",
            selection_policy="stable"
        )
        self.assertEqual(computed_result, "grok-4-1-fast")

    def test_pinned_policy_returns_pin(self):
        computed_result = models.select_xai_model(
            "fake-key",
            selection_policy="pinned",
            pinned_model="grok-3"
        )
        self.assertEqual(computed_result, "grok-3")


class ModelLookupVerification(unittest.TestCase):
    def test_absent_keys_returns_none(self):
        configuration = {}
        computed_result = models.get_models(configuration)
        self.assertIsNone(computed_result["openai"])
        self.assertIsNone(computed_result["xai"])

    def test_openai_key_only(self):
        configuration = {"OPENAI_API_KEY": "sk-test"}
        mock_model_list = [{"id": "gpt-5.2", "created": 1704067200}]
        computed_result = models.get_models(configuration, mock_openai_listing=mock_model_list)
        self.assertEqual(computed_result["openai"], "gpt-5.2")
        self.assertIsNone(computed_result["xai"])

    def test_both_keys_present(self):
        configuration = {
            "OPENAI_API_KEY": "sk-test",
            "XAI_API_KEY": "xai-test",
        }
        mock_openai_list = [{"id": "gpt-5.2", "created": 1704067200}]
        mock_xai_list = [{"id": "grok-4-1-fast", "created": 1704067200}]
        computed_result = models.get_models(configuration, mock_openai_list, mock_xai_list)
        self.assertEqual(computed_result["openai"], "gpt-5.2")
        self.assertEqual(computed_result["xai"], "grok-4-1-fast")


if __name__ == "__main__":
    unittest.main()
