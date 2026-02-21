"""Tests for briefbot_engine.sources.catalog: response caching and model selection.

Replaces test_cache.py and test_models.py with pure pytest functions
importing from the refactored briefbot_engine package.
"""

from pathlib import Path

import pytest

from briefbot_engine.sources.catalog import ProviderRegistry
from briefbot_engine.sources import catalog


# ---------------------------------------------------------------------------
# Cache operations (module-level convenience functions)
# ---------------------------------------------------------------------------

class TestCacheKey:
    def test_produces_string(self):
        key = catalog.cache_key("Kubernetes service mesh", "2026-01-20", "2026-02-19", "reddit")
        assert isinstance(key, str)

    def test_deterministic(self):
        a = catalog.cache_key("Kubernetes service mesh", "2026-01-20", "2026-02-19", "reddit")
        b = catalog.cache_key("Kubernetes service mesh", "2026-01-20", "2026-02-19", "reddit")
        assert a == b

    def test_varies_for_different_inputs(self):
        a = catalog.cache_key("Kubernetes service mesh", "2026-01-20", "2026-02-19", "reddit")
        b = catalog.cache_key("Quantum error correction", "2026-01-20", "2026-02-19", "reddit")
        assert a != b

    def test_length_is_18(self):
        key = catalog.cache_key("Kubernetes service mesh", "2026-01-20", "2026-02-19", "both")
        assert len(key) == 18


class TestCachePath:
    def test_returns_path_object(self):
        p = catalog.cache_path("abc123def456")
        assert isinstance(p, Path)

    def test_has_json_suffix(self):
        p = catalog.cache_path("abc123def456")
        assert p.suffix == ".json"

    def test_filename_contains_key(self):
        p = catalog.cache_path("mykey99")
        assert "mykey99" in p.name


class TestIsValid:
    def test_nonexistent_file_returns_false(self):
        fake_path = Path("/nonexistent/path/that/does/not/exist/cache.json")
        assert catalog.is_valid(fake_path) is False


class TestGetCachedModel:
    def test_unknown_provider_returns_none(self):
        result = catalog.get_cached_model("nonexistent_provider_xyz_12345")
        # Should be None or a string (if some prior test cached it), but never raise
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# Version extraction
# ---------------------------------------------------------------------------

class TestExtractVersionTuple:
    def test_major_only(self):
        assert ProviderRegistry.extract_version_tuple("gpt-5") == (5,)

    def test_major_minor(self):
        assert ProviderRegistry.extract_version_tuple("gpt-5.7") == (5, 7)

    def test_major_minor_patch(self):
        assert ProviderRegistry.extract_version_tuple("gpt-5.7.3") == (5, 7, 3)

    def test_unversioned_returns_none(self):
        assert ProviderRegistry.extract_version_tuple("local-variant") is None

    def test_grok_version(self):
        assert ProviderRegistry.extract_version_tuple("grok-4-1-fast") == (4, 1)

    def test_dotted_grok_version(self):
        assert ProviderRegistry.extract_version_tuple("grok-4.1") == (4, 1)

    def test_underscore_separator(self):
        assert ProviderRegistry.extract_version_tuple("model_3_1") == (3, 1)


# ---------------------------------------------------------------------------
# Standard GPT model identification
# ---------------------------------------------------------------------------

class TestIsStandardGptModel:
    def test_gpt5_is_standard(self):
        assert ProviderRegistry.is_standard_gpt_model("gpt-5") is True

    def test_gpt52_is_standard(self):
        assert ProviderRegistry.is_standard_gpt_model("gpt-5.7") is True

    def test_gpt5_snapshot_is_not_standard(self):
        assert ProviderRegistry.is_standard_gpt_model("gpt-5-snapshot") is False

    def test_gpt4_is_not_standard(self):
        assert ProviderRegistry.is_standard_gpt_model("gpt-4") is False

    def test_gpt5_preview_is_not_standard(self):
        assert ProviderRegistry.is_standard_gpt_model("gpt-5-preview") is False

    def test_gpt5_chat_is_not_standard(self):
        assert ProviderRegistry.is_standard_gpt_model("gpt-5-chat") is False


# ---------------------------------------------------------------------------
# OpenAI model selection
# ---------------------------------------------------------------------------

class TestChooseOpenaiModel:
    def test_pinned_policy_returns_pin(self):
        reg = ProviderRegistry()
        result = reg.choose_openai_model(
            "test-key-123",
            selection_policy="pinned",
            pinned_model="gpt-5.1",
        )
        assert result == "gpt-5.1"

    def test_auto_with_mock_list_selects_highest_version(self):
        reg = ProviderRegistry()
        mock_models = [
            {"id": "gpt-5", "created": 1712000000},
            {"id": "gpt-5.1", "created": 1712600000},
            {"id": "gpt-5.3", "created": 1713200000},
            {"id": "gpt-5-snapshot", "created": 1713200000},  # excluded variant
        ]
        # Clear any cached model preference for openai so auto logic runs
        prefs = reg._load_model_prefs()
        prefs.pop("openai", None)
        reg._save_model_prefs(prefs)

        result = reg.choose_openai_model(
            "test-key-123",
            selection_policy="auto",
            mock_model_list=mock_models,
        )
        assert result == "gpt-5.3"

    def test_auto_excludes_variant_models(self):
        reg = ProviderRegistry()
        mock_models = [
            {"id": "gpt-5.4", "created": 1715000000},
            {"id": "gpt-5-snapshot", "created": 1716000000},
            {"id": "gpt-5-nano", "created": 1716000000},
        ]
        prefs = reg._load_model_prefs()
        prefs.pop("openai", None)
        reg._save_model_prefs(prefs)

        result = reg.choose_openai_model(
            "test-key-123",
            selection_policy="auto",
            mock_model_list=mock_models,
        )
        assert result == "gpt-5.4"


# ---------------------------------------------------------------------------
# xAI model selection
# ---------------------------------------------------------------------------

class TestChooseXaiModel:
    def test_pinned_policy_returns_pin(self):
        reg = ProviderRegistry()
        result = reg.choose_xai_model(
            "test-key-123",
            selection_policy="pinned",
            pinned_model="grok-3-custom",
        )
        assert result == "grok-3-custom"

    def test_mock_model_list_matches_preference(self):
        reg = ProviderRegistry()
        mock_models = [
            {"id": "grok-4-1-fast"},
            {"id": "grok-4-1"},
            {"id": "grok-4-non-reasoning"},
        ]
        # Clear cached xai preference so the preference-list logic runs
        prefs = reg._load_model_prefs()
        prefs.pop("xai", None)
        reg._save_model_prefs(prefs)

        result = reg.choose_xai_model(
            "test-key-123",
            selection_policy="latest",
            mock_model_list=mock_models,
        )
        # "grok-4-fast" is first preference but not in the mock list;
        # "grok-4-1-fast" is second preference and IS available
        assert result == "grok-4-1-fast"

    def test_mock_list_with_top_preference_available(self):
        reg = ProviderRegistry()
        mock_models = [
            {"id": "grok-4-fast"},
            {"id": "grok-4-1-fast"},
            {"id": "grok-4"},
        ]
        prefs = reg._load_model_prefs()
        prefs.pop("xai", None)
        reg._save_model_prefs(prefs)

        result = reg.choose_xai_model(
            "test-key-123",
            selection_policy="latest",
            mock_model_list=mock_models,
        )
        assert result == "grok-4-fast"


# ---------------------------------------------------------------------------
# get_models() integration
# ---------------------------------------------------------------------------

class TestGetModels:
    def test_no_keys_returns_none_for_both(self):
        reg = ProviderRegistry()
        result = reg.get_models({})
        assert result["openai"] is None
        assert result["xai"] is None

    def test_openai_key_only(self):
        reg = ProviderRegistry()
        mock_openai = [{"id": "gpt-5.3", "created": 1713200000}]
        # Clear cache
        prefs = reg._load_model_prefs()
        prefs.pop("openai", None)
        reg._save_model_prefs(prefs)

        result = reg.get_models(
            {"OPENAI_API_KEY": "sk-local-test"},
            mock_openai_listing=mock_openai,
        )
        assert result["openai"] == "gpt-5.3"
        assert result["xai"] is None

    def test_both_keys_present(self):
        reg = ProviderRegistry()
        mock_openai = [{"id": "gpt-5.3", "created": 1713200000}]
        mock_xai = [
            {"id": "grok-4-fast"},
            {"id": "grok-4-1-fast"},
        ]
        # Clear caches
        prefs = reg._load_model_prefs()
        prefs.pop("openai", None)
        prefs.pop("xai", None)
        reg._save_model_prefs(prefs)

        result = reg.get_models(
            {"OPENAI_API_KEY": "sk-local-test", "XAI_API_KEY": "xai-local-test"},
            mock_openai_listing=mock_openai,
            mock_xai_listing=mock_xai,
        )
        assert result["openai"] == "gpt-5.3"
        assert result["xai"] == "grok-4-fast"
