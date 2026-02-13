"""Tests for email sender module."""

import sys
from pathlib import Path

import pytest

# Ensure library modules are discoverable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib.email_sender import (
    _build_email_message,
    _markdown_to_basic_html,
    parse_recipients,
    validate_smtp_config,
)


class TestValidateSmtpConfig:
    """Tests for validate_smtp_config()."""

    def test_valid_config(self):
        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_USER": "user@gmail.com",
            "SMTP_PASSWORD": "app-password",
        }
        assert validate_smtp_config(config) is None

    def test_valid_config_with_optional_from(self):
        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_USER": "user@gmail.com",
            "SMTP_PASSWORD": "app-password",
            "SMTP_FROM": "alias@gmail.com",
        }
        assert validate_smtp_config(config) is None

    def test_missing_host(self):
        config = {
            "SMTP_USER": "user@gmail.com",
            "SMTP_PASSWORD": "pass",
        }
        error = validate_smtp_config(config)
        assert error is not None
        assert "SMTP_HOST" in error

    def test_missing_all(self):
        error = validate_smtp_config({})
        assert error is not None
        assert "SMTP_HOST" in error
        assert "SMTP_USER" in error

    def test_smtp_from_not_required(self):
        """SMTP_FROM is optional — should not appear in missing keys."""
        config = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_USER": "user@gmail.com",
            "SMTP_PASSWORD": "pass",
        }
        assert validate_smtp_config(config) is None

    def test_empty_values_treated_as_missing(self):
        config = {
            "SMTP_HOST": "",
            "SMTP_USER": "user@gmail.com",
            "SMTP_PASSWORD": "pass",
        }
        error = validate_smtp_config(config)
        assert error is not None
        assert "SMTP_HOST" in error


class TestMarkdownToBasicHtml:
    """Tests for _markdown_to_basic_html()."""

    def test_headers(self):
        html = _markdown_to_basic_html("# Title")
        assert "<h1>Title</h1>" in html

    def test_h2(self):
        html = _markdown_to_basic_html("## Subtitle")
        assert "<h2>Subtitle</h2>" in html

    def test_bold(self):
        html = _markdown_to_basic_html("This is **bold** text")
        assert "<strong>bold</strong>" in html

    def test_italic(self):
        html = _markdown_to_basic_html("This is *italic* text")
        assert "<em>italic</em>" in html

    def test_link(self):
        html = _markdown_to_basic_html("[Click here](https://example.com)")
        assert '<a href="https://example.com">Click here</a>' in html

    def test_horizontal_rule(self):
        html = _markdown_to_basic_html("---")
        assert "<hr>" in html

    def test_list_items(self):
        html = _markdown_to_basic_html("- Item one\n- Item two")
        assert "<li>Item one</li>" in html
        assert "<li>Item two</li>" in html

    def test_inline_code(self):
        html = _markdown_to_basic_html("Run `pip install`")
        assert "<code" in html
        assert "pip install" in html


class TestParseRecipients:
    """Tests for parse_recipients()."""

    def test_single_address(self):
        assert parse_recipients("alice@example.com") == ["alice@example.com"]

    def test_multiple_comma_separated(self):
        result = parse_recipients("alice@example.com,bob@example.com")
        assert result == ["alice@example.com", "bob@example.com"]

    def test_whitespace_around_addresses(self):
        result = parse_recipients("alice@example.com , bob@example.com")
        assert result == ["alice@example.com", "bob@example.com"]

    def test_trailing_comma_ignored(self):
        result = parse_recipients("alice@example.com,")
        assert result == ["alice@example.com"]

    def test_empty_string(self):
        assert parse_recipients("") == []


class TestBuildEmailMessage:
    """Tests for _build_email_message()."""

    def test_basic_message(self):
        msg = _build_email_message(
            recipients=["user@example.com"],
            subject="Test Report",
            markdown_body="# Hello\n\nThis is a test.",
            sender="bot@example.com",
        )
        assert msg["From"] == "bot@example.com"
        assert msg["To"] == "user@example.com"
        assert msg["Subject"] == "Test Report"

    def test_multiple_recipients_in_to_header(self):
        msg = _build_email_message(
            recipients=["alice@example.com", "bob@example.com"],
            subject="Test",
            markdown_body="Hello",
            sender="bot@example.com",
        )
        assert msg["To"] == "alice@example.com, bob@example.com"

    def test_message_has_text_and_html(self):
        msg = _build_email_message(
            recipients=["user@example.com"],
            subject="Test",
            markdown_body="Hello world",
            sender="bot@example.com",
        )
        # The message should have alternative parts
        payload = msg.get_payload()
        assert len(payload) >= 1  # At least the alternative part

        # Find the alternative part
        alt_part = payload[0]
        content_types = [p.get_content_type() for p in alt_part.get_payload()]
        assert "text/plain" in content_types
        assert "text/html" in content_types

    def test_job_id_in_footer(self):
        msg = _build_email_message(
            recipients=["user@example.com"],
            subject="Test",
            markdown_body="Hello",
            sender="bot@example.com",
            job_id="cu_ABC123",
        )
        # Check plain text part for job ID
        alt_part = msg.get_payload()[0]
        plain_part = [p for p in alt_part.get_payload() if p.get_content_type() == "text/plain"][0]
        text = plain_part.get_payload(decode=True).decode("utf-8")
        assert "cu_ABC123" in text
        assert "--delete-job" in text

    def test_audio_attachment(self, tmp_path):
        # Create a fake MP3 file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)

        msg = _build_email_message(
            recipients=["user@example.com"],
            subject="Test",
            markdown_body="Hello",
            sender="bot@example.com",
            audio_path=audio_file,
        )
        payload = msg.get_payload()
        # Should have alt part + attachment
        assert len(payload) == 2
        attachment = payload[1]
        assert "test.mp3" in attachment.get("Content-Disposition", "")

    def test_no_attachment_when_file_missing(self):
        msg = _build_email_message(
            recipients=["user@example.com"],
            subject="Test",
            markdown_body="Hello",
            sender="bot@example.com",
            audio_path=Path("/nonexistent/audio.mp3"),
        )
        payload = msg.get_payload()
        # Should only have the alternative part, no attachment
        assert len(payload) == 1
