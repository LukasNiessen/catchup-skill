#
# Job Registry: CRUD operations for scheduled BriefBot jobs
# Persists job records at ~/.config/briefbot/jobs.json
#

import json
import os
import random
import string
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import paths


JOBS_DIRECTORY = paths.root_dir()
JOBS_FILEPATH = paths.jobs_file()


def _generate_job_id() -> str:
    """Generates a unique job ID like 'cu_A1B2C3'."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return "cu_{}".format(suffix)


def _load_jobs_file(filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Loads the jobs registry from disk. Returns empty list if file doesn't exist."""
    path = filepath or JOBS_FILEPATH
    if not path.exists():
        return []
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def _save_jobs_file(jobs: List[Dict[str, Any]], filepath: Optional[Path] = None) -> None:
    """Atomically writes the jobs registry to disk using temp file + rename."""
    path = filepath or JOBS_FILEPATH
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in the same directory, then rename for atomicity
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix="jobs_"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(jobs, f, indent=2)
        # On Windows, os.rename fails if destination exists; use os.replace
        os.replace(tmp_path, str(path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def resolve_python_executable() -> str:
    """Returns the absolute path to the current Python interpreter."""
    return sys.executable


def create_job(
    topic: str,
    schedule: str,
    email: str,
    args_dict: Dict[str, Any],
    python_executable: Optional[str] = None,
    filepath: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Creates a new scheduled job and persists it to the registry.

    Args:
        topic: The research topic.
        schedule: Cron expression string (e.g., "0 6 * * *").
        email: Recipient email address.
        args_dict: Captured CLI arguments (quick, deep, audio, days, sources, etc.).
        python_executable: Path to python interpreter. Defaults to current sys.executable.
        filepath: Override jobs file path (for testing).

    Returns:
        The created job dict with generated ID and timestamps.
    """
    job_id = _generate_job_id()
    now = datetime.now(timezone.utc).isoformat()

    job = {
        "id": job_id,
        "topic": topic,
        "schedule": schedule,
        "email": email,
        "args": args_dict,
        "python_executable": python_executable or resolve_python_executable(),
        "created_at": now,
        "last_run": None,
        "last_status": None,
        "last_error": None,
        "run_count": 0,
    }

    jobs = _load_jobs_file(filepath)
    jobs.append(job)
    _save_jobs_file(jobs, filepath)

    return job


def list_jobs(filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Returns all registered jobs."""
    return _load_jobs_file(filepath)


def get_job(job_id: str, filepath: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Returns a specific job by ID, or None if not found."""
    jobs = _load_jobs_file(filepath)
    for job in jobs:
        if job["id"] == job_id:
            return job
    return None


def delete_job(job_id: str, filepath: Optional[Path] = None) -> bool:
    """
    Removes a job from the registry.

    Returns True if the job was found and removed, False otherwise.
    """
    jobs = _load_jobs_file(filepath)
    original_count = len(jobs)
    jobs = [j for j in jobs if j["id"] != job_id]

    if len(jobs) == original_count:
        return False

    _save_jobs_file(jobs, filepath)
    return True


def update_job_run_status(
    job_id: str,
    status: str,
    error: Optional[str] = None,
    filepath: Optional[Path] = None,
) -> bool:
    """
    Updates a job's last run information.

    Args:
        job_id: The job ID to update.
        status: Run status string (e.g., "success", "error").
        error: Error message if the run failed.
        filepath: Override jobs file path (for testing).

    Returns:
        True if the job was found and updated, False otherwise.
    """
    jobs = _load_jobs_file(filepath)
    now = datetime.now(timezone.utc).isoformat()

    for job in jobs:
        if job["id"] == job_id:
            job["last_run"] = now
            job["last_status"] = status
            job["last_error"] = error
            job["run_count"] = job.get("run_count", 0) + 1
            _save_jobs_file(jobs, filepath)
            return True

    return False


