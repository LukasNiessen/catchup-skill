"""Configuration loading and source validation."""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from . import paths


def _log(message: str):
    """Emit a debug line to stderr when BRIEFBOT_DEBUG is set."""
    if os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write(f"[CONFIG] {message}\n")
        sys.stderr.flush()


CONFIG_DIR = paths.config_dir()
CONFIG_FILE = paths.config_file()
LEGACY_CONFIG_FILE = paths.legacy_config_file()
_TRUTHY = {"1", "true", "yes", "on", "y", "t"}


def _strip_inline_comment(value: str) -> str:
    in_quote = False
    quote_char = ""
    out = []
    for ch in value:
        if ch in ("'", '"'):
            if not in_quote:
                in_quote = True
                quote_char = ch
            elif ch == quote_char:
                in_quote = False
        if ch == "#" and not in_quote:
            break
        out.append(ch)
    return "".join(out).strip()


def parse_dotenv(filepath: Path) -> Dict[str, str]:
    """Parse `.env` style file with inline-comment stripping."""
    parsed: Dict[str, str] = {}

    _log(f"Loading config from: {filepath}")

    if not filepath.exists():
        _log(f"Config file NOT FOUND at: {filepath}")
        return parsed

    _log("Config file exists, parsing...")

    with open(filepath, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            if "=" not in stripped:
                continue

            key, _, value = stripped.partition("=")
            key = key.strip()
            value = _strip_inline_comment(value.strip())

            if len(value) >= 2:
                if value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]

            if key:
                parsed[key] = value
                if "KEY" in key or "PASSWORD" in key or "TOKEN" in key:
                    if value:
                        _log(f"  Loaded: {key} = {value[:6]}...{value[-4:]} ({len(value)} chars)")
                    else:
                        _log(f"  Loaded: {key} = <empty>")
                else:
                    _log(f"  Loaded: {key} = {value}")

    _log(f"Parsed {len(parsed)} key-value pairs from config file")
    return parsed


def _pick_config_file() -> Path:
    """Resolve the config file path, preferring the new location."""
    if CONFIG_FILE.exists():
        return CONFIG_FILE
    if LEGACY_CONFIG_FILE.exists():
        _log(f"Using legacy config file at {LEGACY_CONFIG_FILE}")
        return LEGACY_CONFIG_FILE
    return CONFIG_FILE


def load_config() -> Dict[str, Any]:
    """Load config from file and environment, with env taking precedence."""
    _log("=== Assembling configuration ===")

    config_path = _pick_config_file()
    file_settings = parse_dotenv(config_path)

    env_openai = os.environ.get("OPENAI_API_KEY")
    env_xai = os.environ.get("XAI_API_KEY")
    file_openai = file_settings.get("OPENAI_API_KEY")
    file_xai = file_settings.get("XAI_API_KEY")
    _log(f"OPENAI_API_KEY: env={f'SET ({len(env_openai)} chars)' if env_openai else 'NOT SET'}, file={f'SET ({len(file_openai)} chars)' if file_openai else 'NOT SET'}")
    _log(f"XAI_API_KEY: env={f'SET ({len(env_xai)} chars)' if env_xai else 'NOT SET'}, file={f'SET ({len(file_xai)} chars)' if file_xai else 'NOT SET'}")

    key_defaults = {
        "OPENAI_MODEL_POLICY": "auto",
        "XAI_MODEL_POLICY": "latest",
        "SMTP_PORT": "587",
        "SMTP_USE_TLS": "true",
    }
    keys = [
        "OPENAI_API_KEY",
        "XAI_API_KEY",
        "OPENAI_MODEL_POLICY",
        "OPENAI_MODEL_PIN",
        "XAI_MODEL_POLICY",
        "XAI_MODEL_PIN",
        "ELEVENLABS_API_KEY",
        "ELEVENLABS_VOICE_ID",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "SMTP_USE_TLS",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    cfg = {}
    for key in keys:
        env_value = os.environ.get(key)
        file_value = file_settings.get(key)
        fallback = key_defaults.get(key)
        cfg[key] = env_value or file_value or fallback

    eff_openai = cfg.get("OPENAI_API_KEY")
    eff_xai = cfg.get("XAI_API_KEY")
    _log(f"Resolved OPENAI_API_KEY: {f'YES ({len(eff_openai)} chars, starts with {chr(39)}{eff_openai[:8]}{chr(39)})' if eff_openai else 'NO'}")
    _log(f"Resolved XAI_API_KEY: {f'YES ({len(eff_xai)} chars, starts with {chr(39)}{eff_xai[:8]}{chr(39)})' if eff_xai else 'NO'}")
    _log(f"Resolved XAI_MODEL_POLICY: {cfg.get('XAI_MODEL_POLICY')}")
    _log("=== Configuration assembly complete ===")

    return cfg


def settings_file_exists() -> bool:
    """Check whether the config file exists."""
    return CONFIG_FILE.exists() or LEGACY_CONFIG_FILE.exists()


def determine_available_platforms(configuration: Dict[str, Any]) -> str:
    """Identify accessible platforms based on configured keys.

    Returns one of: "both", "reddit", "x", "web", or "all".
    """
    _log("=== Determining available platforms ===")
    openai_ok = bool(configuration.get("OPENAI_API_KEY"))
    xai_ok = bool(configuration.get("XAI_API_KEY"))
    x_ok = xai_ok

    _log(f"  OpenAI configured: {openai_ok}")
    _log(f"  xAI configured:    {xai_ok}")
    _log(f"  X available (xAI): {x_ok}")

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
    has_x = xai_ok

    if openai_ok and has_x:
        return "none"
    elif openai_ok:
        return "x"
    elif has_x:
        return "reddit"
    else:
        return "both"




def validate_sources(
    requested_sources: str, available_platforms: str, include_web_search: bool = False
) -> Tuple[str, Optional[str]]:
    """Validate requested sources against available credentials.

    Returns (effective_sources, error_message_or_none).
    """
    _log("=== Validating sources ===")
    _log(f"  Requested: '{requested_sources}', Available: '{available_platforms}', Include web: {include_web_search}")

    if available_platforms == "web":
        if requested_sources in ("auto", "web"):
            return "web", None
        return (
            "web",
            "No API keys found. Falling back to WebSearch only. Configure ~/.config/briefbot/.env (or legacy ~/.config/briefbot/.env) to enable Reddit, X, YouTube, and LinkedIn.",
        )

    mode_map = {
        False: {"both": "both", "reddit": "reddit", "x": "x"},
        True: {"both": "all", "reddit": "reddit-web", "x": "x-web"},
    }
    if requested_sources == "auto":
        resolved = mode_map[bool(include_web_search)].get(available_platforms, available_platforms)
        return resolved, None

    if requested_sources == "web":
        return "web", None

    if requested_sources == "all":
        if available_platforms == "both":
            return "all", None
        if available_platforms == "reddit":
            return "all", "Note: X source unavailable (missing xAI key). X/Twitter will be skipped."
        if available_platforms == "x":
            return "all", "Note: OpenAI key missing; Reddit/YouTube/LinkedIn will be skipped."
        return "web", "No API keys configured."

    if requested_sources == "both":
        if available_platforms == "both":
            return ("all", None) if include_web_search else ("both", None)
        missing = "xAI" if available_platforms == "reddit" else "OpenAI"
        return "none", f"Cannot use both sources: missing {missing} credentials. Try --sources=auto for automatic fallback."

    source_requirements = {
        "reddit": "openai",
        "youtube": "openai",
        "linkedin": "openai",
        "x": "x",
    }
    requirement = source_requirements.get(requested_sources)
    if requirement == "openai" and available_platforms == "x":
        label = requested_sources.capitalize()
        return "none", f"{label} was requested but only xAI credentials are configured."
    if requirement == "x" and available_platforms == "reddit":
        return "none", "X source requires an xAI credential, but only an OpenAI key was found."

    if requested_sources == "reddit":
        return ("reddit-web", None) if include_web_search else ("reddit", None)
    return requested_sources, None

