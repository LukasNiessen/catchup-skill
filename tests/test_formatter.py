"""Tests for the output/formatter module (briefbot_engine.presenter)."""

from briefbot_engine.records import Brief, Channel, Signal, build_brief
from briefbot_engine.presenter import compact, context_fragment, full_report, context_path
from briefbot_engine import timeframe


def _make_report(topic="AI agents", mode="both", items=None):
    """Create a minimal Brief for testing."""
    report = build_brief(
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


def _make_reddit_item(key="R1", headline="Big discussion", subreddit="machinelearning"):
    """Create a minimal Reddit Signal."""
    return Signal(
        key=key,
        channel=Channel.REDDIT,
        headline=headline,
        url="https://www.reddit.com/r/{}/comments/abc123/test/".format(subreddit),
        byline=subreddit,
        dated="2026-01-15",
        time_confidence=timeframe.CONFIDENCE_SOLID,
        topicality=0.9,
        rationale="Highly relevant discussion",
        rank=85,
        extras={"subreddit": subreddit},
    )


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


def test_context_fragment_contains_topic():
    report = _make_report(topic="Rust programming")
    result = context_fragment(report)
    assert "Rust programming" in result


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


def test_context_path_contains_briefbot_context_md():
    result = context_path()
    assert "briefbot.context.md" in result
