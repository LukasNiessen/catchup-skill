"""Tests for briefbot_engine.records -- unified content model and factory functions.

Topic theme: Solar panel efficiency improvements 2026
"""

import math

from briefbot_engine.records import (
    Brief,
    Channel,
    Interaction,
    Signal,
    as_dicts,
    build_brief,
    filter_by_date,
    from_linkedin_raw,
    from_reddit_raw,
    from_web_raw,
    from_x_raw,
    from_youtube_raw,
)
from briefbot_engine import timeframe

# ---------------------------------------------------------------------------
# Shared date range for the "solar panel" research window
# ---------------------------------------------------------------------------
START = "2026-01-20"
END = "2026-02-19"


# ---------------------------------------------------------------------------
# from_reddit_raw
# ---------------------------------------------------------------------------

def test_from_reddit_raw_creates_signal():
    raw = {
        "key": "sp_r001",
        "headline": "Solar panel efficiency improvements 2026 -- perovskite tandem breakthrough",
        "url": "https://reddit.com/r/solar/comments/sp_r001",
        "forum": "solar",
        "dated": "2026-02-10",
        "rationale": "Discusses record 33.7% efficiency for perovskite-silicon tandems",
        "topicality": 0.91,
        "signals": {
            "upvotes": 340,
            "comments": 87,
            "ratio": 0.92,
        },
        "thread_notes": [
            {
                "score": 72,
                "stamped": "2026-02-10",
                "author": "pvexpert",
                "excerpt": "The durability data at 85C/85%RH is the real story.",
                "url": "https://reddit.com/r/solar/comments/sp_r001/c1",
            }
        ],
        "notables": ["Durability is the main remaining concern"],
        "flair": "News",
    }

    item = from_reddit_raw(raw, START, END)

    assert isinstance(item, Signal)
    assert item.channel == Channel.REDDIT
    assert item.headline == raw["headline"]
    assert item.key == "sp_r001"
    assert item.url == raw["url"]
    assert item.byline == "solar"
    assert item.dated == "2026-02-10"
    assert item.time_confidence == timeframe.CONFIDENCE_SOLID
    assert item.topicality == 0.91
    assert item.rationale == raw["rationale"]
    # Interaction
    assert item.interaction is not None
    assert item.interaction.upvotes == 340
    assert item.interaction.comments == 87
    assert item.interaction.ratio == 0.92
    assert item.interaction.pulse is not None
    assert item.interaction.pulse > 0
    # Thread notes
    assert len(item.thread_notes) == 1
    assert item.thread_notes[0].author == "pvexpert"
    # Highlights
    assert "Durability" in item.notables[0]
    # Extras
    assert item.extras["subreddit"] == "solar"
    assert item.extras["flair"] == "News"


def test_from_reddit_raw_composite_formula():
    """Verify the Reddit pulse formula uses sqrt scaling and ratio weighting."""
    raw = {
        "key": "sp_r002",
        "headline": "Bifacial panels now standard on utility-scale installs",
        "url": "https://reddit.com/r/solar/comments/sp_r002",
        "forum": "solar",
        "signals": {
            "upvotes": 340,
            "comments": 87,
            "ratio": 0.92,
        },
    }

    item = from_reddit_raw(raw, START, END)

    expected = (
        0.40 * math.sqrt(340)
        + 0.40 * math.sqrt(87)
        + 0.20 * (0.92 * 10)
    )
    assert abs(item.interaction.pulse - expected) < 1e-9


# ---------------------------------------------------------------------------
# from_x_raw
# ---------------------------------------------------------------------------

def test_from_x_raw_creates_signal():
    raw = {
        "key": "sp_x001",
        "snippet": "New perovskite tandem cells hit 33.7% efficiency in certified lab tests #solar2026",
        "url": "https://x.com/solarnews/status/sp_x001",
        "handle": "solarnews",
        "dated": "2026-02-12",
        "rationale": "Breaking efficiency record announcement",
        "topicality": 0.88,
        "signals": {
            "likes": 2100,
            "reposts": 380,
            "replies": 95,
            "quotes": 42,
        },
        "is_repost": False,
        "language": "en",
    }

    item = from_x_raw(raw, START, END)

    assert isinstance(item, Signal)
    assert item.channel == Channel.X
    assert item.headline == raw["snippet"]
    assert item.byline == "solarnews"
    assert item.dated == "2026-02-12"
    assert item.time_confidence == timeframe.CONFIDENCE_SOLID
    # Interaction
    assert item.interaction is not None
    assert item.interaction.likes == 2100
    assert item.interaction.reposts == 380
    assert item.interaction.replies == 95
    assert item.interaction.quotes == 42
    assert item.interaction.pulse is not None
    expected_composite = (
        0.46 * math.sqrt(2100)
        + 0.26 * math.sqrt(95)
        + 0.16 * math.sqrt(380)
        + 0.12 * math.sqrt(42)
    )
    assert abs(item.interaction.pulse - expected_composite) < 1e-9
    # Extras
    assert item.extras["is_repost"] is False
    assert item.extras["language"] == "en"


# ---------------------------------------------------------------------------
# from_youtube_raw
# ---------------------------------------------------------------------------

def test_from_youtube_raw_creates_signal():
    raw = {
        "key": "sp_yt001",
        "headline": "How Perovskite Tandems Will Change Solar Forever",
        "url": "https://youtube.com/watch?v=sp_yt001",
        "channel": "JustHaveFun Engineering",
        "blurb": "Deep dive into perovskite-silicon tandem technology.",
        "dated": "2026-02-05",
        "signals": {"views": 185000, "likes": 4200},
        "topicality": 0.82,
        "rationale": "In-depth technical explainer on tandem cells",
        "duration_seconds": 912,
    }

    item = from_youtube_raw(raw, START, END)

    assert isinstance(item, Signal)
    assert item.channel == Channel.YOUTUBE
    assert item.headline == raw["headline"]
    assert item.byline == "JustHaveFun Engineering"
    assert item.blurb == raw["blurb"]
    assert item.dated == "2026-02-05"
    assert item.time_confidence == timeframe.CONFIDENCE_SOLID
    # Interaction
    assert item.interaction is not None
    assert item.interaction.views == 185000
    assert item.interaction.likes == 4200
    expected_composite = 0.68 * math.sqrt(185000) + 0.32 * math.sqrt(4200)
    assert abs(item.interaction.pulse - expected_composite) < 1e-9
    # Extras
    assert item.extras["duration_seconds"] == 912


# ---------------------------------------------------------------------------
# from_linkedin_raw
# ---------------------------------------------------------------------------

def test_from_linkedin_raw_creates_signal():
    raw = {
        "key": "sp_li001",
        "snippet": "Excited to announce our lab's new perovskite stability record -- 1500 hours at 85C",
        "url": "https://linkedin.com/posts/sp_li001",
        "author": "Dr. Elena Vasquez",
        "role": "Director of PV Research, SunTech Labs",
        "dated": "2026-02-08",
        "signals": {"reactions": 620, "comments": 41},
        "topicality": 0.79,
        "rationale": "Primary researcher sharing first-hand lab results",
    }

    item = from_linkedin_raw(raw, START, END)

    assert isinstance(item, Signal)
    assert item.channel == Channel.LINKEDIN
    assert item.headline == raw["snippet"]
    assert item.byline == "Dr. Elena Vasquez"
    assert item.dated == "2026-02-08"
    assert item.time_confidence == timeframe.CONFIDENCE_SOLID
    # Interaction
    assert item.interaction is not None
    assert item.interaction.reactions == 620
    assert item.interaction.comments == 41
    expected_composite = 0.62 * math.sqrt(620) + 0.38 * math.sqrt(41)
    assert abs(item.interaction.pulse - expected_composite) < 1e-9
    # Extras
    assert item.extras["author_title"] == "Director of PV Research, SunTech Labs"


# ---------------------------------------------------------------------------
# from_web_raw
# ---------------------------------------------------------------------------

def test_from_web_raw_creates_signal_with_no_interaction():
    raw = {
        "key": "sp_w001",
        "headline": "Solar Panel Efficiency Hits New Record in 2026",
        "url": "https://pv-magazine.com/2026/02/07/solar-panel-record",
        "domain": "pv-magazine.com",
        "snippet": "Researchers achieved 33.7% tandem cell efficiency...",
        "dated": "2026-02-07",
        "time_confidence": timeframe.CONFIDENCE_SOLID,
        "topicality": 0.75,
        "rationale": "Trade press coverage of the record",
        "language": "en",
    }

    item = from_web_raw(raw, START, END)

    assert isinstance(item, Signal)
    assert item.channel == Channel.WEB
    assert item.headline == raw["headline"]
    assert item.byline == "pv-magazine.com"
    assert item.blurb == raw["snippet"]
    assert item.interaction is None
    assert item.dated == "2026-02-07"
    assert item.time_confidence == timeframe.CONFIDENCE_SOLID
    assert item.extras["source_domain"] == "pv-magazine.com"
    assert item.extras["language"] == "en"


# ---------------------------------------------------------------------------
# filter_by_date
# ---------------------------------------------------------------------------

def _make_item(key, dated):
    return Signal(
        key=key,
        channel=Channel.REDDIT,
        headline="Solar efficiency " + key,
        url="https://example.com/" + key,
        dated=dated,
    )


def test_filter_by_date_excludes_outside_range():
    items = [
        _make_item("in1", "2026-02-01"),
        _make_item("early", "2025-12-15"),
        _make_item("in2", "2026-02-15"),
        _make_item("late", "2026-03-10"),
    ]

    filtered = filter_by_date(items, START, END)

    ids = [i.key for i in filtered]
    assert "in1" in ids
    assert "in2" in ids
    assert "early" not in ids
    assert "late" not in ids


def test_filter_by_date_keeps_undated_by_default():
    items = [
        _make_item("dated", "2026-02-01"),
        _make_item("undated", None),
    ]

    filtered = filter_by_date(items, START, END)

    assert len(filtered) == 2


def test_filter_by_date_excludes_undated_when_requested():
    items = [
        _make_item("dated", "2026-02-01"),
        _make_item("undated", None),
    ]

    filtered = filter_by_date(items, START, END, exclude_undated=True)

    assert len(filtered) == 1
    assert filtered[0].key == "dated"


# ---------------------------------------------------------------------------
# as_dicts
# ---------------------------------------------------------------------------

def test_as_dicts_converts_list():
    items = [
        _make_item("d1", "2026-02-01"),
        _make_item("d2", "2026-02-05"),
    ]

    result = as_dicts(items)

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(d, dict) for d in result)
    assert result[0]["key"] == "d1"
    assert result[1]["key"] == "d2"


# ---------------------------------------------------------------------------
# Signal.to_dict
# ---------------------------------------------------------------------------

def test_signal_to_dict():
    sig = Interaction(upvotes=340, comments=87, ratio=0.92, pulse=5.5)
    item = Signal(
        key="td001",
        channel=Channel.REDDIT,
        headline="Solar panel efficiency improvements 2026",
        url="https://reddit.com/r/solar/td001",
        byline="solar",
        dated="2026-02-10",
        time_confidence=timeframe.CONFIDENCE_SOLID,
        interaction=sig,
        topicality=0.91,
        rationale="High relevance to query",
    )

    d = item.to_dict()

    assert isinstance(d, dict)
    assert d["key"] == "td001"
    assert d["channel"] == "reddit"
    assert d["headline"] == item.headline
    assert d["interaction"]["upvotes"] == 340
    assert d["interaction"]["comments"] == 87
    assert d["interaction"]["ratio"] == 0.92
    assert d["interaction"]["pulse"] == 5.5
    assert d["dated"] == "2026-02-10"
    assert d["time_confidence"] == timeframe.CONFIDENCE_SOLID


# ---------------------------------------------------------------------------
# build_brief
# ---------------------------------------------------------------------------

def test_build_brief_creates_brief_with_fields():
    rpt = build_brief(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="dense",
        openai_model="gpt-4o",
        xai_model="grok-3",
    )

    assert isinstance(rpt, Brief)
    assert rpt.topic == "Solar panel efficiency improvements 2026"
    assert rpt.span.start == START
    assert rpt.span.end == END
    assert rpt.mode == "dense"
    assert rpt.models.openai == "gpt-4o"
    assert rpt.models.xai == "grok-3"
    assert rpt.generated_at
    assert rpt.items == []
    assert rpt.errors.by_channel == {}


# ---------------------------------------------------------------------------
# Brief platform properties
# ---------------------------------------------------------------------------

def _reddit_item(key):
    return Signal(
        key=key,
        channel=Channel.REDDIT,
        headline="Reddit solar " + key,
        url="https://reddit.com/" + key,
    )


def _x_item(key):
    return Signal(
        key=key,
        channel=Channel.X,
        headline="X solar " + key,
        url="https://x.com/" + key,
    )


def test_brief_reddit_property():
    rpt = build_brief(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )
    rpt.items = [_reddit_item("r1"), _x_item("x1"), _reddit_item("r2")]

    reddit_items = rpt.reddit

    assert len(reddit_items) == 2
    assert all(i.channel == Channel.REDDIT for i in reddit_items)


def test_brief_x_property():
    rpt = build_brief(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )
    rpt.items = [_reddit_item("r1"), _x_item("x1"), _x_item("x2")]

    x_items = rpt.x

    assert len(x_items) == 2
    assert all(i.channel == Channel.X for i in x_items)


# ---------------------------------------------------------------------------
# Brief error properties
# ---------------------------------------------------------------------------

def test_brief_reddit_error_property():
    rpt = build_brief(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )

    assert rpt.reddit_error is None

    rpt.reddit_error = "Rate limit exceeded"
    assert rpt.reddit_error == "Rate limit exceeded"
    assert rpt.errors.by_channel["reddit"] == "Rate limit exceeded"


def test_brief_x_error_property():
    rpt = build_brief(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )

    assert rpt.x_error is None

    rpt.x_error = "API key invalid"
    assert rpt.x_error == "API key invalid"
    assert rpt.errors.by_channel["x"] == "API key invalid"


def test_brief_error_setter_ignores_none():
    rpt = build_brief(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )

    rpt.reddit_error = None

    assert "reddit" not in rpt.errors.by_channel
