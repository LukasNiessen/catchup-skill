#!/usr/bin/env python3
#
# BriefBot Setup Wizard: Interactive configuration for all settings
#
# Usage:
#     python setup.py                 # Run the full interactive setup wizard
#     python setup.py --show          # Show current config (non-interactive)
#     python setup.py --set K=V ...   # Set one or more config values
#     python setup.py --unset K ...   # Remove one or more config values
#     python setup.py --start-bot     # Start the Telegram bot listener
#     python setup.py --stop-bot      # Stop the Telegram bot listener
#     python setup.py --bot-status    # Check Telegram bot listener status
#

import os
import platform
import signal
import subprocess
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure library modules are discoverable
MODULE_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MODULE_ROOT))

from lib import env

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".config" / "briefbot"
ENV_FILE = CONFIG_DIR / ".env"
PID_FILE = CONFIG_DIR / "telegram_bot.pid"
BOT_SCRIPT = MODULE_ROOT / "telegram_bot.py"

# Configuration sections — each is (section_title, list_of_fields)
# Fields: (key, label, is_secret, default_value_or_None, help_text)
CONFIG_SECTIONS = [
    (
        "Research API Keys",
        [
            ("OPENAI_API_KEY", "OpenAI API Key", True, None,
             "For Reddit, YouTube, LinkedIn research (uses OpenAI's web_search tool)"),
            ("XAI_API_KEY", "xAI API Key", True, None,
             "For X/Twitter research (uses xAI's x_search tool)"),
        ],
    ),
    (
        "Audio (Optional)",
        [
            ("ELEVENLABS_API_KEY", "ElevenLabs API Key", True, None,
             "For premium TTS audio (--audio flag). Falls back to edge-tts if not set"),
            ("ELEVENLABS_VOICE_ID", "ElevenLabs Voice ID", False, None,
             "Specific voice to use (leave blank for default)"),
        ],
    ),
    (
        "Email Delivery (Optional)",
        [
            ("SMTP_HOST", "SMTP Host", False, None,
             "e.g. smtp.gmail.com"),
            ("SMTP_PORT", "SMTP Port", False, "587",
             "Usually 587 for TLS"),
            ("SMTP_USER", "SMTP Username", False, None,
             "Your email login (e.g. you@gmail.com)"),
            ("SMTP_PASSWORD", "SMTP Password", True, None,
             "For Gmail: use an App Password, not your regular password"),
            ("SMTP_FROM", "SMTP From Address", False, None,
             "Optional — defaults to SMTP_USER if not set"),
            ("SMTP_USE_TLS", "Use TLS", False, "true",
             "true or false"),
        ],
    ),
    (
        "Telegram (Optional)",
        [
            ("TELEGRAM_BOT_TOKEN", "Bot Token", True, None,
             "Create a bot via @BotFather on Telegram"),
            ("TELEGRAM_CHAT_ID", "Default Chat ID", False, None,
             "Comma-separated for multiple. Get yours via @userinfobot"),
        ],
    ),
    (
        "X/Twitter Browser Cookies (Optional)",
        [
            ("AUTH_TOKEN", "Auth Token (cookie)", True, None,
             "For Bird X search — extract from browser DevTools"),
            ("CT0", "CT0 (cookie)", True, None,
             "For Bird X search — extract from browser DevTools"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_value(value: str, is_secret: bool) -> str:
    """
    Returns a display-safe representation of a config value.

    Secrets show first 3 and last 3 chars with *** in between.
    Non-secrets show the full value.
    """
    if not value:
        return "not set"

    if not is_secret:
        return value

    if len(value) <= 8:
        return value[:2] + "***"

    return value[:3] + "***" + value[-3:]


def _read_current_env() -> dict:
    """
    Reads the raw .env file into a dict, preserving all keys
    (including those with empty values, unlike env.parse_environment_file
    which skips empties).
    """
    values = {}

    if not ENV_FILE.exists():
        return values

    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, _, val = stripped.partition("=")
            key = key.strip()
            val = val.strip()
            # Remove quotes
            if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
                val = val[1:-1]
            values[key] = val

    return values


def _write_env(values: dict) -> None:
    """
    Writes the config dict to the .env file with section comments.

    Preserves only non-empty values. Creates the config directory if needed.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    lines = ["# BriefBot Configuration", "# Generated by setup wizard", ""]

    for section_title, fields in CONFIG_SECTIONS:
        section_lines = []
        for key, label, _is_secret, _default, _help in fields:
            val = values.get(key, "")
            if val:
                section_lines.append("{}={}".format(key, val))

        if section_lines:
            lines.append("# {}".format(section_title))
            lines.extend(section_lines)
            lines.append("")

    # Preserve any unknown keys that were in the original file
    known_keys = set()
    for _, fields in CONFIG_SECTIONS:
        for key, *_ in fields:
            known_keys.add(key)

    unknown_lines = []
    for key, val in values.items():
        if key not in known_keys and val:
            unknown_lines.append("{}={}".format(key, val))

    if unknown_lines:
        lines.append("# Other")
        lines.extend(unknown_lines)
        lines.append("")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Secure the file on Unix
    if sys.platform != "win32":
        os.chmod(str(ENV_FILE), 0o600)


def _print_summary_table(values: dict):
    """
    Prints a full configuration summary table grouped by section.
    """
    config = env.get_config()
    available = env.get_available_sources(config)

    mode_descriptions = {
        "both": "Full mode (Reddit + X + YouTube + LinkedIn + Web)",
        "reddit": "OpenAI mode (Reddit + YouTube + LinkedIn + Web)",
        "x": "X-only mode (X/Twitter + Web)",
        "web": "Web-only mode (WebSearch fallback)",
    }

    running, pid = bot_status()

    print()
    print("  Research mode:  {}".format(mode_descriptions.get(available, available)))
    print("  Telegram bot:   {}".format(
        "running (PID {})".format(pid) if running else "stopped"
    ))
    print()

    # Compute column widths
    all_rows = []
    for section_title, fields in CONFIG_SECTIONS:
        for key, label, is_secret, _default, _help in fields:
            val = values.get(key, "")
            display = _mask_value(val, is_secret)
            all_rows.append((section_title, key, display))

    max_key = max(len(r[1]) for r in all_rows)
    max_val = max(len(r[2]) for r in all_rows)
    # Minimum widths
    max_key = max(max_key, 7)  # "Setting"
    max_val = max(max_val, 5)  # "Value"

    divider = "  +-{}-+-{}-+".format("-" * max_key, "-" * max_val)
    header = "  | {} | {} |".format("Setting".ljust(max_key), "Value".ljust(max_val))

    last_section = None
    for section_title, key, display in all_rows:
        if section_title != last_section:
            if last_section is not None:
                print(divider)
                print()
            print("  {}".format(section_title))
            print(divider)
            print(header)
            print(divider)
            last_section = section_title

        print("  | {} | {} |".format(key.ljust(max_key), display.ljust(max_val)))

    print(divider)
    print()


def _prompt_value(key: str, label: str, is_secret: bool, current: str, help_text: str) -> str:
    """
    Prompts the user for a single config value.

    Returns the new value (may be same as current if user pressed Enter).
    Returns empty string if user typed 'clear'.
    """
    masked = _mask_value(current, is_secret)

    # Build the prompt line
    if current:
        prompt_str = "  {} [{}]: ".format(label, masked)
    else:
        prompt_str = "  {} (not set): ".format(label)

    # Show help text
    print("  # {}".format(help_text))

    try:
        user_input = input(prompt_str).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return current

    if not user_input:
        # Keep current value
        return current

    if user_input.lower() == "clear":
        return ""

    return user_input


# ---------------------------------------------------------------------------
# Telegram bot lifecycle
# ---------------------------------------------------------------------------


def _get_bot_pid() -> int:
    """Reads the PID from the PID file. Returns 0 if not found."""
    if not PID_FILE.exists():
        return 0

    try:
        pid = int(PID_FILE.read_text().strip())
        return pid
    except (ValueError, OSError):
        return 0


def _is_process_alive(pid: int) -> bool:
    """Checks if a process with the given PID is running."""
    if pid <= 0:
        return False

    if sys.platform == "win32":
        # Use tasklist to check
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "PID eq {}".format(pid), "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in result.stdout
        except Exception:
            return False
    else:
        # Unix: send signal 0
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def bot_status() -> tuple:
    """
    Returns (is_running: bool, pid: int).
    """
    pid = _get_bot_pid()
    if pid and _is_process_alive(pid):
        return True, pid

    # Stale PID file — clean up
    if PID_FILE.exists() and pid:
        PID_FILE.unlink(missing_ok=True)

    return False, 0


def bot_start() -> tuple:
    """
    Starts the Telegram bot in the background.

    Returns (success: bool, message: str).
    """
    running, pid = bot_status()
    if running:
        return False, "Bot is already running (PID {})".format(pid)

    # Validate config
    config = env.get_config()
    if not config.get("TELEGRAM_BOT_TOKEN"):
        return False, "TELEGRAM_BOT_TOKEN not set. Run setup first."

    python_exe = sys.executable
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        # Windows: use START to spawn a detached process
        # CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS flags
        process = subprocess.Popen(
            [python_exe, str(BOT_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )
        pid = process.pid
    else:
        # Unix: use nohup-style daemonization
        process = subprocess.Popen(
            [python_exe, str(BOT_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        pid = process.pid

    # Write PID file
    PID_FILE.write_text(str(pid), encoding="utf-8")

    return True, "Bot started (PID {})".format(pid)


def bot_stop() -> tuple:
    """
    Stops the Telegram bot.

    Returns (success: bool, message: str).
    """
    running, pid = bot_status()
    if not running:
        return False, "Bot is not running"

    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, timeout=10,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception as err:
        return False, "Failed to stop bot: {}".format(err)

    PID_FILE.unlink(missing_ok=True)
    return True, "Bot stopped (was PID {})".format(pid)


# ---------------------------------------------------------------------------
# Non-interactive commands (for Claude / scripting)
# ---------------------------------------------------------------------------


def show_config():
    """
    Prints the current configuration in a structured, readable format.

    Non-interactive — designed for Claude to read and present to the user.
    """
    current = _read_current_env()
    config = env.get_config()
    available = env.get_available_sources(config)

    mode_descriptions = {
        "both": "Full mode (Reddit + X + YouTube + LinkedIn + Web)",
        "reddit": "OpenAI mode (Reddit + YouTube + LinkedIn + Web)",
        "x": "X-only mode (X/Twitter + Web)",
        "web": "Web-only mode (WebSearch fallback)",
    }

    print("BRIEFBOT_CONFIG_START")
    print("config_file={}".format(ENV_FILE))
    print("research_mode={}".format(mode_descriptions.get(available, available)))

    running, pid = bot_status()
    print("telegram_bot={}".format("running (PID {})".format(pid) if running else "stopped"))

    print()

    for section_title, fields in CONFIG_SECTIONS:
        print("[{}]".format(section_title))

        for key, label, is_secret, default, help_text in fields:
            val = current.get(key, "")
            masked = _mask_value(val, is_secret)
            status = "set" if val else "not set"
            print("  {}={} | {} | {}".format(key, masked, status, help_text))

        print()

    print("BRIEFBOT_CONFIG_END")


def set_values(pairs: list):
    """
    Sets one or more config values from KEY=VALUE pairs.

    If VALUE is empty (KEY=), the key is removed.
    """
    current = _read_current_env()

    for pair in pairs:
        if "=" not in pair:
            print("Error: Invalid format '{}'. Use KEY=VALUE".format(pair), file=sys.stderr)
            sys.exit(1)

        key, _, value = pair.partition("=")
        key = key.strip()
        value = value.strip()

        if value:
            current[key] = value
            print("Set {}".format(key))
        else:
            current.pop(key, None)
            print("Cleared {}".format(key))

    _write_env(current)
    print("Configuration saved.")


def unset_values(keys: list):
    """Removes one or more config keys."""
    current = _read_current_env()

    for key in keys:
        key = key.strip()
        if key in current:
            del current[key]
            print("Cleared {}".format(key))
        else:
            print("{} was not set".format(key))

    _write_env(current)
    print("Configuration saved.")


# ---------------------------------------------------------------------------
# Setup wizard
# ---------------------------------------------------------------------------


def run_setup():
    """Runs the interactive setup wizard."""
    print()
    print("=" * 50)
    print("  BriefBot Setup")
    print("=" * 50)
    print()
    print("  Config file: {}".format(ENV_FILE))
    print()
    print("  For each setting:")
    print("    Enter   = keep current value")
    print("    type    = set new value")
    print("    clear   = remove the value")
    print()

    # Load current values
    current = _read_current_env()
    updated = dict(current)

    for section_title, fields in CONFIG_SECTIONS:
        print("--- {} ---".format(section_title))
        print()

        for key, label, is_secret, default, help_text in fields:
            current_val = current.get(key, "")
            new_val = _prompt_value(key, label, is_secret, current_val, help_text)
            if new_val:
                updated[key] = new_val
            elif key in updated:
                del updated[key]

        print()

    # Telegram bot listener section
    print("--- Telegram Bot Listener ---")
    print()

    running, pid = bot_status()
    if running:
        print("  Status: RUNNING (PID {})".format(pid))
    else:
        print("  Status: not running")

    # Only offer bot control if token is configured
    has_token = bool(updated.get("TELEGRAM_BOT_TOKEN"))

    if has_token:
        if running:
            try:
                answer = input("  Stop the bot? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
                print()

            if answer in ("y", "yes"):
                ok, msg = bot_stop()
                print("  {}".format(msg))
        else:
            try:
                answer = input("  Start the bot? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
                print()

            if answer in ("y", "yes"):
                # Save config first so the bot can read it
                _write_env(updated)
                ok, msg = bot_start()
                print("  {}".format(msg))
    else:
        print("  (Set TELEGRAM_BOT_TOKEN above to enable the bot listener)")

    print()

    # Save
    _write_env(updated)

    print()
    print("=" * 50)
    print("  Configuration saved to {}".format(ENV_FILE))
    print("=" * 50)

    # Show full configuration table
    _print_summary_table(updated)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]

    if "--show" in args:
        show_config()
        sys.exit(0)

    if "--set" in args:
        idx = args.index("--set")
        pairs = args[idx + 1:]
        if not pairs:
            print("Usage: setup.py --set KEY=VALUE [KEY=VALUE ...]", file=sys.stderr)
            sys.exit(1)
        set_values(pairs)
        sys.exit(0)

    if "--unset" in args:
        idx = args.index("--unset")
        keys = args[idx + 1:]
        if not keys:
            print("Usage: setup.py --unset KEY [KEY ...]", file=sys.stderr)
            sys.exit(1)
        unset_values(keys)
        sys.exit(0)

    if "--start-bot" in args:
        ok, msg = bot_start()
        print(msg)
        sys.exit(0 if ok else 1)

    if "--stop-bot" in args:
        ok, msg = bot_stop()
        print(msg)
        sys.exit(0 if ok else 1)

    if "--bot-status" in args:
        running, pid = bot_status()
        if running:
            print("Telegram bot is RUNNING (PID {})".format(pid))
        else:
            print("Telegram bot is not running")
        sys.exit(0)

    run_setup()


if __name__ == "__main__":
    main()
