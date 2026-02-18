#
# Model Selection: Automatic API model discovery and selection for the BriefBot skill
# Handles model availability checks and version-based prioritization
#

import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from . import cache, http


def _log(message: str):
    """Emit a debug log line to stderr, gated by BRIEFBOT_DEBUG."""
    if os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write("[MODELS] {}\n".format(message))
        sys.stderr.flush()

# OpenAI API configuration
OPENAI_MODEL_LISTING_ENDPOINT = "https://api.openai.com/v1/models"
OPENAI_DEFAULT_MODELS = ["gpt-5.2", "gpt-5.1", "gpt-5", "gpt-4o"]

# xAI API configuration - Agent Tools API requires grok-4 family
XAI_MODEL_LISTING_ENDPOINT = "https://api.x.ai/v1/models"
XAI_HARDCODED_FALLBACK = "grok-4-1-fast"

# Preferred xAI models in priority order (first match wins).
# Any grok-4+ model supports x_search, but we prefer fast variants.
XAI_MODEL_PREFERENCE = [
    "grok-4-1-fast",
    "grok-4-1-fast-non-reasoning",
    "grok-4-fast",
    "grok-4-1",
    "grok-4",
]


def extract_version_tuple(model_identifier: str) -> Optional[Tuple[int, ...]]:
    """
    Extracts semantic version numbers from a model identifier.

    Examples:
        gpt-5 -> (5,)
        gpt-5.2 -> (5, 2)
        gpt-5.2.1 -> (5, 2, 1)
    """
    version_pattern = re.search(r'(\d+(?:\.\d+)*)', model_identifier)

    if version_pattern is None:
        return None

    version_string = version_pattern.group(1)
    version_components = version_string.split('.')
    return tuple(int(component) for component in version_components)


def is_standard_gpt_model(model_identifier: str) -> bool:
    """
    Determines if a model is a mainline GPT model (not a specialized variant).

    Excludes mini, nano, chat, codex, pro, preview, and turbo variants
    to ensure selection of full-capability models.
    """
    normalized_id = model_identifier.lower()

    # Must match gpt-5 series pattern
    pattern_match = re.match(r'^gpt-5(\.\d+)*$', normalized_id)
    if not pattern_match:
        return False

    # Check for excluded variant keywords
    excluded_variants = ['mini', 'nano', 'chat', 'codex', 'pro', 'preview', 'turbo']

    for variant in excluded_variants:
        if variant in normalized_id:
            return False

    return True


def choose_openai_model(
    api_credential: str,
    selection_policy: str = "auto",
    pinned_model: Optional[str] = None,
    mock_model_list: Optional[List[Dict]] = None,
) -> str:
    """
    Selects the optimal OpenAI model based on the specified policy.

    Selection policies:
    - 'pinned': Use the exact model specified
    - 'auto': Automatically select the newest mainline model

    Returns the selected model identifier.
    """
    # Honor explicit model pinning
    if selection_policy == "pinned" and pinned_model:
        return pinned_model

    # Check for cached selection first
    cached_selection = cache.get_cached_model("openai")
    if cached_selection:
        return cached_selection

    # Retrieve available models
    if mock_model_list is not None:
        available_models = mock_model_list
    else:
        try:
            authorization_headers = {"Authorization": "Bearer {}".format(api_credential)}
            api_response = http.perform_get_request(OPENAI_MODEL_LISTING_ENDPOINT, request_headers=authorization_headers)
            available_models = api_response.get("data", [])
        except http.HTTPError:
            return OPENAI_DEFAULT_MODELS[0]

    # Filter to mainline models only
    eligible_models = [
        model for model in available_models
        if is_standard_gpt_model(model.get("id", ""))
    ]

    if len(eligible_models) == 0:
        return OPENAI_DEFAULT_MODELS[0]

    # Sort by version (descending) then creation timestamp
    def compute_sort_key(model_entry):
        version_tuple = extract_version_tuple(model_entry.get("id", "")) or (0,)
        creation_timestamp = model_entry.get("created", 0)
        return (version_tuple, creation_timestamp)

    eligible_models.sort(key=compute_sort_key, reverse=True)
    optimal_model = eligible_models[0]["id"]

    # Persist selection for future use
    cache.set_cached_model("openai", optimal_model)

    return optimal_model


def choose_xai_model(
    api_credential: str,
    selection_policy: str = "latest",
    pinned_model: Optional[str] = None,
    mock_model_list: Optional[List[Dict]] = None,
) -> str:
    """
    Selects the optimal xAI model based on the specified policy.

    Queries the xAI /v1/models API to discover which models the key
    actually has access to, then picks the best grok-4+ model.

    Selection policies:
    - 'pinned': Use the exact model specified
    - 'latest'/'stable': Auto-select from available grok-4 models

    Returns the selected model identifier.
    """
    _log("=== choose_xai_model ===")
    _log("  Policy: '{}', Pinned: {}".format(selection_policy, pinned_model))

    # Honor explicit model pinning
    if selection_policy == "pinned" and pinned_model:
        _log("  Using PINNED model: {}".format(pinned_model))
        return pinned_model

    # Check cache first
    cached_selection = cache.get_cached_model("xai")
    if cached_selection:
        _log("  Using CACHED model: {}".format(cached_selection))
        return cached_selection

    # Query the API for actually available models
    if mock_model_list is not None:
        available_models = mock_model_list
        _log("  Using mock model list ({} models)".format(len(available_models)))
    else:
        try:
            authorization_headers = {"Authorization": "Bearer {}".format(api_credential)}
            api_response = http.perform_get_request(XAI_MODEL_LISTING_ENDPOINT, request_headers=authorization_headers)
            available_models = api_response.get("data", [])
            _log("  Fetched {} models from xAI API".format(len(available_models)))
        except http.HTTPError as err:
            _log("  Failed to fetch models ({}), using hardcoded fallback: {}".format(
                err, XAI_HARDCODED_FALLBACK))
            cache.set_cached_model("xai", XAI_HARDCODED_FALLBACK)
            return XAI_HARDCODED_FALLBACK

    available_ids = {m.get("id", "") for m in available_models}
    _log("  Available model IDs: {}".format(sorted(available_ids)))

    # Pick the best model from the preference list
    for preferred in XAI_MODEL_PREFERENCE:
        if preferred in available_ids:
            _log("  Matched preferred model: {}".format(preferred))
            cache.set_cached_model("xai", preferred)
            return preferred

    # No preferred model found - pick any grok-4+ model
    grok4_models = sorted(
        [mid for mid in available_ids if mid.startswith("grok-4")],
        reverse=True,
    )
    if grok4_models:
        selected = grok4_models[0]
        _log("  No preferred match, using first grok-4 model: {}".format(selected))
        cache.set_cached_model("xai", selected)
        return selected

    # Last resort: hardcoded fallback
    _log("  WARNING: No grok-4 models available! Falling back to: {}".format(XAI_HARDCODED_FALLBACK))
    _log("  Available models were: {}".format(sorted(available_ids)))
    cache.set_cached_model("xai", XAI_HARDCODED_FALLBACK)
    return XAI_HARDCODED_FALLBACK


def get_models(
    configuration: Dict,
    mock_openai_listing: Optional[List[Dict]] = None,
    mock_xai_listing: Optional[List[Dict]] = None,
) -> Dict[str, Optional[str]]:
    """
    Retrieves selected models for all configured providers.

    Returns a dictionary with 'openai' and 'xai' keys containing
    the selected model identifiers (or None if provider not configured).
    """
    _log("=== get_models ===")
    selected_models = {"openai": None, "xai": None}

    # Select OpenAI model if key is configured
    openai_key = configuration.get("OPENAI_API_KEY")
    _log("  OpenAI key present: {}".format(bool(openai_key)))
    if openai_key:
        selected_models["openai"] = choose_openai_model(
            openai_key,
            configuration.get("OPENAI_MODEL_POLICY", "auto"),
            configuration.get("OPENAI_MODEL_PIN"),
            mock_openai_listing,
        )
        _log("  OpenAI model selected: {}".format(selected_models["openai"]))

    # Select xAI model if key is configured
    xai_key = configuration.get("XAI_API_KEY")
    _log("  xAI key present: {}".format(bool(xai_key)))
    if xai_key:
        selected_models["xai"] = choose_xai_model(
            xai_key,
            configuration.get("XAI_MODEL_POLICY", "latest"),
            configuration.get("XAI_MODEL_PIN"),
            mock_xai_listing,
        )
        _log("  xAI model selected: {}".format(selected_models["xai"]))
    else:
        _log("  xAI key NOT present, skipping model selection (xai=None)")

    _log("  Final models: {}".format(selected_models))
    return selected_models
