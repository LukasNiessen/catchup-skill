#!/usr/bin/env python3
#
# Scheduled Job Runner: Opens Claude Code and runs the /briefbot skill
# Invoked by cron/schtasks: python run_job.py <job_id>
#
# This script ensures the EXACT SAME entry point as interactive /briefbot usage:
#   1. Loads the job from ~/.config/briefbot/jobs.json
#   2. Shows an info banner so the user knows what's happening
#   3. Reconstructs the /briefbot command from the job record
#   4. Launches `claude "/briefbot ..." --dangerously-skip-permissions`
#      in interactive mode — the skill loads and runs identically to manual usage
#   5. Updates job run status in the registry
#   6. Logs everything to ~/.config/briefbot/logs/<job_id>.log
#
# Cross-platform:
#   - Windows (schtasks): subprocess.Popen() inherits the console TTY;
#     a threading.Timer injects Enter to auto-accept the bypass prompt
#   - Linux/macOS (crontab): pty.fork() creates a pseudo-terminal;
#     a daemon thread injects Enter to auto-accept the bypass prompt
#

import logging
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

# Ensure library modules are discoverable
MODULE_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MODULE_ROOT))

from briefbot_engine.scheduling import cron, jobs


LOG_DIRECTORY = Path.home() / ".config" / "briefbot" / "logs"

BANNER_PAUSE_SECONDS = 15

# Module-level logger — set up once run_job() calls setup_logging()
log = logging.getLogger("briefbot.job")


def setup_logging(job_id: str) -> logging.Logger:
    """Configures file-based logging for this job run."""
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIRECTORY / "{}.log".format(job_id)

    logger = logging.getLogger("briefbot.job.{}".format(job_id))
    logger.setLevel(logging.INFO)

    # File handler (append mode)
    file_handler = logging.FileHandler(str(log_path), mode="a")
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    )
    logger.addHandler(file_handler)

    return logger


def _clean_env(logger=None):
    """Return a copy of the environment without CLAUDECODE so subprocesses
    don't think they are nested inside another Claude Code session."""
    had_var = "CLAUDECODE" in os.environ
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    if had_var and logger:
        logger.info("_clean_env: stripped CLAUDECODE from subprocess environment")
    return env


def find_claude_cli() -> str:
    """
    Locates the claude CLI executable.

    Returns the path to claude, or raises RuntimeError if not found.
    """
    claude_path = shutil.which("claude")
    if claude_path:
        return claude_path

    raise RuntimeError(
        "Claude Code CLI not found on PATH. "
        "Install it (https://docs.anthropic.com/en/docs/claude-code) "
        "or ensure 'claude' is on your PATH."
    )


def _build_briefbot_args(job: dict) -> list:
    """
    Builds the argument list for the /briefbot skill from a job record.
    """
    args = ['"{}"'.format(job["topic"].replace('"', '\\"'))]
    job_args = job.get("args", {})

    if job_args.get("quick"):
        args.append("--quick")
    elif job_args.get("deep"):
        args.append("--deep")

    days = job_args.get("days", 30)
    if days != 30:
        args.append("--days={}".format(days))

    sources = job_args.get("sources", "auto")
    if sources != "auto":
        args.append("--sources={}".format(sources))

    if job_args.get("include_web"):
        args.append("--include-web")

    if job_args.get("audio"):
        args.append("--audio")

    if job.get("email"):
        args.append("--email {}".format(job["email"]))

    telegram = job_args.get("telegram")
    if telegram:
        if telegram == "__default__":
            args.append("--telegram")
        else:
            args.append("--telegram {}".format(telegram))

    return args


def build_skill_command(job: dict) -> str:
    """
    Reconstructs the /briefbot command exactly as a user would type it.
    """
    return "/briefbot " + " ".join(_build_briefbot_args(job))


def print_banner(job: dict, skill_command: str) -> None:
    """
    Prints a prominent info banner to the terminal so the user
    knows this window was opened by a scheduled BriefBot job.
    """
    job_id = job["id"]
    topic = job["topic"]
    schedule_raw = job["schedule"]
    email = job.get("email", "")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        parsed = cron.parse_cron_expression(schedule_raw)
        schedule_desc = cron.describe_schedule(parsed)
    except ValueError:
        schedule_desc = schedule_raw

    border = "=" * 66

    lines = [
        "",
        border,
        "  BRIEFBOT SCHEDULED JOB",
        border,
        "",
        "  Job ID:    {}".format(job_id),
        "  Topic:     {}".format(topic),
        "  Schedule:  {} ({})".format(schedule_raw, schedule_desc),
    ]

    if email:
        lines.append("  Email:     {}".format(email))

    lines.extend([
        "  Fired at:  {}".format(now_str),
        "",
        "  Command:   {}".format(skill_command),
        "",
        border,
        "",
        "  This window was opened by a scheduled BriefBot job.",
        "  You may MINIMIZE this window, but do NOT close it.",
        "  It will close automatically when the job finishes.",
        "",
        border,
        "",
    ])

    print("\n".join(lines), flush=True)

    for remaining in range(BANNER_PAUSE_SECONDS, 0, -1):
        print("  Starting in {}...".format(remaining), end="\r", flush=True)
        time.sleep(1)

    print("  Starting now.    ", flush=True)
    print("", flush=True)


def _send_enter_windows():
    """Inject an Enter keypress into the Windows console input buffer."""
    import ctypes
    from ctypes import wintypes, byref, Structure, Union

    class CHAR_UNION(Union):
        _fields_ = [("UnicodeChar", ctypes.c_wchar),
                     ("AsciiChar", ctypes.c_char)]

    class KEY_EVENT_RECORD(Structure):
        _fields_ = [("bKeyDown", ctypes.c_int),
                     ("wRepeatCount", ctypes.c_ushort),
                     ("wVirtualKeyCode", ctypes.c_ushort),
                     ("wVirtualScanCode", ctypes.c_ushort),
                     ("uChar", CHAR_UNION),
                     ("dwControlKeyState", ctypes.c_ulong)]

    class EVENT_UNION(Union):
        _fields_ = [("KeyEvent", KEY_EVENT_RECORD)]

    class INPUT_RECORD(Structure):
        _fields_ = [("EventType", ctypes.c_ushort),
                     ("Event", EVENT_UNION)]

    handle = ctypes.windll.kernel32.GetStdHandle(
        ctypes.c_ulong(0xFFFFFFF6)  # STD_INPUT_HANDLE (-10)
    )
    written = ctypes.c_ulong()

    for key_down in (True, False):
        rec = INPUT_RECORD()
        rec.EventType = 0x0001  # KEY_EVENT
        rec.Event.KeyEvent.bKeyDown = int(key_down)
        rec.Event.KeyEvent.wRepeatCount = 1
        rec.Event.KeyEvent.wVirtualKeyCode = 0x0D   # VK_RETURN
        rec.Event.KeyEvent.wVirtualScanCode = 0x1C
        rec.Event.KeyEvent.uChar.UnicodeChar = '\r'
        rec.Event.KeyEvent.dwControlKeyState = 0
        ctypes.windll.kernel32.WriteConsoleInputW(
            handle, byref(rec), 1, byref(written)
        )


def _run_claude_windows(claude_exe: str, skill_command: str) -> int:
    """
    Launches Claude Code on Windows by inheriting the console TTY.

    Windows schtasks opens a real console window, so subprocess.Popen()
    with inherited stdio gives Claude a real TTY — identical to a user
    opening cmd.exe and typing the command.

    A threading.Timer injects an Enter keypress after 3 seconds to
    auto-accept the --dangerously-skip-permissions confirmation prompt.
    """
    full_args = [claude_exe, skill_command, "--dangerously-skip-permissions"]
    log.info("_run_claude_windows: spawning Popen: %s", full_args)
    log.info("_run_claude_windows: CLAUDECODE in env: %s", "CLAUDECODE" in os.environ)
    proc = subprocess.Popen(
        full_args,
        env=_clean_env(log),
    )
    log.info("_run_claude_windows: process started, pid=%d — injecting Enter in 3s", proc.pid)
    # After 3s, inject Enter to accept the bypass prompt
    timer = threading.Timer(3.0, _send_enter_windows)
    timer.start()
    rc = proc.wait()
    timer.cancel()  # No-op if already fired
    log.info("_run_claude_windows: process exited — returncode=%d", rc)
    return rc


def _run_claude_unix(claude_exe: str, skill_command: str) -> int:
    """
    Launches Claude Code on Linux/macOS using a pseudo-terminal.

    Cron runs headlessly with no TTY. Claude Code's Ink TUI requires
    raw mode on stdin, which needs a real terminal. Python's pty module
    creates a pseudo-terminal so Claude sees a real TTY — identical to
    a user opening a terminal and typing the command.

    A daemon thread injects an Enter keypress after 3 seconds to
    auto-accept the --dangerously-skip-permissions confirmation prompt.
    """
    import os
    import pty

    log.info("_run_claude_unix: forking pty for Claude Code")
    log.info("_run_claude_unix: CLAUDECODE in env: %s", "CLAUDECODE" in os.environ)
    pid, fd = pty.fork()

    if pid == 0:
        # Child process — becomes Claude Code with a real PTY
        # Strip CLAUDECODE env var to avoid nested-session detection
        os.environ.pop("CLAUDECODE", None)
        os.execvp(
            claude_exe,
            [claude_exe, skill_command, "--dangerously-skip-permissions"],
        )
        # execvp never returns on success; exit if it somehow fails
        os._exit(127)

    log.info("_run_claude_unix: child pid=%d, reading PTY output", pid)

    # Inject Enter after 3s to accept bypass prompt
    def send_enter():
        time.sleep(3)
        try:
            os.write(fd, b"\r")
        except OSError:
            pass

    enter_thread = threading.Thread(target=send_enter, daemon=True)
    enter_thread.start()

    # Parent process — read PTY output until Claude exits
    try:
        while True:
            try:
                data = os.read(fd, 4096)
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except OSError:
                break
    finally:
        os.close(fd)

    # Wait for child to exit and extract return code
    _, status = os.waitpid(pid, 0)

    if os.WIFEXITED(status):
        rc = os.WEXITSTATUS(status)
        log.info("_run_claude_unix: child exited normally — returncode=%d", rc)
        return rc
    log.error("_run_claude_unix: child did not exit normally — status=%d", status)
    return 1


def run_claude(claude_exe: str, skill_command: str) -> int:
    """
    Launches Claude Code interactively with the /briefbot skill command.

    Uses `claude "<skill_command>" --dangerously-skip-permissions` which:
      - Starts Claude in interactive mode (skills load, full TUI)
      - Submits the /briefbot command as the initial message
      - Skips all permission prompts for unattended execution

    Platform-specific TTY handling:
      - Windows: inherits console TTY from schtasks
      - Linux/macOS: creates a pseudo-terminal via pty.fork()
    """
    plat = platform.system()
    log.info("run_claude called — platform=%s, claude_exe=%s, skill_command=%r", plat, claude_exe, skill_command)
    if plat == "Windows":
        return _run_claude_windows(claude_exe, skill_command)
    else:
        return _run_claude_unix(claude_exe, skill_command)


def run_job(job_id: str) -> None:
    """
    Executes a scheduled research job by launching Claude Code
    and running the /briefbot skill — the exact same entry point
    as interactive usage.
    """
    logger = setup_logging(job_id)
    logger.info("=" * 60)
    logger.info("Starting scheduled run for job %s", job_id)

    # Load job record
    job = jobs.get_job(job_id)
    if job is None:
        logger.error("Job %s not found in registry", job_id)
        print("Error: Job {} not found".format(job_id), file=sys.stderr)
        sys.exit(1)

    logger.info("Topic: %s", job["topic"])
    logger.info("Schedule: %s", job["schedule"])
    logger.info("Email: %s", job.get("email", ""))

    try:
        claude_exe = find_claude_cli()
        logger.info("Claude CLI: %s", claude_exe)

        skill_command = build_skill_command(job)
        logger.info("Skill command: %s", skill_command)

        # Show the info banner and countdown
        print_banner(job, skill_command)

        # Launch Claude Code interactively with the /briefbot skill
        logger.info("Launching Claude Code (interactive mode)...")
        logger.info("Platform: %s", platform.system())
        return_code = run_claude(claude_exe, skill_command)
        logger.info("Claude exited with code %d", return_code)

        # Update job status
        if return_code == 0:
            jobs.update_job_run_status(job_id, "success")
            logger.info("Job %s completed successfully", job_id)
        else:
            error_msg = "Claude exited with code {}".format(return_code)
            logger.error("Job %s failed: %s", job_id, error_msg)
            jobs.update_job_run_status(job_id, "error", error=error_msg)
            sys.exit(1)

    except Exception as exc:
        error_msg = "{}: {}".format(type(exc).__name__, exc)
        logger.error("Job %s failed: %s", job_id, error_msg)
        logger.error(traceback.format_exc())
        jobs.update_job_run_status(job_id, "error", error=error_msg)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_job.py <job_id>", file=sys.stderr)
        sys.exit(1)

    run_job(sys.argv[1])
