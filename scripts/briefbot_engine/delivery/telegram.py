#
# Telegram Delivery: Sends research reports via the Telegram Bot API
# Uses stdlib urllib for zero external dependencies
#

import json
import re
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional


# Telegram message length limit
MAX_MESSAGE_LENGTH = 4096


def validate_telegram_config(config: Dict[str, Any]) -> Optional[str]:
    """
    Validates that the required Telegram configuration key is present.

    TELEGRAM_CHAT_ID is optional here — it can be provided via CLI override.

    Returns None if valid, or an error message describing what's missing.
    """
    if not config.get("TELEGRAM_BOT_TOKEN"):
        return "Missing TELEGRAM_BOT_TOKEN. Add it to ~/.config/briefbot/.env"
    return None


def _call_telegram_api(
    token: str,
    method: str,
    params: Optional[Dict[str, str]] = None,
    files: Optional[Dict[str, Path]] = None,
) -> dict:
    """
    Low-level Telegram Bot API caller using urllib.

    Args:
        token: Bot API token.
        method: API method name (e.g., 'sendMessage', 'sendDocument').
        params: Form fields to include in the request.
        files: Dict of field_name -> file_path for file uploads.

    Returns:
        Parsed JSON response from the Telegram API.

    Raises:
        RuntimeError: If the API returns an error.
    """
    url = "https://api.telegram.org/bot{}/{}".format(token, method)

    if files:
        # Multipart form-data for file uploads
        boundary = "----BriefBotBoundary9876543210"
        body_parts = []

        # Add text params
        if params:
            for key, value in params.items():
                body_parts.append("--{}".format(boundary).encode())
                body_parts.append(
                    'Content-Disposition: form-data; name="{}"'.format(key).encode()
                )
                body_parts.append(b"")
                body_parts.append(str(value).encode("utf-8"))

        # Add file parts
        for field_name, file_path in files.items():
            file_path = Path(file_path)
            body_parts.append("--{}".format(boundary).encode())
            body_parts.append(
                'Content-Disposition: form-data; name="{}"; filename="{}"'.format(
                    field_name, file_path.name
                ).encode()
            )
            body_parts.append(b"Content-Type: application/octet-stream")
            body_parts.append(b"")
            body_parts.append(file_path.read_bytes())

        body_parts.append("--{}--".format(boundary).encode())
        body = b"\r\n".join(body_parts)

        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "multipart/form-data; boundary={}".format(boundary),
            },
        )
    else:
        # Simple URL-encoded form for text-only requests
        data = urllib.parse.urlencode(params or {}).encode("utf-8")
        request = urllib.request.Request(url, data=data)

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        try:
            error_body = json.loads(err.read().decode("utf-8"))
            description = error_body.get("description", str(err))
        except Exception:
            description = str(err)
        raise RuntimeError("Telegram API error: {}".format(description))
    except urllib.error.URLError as err:
        raise RuntimeError("Telegram network error: {}".format(err.reason))

    if not result.get("ok"):
        raise RuntimeError(
            "Telegram API error: {}".format(result.get("description", "Unknown error"))
        )

    return result


def _markdown_to_telegram_html(markdown_text: str) -> str:
    """
    Converts markdown to Telegram-safe HTML.

    Telegram supports a limited HTML subset: <b>, <i>, <a>, <code>, <pre>.
    Unsupported tags are stripped. HTML entities in the source text are escaped.
    """
    html = markdown_text

    # Escape HTML entities first (preserve markdown syntax)
    html = html.replace("&", "&amp;")
    html = html.replace("<", "&lt;")
    html = html.replace(">", "&gt;")

    # Code blocks (``` ... ```)
    html = re.sub(
        r"```[\w]*\n(.*?)```",
        r"<pre>\1</pre>",
        html,
        flags=re.DOTALL,
    )

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Headers — convert to bold (Telegram has no header tags)
    html = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    html = re.sub(r"\*(.+?)\*", r"<i>\1</i>", html)

    # Links [text](url)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Horizontal rules — replace with a thin line
    thin_line = "\u2500" * 20
    html = re.sub(r"^---+$", thin_line, html, flags=re.MULTILINE)
    html = re.sub(r"^===+$", thin_line, html, flags=re.MULTILINE)

    # List items — keep as-is with bullet character
    bullet = "\u2022"
    html = re.sub(r"^[*\-] (.+)$", bullet + r" \1", html, flags=re.MULTILINE)

    return html.strip()


def _split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Splits a long message into chunks that fit within Telegram's limit.

    Tries to split on double-newlines (paragraphs) first, then single
    newlines, then hard-truncates as a last resort.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try to split at a paragraph boundary
        split_pos = remaining.rfind("\n\n", 0, max_length)
        if split_pos == -1:
            # Try single newline
            split_pos = remaining.rfind("\n", 0, max_length)
        if split_pos == -1:
            # Hard truncate
            split_pos = max_length

        chunks.append(remaining[:split_pos])
        remaining = remaining[split_pos:].lstrip("\n")

    return chunks


def send_telegram_message(
    chat_id: str,
    markdown_body: str,
    subject: str,
    config: Dict[str, Any],
    audio_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
) -> None:
    """
    Sends a briefing to a Telegram chat.

    Sends the text (split if >4096 chars), then sends audio and PDF
    as documents if provided.

    Args:
        chat_id: Telegram chat ID to send to.
        markdown_body: The report content in markdown format.
        subject: Briefing subject line (used as header).
        config: Configuration dict containing TELEGRAM_BOT_TOKEN.
        audio_path: Optional path to an MP3 file to send.
        pdf_path: Optional path to a PDF file to send.

    Raises:
        ValueError: If Telegram config is incomplete.
        RuntimeError: If the Telegram API returns an error.
    """
    validation_error = validate_telegram_config(config)
    if validation_error:
        raise ValueError(validation_error)

    token = config["TELEGRAM_BOT_TOKEN"]

    # Build the full message with subject header
    full_text = "<b>{}</b>\n\n{}".format(
        subject.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
        _markdown_to_telegram_html(markdown_body),
    )

    # Split and send text messages
    chunks = _split_message(full_text)
    for chunk in chunks:
        _call_telegram_api(token, "sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        })

    # Send audio file as document
    if audio_path and Path(audio_path).exists():
        _call_telegram_api(
            token,
            "sendDocument",
            {"chat_id": chat_id, "caption": "Audio briefing"},
            {"document": Path(audio_path)},
        )

    # Send PDF as document
    if pdf_path and Path(pdf_path).exists():
        _call_telegram_api(
            token,
            "sendDocument",
            {"chat_id": chat_id, "caption": "PDF briefing"},
            {"document": Path(pdf_path)},
        )
