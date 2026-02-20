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
from typing import Any, Dict, List, Optional


def validate_smtp_config(config: Dict[str, Any]) -> Optional[str]:
    """
    Validates that all required SMTP configuration keys are present.

    SMTP_FROM is optional — defaults to SMTP_USER when not set.

    Returns None if valid, or an error message describing what's missing.
    """
    required_keys = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"]
    missing = [k for k in required_keys if not config.get(k)]

    if missing:
        return "Missing SMTP configuration: {}. Add these to ~/.config/briefbot/.env".format(
            ", ".join(missing)
        )
    return None


def _markdown_to_news_html(markdown_text: str) -> str:
    """
    Converts markdown to polished news-site-style HTML for email.
    Handles headers, bold, italic, links (styled as inline citations),
    lists, code blocks, and horizontal rules.
    No external dependencies required.
    """
    html = markdown_text

    # Escape HTML entities first (but preserve markdown syntax chars)
    html = html.replace("&", "&amp;")
    html = html.replace("<", "&lt;")
    html = html.replace(">", "&gt;")

    # Code blocks (``` ... ```)
    html = re.sub(
        r"```[\w]*\n(.*?)```",
        r'<pre style="background:#f8f9fa;padding:14px 16px;border-radius:6px;'
        r'overflow-x:auto;font-size:13px;line-height:1.5;border:1px solid #e9ecef;'
        r'font-family:Consolas,Monaco,monospace;">\1</pre>',
        html,
        flags=re.DOTALL,
    )

    # Inline code
    html = re.sub(
        r"`([^`]+)`",
        r'<code style="background:#f0f1f3;padding:2px 6px;border-radius:3px;'
        r'font-size:0.9em;font-family:Consolas,Monaco,monospace;">\1</code>',
        html,
    )

    # Headers — white text on dark background for dark-mode resilience
    html = re.sub(
        r"^### (.+)$",
        r'<h3 style="font-size:16px;font-weight:700;color:#ffffff;margin:24px 0 8px 0;'
        r'padding:8px 12px;background:#1a1a2e;border-radius:4px;line-height:1.3;">\1</h3>',
        html,
        flags=re.MULTILINE,
    )
    html = re.sub(
        r"^## (.+)$",
        r'<h2 style="font-size:20px;font-weight:700;color:#ffffff;margin:32px 0 12px 0;'
        r'padding:10px 14px;background:linear-gradient(135deg,#1a1a2e,#0f3460);border-radius:6px;line-height:1.3;">\1</h2>',
        html,
        flags=re.MULTILINE,
    )
    html = re.sub(
        r"^# (.+)$",
        r'<h1 style="font-size:26px;font-weight:800;color:#ffffff;margin:0 0 16px 0;'
        r'padding:12px 16px;background:linear-gradient(135deg,#1a1a2e,#0f3460);border-radius:8px;line-height:1.2;">\1</h1>',
        html,
        flags=re.MULTILINE,
    )

    # Bold and italic
    html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Links [text](url) — styled as inline citations / source links
    html = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" style="color:#4361ee;text-decoration:none;'
        r'border-bottom:1px solid #4361ee40;">\1</a>',
        html,
    )

    # Unordered list items
    html = re.sub(
        r"^[*\-] (.+)$",
        r'<li style="margin-bottom:6px;line-height:1.6;">\1</li>',
        html,
        flags=re.MULTILINE,
    )

    # Wrap consecutive <li> in <ul>
    html = re.sub(
        r"((?:<li[^>]*>.*?</li>\s*)+)",
        r'<ul style="padding-left:20px;margin:12px 0;">\1</ul>',
        html,
        flags=re.DOTALL,
    )

    # Horizontal rules — styled divider
    html = re.sub(
        r"^---+$",
        '<hr style="border:none;border-top:1px solid #e0e0e0;margin:28px 0;">',
        html,
        flags=re.MULTILINE,
    )
    html = re.sub(
        r"^===+$",
        '<hr style="border:none;border-top:1px solid #e0e0e0;margin:28px 0;">',
        html,
        flags=re.MULTILINE,
    )

    # Paragraphs: double newlines become paragraph breaks
    html = re.sub(r"\n\n+", "</p><p>", html)
    # Single newlines to line breaks
    html = html.replace("\n", "<br>\n")

    # Wrap in paragraph tags
    html = "<p>" + html + "</p>"

    # Clean up empty paragraphs
    html = re.sub(r"<p>\s*</p>", "", html)

    # Style all paragraphs
    html = html.replace("<p>", '<p style="margin:0 0 14px 0;line-height:1.7;color:#2d2d2d;">')

    return html


def build_newsletter_html(subject: str, markdown_body: str) -> str:
    """
    Builds the full HTML newsletter document from markdown content.

    Returns the complete HTML string — used for both email delivery and PDF
    generation so the PDF mirrors the email layout exactly.
    """
    import datetime

    date_str = datetime.date.today().strftime("%B %d, %Y")
    html_body = _markdown_to_news_html(markdown_body)

    return """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">

<!-- Outer wrapper for background color -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;">
<tr><td align="center" style="padding:24px 16px;">

<!-- Main card -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">

<!-- Header banner -->
<tr>
<td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);padding:28px 32px 24px 32px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td>
      <span style="font-size:12px;font-weight:600;letter-spacing:2px;color:#4cc9f0;text-transform:uppercase;">BriefBot</span>
    </td>
    <td align="right">
      <span style="font-size:12px;color:#8d99ae;">{date}</span>
    </td>
  </tr>
  <tr>
    <td colspan="2" style="padding-top:12px;">
      <span style="font-size:22px;font-weight:800;color:#ffffff;line-height:1.3;">{subject}</span>
    </td>
  </tr>
  </table>
</td>
</tr>

<!-- Body content -->
<tr>
<td style="padding:28px 32px 12px 32px;font-size:15px;color:#2d2d2d;line-height:1.7;">
{body}
</td>
</tr>

<!-- Footer -->
<tr>
<td style="padding:16px 32px 24px 32px;border-top:1px solid #e9ecef;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="font-size:12px;color:#8d99ae;line-height:1.5;">
      Compiled by <strong style="color:#4361ee;">BriefBot</strong><br>
      Sources are linked inline throughout this briefing.
    </td>
  </tr>
  </table>
</td>
</tr>

</table>
<!-- End main card -->

</td></tr>
</table>
<!-- End outer wrapper -->

</body>
</html>""".format(
        subject=subject.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
        date=date_str,
        body=html_body,
    )


def _build_email_message(
    recipients: List[str],
    subject: str,
    markdown_body: str,
    sender: str,
    job_id: Optional[str] = None,
    audio_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
) -> MIMEMultipart:
    """
    Builds a MIME multipart email with text/plain + text/html parts
    and optional MP3 / PDF attachments.  HTML uses a news-site-inspired layout.
    """
    msg = MIMEMultipart("mixed")
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
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

    # HTML version — news-site layout
    html_content = build_newsletter_html(subject, full_text)

    html_part = MIMEText(html_content, "html", "utf-8")
    alt_part.attach(html_part)

    msg.attach(alt_part)

    # Attach PDF if provided
    if pdf_path and pdf_path.exists():
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
        pdf_attachment.add_header(
            "Content-Disposition", "attachment", filename=pdf_path.name
        )
        msg.attach(pdf_attachment)

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


def parse_recipients(recipient_str: str) -> List[str]:
    """
    Parses a comma-separated recipient string into a list of addresses.

    Strips whitespace around each address and discards empty entries.
    """
    return [addr.strip() for addr in recipient_str.split(",") if addr.strip()]


def send_report_email(
    recipient: str,
    subject: str,
    markdown_body: str,
    config: Dict[str, Any],
    job_id: Optional[str] = None,
    audio_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
) -> None:
    """
    Sends a research report email via SMTP.

    Args:
        recipient: One or more email addresses, comma-separated.
        subject: Email subject line.
        markdown_body: The report content in markdown format.
        config: Configuration dict containing SMTP_* keys.
        job_id: Optional job ID for the unsubscribe footer.
        audio_path: Optional path to an MP3 file to attach.
        pdf_path: Optional path to a PDF file to attach.

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
    sender = config.get("SMTP_FROM") or user
    use_tls = str(config.get("SMTP_USE_TLS", "true")).lower() in ("true", "1", "yes")

    recipients = parse_recipients(recipient)

    msg = _build_email_message(
        recipients, subject, markdown_body, sender, job_id, audio_path, pdf_path
    )

    if use_tls:
        server = smtplib.SMTP(host, port)
        server.starttls()
    else:
        server = smtplib.SMTP(host, port)

    try:
        server.login(user, password)
        server.sendmail(sender, recipients, msg.as_string())
    finally:
        server.quit()
