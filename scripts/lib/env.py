"""Configuration and credential management."""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any


def _log(message: str):
    """Emit a debug line to stderr when BRIEFBOT_DEBUG is set."""
    if os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write(f"[ENV] {message}\n")
        sys.stderr.flush()


CONFIG_DIR = Path.home() / ".config" / "briefbot"
CONFIG_FILE = CONFIG_DIR / ".env"


def parse_dotenv(filepath: Path) -> Dict[str, str]:
    """Parse a dotenv-style file into a dict, handling comments and quotes."""
    parsed = {}

    _log(f"Loading config from: {filepath}")

    if not filepath.exists():
        _log(f"Config file NOT FOUND at: {filepath}")
        return parsed

    _log("Config file exists, parsing...")

    with open(filepath, "r") as fh:
        for raw_line in fh:
            stripped = raw_line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            if "=" not in stripped:
                continue

            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()

            # Strip surrounding quotes
            if len(value) >= 2:
                if value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]

            if key and value:
                parsed[key] = value
                if "KEY" in key or "PASSWORD" in key or "TOKEN" in key:
                    _log(f"  Loaded: {key} = {value[:6]}...{value[-4:]} ({len(value)} chars)")
                else:
                    _log(f"  Loaded: {key} = {value}")

    _log(f"Parsed {len(parsed)} key-value pairs from config file")
    return parsed


def load_config() -> Dict[str, Any]:
    """Build complete config from file + env vars (env vars take precedence)."""
    _log("=== Assembling configuration ===")

    file_settings = parse_dotenv(CONFIG_FILE)

    env_openai = os.environ.get("OPENAI_API_KEY")
    env_xai = os.environ.get("XAI_API_KEY")
    file_openai = file_settings.get("OPENAI_API_KEY")
    file_xai = file_settings.get("XAI_API_KEY")
    _log(f"OPENAI_API_KEY: env={f'SET ({len(env_openai)} chars)' if env_openai else 'NOT SET'}, file={f'SET ({len(file_openai)} chars)' if file_openai else 'NOT SET'}")
    _log(f"XAI_API_KEY: env={f'SET ({len(env_xai)} chars)' if env_xai else 'NOT SET'}, file={f'SET ({len(file_xai)} chars)' if file_xai else 'NOT SET'}")

    cfg = {
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
        "AUTH_TOKEN": os.environ.get("AUTH_TOKEN") or file_settings.get("AUTH_TOKEN"),
        "CT0": os.environ.get("CT0") or file_settings.get("CT0"),
    }

    eff_openai = cfg.get("OPENAI_API_KEY")
    eff_xai = cfg.get("XAI_API_KEY")
    _log(f"Resolved OPENAI_API_KEY: {f'YES ({len(eff_openai)} chars, starts with {chr(39)}{eff_openai[:8]}{chr(39)})' if eff_openai else 'NO'}")
    _log(f"Resolved XAI_API_KEY: {f'YES ({len(eff_xai)} chars, starts with {chr(39)}{eff_xai[:8]}{chr(39)})' if eff_xai else 'NO'}")
    _log(f"Resolved XAI_MODEL_POLICY: {cfg.get('XAI_MODEL_POLICY')}")
    _log("=== Configuration assembly complete ===")

    return cfg


def settings_file_exists() -> bool:
    """Check whether the config file exists."""
    return CONFIG_FILE.exists()


def determine_available_platforms(configuration: Dict[str, Any]) -> str:
    """Identify accessible platforms based on configured keys and Bird cookies."""
    _log("=== Determining available platforms ===")
    openai_ok = bool(configuration.get("OPENAI_API_KEY"))
    xai_ok = bool(configuration.get("XAI_API_KEY"))
    bird_ok = is_bird_x_available()

    x_ok = xai_ok or bird_ok

    _log(f"  OpenAI configured: {openai_ok}")
    _log(f"  xAI configured:    {xai_ok}")
    _log(f"  Bird available:     {bird_ok}")
    _log(f"  X available (xAI or Bird): {x_ok}")

    if openai_ok and x_ok:
        _log("  Result: 'both' (OpenAI + X)")
        return "both"
    elif openai_ok:
        _log("  Result: 'reddit' (OpenAI only, no X)")
        return "reddit"
    elif x_ok:
        _log("  Result: 'x' (X only, no OpenAI)")
        return "x"
    else:
        _log("  Result: 'web' (NO API keys, WebSearch fallback only)")
        return "web"


def identify_missing_credentials(configuration: Dict[str, Any]) -> str:
    """Return which API keys are absent: 'none', 'x', 'reddit', or 'both'."""
    openai_ok = bool(configuration.get("OPENAI_API_KEY"))
    xai_ok = bool(configuration.get("XAI_API_KEY"))
    bird_ok = is_bird_x_available()

    has_x = xai_ok or bird_ok

    if openai_ok and has_x:
        return "none"
    elif openai_ok:
        return "x"
    elif has_x:
        return "reddit"
    else:
        return "both"


def is_bird_x_available() -> bool:
    """Check if Bird X search is installed and authenticated."""
    try:
        from lib import bird_x

        installed = bird_x.is_bird_installed()
        authenticated = bool(bird_x.is_bird_authenticated()) if installed else False
        result = installed and authenticated
        _log(f"Bird X check: installed={installed}, authenticated={authenticated}, available={result}")
        return result
    except Exception as exc:
        _log(f"Bird X check failed with exception: {exc}")
        return False


def validate_sources(
    requested_sources: str, available_platforms: str, include_web_search: bool = False
) -> tuple[str, Optional[str]]:
    """Validate requested sources against available credentials.

    Returns (effective_sources, error_message_or_none).
    """
    _log("=== Validating sources ===")
    _log(f"  Requested: '{requested_sources}', Available: '{available_platforms}', Include web: {include_web_search}")

    # No keys at all
    if available_platforms == "web":
        if requested_sources == "auto":
            _log("  No API keys, auto -> 'web' (WebSearch fallback)")
            return "web", None
        elif requested_sources == "web":
            _log("  No API keys, web -> 'web'")
            return "web", None
        else:
            _log(f"  No API keys, requested '{requested_sources}' -> forced to 'web' with warning")
            return (
                "web",
                "No API keys found \u2014 falling back to WebSearch only. Configure keys in ~/.config/briefbot/.env to enable Reddit, X, YouTube, and LinkedIn.",
            )

    # Auto: use whatever is available
    if requested_sources == "auto":
        if include_web_search:
            mapping = {
                "both": "all",
                "reddit": "reddit-web",
                "x": "x-web",
            }
            result = mapping.get(available_platforms, available_platforms)
            _log(f"  Auto + web -> '{result}'")
            return result, None
        _log(f"  Auto -> '{available_platforms}'")
        return available_platforms, None

    # Explicit web-only
    if requested_sources == "web":
        return "web", None

    # All sources
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

    # Both explicitly
    if requested_sources == "both":
        if available_platforms != "both":
            missing_provider = "xAI" if available_platforms == "reddit" else "OpenAI"
            return (
                "none",
                f"Cannot use both sources: {missing_provider} key not configured. Try --sources=auto to use whatever is available.",
            )
        if include_web_search:
            return "all", None
        return "both", None

    # Reddit explicitly
    if requested_sources == "reddit":
        if available_platforms == "x":
            return "none", "Reddit was requested but only an xAI key is configured."
        if include_web_search:
            return "reddit-web", None
        return "reddit", None

    # X explicitly
    if requested_sources == "x":
        if available_platforms == "reddit":
            return "none", "X was requested but only an OpenAI key is configured."
        if include_web_search:
            return "x-web", None
        return "x", None

    # YouTube explicitly (needs OpenAI)
    if requested_sources == "youtube":
        if available_platforms == "x":
            return (
                "none",
                "YouTube was requested but only an xAI key is configured (YouTube requires OpenAI).",
            )
        return "youtube", None

    # LinkedIn explicitly (needs OpenAI)
    if requested_sources == "linkedin":
        if available_platforms == "x":
            return (
                "none",
                "LinkedIn was requested but only an xAI key is configured (LinkedIn requires OpenAI).",
            )
        return "linkedin", None

    # Unknown value -- pass through
    return requested_sources, None


# -- Backward-compatible aliases for external callers --
SETTINGS_DIRECTORY = CONFIG_DIR
SETTINGS_FILEPATH = CONFIG_FILE
parse_environment_file = parse_dotenv
assemble_configuration = load_config
