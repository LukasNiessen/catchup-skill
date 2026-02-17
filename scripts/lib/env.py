#
# Configuration Management: Environment and credential handling for the BriefBot skill
# Manages API key loading and source availability determination
#

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any


def _log(message: str):
    """Emit a debug log line to stderr, gated by LAST30DAYS_DEBUG."""
    if os.environ.get("LAST30DAYS_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write("[ENV] {}\n".format(message))
        sys.stderr.flush()

# Configuration file locations
SETTINGS_DIRECTORY = Path.home() / ".config" / "briefbot"
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

    _log("Loading config from: {}".format(filepath))

    if not filepath.exists():
        _log("Config file NOT FOUND at: {}".format(filepath))
        return parsed_values

    _log("Config file exists, parsing...")

    with open(filepath, "r") as file_handle:
        for raw_line in file_handle:
            stripped_line = raw_line.strip()

            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith("#"):
                continue

            # Parse key=value pairs
            if "=" not in stripped_line:
                continue

            key_part, _, value_part = stripped_line.partition("=")
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
                # Mask sensitive values in logs
                if "KEY" in key_part or "PASSWORD" in key_part or "TOKEN" in key_part:
                    _log("  Loaded: {} = {}...{} ({} chars)".format(
                        key_part, value_part[:6], value_part[-4:], len(value_part)))
                else:
                    _log("  Loaded: {} = {}".format(key_part, value_part))

    _log("Parsed {} key-value pairs from config file".format(len(parsed_values)))
    return parsed_values


# Preserve the original function name for API compatibility
load_env_file = parse_environment_file


def assemble_configuration() -> Dict[str, Any]:
    """
    Builds the complete configuration from file and environment variables.

    Environment variables take precedence over file-based configuration,
    allowing runtime overrides without modifying the config file.
    """
    _log("=== Assembling configuration ===")

    # Load file-based configuration first
    file_settings = parse_environment_file(SETTINGS_FILEPATH)

    # Log environment variable overrides
    env_openai = os.environ.get("OPENAI_API_KEY")
    env_xai = os.environ.get("XAI_API_KEY")
    file_openai = file_settings.get("OPENAI_API_KEY")
    file_xai = file_settings.get("XAI_API_KEY")
    _log("OPENAI_API_KEY: env={}, file={}".format(
        "SET ({} chars)".format(len(env_openai)) if env_openai else "NOT SET",
        "SET ({} chars)".format(len(file_openai)) if file_openai else "NOT SET",
    ))
    _log("XAI_API_KEY: env={}, file={}".format(
        "SET ({} chars)".format(len(env_xai)) if env_xai else "NOT SET",
        "SET ({} chars)".format(len(file_xai)) if file_xai else "NOT SET",
    ))

    # Build configuration with environment variable overrides
    configuration = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY")
        or file_settings.get("OPENAI_API_KEY"),
        "XAI_API_KEY": os.environ.get("XAI_API_KEY")
        or file_settings.get("XAI_API_KEY"),
        "OPENAI_MODEL_POLICY": os.environ.get("OPENAI_MODEL_POLICY")
        or file_settings.get("OPENAI_MODEL_POLICY", "auto"),
        "OPENAI_MODEL_PIN": os.environ.get("OPENAI_MODEL_PIN")
        or file_settings.get("OPENAI_MODEL_PIN"),
        "XAI_MODEL_POLICY": os.environ.get("XAI_MODEL_POLICY")
        or file_settings.get("XAI_MODEL_POLICY", "latest"),
        "XAI_MODEL_PIN": os.environ.get("XAI_MODEL_PIN")
        or file_settings.get("XAI_MODEL_PIN"),
        "ELEVENLABS_API_KEY": os.environ.get("ELEVENLABS_API_KEY")
        or file_settings.get("ELEVENLABS_API_KEY"),
        "ELEVENLABS_VOICE_ID": os.environ.get("ELEVENLABS_VOICE_ID")
        or file_settings.get("ELEVENLABS_VOICE_ID"),
        "SMTP_HOST": os.environ.get("SMTP_HOST") or file_settings.get("SMTP_HOST"),
        "SMTP_PORT": os.environ.get("SMTP_PORT")
        or file_settings.get("SMTP_PORT", "587"),
        "SMTP_USER": os.environ.get("SMTP_USER") or file_settings.get("SMTP_USER"),
        "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD")
        or file_settings.get("SMTP_PASSWORD"),
        "SMTP_FROM": os.environ.get("SMTP_FROM") or file_settings.get("SMTP_FROM"),
        "SMTP_USE_TLS": os.environ.get("SMTP_USE_TLS")
        or file_settings.get("SMTP_USE_TLS", "true"),
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN")
        or file_settings.get("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID")
        or file_settings.get("TELEGRAM_CHAT_ID"),
        # X/Twitter browser cookies for Bird search (Chrome 127+ App-Bound Encryption workaround)
        "AUTH_TOKEN": os.environ.get("AUTH_TOKEN") or file_settings.get("AUTH_TOKEN"),
        "CT0": os.environ.get("CT0") or file_settings.get("CT0"),
    }

    # Final summary of resolved configuration
    effective_openai = configuration.get("OPENAI_API_KEY")
    effective_xai = configuration.get("XAI_API_KEY")
    _log("Resolved OPENAI_API_KEY: {}".format(
        "YES ({} chars, starts with '{}')".format(len(effective_openai), effective_openai[:8]) if effective_openai else "NO"
    ))
    _log("Resolved XAI_API_KEY: {}".format(
        "YES ({} chars, starts with '{}')".format(len(effective_xai), effective_xai[:8]) if effective_xai else "NO"
    ))
    _log("Resolved XAI_MODEL_POLICY: {}".format(configuration.get("XAI_MODEL_POLICY")))
    _log("=== Configuration assembly complete ===")

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
    Identifies which data sources are accessible based on configured API keys
    and Bird X search availability (browser cookies).

    Returns:
    - 'both': OpenAI and X available (via xAI key or Bird)
    - 'reddit': Only OpenAI key present (Reddit/YouTube/LinkedIn available)
    - 'x': Only X available (via xAI key or Bird)
    - 'web': No keys or Bird present (WebSearch fallback only)
    """
    _log("=== Determining available platforms ===")
    openai_configured = bool(configuration.get("OPENAI_API_KEY"))
    xai_configured = bool(configuration.get("XAI_API_KEY"))
    bird_available = is_bird_x_available()

    x_available = xai_configured or bird_available

    _log("  OpenAI configured: {}".format(openai_configured))
    _log("  xAI configured:    {}".format(xai_configured))
    _log("  Bird available:     {}".format(bird_available))
    _log("  X available (xAI or Bird): {}".format(x_available))

    if openai_configured and x_available:
        _log("  Result: 'both' (OpenAI + X)")
        return "both"
    elif openai_configured:
        _log("  Result: 'reddit' (OpenAI only, no X)")
        return "reddit"
    elif x_available:
        _log("  Result: 'x' (X only, no OpenAI)")
        return "x"
    else:
        _log("  Result: 'web' (NO API keys, WebSearch fallback only)")
        return "web"


# Preserve the original function name for API compatibility
get_available_sources = determine_available_platforms


def identify_missing_credentials(configuration: Dict[str, Any]) -> str:
    """
    Determines which API keys are not configured.
    Bird X search (browser cookies) suppresses the xAI "missing" status.

    Returns:
    - 'none': All keys present (or Bird covers X)
    - 'x': xAI key missing and Bird unavailable
    - 'reddit': OpenAI key missing
    - 'both': Both keys missing and Bird unavailable
    """
    openai_configured = bool(configuration.get("OPENAI_API_KEY"))
    xai_configured = bool(configuration.get("XAI_API_KEY"))
    bird_available = is_bird_x_available()

    has_x = xai_configured or bird_available

    if openai_configured and has_x:
        return "none"
    elif openai_configured:
        return "x"
    elif has_x:
        return "reddit"
    else:
        return "both"


# Preserve the original function name for API compatibility
get_missing_keys = identify_missing_credentials


def is_bird_x_available() -> bool:
    """
    Checks if Bird X search is installed and authenticated.
    Lazy-imports bird_x to avoid circular dependencies.
    """
    try:
        from lib import bird_x

        installed = bird_x.is_bird_installed()
        authenticated = bool(bird_x.is_bird_authenticated()) if installed else False
        result = installed and authenticated
        _log("Bird X check: installed={}, authenticated={}, available={}".format(
            installed, authenticated, result))
        return result
    except Exception as exc:
        _log("Bird X check failed with exception: {}".format(exc))
        return False


def validate_sources(
    requested_sources: str, available_platforms: str, include_web_search: bool = False
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
    _log("=== Validating sources ===")
    _log("  Requested: '{}', Available: '{}', Include web: {}".format(
        requested_sources, available_platforms, include_web_search))

    # Handle case where no API keys are configured
    if available_platforms == "web":
        if requested_sources == "auto":
            _log("  No API keys, auto -> 'web' (WebSearch fallback)")
            return "web", None
        elif requested_sources == "web":
            _log("  No API keys, web -> 'web'")
            return "web", None
        else:
            _log("  No API keys, requested '{}' -> forced to 'web' with warning".format(requested_sources))
            return (
                "web",
                "No API keys configured. Using WebSearch fallback. Add keys to ~/.config/briefbot/.env for Reddit/X/YouTube/LinkedIn.",
            )

    # Auto mode: use whatever is available
    if requested_sources == "auto":
        if include_web_search:
            source_mapping = {
                "both": "all",
                "reddit": "reddit-web",
                "x": "x-web",
            }
            result = source_mapping.get(available_platforms, available_platforms)
            _log("  Auto + web -> '{}'".format(result))
            return result, None
        _log("  Auto -> '{}'".format(available_platforms))
        return available_platforms, None

    # Explicit web-only mode
    if requested_sources == "web":
        return "web", None

    # All sources mode
    if requested_sources == "all":
        if available_platforms == "both":
            return "all", None
        elif available_platforms == "reddit":
            return (
                "all",
                "Note: No X source available (no xAI key and Bird not authenticated). X/Twitter will be skipped.",
            )
        elif available_platforms == "x":
            return (
                "all",
                "Note: OpenAI key not configured, Reddit/YouTube/LinkedIn will be skipped.",
            )
        return "web", "No API keys configured."

    # Both sources explicitly requested
    if requested_sources == "both":
        if available_platforms != "both":
            missing_provider = "xAI" if available_platforms == "reddit" else "OpenAI"
            return (
                "none",
                "Requested both sources but {} key is missing. Use --sources=auto to use available keys.".format(
                    missing_provider
                ),
            )
        if include_web_search:
            return "all", None
        return "both", None

    # Reddit explicitly requested
    if requested_sources == "reddit":
        if available_platforms == "x":
            return "none", "Requested Reddit but only xAI key is available."
        if include_web_search:
            return "reddit-web", None
        return "reddit", None

    # X explicitly requested
    if requested_sources == "x":
        if available_platforms == "reddit":
            return "none", "Requested X but only OpenAI key is available."
        if include_web_search:
            return "x-web", None
        return "x", None

    # YouTube explicitly requested (requires OpenAI)
    if requested_sources == "youtube":
        if available_platforms == "x":
            return (
                "none",
                "Requested YouTube but only xAI key is available (YouTube uses OpenAI).",
            )
        return "youtube", None

    # LinkedIn explicitly requested (requires OpenAI)
    if requested_sources == "linkedin":
        if available_platforms == "x":
            return (
                "none",
                "Requested LinkedIn but only xAI key is available (LinkedIn uses OpenAI).",
            )
        return "linkedin", None

    # Pass through unrecognized values
    return requested_sources, None
