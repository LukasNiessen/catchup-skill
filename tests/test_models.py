import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import models


class TestVersion(unittest.TestCase):
    def test_extracts_major_version(self):
        got = models.extract_version_tuple("gpt-5")
        self.assertEqual(got, (5,))

    def test_extracts_minor_version(self):
        got = models.extract_version_tuple("gpt-5.2")
        self.assertEqual(got, (5, 2))

    def test_extracts_patch_version(self):
        got = models.extract_version_tuple("gpt-5.2.1")
        self.assertEqual(got, (5, 2, 1))

    def test_handles_unversioned_model(self):
        got = models.extract_version_tuple("custom-model")
        self.assertIsNone(got)


class TestMainline(unittest.TestCase):
    def test_gpt5_is_mainline(self):
        self.assertTrue(models.is_standard_gpt_model("gpt-5"))

    def test_gpt52_is_mainline(self):
        self.assertTrue(models.is_standard_gpt_model("gpt-5.2"))

    def test_gpt5_mini_is_not_mainline(self):
        self.assertFalse(models.is_standard_gpt_model("gpt-5-mini"))

    def test_gpt4_is_not_mainline(self):
        self.assertFalse(models.is_standard_gpt_model("gpt-4"))


class TestOpenAI(unittest.TestCase):
    def test_pinned_policy_returns_pin(self):
        got = models.choose_openai_model(
            "fake-key",
            selection_policy="pinned",
            pinned_model="gpt-5.1"
        )
        self.assertEqual(got, "gpt-5.1")

    def test_auto_selects_latest(self):
        mock_model_list = [
            {"id": "gpt-5.2", "created": 1704067200},
            {"id": "gpt-5.1", "created": 1701388800},
            {"id": "gpt-5", "created": 1698710400},
        ]
        got = models.choose_openai_model(
            "fake-key",
            selection_policy="auto",
            mock_model_list=mock_model_list
        )
        self.assertEqual(got, "gpt-5.2")

    def test_auto_excludes_variants(self):
        mock_model_list = [
            {"id": "gpt-5.2", "created": 1704067200},
            {"id": "gpt-5-mini", "created": 1704067200},
            {"id": "gpt-5.1", "created": 1701388800},
        ]
        got = models.choose_openai_model(
            "fake-key",
            selection_policy="auto",
            mock_model_list=mock_model_list
        )
        self.assertEqual(got, "gpt-5.2")


class TestXAI(unittest.TestCase):
    def test_latest_policy_returns_latest(self):
        got = models.choose_xai_model(
            "fake-key",
            selection_policy="latest"
        )
        self.assertEqual(got, "grok-4-1-fast")

    def test_stable_policy_returns_stable(self):
        # Clear cache to avoid interference
        from lib import cache
        cache._MODEL_FILE.unlink(missing_ok=True)
        got = models.choose_xai_model(
            "fake-key",
            selection_policy="stable"
        )
        self.assertEqual(got, "grok-4-1-fast")

    def test_pinned_policy_returns_pin(self):
        got = models.choose_xai_model(
            "fake-key",
            selection_policy="pinned",
            pinned_model="grok-3"
        )
        self.assertEqual(got, "grok-3")


class TestLookup(unittest.TestCase):
    def test_absent_keys_returns_none(self):
        configuration = {}
        got = models.get_models(configuration)
        self.assertIsNone(got["openai"])
        self.assertIsNone(got["xai"])

    def test_openai_key_only(self):
        configuration = {"OPENAI_API_KEY": "sk-test"}
        mock_model_list = [{"id": "gpt-5.2", "created": 1704067200}]
        got = models.get_models(configuration, mock_openai_listing=mock_model_list)
        self.assertEqual(got["openai"], "gpt-5.2")
        self.assertIsNone(got["xai"])

    def test_both_keys_present(self):
        configuration = {
            "OPENAI_API_KEY": "sk-test",
            "XAI_API_KEY": "xai-test",
        }
        mock_openai_list = [{"id": "gpt-5.2", "created": 1704067200}]
        mock_xai_list = [{"id": "grok-4-1-fast", "created": 1704067200}]
        got = models.get_models(configuration, mock_openai_list, mock_xai_list)
        self.assertEqual(got["openai"], "gpt-5.2")
        self.assertEqual(got["xai"], "grok-4-1-fast")


if __name__ == "__main__":
    unittest.main()
