"""Tests for the email delivery module (briefbot_engine.delivery.email)."""

import pytest

from briefbot_engine.delivery.email import (
    validate_smtp_config,
    _markdown_to_news_html,
    parse_recipients,
    _build_email_message,
)


# ---------------------------------------------------------------------------
# validate_smtp_config()
# ---------------------------------------------------------------------------

def test_validate_valid_config_returns_none():
    config = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_USER": "user@example.com",
        "SMTP_PASSWORD": "secret",
    }
    assert validate_smtp_config(config) is None


def test_validate_missing_host_returns_error():
    config = {
        "SMTP_USER": "user@example.com",
        "SMTP_PASSWORD": "secret",
    }
    result = validate_smtp_config(config)
    assert result is not None
    assert "SMTP_HOST" in result


def test_validate_empty_values_treated_as_missing():
    config = {
        "SMTP_HOST": "",
        "SMTP_USER": "user@example.com",
        "SMTP_PASSWORD": "secret",
    }
    result = validate_smtp_config(config)
    assert result is not None
    assert "SMTP_HOST" in result


# ---------------------------------------------------------------------------
# _markdown_to_news_html()
# ---------------------------------------------------------------------------

def test_markdown_to_html_headers():
    html = _markdown_to_news_html("# Main Title")
    assert "<h1" in html
    assert "Main Title" in html


def test_markdown_to_html_bold():
    html = _markdown_to_news_html("This is **bold** text")
    assert "<strong>bold</strong>" in html


def test_markdown_to_html_italic():
    html = _markdown_to_news_html("This is *italic* text")
    assert "<em>italic</em>" in html


def test_markdown_to_html_links():
    html = _markdown_to_news_html("[Click here](https://example.com)")
    assert 'href="https://example.com"' in html
    assert "Click here" in html


def test_markdown_to_html_list_items():
    html = _markdown_to_news_html("- First item\n- Second item")
    assert "<li" in html
    assert "First item" in html
    assert "Second item" in html


def test_markdown_to_html_inline_code():
    html = _markdown_to_news_html("Use `pip install` here")
    assert "<code" in html
    assert "pip install" in html


# ---------------------------------------------------------------------------
# parse_recipients()
# ---------------------------------------------------------------------------

def test_parse_single_recipient():
    result = parse_recipients("alice@example.com")
    assert result == ["alice@example.com"]


def test_parse_multiple_comma_separated():
    result = parse_recipients("alice@example.com, bob@example.com")
    assert result == ["alice@example.com", "bob@example.com"]


def test_parse_whitespace_handling():
    result = parse_recipients("  alice@example.com ,  bob@example.com  ")
    assert result == ["alice@example.com", "bob@example.com"]


def test_parse_trailing_comma():
    result = parse_recipients("alice@example.com,")
    assert result == ["alice@example.com"]


def test_parse_empty_string():
    result = parse_recipients("")
    assert result == []


# ---------------------------------------------------------------------------
# _build_email_message()
# ---------------------------------------------------------------------------

def test_build_email_basic_fields():
    msg = _build_email_message(
        recipients=["alice@example.com"],
        subject="Weekly Brief",
        markdown_body="# Hello World",
        sender="bot@example.com",
    )
    assert msg["From"] == "bot@example.com"
    assert "alice@example.com" in msg["To"]
    assert msg["Subject"] == "Weekly Brief"


def test_build_email_multiple_recipients():
    msg = _build_email_message(
        recipients=["alice@example.com", "bob@example.com"],
        subject="Report",
        markdown_body="Content here",
        sender="bot@example.com",
    )
    assert "alice@example.com" in msg["To"]
    assert "bob@example.com" in msg["To"]


def test_build_email_has_text_and_html_parts():
    msg = _build_email_message(
        recipients=["alice@example.com"],
        subject="Report",
        markdown_body="# Some markdown",
        sender="bot@example.com",
    )
    # The message is multipart/mixed with an alternative sub-part
    payload = msg.get_payload()
    assert len(payload) >= 1

    # Find the alternative part
    alt_part = payload[0]
    content_types = [part.get_content_type() for part in alt_part.get_payload()]
    assert "text/plain" in content_types
    assert "text/html" in content_types
