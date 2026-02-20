#!/usr/bin/env python3
"""BriefBot Cookie Bridge - Native Messaging Host.

Receives X/Twitter cookies (auth_token, ct0) from the Chrome extension
via Chrome's Native Messaging protocol and writes them to briefbot's
config file at ~/.config/briefbot/.env.

Protocol: stdin/stdout with 4-byte little-endian length prefix + JSON.
"""

import json
import struct
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "briefbot"
CONFIG_FILE = CONFIG_DIR / ".env"


def read_message():
    """Read a single native messaging message from stdin."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length or len(raw_length) < 4:
        return None
    length = struct.unpack("<I", raw_length)[0]
    if length == 0 or length > 1024 * 1024:  # sanity check: max 1MB
        return None
    data = sys.stdin.buffer.read(length)
    if len(data) < length:
        return None
    return json.loads(data)


def write_message(msg):
    """Write a single native messaging message to stdout."""
    data = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def update_env_file(auth_token: str, ct0: str):
    """Write AUTH_TOKEN and CT0 to the briefbot .env config file.

    Preserves all other existing settings in the file.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing lines
    existing_lines = []
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            existing_lines = f.readlines()

    # Track which keys we've updated
    found_auth = False
    found_ct0 = False
    new_lines = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith("AUTH_TOKEN="):
            new_lines.append(f"AUTH_TOKEN={auth_token}\n")
            found_auth = True
        elif stripped.startswith("CT0="):
            new_lines.append(f"CT0={ct0}\n")
            found_ct0 = True
        else:
            new_lines.append(line)

    # Append any keys that weren't already in the file
    if not found_auth:
        new_lines.append(f"AUTH_TOKEN={auth_token}\n")
    if not found_ct0:
        new_lines.append(f"CT0={ct0}\n")

    with open(CONFIG_FILE, "w") as f:
        f.writelines(new_lines)


def main():
    msg = read_message()
    if not msg:
        write_message({"status": "error", "message": "No message received"})
        return

    auth_token = msg.get("auth_token")
    ct0 = msg.get("ct0")

    if not auth_token or not ct0:
        write_message({"status": "error", "message": "Missing auth_token or ct0"})
        return

    try:
        update_env_file(auth_token, ct0)
        write_message({"status": "ok"})
    except Exception as e:
        write_message({"status": "error", "message": str(e)})


if __name__ == "__main__":
    main()
