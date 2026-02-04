#
# Configuration Management: Environment and credential handling for the catchup skill
# Manages API key loading and source availability determination
#

import os
from pathlib import Path
from typing import Optional, Dict, Any

# Configuration file locations
SETTINGS_DIRECTORY = Path.home() / ".config" / "catchup"
SETTINGS_FILEPATH = SETTINGS_DIRECTORY / ".env"


def parse_environment_file(filepath: Path) -> Dict[str, str]:
    """
    Parses a dotenv-style configuration file into a dictionary.

    Handles:
    - Comment lines (starting with #)
    - Quoted values (single or double quotes)
    - Empty lines
    """
    parsed_values = {}

    if not filepath.exists():
        return parsed_values

    with open(filepath, 'r') as file_handle:
        for raw_line in file_handle:
            stripped_line = raw_line.strip()

            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith('#'):
                continue

            # Parse key=value pairs
            if '=' not in stripped_line:
                continue

            key_part, _, value_part = stripped_line.partition('=')
            key_part = key_part.strip()
            value_part = value_part.strip()

            # Remove surrounding quotes if present
            if len(value_part) >= 2:
                first_char = value_part[0]
                last_char = value_part[-1]
                if first_char in ('"', "'") and last_char == first_char:
                    value_part = value_part[1:-1]

            # Only store non-empty key-value pairs
            if key_part and value_part:
                parsed_values[key_part] = value_part

    return parsed_values


# Preserve the original function name for API compatibility
load_env_file = parse_environment_file


def assemble_configuration() -> Dict[str, Any]:
    """
    Builds the complete configuration from file and environment variables.

    Environment variables take precedence over file-based configuration,
    allowing runtime overrides without modifying the config file.
    """
    # Load file-based configuration first
    file_settings = parse_environment_file(SETTINGS_FILEPATH)

    # Build configuration with environment variable overrides
    configuration = {
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY') or file_settings.get('OPENAI_API_KEY'),
        'XAI_API_KEY': os.environ.get('XAI_API_KEY') or file_settings.get('XAI_API_KEY'),
        'OPENAI_MODEL_POLICY': os.environ.get('OPENAI_MODEL_POLICY') or file_settings.get('OPENAI_MODEL_POLICY', 'auto'),
        'OPENAI_MODEL_PIN': os.environ.get('OPENAI_MODEL_PIN') or file_settings.get('OPENAI_MODEL_PIN'),
        'XAI_MODEL_POLICY': os.environ.get('XAI_MODEL_POLICY') or file_settings.get('XAI_MODEL_POLICY', 'latest'),
        'XAI_MODEL_PIN': os.environ.get('XAI_MODEL_PIN') or file_settings.get('XAI_MODEL_PIN'),
    }

    return configuration


# Preserve the original function name for API compatibility
get_config = assemble_configuration


def settings_file_exists() -> bool:
    """Checks whether the configuration file has been created."""
    return SETTINGS_FILEPATH.exists()


# Preserve the original function name for API compatibility
config_exists = settings_file_exists


def determine_available_platforms(configuration: Dict[str, Any]) -> str:
    """
    Identifies which data sources are accessible based on configured API keys.

    Returns:
    - 'both': OpenAI and xAI keys present (Reddit + X available)
    - 'reddit': Only OpenAI key present (Reddit/YouTube/LinkedIn available)
    - 'x': Only xAI key present (X/Twitter available)
    - 'web': No keys present (WebSearch fallback only)
    """
    openai_configured = bool(configuration.get('OPENAI_API_KEY'))
    xai_configured = bool(configuration.get('XAI_API_KEY'))

    if openai_configured and xai_configured:
        return 'both'
    elif openai_configured:
        return 'reddit'
    elif xai_configured:
        return 'x'
    else:
        return 'web'


# Preserve the original function name for API compatibility
get_available_sources = determine_available_platforms


def identify_missing_credentials(configuration: Dict[str, Any]) -> str:
    """
    Determines which API keys are not configured.

    Returns:
    - 'none': All keys present
    - 'x': xAI key missing
    - 'reddit': OpenAI key missing
    - 'both': Both keys missing
    """
    openai_configured = bool(configuration.get('OPENAI_API_KEY'))
    xai_configured = bool(configuration.get('XAI_API_KEY'))

    if openai_configured and xai_configured:
        return 'none'
    elif openai_configured:
        return 'x'
    elif xai_configured:
        return 'reddit'
    else:
        return 'both'


# Preserve the original function name for API compatibility
get_missing_keys = identify_missing_credentials


def validate_sources(
    requested_sources: str,
    available_platforms: str,
    include_web_search: bool = False
) -> tuple[str, Optional[str]]:
    """
    Validates requested data sources against available API credentials.

    Args:
        requested_sources: User's requested sources ('auto', 'reddit', 'x', etc.)
        available_platforms: Result from determine_available_platforms()
        include_web_search: Whether to include WebSearch alongside other sources

    Returns:
        Tuple of (effective_sources, error_message)
        - effective_sources: The sources that will actually be used
        - error_message: Warning or error text, or None if valid
    """
    # Handle case where no API keys are configured
    if available_platforms == 'web':
        if requested_sources == 'auto':
            return 'web', None
        elif requested_sources == 'web':
            return 'web', None
        else:
            return 'web', "No API keys configured. Using WebSearch fallback. Add keys to ~/.config/catchup/.env for Reddit/X/YouTube/LinkedIn."

    # Auto mode: use whatever is available
    if requested_sources == 'auto':
        if include_web_search:
            source_mapping = {
                'both': 'all',
                'reddit': 'reddit-web',
                'x': 'x-web',
            }
            return source_mapping.get(available_platforms, available_platforms), None
        return available_platforms, None

    # Explicit web-only mode
    if requested_sources == 'web':
        return 'web', None

    # All sources mode
    if requested_sources == 'all':
        if available_platforms == 'both':
            return 'all', None
        elif available_platforms == 'reddit':
            return 'all', "Note: xAI key not configured, X/Twitter will be skipped."
        elif available_platforms == 'x':
            return 'all', "Note: OpenAI key not configured, Reddit/YouTube/LinkedIn will be skipped."
        return 'web', "No API keys configured."

    # Both sources explicitly requested
    if requested_sources == 'both':
        if available_platforms != 'both':
            missing_provider = 'xAI' if available_platforms == 'reddit' else 'OpenAI'
            return 'none', "Requested both sources but {} key is missing. Use --sources=auto to use available keys.".format(missing_provider)
        if include_web_search:
            return 'all', None
        return 'both', None

    # Reddit explicitly requested
    if requested_sources == 'reddit':
        if available_platforms == 'x':
            return 'none', "Requested Reddit but only xAI key is available."
        if include_web_search:
            return 'reddit-web', None
        return 'reddit', None

    # X explicitly requested
    if requested_sources == 'x':
        if available_platforms == 'reddit':
            return 'none', "Requested X but only OpenAI key is available."
        if include_web_search:
            return 'x-web', None
        return 'x', None

    # YouTube explicitly requested (requires OpenAI)
    if requested_sources == 'youtube':
        if available_platforms == 'x':
            return 'none', "Requested YouTube but only xAI key is available (YouTube uses OpenAI)."
        return 'youtube', None

    # LinkedIn explicitly requested (requires OpenAI)
    if requested_sources == 'linkedin':
        if available_platforms == 'x':
            return 'none', "Requested LinkedIn but only xAI key is available (LinkedIn uses OpenAI)."
        return 'linkedin', None

    # Pass through unrecognized values
    return requested_sources, None
