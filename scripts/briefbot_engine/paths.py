"""Shared filesystem locations for BriefBot."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _env_path(name: str) -> Optional[Path]:
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    return Path(value).expanduser()


def root_dir() -> Path:
    """Return the base directory for BriefBot config/logs/jobs."""
    override = _env_path("BRIEFBOT_HOME") or _env_path("BRIEFBOT_ROOT")
    if override:
        return override
    return Path.home() / ".config" / "briefbot"


def config_dir() -> Path:
    return root_dir()


def config_file() -> Path:
    return config_dir() / ".env"


def legacy_config_file() -> Path:
    return config_file()


def data_dir() -> Path:
    return Path.home() / ".local" / "share" / "briefbot"


def output_dir() -> Path:
    return data_dir() / "out"


def logs_dir() -> Path:
    return root_dir() / "logs"


def jobs_file() -> Path:
    return root_dir() / "jobs.json"
