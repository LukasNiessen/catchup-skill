"""Tests for the output/formatter module (briefbot_engine.output)."""

import pytest

from briefbot_engine.content import Report, ContentItem, Source, Engagement, build_report
from briefbot_engine.output import compact, context_fragment, full_report, context_path
from briefbot_engine import temporal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(topic="AI agents", mode="both", items=None):
    """Create a minimal Report for testing."""
    report = build_report(
        topic=topic,
        start="2026-01-01",
        end="2026-01-31",
        mode=mode,
        openai_model="gpt-4o-mini",
        xai_model="grok-2",
    )
    report.generated_at = "2026-01-31T12:00:00+00:00"
    report.items = items or []
    return report


def _make_reddit_item(uid="R1", title="Big discussion", subreddit="machinelearning"):
    """Create a minimal Reddit ContentItem."""
    return ContentItem(
        uid=uid,
        source=Source.REDDIT,
        title=title,
        link="https://www.reddit.com/r/{}/comments/abc123/test/".format(subreddit),
        author=subreddit,
        published="2026-01-15",
        date_confidence=temporal.CONFIDENCE_SOLID,
        engagement=Engagement(upvotes=42, comments=10),
        relevance=0.9,
        reason="Highly relevant discussion",
        score=85,
        meta={"subreddit": subreddit},
    )


# ---------------------------------------------------------------------------
# compact()
# ---------------------------------------------------------------------------

def test_compact_basic_report_contains_topic():
    report = _make_report()
    result = compact(report)
    assert "AI agents" in result


def test_compact_basic_report_contains_date_range():
    report = _make_report()
    result = compact(report)
    assert "2026-01-01" in result
    assert "2026-01-31" in result


def test_compact_basic_report_contains_mode():
    report = _make_report()
    result = compact(report)
    assert "both" in result


def test_compact_with_reddit_items_shows_item_id():
    item = _make_reddit_item()
    report = _make_report(items=[item])
    result = compact(report)
    assert "R1" in result


def test_compact_with_reddit_items_shows_headline():
    item = _make_reddit_item()
    report = _make_report(items=[item])
    result = compact(report)
    assert "Big discussion" in result


def test_compact_with_reddit_items_shows_subreddit():
    item = _make_reddit_item(subreddit="python")
    report = _make_report(items=[item])
    result = compact(report)
    assert "r/python" in result


# ---------------------------------------------------------------------------
# context_fragment()
# ---------------------------------------------------------------------------

def test_context_fragment_contains_topic():
    report = _make_report(topic="Rust programming")
    result = context_fragment(report)
    assert "Rust programming" in result


# ---------------------------------------------------------------------------
# full_report()
# ---------------------------------------------------------------------------

def test_full_report_contains_topic_as_h1():
    report = _make_report(topic="LLM fine-tuning")
    result = full_report(report)
    assert "# LLM fine-tuning" in result


def test_full_report_contains_models_used_section():
    report = _make_report()
    result = full_report(report)
    assert "## Models Used" in result
    assert "gpt-4o-mini" in result
    assert "grok-2" in result


# ---------------------------------------------------------------------------
# context_path()
# ---------------------------------------------------------------------------

def test_context_path_contains_briefbot_context_md():
    result = context_path()
    assert "briefbot.context.md" in result
