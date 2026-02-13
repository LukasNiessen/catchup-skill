#
# Email Delivery: Sends research reports via SMTP
# Uses stdlib smtplib for zero external dependencies
#

import mimetypes
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional


def validate_smtp_config(config: Dict[str, Any]) -> Optional[str]:
    """
    Validates that all required SMTP configuration keys are present.

    Returns None if valid, or an error message describing what's missing.
    """
    required_keys = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"]
    missing = [k for k in required_keys if not config.get(k)]

    if missing:
        return "Missing SMTP configuration: {}. Add these to ~/.config/briefbot/.env".format(
            ", ".join(missing)
        )
    return None


def _markdown_to_basic_html(markdown_text: str) -> str:
    """
    Converts markdown to basic HTML using regex.
    Handles headers, bold, italic, links, lists, and code blocks.
    No external dependencies required.
    """
    html = markdown_text

    # Escape HTML entities first
    html = html.replace("&", "&amp;")
    html = html.replace("<", "&lt;")
    html = html.replace(">", "&gt;")

    # Code blocks (``` ... ```)
    html = re.sub(
        r"```[\w]*\n(.*?)```",
        r"<pre style='background:#f4f4f4;padding:12px;border-radius:4px;overflow-x:auto;'>\1</pre>",
        html,
        flags=re.DOTALL,
    )

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code style='background:#f4f4f4;padding:2px 4px;border-radius:2px;'>\1</code>", html)

    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Links [text](url)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Unordered lists
    html = re.sub(r"^[*\-] (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r"^---+$", "<hr>", html, flags=re.MULTILINE)
    html = re.sub(r"^===+$", "<hr>", html, flags=re.MULTILINE)

    # Paragraphs: convert double newlines to paragraph breaks
    html = re.sub(r"\n\n+", "</p><p>", html)
    # Single newlines to line breaks
    html = html.replace("\n", "<br>\n")

    # Wrap in paragraph tags
    html = "<p>" + html + "</p>"

    # Clean up empty paragraphs
    html = re.sub(r"<p>\s*</p>", "", html)

    return html


def _build_email_message(
    recipient: str,
    subject: str,
    markdown_body: str,
    sender: str,
    job_id: Optional[str] = None,
    audio_path: Optional[Path] = None,
) -> MIMEMultipart:
    """
    Builds a MIME multipart email with text/plain + text/html parts
    and an optional MP3 attachment.
    """
    msg = MIMEMultipart("mixed")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    # Add footer with job info
    footer = "\n\n---\n"
    if job_id:
        footer += "Sent by BriefBot scheduled job {}\n".format(job_id)
        footer += "To stop receiving these emails, run:\n"
        footer += "  python briefbot.py --delete-job {}\n".format(job_id)
    else:
        footer += "Sent by BriefBot\n"

    full_text = markdown_body + footer

    # Create alternative part for text and HTML
    alt_part = MIMEMultipart("alternative")

    # Plain text version
    text_part = MIMEText(full_text, "plain", "utf-8")
    alt_part.attach(text_part)

    # HTML version
    html_body = _markdown_to_basic_html(full_text)
    html_content = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; color: #333;">
{}
</body>
</html>""".format(html_body)

    html_part = MIMEText(html_content, "html", "utf-8")
    alt_part.attach(html_part)

    msg.attach(alt_part)

    # Attach audio file if provided
    if audio_path and audio_path.exists():
        content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"
        maintype, subtype = content_type.split("/", 1)
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        attachment = MIMEApplication(audio_data, _subtype=subtype)
        attachment.add_header(
            "Content-Disposition", "attachment", filename=audio_path.name
        )
        msg.attach(attachment)

    return msg


def send_report_email(
    recipient: str,
    subject: str,
    markdown_body: str,
    config: Dict[str, Any],
    job_id: Optional[str] = None,
    audio_path: Optional[Path] = None,
) -> None:
    """
    Sends a research report email via SMTP.

    Args:
        recipient: Email address to send to.
        subject: Email subject line.
        markdown_body: The report content in markdown format.
        config: Configuration dict containing SMTP_* keys.
        job_id: Optional job ID for the unsubscribe footer.
        audio_path: Optional path to an MP3 file to attach.

    Raises:
        ValueError: If SMTP config is incomplete.
        smtplib.SMTPException: If sending fails.
    """
    validation_error = validate_smtp_config(config)
    if validation_error:
        raise ValueError(validation_error)

    host = config["SMTP_HOST"]
    port = int(config.get("SMTP_PORT", 587))
    user = config["SMTP_USER"]
    password = config["SMTP_PASSWORD"]
    sender = config["SMTP_FROM"]
    use_tls = str(config.get("SMTP_USE_TLS", "true")).lower() in ("true", "1", "yes")

    msg = _build_email_message(
        recipient, subject, markdown_body, sender, job_id, audio_path
    )

    if use_tls:
        server = smtplib.SMTP(host, port)
        server.starttls()
    else:
        server = smtplib.SMTP(host, port)

    try:
        server.login(user, password)
        server.sendmail(sender, [recipient], msg.as_string())
    finally:
        server.quit()
