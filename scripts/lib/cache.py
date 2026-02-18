#
# Persistence Layer: Caching subsystem for the BriefBot skill
# Manages disk-based storage of API responses and model selections
#

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Storage location for cached artifacts
STORAGE_DIRECTORY = Path.home() / ".cache" / "briefbot"

# Time-to-live settings for different cache types
STANDARD_TTL_HOURS = 24
MODEL_SELECTION_TTL_DAYS = 7


def initialize_storage():
    """
    Creates the cache directory if it doesn't already exist.

    This is called automatically before any write operations to ensure
    the storage location is available.
    """
    STORAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)


def compute_cache_identifier(
    subject_matter: str,
    start_date: str,
    end_date: str,
    platform_selection: str
) -> str:
    """
    Generates a deterministic cache key from query parameters.

    The key is a truncated SHA-256 hash ensuring unique identification
    of each distinct query combination.
    """
    composite_data = "{}|{}|{}|{}".format(subject_matter, start_date, end_date, platform_selection)
    full_hash = hashlib.sha256(composite_data.encode()).hexdigest()
    return full_hash[:16]


def resolve_cache_filepath(cache_identifier: str) -> Path:
    """Determines the filesystem path for a given cache identifier."""
    return STORAGE_DIRECTORY / "{}.json".format(cache_identifier)


def verify_cache_validity(cache_filepath: Path, ttl_hours: int = STANDARD_TTL_HOURS) -> bool:
    """
    Checks whether a cached file exists and is within its time-to-live window.

    Returns False if the file doesn't exist, can't be accessed, or has expired.
    """
    if not cache_filepath.exists():
        return False

    try:
        file_stats = cache_filepath.stat()
        modification_time = datetime.fromtimestamp(file_stats.st_mtime, tz=timezone.utc)
        current_time = datetime.now(timezone.utc)
        elapsed_hours = (current_time - modification_time).total_seconds() / 3600
        return elapsed_hours < ttl_hours
    except OSError:
        return False


def retrieve_cached_data(cache_identifier: str, ttl_hours: int = STANDARD_TTL_HOURS) -> Optional[dict]:
    """
    Loads previously cached data if it exists and hasn't expired.

    Returns None if the cache miss occurs or data is corrupted.
    """
    cache_filepath = resolve_cache_filepath(cache_identifier)

    if not verify_cache_validity(cache_filepath, ttl_hours):
        return None

    try:
        with open(cache_filepath, 'r') as file_handle:
            return json.load(file_handle)
    except (json.JSONDecodeError, OSError):
        return None


def compute_cache_age(cache_filepath: Path) -> Optional[float]:
    """
    Calculates how many hours have elapsed since the cache file was written.

    Returns None if the file doesn't exist or can't be read.
    """
    if not cache_filepath.exists():
        return None

    try:
        file_stats = cache_filepath.stat()
        modification_time = datetime.fromtimestamp(file_stats.st_mtime, tz=timezone.utc)
        current_time = datetime.now(timezone.utc)
        return (current_time - modification_time).total_seconds() / 3600
    except OSError:
        return None


def retrieve_cached_data_with_metadata(
    cache_identifier: str,
    ttl_hours: int = STANDARD_TTL_HOURS
) -> tuple:
    """
    Retrieves cached data along with its age in hours.

    Returns a tuple of (data, age_hours). Both values are None on cache miss.
    """
    cache_filepath = resolve_cache_filepath(cache_identifier)

    if not verify_cache_validity(cache_filepath, ttl_hours):
        return None, None

    age_hours = compute_cache_age(cache_filepath)

    try:
        with open(cache_filepath, 'r') as file_handle:
            return json.load(file_handle), age_hours
    except (json.JSONDecodeError, OSError):
        return None, None


def persist_to_cache(cache_identifier: str, payload: dict):
    """
    Writes data to the cache storage.

    Failures are silently ignored to prevent cache issues from
    disrupting the main application flow.
    """
    initialize_storage()
    cache_filepath = resolve_cache_filepath(cache_identifier)

    try:
        with open(cache_filepath, 'w') as file_handle:
            json.dump(payload, file_handle)
    except OSError:
        pass


def purge_all_caches():
    """
    Removes all cached JSON files from the storage directory.

    Individual file deletion failures are ignored to ensure
    the operation completes for as many files as possible.
    """
    if not STORAGE_DIRECTORY.exists():
        return

    json_files = STORAGE_DIRECTORY.glob("*.json")
    for cached_file in json_files:
        try:
            cached_file.unlink()
        except OSError:
            pass


# Model selection persistence (uses extended TTL)
MODEL_SELECTION_FILEPATH = STORAGE_DIRECTORY / "model_selection.json"


def retrieve_model_selections() -> dict:
    """
    Loads the cached model selection preferences.

    Returns an empty dict if no valid cache exists.
    """
    ttl_hours = MODEL_SELECTION_TTL_DAYS * 24

    if not verify_cache_validity(MODEL_SELECTION_FILEPATH, ttl_hours):
        return {}

    try:
        with open(MODEL_SELECTION_FILEPATH, 'r') as file_handle:
            return json.load(file_handle)
    except (json.JSONDecodeError, OSError):
        return {}


def persist_model_selections(selection_data: dict):
    """Saves model selection preferences to disk."""
    initialize_storage()

    try:
        with open(MODEL_SELECTION_FILEPATH, 'w') as file_handle:
            json.dump(selection_data, file_handle)
    except OSError:
        pass


def get_cached_model(provider_name: str) -> Optional[str]:
    """Retrieves the cached model identifier for a specific provider."""
    selections = retrieve_model_selections()
    return selections.get(provider_name)


def set_cached_model(provider_name: str, model_identifier: str):
    """
    Stores a model selection for a provider.

    Also records the timestamp of the update for cache management.
    """
    selections = retrieve_model_selections()
    selections[provider_name] = model_identifier
    selections['updated_at'] = datetime.now(timezone.utc).isoformat()
    persist_model_selections(selections)
