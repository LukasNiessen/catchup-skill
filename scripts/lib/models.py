#
# Model Selection: Automatic API model discovery and selection for the catchup skill
# Handles model availability checks and version-based prioritization
#

import re
from typing import Dict, List, Optional, Tuple

from . import cache, http

# OpenAI API configuration
OPENAI_MODEL_LISTING_ENDPOINT = "https://api.openai.com/v1/models"
OPENAI_DEFAULT_MODELS = ["gpt-5.2", "gpt-5.1", "gpt-5", "gpt-4o"]

# xAI API configuration - Agent Tools API requires grok-4 family
XAI_MODEL_LISTING_ENDPOINT = "https://api.x.ai/v1/models"
XAI_MODEL_ALIASES = {
    "latest": "grok-4-1-fast",  # Required for x_search tool
    "stable": "grok-4-1-fast",
}


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


# Preserve the original function name for API compatibility
parse_version = extract_version_tuple


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


# Preserve the original function name for API compatibility
is_mainline_openai_model = is_standard_gpt_model


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
            api_response = http.get(OPENAI_MODEL_LISTING_ENDPOINT, request_headers=authorization_headers)
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


# Preserve the original function name for API compatibility
select_openai_model = choose_openai_model


def choose_xai_model(
    api_credential: str,
    selection_policy: str = "latest",
    pinned_model: Optional[str] = None,
    mock_model_list: Optional[List[Dict]] = None,
) -> str:
    """
    Selects the optimal xAI model based on the specified policy.

    Selection policies:
    - 'pinned': Use the exact model specified
    - 'latest': Use the most recent stable model
    - 'stable': Use the proven stable model

    Returns the selected model identifier.
    """
    # Honor explicit model pinning
    if selection_policy == "pinned" and pinned_model:
        return pinned_model

    # Use alias system for named policies
    if selection_policy in XAI_MODEL_ALIASES:
        resolved_model = XAI_MODEL_ALIASES[selection_policy]

        # Check cache first
        cached_selection = cache.get_cached_model("xai")
        if cached_selection:
            return cached_selection

        # Cache the resolved alias
        cache.set_cached_model("xai", resolved_model)
        return resolved_model

    # Default to latest
    return XAI_MODEL_ALIASES["latest"]


# Preserve the original function name for API compatibility
select_xai_model = choose_xai_model


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
    selected_models = {"openai": None, "xai": None}

    # Select OpenAI model if key is configured
    openai_key = configuration.get("OPENAI_API_KEY")
    if openai_key:
        selected_models["openai"] = choose_openai_model(
            openai_key,
            configuration.get("OPENAI_MODEL_POLICY", "auto"),
            configuration.get("OPENAI_MODEL_PIN"),
            mock_openai_listing,
        )

    # Select xAI model if key is configured
    xai_key = configuration.get("XAI_API_KEY")
    if xai_key:
        selected_models["xai"] = choose_xai_model(
            xai_key,
            configuration.get("XAI_MODEL_POLICY", "latest"),
            configuration.get("XAI_MODEL_PIN"),
            mock_xai_listing,
        )

    return selected_models
