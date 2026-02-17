#!/usr/bin/env python3
#
# Telegram Bot Listener: Receives research requests via Telegram messages
# and runs the full BriefBot pipeline, sending results back to the chat.
#
# Usage:
#     python scripts/telegram_bot.py                  # Start the bot (foreground)
#     python scripts/telegram_bot.py start             # Start the bot (background)
#     python scripts/telegram_bot.py stop              # Stop the background bot
#     python scripts/telegram_bot.py status            # Check if bot is running
#     python scripts/telegram_bot.py pair list         # Show pending pairing requests
#     python scripts/telegram_bot.py pair approve CODE # Approve a pairing request
#     python scripts/telegram_bot.py pair revoke ID    # Remove a chat from the whitelist
#
# Then text the bot on Telegram:
#     @BotName ai news
#     @BotName best python libs --deep
#     @BotName crypto --audio --days=7
#

import json
import logging
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure library modules are discoverable
MODULE_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MODULE_ROOT))

from lib import env, telegram_sender

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = Path.home() / ".config" / "briefbot" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_DIR / "telegram_bot.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger("briefbot.telegram_bot")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLL_TIMEOUT = 30  # seconds (Telegram long-polling)
RECOGNIZED_FLAGS = {"--audio", "--deep", "--quick", "--include-web"}
RECOGNIZED_KV_FLAGS = {"--days", "--sources"}  # flags that take =VALUE

# Additional @usernames the bot responds to (lowercase, without @)
EXTRA_USERNAMES = ["ALPHAGORILLADRAGONBOT"]

PAIRINGS_FILE = Path.home() / ".config" / "briefbot" / "pairings.json"
ENV_FILE = Path.home() / ".config" / "briefbot" / ".env"

HELP_TEXT = (
    "Mention me with a topic and I'll research it.\n\n"
    "Examples:\n"
    "  @{bot} ai news\n"
    "  @{bot} best python frameworks --deep\n"
    "  @{bot} crypto trends --audio --days=7\n\n"
    "Flags:\n"
    "  --audio       Generate audio briefing\n"
    "  --deep        Comprehensive research\n"
    "  --quick       Faster, fewer sources\n"
    "  --days=N      Search last N days (default 30)\n"
    "  --sources=X   Source filter (auto/reddit/x/all)\n"
    "  --include-web Include general web search\n"
)

# ---------------------------------------------------------------------------
# Pairing persistence
# ---------------------------------------------------------------------------

_pairings_lock = threading.Lock()


def _load_pairings() -> dict:
    """Loads pending pairing requests from disk."""
    if not PAIRINGS_FILE.exists():
        return {}
    try:
        return json.loads(PAIRINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_pairings(pairings: dict) -> None:
    """Writes pending pairing requests to disk."""
    PAIRINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PAIRINGS_FILE.write_text(
        json.dumps(pairings, indent=2), encoding="utf-8"
    )


def _generate_code() -> str:
    """Generates a short alphanumeric pairing code."""
    return secrets.token_hex(3).upper()  # 6 hex chars, e.g. "A3F1B2"


def create_pairing(chat_id: str, user_info: dict) -> str:
    """
    Creates a pending pairing for an unknown chat.

    If a pending pairing already exists for this chat_id, returns the
    existing code instead of generating a new one.

    Returns the pairing code.
    """
    with _pairings_lock:
        pairings = _load_pairings()

        # Check if this chat already has a pending code
        for code, entry in pairings.items():
            if str(entry.get("chat_id")) == str(chat_id):
                return code

        code = _generate_code()
        pairings[code] = {
            "chat_id": str(chat_id),
            "username": user_info.get("username", ""),
            "first_name": user_info.get("first_name", ""),
            "last_name": user_info.get("last_name", ""),
            "requested_at": datetime.now().isoformat(timespec="seconds"),
        }
        _save_pairings(pairings)
        return code


def approve_pairing(code: str) -> dict:
    """
    Approves a pending pairing by code.

    Removes it from pairings.json and appends the chat_id to
    TELEGRAM_CHAT_ID in the .env file.

    Returns the pairing entry, or raises ValueError if not found.
    """
    with _pairings_lock:
        pairings = _load_pairings()
        code_upper = code.upper()

        if code_upper not in pairings:
            raise ValueError("Pairing code '{}' not found".format(code))

        entry = pairings.pop(code_upper)
        _save_pairings(pairings)

    # Append chat_id to TELEGRAM_CHAT_ID in .env
    _add_chat_id_to_env(entry["chat_id"])
    return entry


def revoke_chat_id(chat_id: str) -> None:
    """
    Removes a chat_id from the TELEGRAM_CHAT_ID whitelist in .env.

    Also removes any pending pairing for that chat.
    """
    # Remove from pending pairings
    with _pairings_lock:
        pairings = _load_pairings()
        to_remove = [
            code for code, e in pairings.items()
            if str(e.get("chat_id")) == str(chat_id)
        ]
        for code in to_remove:
            del pairings[code]
        if to_remove:
            _save_pairings(pairings)

    # Remove from .env
    _remove_chat_id_from_env(chat_id)


def _add_chat_id_to_env(chat_id: str) -> None:
    """Appends a chat_id to the TELEGRAM_CHAT_ID value in .env."""
    if not ENV_FILE.exists():
        return

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TELEGRAM_CHAT_ID") and "=" in stripped:
            found = True
            key, _, value = stripped.partition("=")
            value = value.strip().strip("\"'")
            existing = {v.strip() for v in value.split(",") if v.strip()}
            if str(chat_id) not in existing:
                existing.add(str(chat_id))
            new_lines.append("{}={}".format(key.strip(), ",".join(sorted(existing))))
        else:
            new_lines.append(line)

    if not found:
        new_lines.append("TELEGRAM_CHAT_ID={}".format(chat_id))

    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _remove_chat_id_from_env(chat_id: str) -> None:
    """Removes a chat_id from the TELEGRAM_CHAT_ID value in .env."""
    if not ENV_FILE.exists():
        return

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TELEGRAM_CHAT_ID") and "=" in stripped:
            key, _, value = stripped.partition("=")
            value = value.strip().strip("\"'")
            existing = {v.strip() for v in value.split(",") if v.strip()}
            existing.discard(str(chat_id))
            if existing:
                new_lines.append("{}={}".format(key.strip(), ",".join(sorted(existing))))
            # If empty, drop the line entirely
        else:
            new_lines.append(line)

    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _load_allowed_chat_ids() -> set:
    """Reads the current whitelist from .env (live reload)."""
    config = env.get_config()
    raw = config.get("TELEGRAM_CHAT_ID", "")
    return {cid.strip() for cid in raw.split(",") if cid.strip()}


# ---------------------------------------------------------------------------
# CLI: pair subcommands
# ---------------------------------------------------------------------------


def cli_pair_list() -> None:
    """Lists all pending pairing requests."""
    pairings = _load_pairings()

    if not pairings:
        print("No pending pairing requests.")
        print("\nWhen someone messages the bot, they'll get a pairing code.")
        return

    print("Pending pairing requests:\n")
    for code, entry in pairings.items():
        name_parts = [entry.get("first_name", ""), entry.get("last_name", "")]
        display_name = " ".join(p for p in name_parts if p) or "(no name)"
        username = entry.get("username", "")
        username_str = " @{}".format(username) if username else ""

        print("  Code:       {}".format(code))
        print("  Chat ID:    {}".format(entry["chat_id"]))
        print("  User:       {}{}".format(display_name, username_str))
        print("  Requested:  {}".format(entry.get("requested_at", "?")))
        print()

    print("To approve:  python telegram_bot.py pair approve CODE")


def cli_pair_approve(code: str) -> None:
    """Approves a pending pairing request by code."""
    try:
        entry = approve_pairing(code)
    except ValueError as err:
        print("Error: {}".format(err), file=sys.stderr)
        sys.exit(1)

    name_parts = [entry.get("first_name", ""), entry.get("last_name", "")]
    display_name = " ".join(p for p in name_parts if p) or "(no name)"
    username = entry.get("username", "")

    print("Approved! Chat {} is now whitelisted.".format(entry["chat_id"]))
    print("  User: {}{}".format(
        display_name,
        " @{}".format(username) if username else "",
    ))
    print("\nThe bot will pick up the new whitelist automatically.")

    # Try to notify the user on Telegram
    config = env.get_config()
    token = config.get("TELEGRAM_BOT_TOKEN")
    if token:
        try:
            _send_message(
                token, entry["chat_id"],
                "You've been approved! Send me a topic to research.\n"
                "Type /help for usage info.",
            )
            print("Sent approval notification to Telegram.")
        except Exception:
            pass  # Non-critical


def cli_pair_revoke(chat_id: str) -> None:
    """Removes a chat_id from the whitelist."""
    revoke_chat_id(chat_id)
    print("Chat {} removed from whitelist.".format(chat_id))


# ---------------------------------------------------------------------------
# Telegram API helpers
# ---------------------------------------------------------------------------


def _get_me(token: str) -> str:
    """Calls getMe to retrieve the bot's username. Returns lowercase username."""
    url = "https://api.telegram.org/bot{}/getMe".format(token)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as err:
        log.error("getMe failed: %s", err)
        sys.exit(1)

    if not data.get("ok"):
        log.error("getMe not ok: %s", data.get("description"))
        sys.exit(1)

    username = data["result"].get("username", "")
    if not username:
        log.error("Bot has no username set")
        sys.exit(1)

    return username.lower()


def _is_bot_mentioned(text: str, bot_usernames: list, message: dict) -> bool:
    """
    Checks whether the bot is directly addressed in a message.

    Returns True if:
      - The chat is private (1-on-1 with the bot — always addressed)
      - The text contains any of the recognized @usernames (case-insensitive)
      - The message has entities that mention any recognized username
    """
    chat_type = message.get("chat", {}).get("type", "")
    if chat_type == "private":
        return True

    text_lower = text.lower()

    # Check plain-text @mention for any recognized username
    for username in bot_usernames:
        if "@{}".format(username) in text_lower:
            return True

    # Check entities (Telegram marks @mentions and /command@bot as entities)
    for entity in message.get("entities", []):
        if entity.get("type") == "mention":
            offset = entity["offset"]
            length = entity["length"]
            mention = text[offset : offset + length].lower().lstrip("@")
            if mention in bot_usernames:
                return True

    return False


def _strip_mentions(text: str, bot_usernames: list) -> str:
    """Removes all recognized @botusername variants from the message text."""
    for username in bot_usernames:
        text = re.sub(r"@" + re.escape(username), "", text, flags=re.IGNORECASE)
    return text.strip()


def _get_updates(token: str, offset: int) -> list:
    """Fetches new messages via Telegram getUpdates long-polling."""
    params = urllib.parse.urlencode(
        {
            "offset": offset,
            "timeout": POLL_TIMEOUT,
            "allowed_updates": json.dumps(["message"]),
        }
    )
    url = "https://api.telegram.org/bot{}/getUpdates?{}".format(token, params)

    try:
        with urllib.request.urlopen(url, timeout=POLL_TIMEOUT + 10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as err:
        log.warning("getUpdates failed: %s", err)
        return []

    if not data.get("ok"):
        log.warning("getUpdates not ok: %s", data.get("description"))
        return []

    return data.get("result", [])


def _send_message(token: str, chat_id: str, text: str) -> None:
    """Sends a plain-text message to a Telegram chat."""
    telegram_sender._call_telegram_api(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
        },
    )


# ---------------------------------------------------------------------------
# Message parsing
# ---------------------------------------------------------------------------


def parse_message(text: str) -> tuple:
    """
    Parses a Telegram message into (topic, flags_string).

    Everything before the first -- flag is the topic.
    Recognized flags are passed through verbatim.

    Returns:
        (topic, flags_string) — e.g. ("ai news", "--audio --days=7")
    """
    words = text.strip().split()
    topic_parts = []
    flag_parts = []

    for word in words:
        if word.startswith("--"):
            flag_parts.append(word)
        else:
            # Only add to topic if we haven't hit any flags yet
            if not flag_parts:
                topic_parts.append(word)
            else:
                # Words after flags — treat as part of topic (unlikely but safe)
                topic_parts.append(word)

    topic = " ".join(topic_parts).strip()
    flags = " ".join(flag_parts).strip()
    return topic, flags


# ---------------------------------------------------------------------------
# Research execution
# ---------------------------------------------------------------------------


def find_claude_cli() -> str:
    """Locates the claude CLI executable, or returns None for lite mode."""
    return shutil.which("claude")


def run_research_full(claude_exe: str, topic: str, flags: str, chat_id: str) -> str:
    """
    Runs the full BriefBot pipeline via Claude CLI.

    Returns stdout/stderr output for logging, or raises on failure.
    """
    cmd = "/briefbot {} {} --telegram {}".format(topic, flags, chat_id).strip()
    # Collapse multiple spaces
    while "  " in cmd:
        cmd = cmd.replace("  ", " ")

    log.info('Running: claude -p "%s" --dangerously-skip-permissions', cmd)

    result = subprocess.run(
        [claude_exe, "-p", cmd, "--dangerously-skip-permissions"],
        capture_output=True,
        text=True,
        timeout=600,  # 10 minute max
    )

    output = (result.stdout or "") + (result.stderr or "")

    if result.returncode != 0:
        raise RuntimeError(
            "Claude exited with code {} — {}".format(
                result.returncode, output[-500:] if output else "(no output)"
            )
        )

    return output


def run_research_lite(topic: str, flags: str, chat_id: str, config: dict) -> None:
    """
    Lite-mode fallback: runs briefbot.py directly, then delivers via Telegram.

    Used when the Claude CLI is not available on PATH.
    """
    # Build briefbot.py arguments
    briefbot_script = MODULE_ROOT / "briefbot.py"
    cmd = [sys.executable, str(briefbot_script), topic, "--emit=md"]

    # Parse flags into individual args
    for flag in flags.split():
        if flag.strip():
            cmd.append(flag.strip())

    log.info("Lite mode: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute max
    )

    if result.returncode != 0:
        raise RuntimeError(
            "briefbot.py exited with code {} — {}".format(
                result.returncode,
                (result.stderr or "")[-500:] or "(no output)",
            )
        )

    md_output = result.stdout.strip()
    if not md_output:
        raise RuntimeError("briefbot.py produced no output")

    # Deliver via Telegram
    telegram_sender.send_telegram_message(
        chat_id=chat_id,
        markdown_body=md_output,
        subject="BriefBot: {}".format(topic),
        config=config,
    )


def handle_research(
    token: str,
    chat_id: str,
    topic: str,
    flags: str,
    claude_exe: str,
    config: dict,
) -> None:
    """
    Executes research and sends results. Runs inside a thread pool.

    On error, sends an error message to the chat.
    """
    try:
        if claude_exe:
            run_research_full(claude_exe, topic, flags, chat_id)
        else:
            run_research_lite(topic, flags, chat_id, config)
        log.info("Research complete for topic: %s", topic)
    except subprocess.TimeoutExpired:
        log.error("Research timed out for topic: %s", topic)
        _send_message(token, chat_id, "Research timed out for: {}".format(topic))
    except Exception as err:
        log.error("Research failed for '%s': %s", topic, err)
        _send_message(
            token,
            chat_id,
            "Research failed for '{}': {}".format(topic, str(err)[:300]),
        )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    # Load config
    config = env.get_config()
    token = config.get("TELEGRAM_BOT_TOKEN")

    if not token:
        log.error("TELEGRAM_BOT_TOKEN not set. Add it to ~/.config/briefbot/.env")
        sys.exit(1)

    # Load initial whitelist (live-reloaded on each message)
    allowed_chat_ids = _load_allowed_chat_ids()
    if not allowed_chat_ids:
        log.warning(
            "TELEGRAM_CHAT_ID is empty — bot will only issue pairing codes "
            "until you approve someone"
        )

    # Learn the bot's own username (for @mention detection)
    bot_username = _get_me(token)
    bot_usernames = list({bot_username} | {u for u in EXTRA_USERNAMES})
    log.info("Listening to mentions: %s", ", ".join("@" + u for u in bot_usernames))

    # Locate Claude CLI
    claude_exe = find_claude_cli()
    if claude_exe:
        log.info("Claude CLI found: %s", claude_exe)
    else:
        log.warning("Claude CLI not found — running in lite mode (no synthesis)")

    if allowed_chat_ids:
        log.info("Whitelisted chats: %s", ", ".join(sorted(allowed_chat_ids)))
    log.info("Listening...")

    offset = 0
    executor = ThreadPoolExecutor(max_workers=2)

    try:
        while True:
            updates = _get_updates(token, offset)

            for update in updates:
                update_id = update.get("update_id", 0)
                offset = update_id + 1

                message = update.get("message")
                if not message:
                    continue

                chat = message.get("chat", {})
                chat_id = str(chat.get("id", ""))
                chat_type = chat.get("type", "")
                text = (message.get("text") or "").strip()
                from_user = message.get("from", {})

                if not text:
                    continue

                # Reload whitelist from .env on every message so approvals
                # take effect without restarting the bot
                allowed_chat_ids = _load_allowed_chat_ids()

                # Unknown chat → pairing flow (private chats only)
                if chat_id not in allowed_chat_ids:
                    if chat_type == "private":
                        code = create_pairing(chat_id, from_user)
                        log.info(
                            "Pairing code %s issued to chat %s (@%s)",
                            code, chat_id, from_user.get("username", "?"),
                        )
                        _send_message(
                            token, chat_id,
                            "You're not authorized yet.\n\n"
                            "Your pairing code: {}\n\n"
                            "Ask the bot owner to run:\n"
                            "  python telegram_bot.py pair approve {}".format(code, code),
                        )
                    else:
                        log.warning(
                            "Ignored message from unknown chat %s: %s",
                            chat_id, text[:50],
                        )
                    continue

                # Only respond when the bot is directly mentioned (or in private chat)
                if not _is_bot_mentioned(text, bot_usernames, message):
                    continue

                # Strip all recognized @mentions from the text before parsing
                text = _strip_mentions(text, bot_usernames)

                log.info("Received: %s", text)

                if not text:
                    continue

                # Handle commands (with and without @suffix)
                cmd = text.lower().split("@")[0]  # "/help@BotName" → "/help"
                if cmd in ("/start",):
                    _send_message(
                        token,
                        chat_id,
                        "Welcome to BriefBot! Mention me with a topic to research.\n\n"
                        "Type /help for usage info.",
                    )
                    continue

                if cmd in ("/help",):
                    _send_message(
                        token, chat_id, HELP_TEXT.replace("{bot}", bot_username)
                    )
                    continue

                # Ignore other / commands
                if text.startswith("/"):
                    _send_message(
                        token,
                        chat_id,
                        "Unknown command. Type /help for usage info.",
                    )
                    continue

                # Parse topic and flags
                topic, flags = parse_message(text)

                if not topic:
                    _send_message(
                        token,
                        chat_id,
                        "Please provide a topic. Example: ai news --deep",
                    )
                    continue

                # Acknowledge
                _send_message(token, chat_id, "Researching {}...".format(topic))

                # Run research in background thread
                executor.submit(
                    handle_research,
                    token,
                    chat_id,
                    topic,
                    flags,
                    claude_exe,
                    config,
                )

    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        executor.shutdown(wait=False)
        log.info("Bye.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]

    # Subcommand: pair
    if args and args[0] == "pair":
        sub = args[1] if len(args) > 1 else ""

        if sub == "list":
            cli_pair_list()
        elif sub == "approve" and len(args) > 2:
            cli_pair_approve(args[2])
        elif sub == "revoke" and len(args) > 2:
            cli_pair_revoke(args[2])
        else:
            print("Usage:")
            print("  python telegram_bot.py pair list            Show pending requests")
            print("  python telegram_bot.py pair approve CODE    Approve a pairing")
            print("  python telegram_bot.py pair revoke CHAT_ID  Remove a chat from whitelist")
            sys.exit(1)

    # Subcommands: start / stop / status (delegate to setup.py lifecycle)
    elif args and args[0] == "start":
        from setup import bot_start
        ok, msg = bot_start()
        print(msg)
        sys.exit(0 if ok else 1)

    elif args and args[0] == "stop":
        from setup import bot_stop
        ok, msg = bot_stop()
        print(msg)
        sys.exit(0 if ok else 1)

    elif args and args[0] == "status":
        from setup import bot_status
        running, pid = bot_status()
        if running:
            print("Telegram bot is RUNNING (PID {})".format(pid))
        else:
            print("Telegram bot is not running")
        sys.exit(0)

    else:
        main()
