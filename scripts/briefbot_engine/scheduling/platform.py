#
# OS Scheduler Integration: Registers/unregisters jobs with crontab or schtasks
# Cross-platform support for Linux/macOS (crontab) and Windows (schtasks)
#

import platform
import subprocess
from pathlib import Path
from typing import Any, Dict

from . import cron
from .. import locations


# Tag format used to identify briefbot entries in crontab
CRONTAB_TAG_PREFIX = "# briefbot:"

# Task name prefix for Windows schtasks
SCHTASKS_PREFIX = "briefbot_"


def _is_windows() -> bool:
    """Returns True if running on Windows."""
    return platform.system() == "Windows"


def register_job(job: Dict[str, Any], runner_path: Path) -> str:
    """
    Registers a job with the OS scheduler.

    Args:
        job: Job dict from the registry (must contain id, schedule, python_executable).
        runner_path: Absolute path to the run_job.py script.

    Returns:
        A description of what was registered.

    Raises:
        RuntimeError: If registration fails.
    """
    if _is_windows():
        return _register_schtasks(job, runner_path)
    else:
        return _register_crontab(job, runner_path)


def unregister_job(job: Dict[str, Any]) -> str:
    """
    Removes a job from the OS scheduler.

    Args:
        job: Job dict from the registry (must contain id, schedule).

    Returns:
        A description of what was removed.

    Raises:
        RuntimeError: If removal fails.
    """
    if _is_windows():
        return _unregister_schtasks(job)
    else:
        return _unregister_crontab(job)


def _register_crontab(job: Dict[str, Any], runner_path: Path) -> str:
    """Adds a tagged crontab entry for this job."""
    job_id = job["id"]
    schedule = job["schedule"]
    python_exe = job["python_executable"]
    tag = "{}{}".format(CRONTAB_TAG_PREFIX, job_id)

    # Build the cron line
    log_dir = locations.logs_dir()
    cron_command = '{} "{}" {} >> "{}/{}.log" 2>&1'.format(
        python_exe, runner_path, job_id, str(log_dir).replace('"', ""), job_id
    )
    cron_line = "{} {} {}".format(schedule, cron_command, tag)

    # Read existing crontab
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        )
        existing_lines = result.stdout.strip().split("\n") if result.returncode == 0 else []
    except FileNotFoundError:
        raise RuntimeError("crontab command not found. Is cron installed?")

    # Remove any existing entry for this job
    filtered_lines = [line for line in existing_lines if tag not in line]

    # Add the new entry
    filtered_lines.append(cron_line)

    # Write back
    new_crontab = "\n".join(filtered_lines) + "\n"
    result = subprocess.run(
        ["crontab", "-"], input=new_crontab, capture_output=True, text=True
    )

    if result.returncode != 0:
        raise RuntimeError("Failed to update crontab: {}".format(result.stderr.strip()))

    description = cron.describe_schedule(cron.parse_cron_expression(schedule))
    return "Registered crontab entry: {} ({})".format(job_id, description)


def _unregister_crontab(job: Dict[str, Any]) -> str:
    """Removes the tagged crontab entry for this job."""
    job_id = job["id"]
    tag = "{}{}".format(CRONTAB_TAG_PREFIX, job_id)

    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return "No crontab entries found."
        existing_lines = result.stdout.strip().split("\n")
    except FileNotFoundError:
        return "crontab command not found."

    filtered_lines = [line for line in existing_lines if tag not in line]

    if len(filtered_lines) == len(existing_lines):
        return "No crontab entry found for {}".format(job_id)

    # Write back (handle empty crontab)
    if all(not line.strip() for line in filtered_lines):
        # Remove crontab entirely if empty
        subprocess.run(["crontab", "-r"], capture_output=True, text=True)
    else:
        new_crontab = "\n".join(filtered_lines) + "\n"
        subprocess.run(
            ["crontab", "-"], input=new_crontab, capture_output=True, text=True
        )

    return "Removed crontab entry for {}".format(job_id)


def _register_schtasks(job: Dict[str, Any], runner_path: Path) -> str:
    """Creates a Windows scheduled task for this job."""
    job_id = job["id"]
    schedule = job["schedule"]
    python_exe = job["python_executable"]
    task_name = "{}{}".format(SCHTASKS_PREFIX, job_id)

    parsed = cron.parse_cron_expression(schedule)
    schtasks_args = cron.cron_to_schtasks_args(parsed)

    # Build the command that schtasks will run
    task_command = '"{}" "{}" {}'.format(python_exe, runner_path, job_id)

    # Construct schtasks /Create command
    cmd = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", task_command,
    ] + schtasks_args + ["/F"]  # /F forces overwrite of existing task

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            "Failed to create scheduled task: {}".format(result.stderr.strip())
        )

    description = cron.describe_schedule(parsed)
    return "Registered Windows task: {} ({})".format(task_name, description)


def _unregister_schtasks(job: Dict[str, Any]) -> str:
    """Deletes a Windows scheduled task for this job."""
    job_id = job["id"]
    task_name = "{}{}".format(SCHTASKS_PREFIX, job_id)

    cmd = ["schtasks", "/Delete", "/TN", task_name, "/F"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "does not exist" in stderr.lower() or "cannot find" in stderr.lower():
            return "No scheduled task found for {}".format(job_id)
        raise RuntimeError("Failed to delete scheduled task: {}".format(stderr))

    return "Removed Windows task: {}".format(task_name)

