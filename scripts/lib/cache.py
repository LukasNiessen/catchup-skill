"""Disk-based caching for API responses and model preferences."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

CACHE_DIR = Path.home() / ".cache" / "briefbot"
DEFAULT_TTL = 24
MODEL_TTL_DAYS = 7


def _ensure_dir():
    """Create the cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_key(topic: str, start: str, end: str, platform: str) -> str:
    """Generate a deterministic 16-char hash key from query parameters."""
    raw = f"{topic}|{start}|{end}|{platform}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def cache_path(key: str) -> Path:
    """Return the filesystem path for a cache key."""
    return CACHE_DIR / f"{key}.json"


def is_valid(filepath: Path, ttl_hours: int = DEFAULT_TTL) -> bool:
    """Check whether a cache file exists and hasn't expired."""
    if not filepath.exists():
        return False

    try:
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
        return elapsed < ttl_hours
    except OSError:
        return False


def load(key: str, ttl_hours: int = DEFAULT_TTL) -> Optional[dict]:
    """Load cached data if it exists and is fresh, else None."""
    fp = cache_path(key)

    if not is_valid(fp, ttl_hours):
        return None

    try:
        with open(fp, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def age_hours(filepath: Path) -> Optional[float]:
    """Return hours since the cache file was last written, or None."""
    if not filepath.exists():
        return None

    try:
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
    except OSError:
        return None


def load_with_age(key: str, ttl_hours: int = DEFAULT_TTL) -> tuple:
    """Return (data, age_hours) tuple; both None on cache miss."""
    fp = cache_path(key)

    if not is_valid(fp, ttl_hours):
        return None, None

    hours = age_hours(fp)

    try:
        with open(fp, 'r') as f:
            return json.load(f), hours
    except (json.JSONDecodeError, OSError):
        return None, None


def save(key: str, data: dict):
    """Write data to cache. Failures are silently ignored."""
    _ensure_dir()
    fp = cache_path(key)

    try:
        with open(fp, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass


def clear_all():
    """Remove all cached JSON files."""
    if not CACHE_DIR.exists():
        return

    for f in CACHE_DIR.glob("*.json"):
        try:
            f.unlink()
        except OSError:
            pass


# Model preference persistence (extended TTL)
_MODEL_FILE = CACHE_DIR / "model_selection.json"


def _load_model_prefs() -> dict:
    """Load cached model preferences, or empty dict if stale/missing."""
    ttl_hours = MODEL_TTL_DAYS * 24

    if not is_valid(_MODEL_FILE, ttl_hours):
        return {}

    try:
        with open(_MODEL_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_model_prefs(data: dict):
    """Save model preferences to disk."""
    _ensure_dir()

    try:
        with open(_MODEL_FILE, 'w') as f:
            json.dump(data, f)
    except OSError:
        pass


def get_cached_model(provider_name: str) -> Optional[str]:
    """Retrieve the cached model identifier for a provider."""
    return _load_model_prefs().get(provider_name)


def set_cached_model(provider_name: str, model_identifier: str):
    """Store a model selection for a provider with a timestamp."""
    prefs = _load_model_prefs()
    prefs[provider_name] = model_identifier
    prefs['updated_at'] = datetime.now(timezone.utc).isoformat()
    _save_model_prefs(prefs)
