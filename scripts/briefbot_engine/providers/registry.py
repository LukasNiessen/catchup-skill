"""Provider cache + model selection registry."""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .. import net


def _log(message: str):
    """Emit a debug log line to stderr, gated by BRIEFBOT_DEBUG."""
    if os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write("[REGISTRY] {}\n".format(message))
        sys.stderr.flush()


class ProviderRegistry:
    """Manages response caching (JSON files with TTL) and model selection."""

    CACHE_DIR = Path.home() / ".cache" / "briefbot"
    DEFAULT_TTL = 20
    MODEL_TTL_DAYS = 4

    # OpenAI API configuration
    OPENAI_MODEL_LISTING_ENDPOINT = "https://api.openai.com/v1/models"
    OPENAI_DEFAULT_MODELS = ["gpt-5.2", "gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o"]

    # xAI API configuration
    XAI_MODEL_LISTING_ENDPOINT = "https://api.x.ai/v1/models"
    XAI_HARDCODED_FALLBACK = "grok-4-fast"
    XAI_MODEL_PREFERENCE = [
        "grok-4-fast",
        "grok-4-1-fast",
        "grok-4-1-fast-non-reasoning",
        "grok-4-1-non-reasoning",
        "grok-4-1",
        "grok-4-non-reasoning",
        "grok-4",
    ]

    def __init__(self):
        self._model_file = self.CACHE_DIR / "model_prefs.json"

    # -----------------------------------------------------------------
    # Response caching
    # -----------------------------------------------------------------

    def _ensure_dir(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def cache_key(self, topic: str, start: str, end: str, platform: str) -> str:
        raw = f"{topic}|{start}|{end}|{platform}"
        digest = hashlib.blake2s(raw.encode("utf-8"), digest_size=16).hexdigest()
        return digest[:20]

    def cache_path(self, key: str) -> Path:
        return self.CACHE_DIR / f"{key}.json"

    def is_valid(self, filepath: Path, ttl_hours: int = None) -> bool:
        ttl = self.DEFAULT_TTL if ttl_hours is None else ttl_hours
        if not filepath.exists():
            return False
        try:
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
            return elapsed < ttl
        except OSError:
            return False

    def load(self, key: str, ttl_hours: int = None) -> Optional[dict]:
        ttl = self.DEFAULT_TTL if ttl_hours is None else ttl_hours
        fp = self.cache_path(key)
        if not self.is_valid(fp, ttl):
            return None
        try:
            with open(fp, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None

    def age_hours(self, filepath: Path) -> Optional[float]:
        if not filepath.exists():
            return None
        try:
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
            return (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
        except OSError:
            return None

    def load_with_age(self, key: str, ttl_hours: int = None) -> tuple:
        ttl = self.DEFAULT_TTL if ttl_hours is None else ttl_hours
        fp = self.cache_path(key)
        if not self.is_valid(fp, ttl):
            return None, None
        hours = self.age_hours(fp)
        try:
            with open(fp, "r", encoding="utf-8") as handle:
                return json.load(handle), hours
        except (json.JSONDecodeError, OSError):
            return None, None

    def save(self, key: str, data: dict):
        self._ensure_dir()
        fp = self.cache_path(key)
        try:
            with open(fp, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except OSError:
            pass

    def clear_all(self):
        if not self.CACHE_DIR.exists():
            return
        for f in self.CACHE_DIR.glob("*.json"):
            if f.name == "model_prefs.json":
                continue
            try:
                f.unlink()
            except OSError:
                pass

    def cache_stats(self) -> dict:
        if not self.CACHE_DIR.exists():
            return {"entries": 0, "size_bytes": 0}
        count = 0
        total_size = 0
        for f in self.CACHE_DIR.glob("*.json"):
            try:
                total_size += f.stat().st_size
                count += 1
            except OSError:
                pass
        return {"entries": count, "size_bytes": total_size}

    # -----------------------------------------------------------------
    # Model preference persistence
    # -----------------------------------------------------------------

    def _load_model_prefs(self) -> dict:
        ttl_hours = self.MODEL_TTL_DAYS * 24
        if not self.is_valid(self._model_file, ttl_hours):
            return {}
        try:
            with open(self._model_file, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_model_prefs(self, data: dict):
        self._ensure_dir()
        try:
            with open(self._model_file, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except OSError:
            pass

    def get_cached_model(self, provider_name: str) -> Optional[str]:
        return self._load_model_prefs().get(provider_name)

    def set_cached_model(self, provider_name: str, model_identifier: str):
        prefs = self._load_model_prefs()
        now = datetime.now(timezone.utc).isoformat()
        prefs[provider_name] = model_identifier
        prefs["updated_at"] = now
        prefs["selected_at"] = now
        self._save_model_prefs(prefs)

    # -----------------------------------------------------------------
    # Model selection
    # -----------------------------------------------------------------

    @staticmethod
    def extract_version_tuple(model_identifier: str) -> Optional[Tuple[int, ...]]:
        version_pattern = re.search(r"(\d+(?:[._]\d+)*)", model_identifier)
        if version_pattern is None:
            return None
        version_string = version_pattern.group(1)
        version_components = re.split(r"[._]", version_string)
        return tuple(int(component) for component in version_components)

    @staticmethod
    def is_standard_gpt_model(model_identifier: str) -> bool:
        normalized_id = model_identifier.lower()
        pattern_match = re.match(r"^gpt-5(\.\d+)*$", normalized_id)
        if not pattern_match:
            return False
        excluded_variants = ["mini", "nano", "chat", "codex", "preview", "turbo", "experimental", "snapshot"]
        for variant in excluded_variants:
            if variant in normalized_id:
                return False
        return True

    def choose_openai_model(
        self,
        api_credential: str,
        selection_policy: str = "auto",
        pinned_model: Optional[str] = None,
        mock_model_list: Optional[List[Dict]] = None,
    ) -> str:
        if selection_policy == "pinned" and pinned_model:
            return pinned_model

        cached_selection = self.get_cached_model("openai")
        if cached_selection:
            return cached_selection

        if mock_model_list is not None:
            available_models = mock_model_list
        else:
            try:
                authorization_headers = {"Authorization": "Bearer {}".format(api_credential)}
                available_models = net.get(self.OPENAI_MODEL_LISTING_ENDPOINT, headers=authorization_headers).get(
                    "data", []
                )
            except net.HTTPError:
                return self.OPENAI_DEFAULT_MODELS[0]

        eligible_models = [model for model in available_models if self.is_standard_gpt_model(model.get("id", ""))]

        if len(eligible_models) == 0:
            return self.OPENAI_DEFAULT_MODELS[0]

        def compute_sort_key(model_entry):
            version_tuple = self.extract_version_tuple(model_entry.get("id", "")) or (0,)
            creation_timestamp = model_entry.get("created", 0)
            return (version_tuple, creation_timestamp)

        eligible_models.sort(key=compute_sort_key, reverse=True)
        optimal_model = eligible_models[0]["id"]

        self.set_cached_model("openai", optimal_model)
        return optimal_model

    def discover_xai_models(self, api_credential: str) -> List[str]:
        try:
            authorization_headers = {"Authorization": "Bearer {}".format(api_credential)}
            api_response = net.get(self.XAI_MODEL_LISTING_ENDPOINT, headers=authorization_headers)
            return [m.get("id", "") for m in api_response.get("data", []) if m.get("id")]
        except net.HTTPError as err:
            _log("discover_xai_models failed: {}".format(err))
            return []

    def choose_xai_model(
        self,
        api_credential: str,
        selection_policy: str = "latest",
        pinned_model: Optional[str] = None,
        mock_model_list: Optional[List[Dict]] = None,
    ) -> str:
        _log("=== choose_xai_model ===")
        _log("  Policy: '{}', Pinned: {}".format(selection_policy, pinned_model))

        if selection_policy == "pinned" and pinned_model:
            _log("  Using PINNED model: {}".format(pinned_model))
            return pinned_model

        cached_selection = self.get_cached_model("xai")
        if cached_selection:
            _log("  Using CACHED model: {}".format(cached_selection))
            return cached_selection

        if mock_model_list is not None:
            available_ids = {m.get("id", "") for m in mock_model_list}
            _log("  Using mock model list ({} models)".format(len(available_ids)))
        else:
            discovered = self.discover_xai_models(api_credential)
            if not discovered:
                _log("  Failed to discover models, using hardcoded fallback: {}".format(
                    self.XAI_HARDCODED_FALLBACK))
                self.set_cached_model("xai", self.XAI_HARDCODED_FALLBACK)
                return self.XAI_HARDCODED_FALLBACK
            available_ids = set(discovered)
            _log("  Fetched {} models from xAI API".format(len(available_ids)))
        _log("  Available model IDs: {}".format(sorted(available_ids)))

        for preferred in self.XAI_MODEL_PREFERENCE:
            if preferred in available_ids:
                _log("  Matched preferred model: {}".format(preferred))
                self.set_cached_model("xai", preferred)
                return preferred

        grok4_models = sorted(
            [mid for mid in available_ids if mid.startswith("grok-4")],
            reverse=True,
        )
        if grok4_models:
            selected = grok4_models[0]
            _log("  No preferred match, using first grok-4 model: {}".format(selected))
            self.set_cached_model("xai", selected)
            return selected

        _log("  WARNING: No grok-4 models available! Falling back to: {}".format(self.XAI_HARDCODED_FALLBACK))
        self.set_cached_model("xai", self.XAI_HARDCODED_FALLBACK)
        return self.XAI_HARDCODED_FALLBACK

    def get_models(
        self,
        configuration: Dict,
        mock_openai_listing: Optional[List[Dict]] = None,
        mock_xai_listing: Optional[List[Dict]] = None,
    ) -> Dict[str, Optional[str]]:
        _log("=== get_models ===")
        selected_models = {"openai": None, "xai": None}

        openai_key = configuration.get("OPENAI_API_KEY")
        _log("  OpenAI key present: {}".format(bool(openai_key)))
        if openai_key:
            selected_models["openai"] = self.choose_openai_model(
                openai_key,
                configuration.get("OPENAI_MODEL_POLICY", "auto"),
                configuration.get("OPENAI_MODEL_PIN"),
                mock_openai_listing,
            )
            _log("  OpenAI model selected: {}".format(selected_models["openai"]))

        xai_key = configuration.get("XAI_API_KEY")
        _log("  xAI key present: {}".format(bool(xai_key)))
        if xai_key:
            selected_models["xai"] = self.choose_xai_model(
                xai_key,
                configuration.get("XAI_MODEL_POLICY", "latest"),
                configuration.get("XAI_MODEL_PIN"),
                mock_xai_listing,
            )
            _log("  xAI model selected: {}".format(selected_models["xai"]))

        _log("  Final models: {}".format(selected_models))
        return selected_models


# Module-level singleton
_registry = ProviderRegistry()

# Module-level convenience functions that delegate to the singleton
cache_key = _registry.cache_key
cache_path = _registry.cache_path
is_valid = _registry.is_valid
load = _registry.load
age_hours = _registry.age_hours
load_with_age = _registry.load_with_age
save = _registry.save
clear_all = _registry.clear_all
cache_stats = _registry.cache_stats
get_cached_model = _registry.get_cached_model
set_cached_model = _registry.set_cached_model
extract_version_tuple = ProviderRegistry.extract_version_tuple
is_standard_gpt_model = ProviderRegistry.is_standard_gpt_model
choose_openai_model = _registry.choose_openai_model
choose_xai_model = _registry.choose_xai_model
discover_xai_models = _registry.discover_xai_models
get_models = _registry.get_models
