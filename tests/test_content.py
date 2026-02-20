"""Tests for briefbot_engine.content -- unified content model and factory functions.

Topic theme: Solar panel efficiency improvements 2026
"""

import math

from briefbot_engine.content import (
    ContentItem,
    Report,
    Signals,
    Source,
    as_dicts,
    build_report,
    filter_by_date,
    from_linkedin_raw,
    from_reddit_raw,
    from_web_raw,
    from_x_raw,
    from_youtube_raw,
)

# ---------------------------------------------------------------------------
# Shared date range for the "solar panel" research window
# ---------------------------------------------------------------------------
START = "2026-01-20"
END = "2026-02-19"


# ---------------------------------------------------------------------------
# from_reddit_raw
# ---------------------------------------------------------------------------

def test_from_reddit_raw_creates_content_item():
    raw = {
        "id": "sp_r001",
        "title": "Solar panel efficiency improvements 2026 -- perovskite tandem breakthrough",
        "url": "https://reddit.com/r/solar/comments/sp_r001",
        "subreddit": "solar",
        "date": "2026-02-10",
        "why_relevant": "Discusses record 33.7% efficiency for perovskite-silicon tandems",
        "relevance": 0.91,
        "engagement": {
            "score": 340,
            "num_comments": 87,
            "upvote_ratio": 0.92,
        },
        "top_comments": [
            {
                "score": 72,
                "date": "2026-02-10",
                "author": "pvexpert",
                "excerpt": "The durability data at 85C/85%RH is the real story.",
                "url": "https://reddit.com/r/solar/comments/sp_r001/c1",
            }
        ],
        "comment_insights": ["Durability is the main remaining concern"],
        "flair": "News",
    }

    item = from_reddit_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.REDDIT
    assert item.headline == raw["title"]
    assert item.item_id == "sp_r001"
    assert item.permalink == raw["url"]
    assert item.author == "solar"  # subreddit is stored as author
    assert item.published == "2026-02-10"
    assert item.date_trust == "high"
    assert item.relevance == 0.91
    assert item.rationale == raw["why_relevant"]
    # Signals
    assert item.signals is not None
    assert item.signals.upvotes == 340
    assert item.signals.comments == 87
    assert item.signals.vote_ratio == 0.92
    assert item.signals.composite is not None
    assert item.signals.composite > 0
    # Thread comments
    assert len(item.thread_comments) == 1
    assert item.thread_comments[0].author == "pvexpert"
    # Thread insights
    assert "Durability" in item.thread_insights[0]
    # Meta
    assert item.meta["subreddit"] == "solar"
    assert item.meta["flair"] == "News"


def test_from_reddit_raw_composite_formula():
    """Verify the Reddit composite formula: 0.48*log1p(upvotes) + 0.37*log1p(comments) + 0.15*(ratio*12)."""
    raw = {
        "id": "sp_r002",
        "title": "Bifacial panels now standard on utility-scale installs",
        "url": "https://reddit.com/r/solar/comments/sp_r002",
        "subreddit": "solar",
        "engagement": {
            "score": 340,
            "num_comments": 87,
            "upvote_ratio": 0.92,
        },
    }

    item = from_reddit_raw(raw, START, END)

    expected = (
        0.48 * math.log1p(340)
        + 0.37 * math.log1p(87)
        + 0.15 * (0.92 * 12)
    )
    assert abs(item.signals.composite - expected) < 1e-9


# ---------------------------------------------------------------------------
# from_x_raw
# ---------------------------------------------------------------------------

def test_from_x_raw_creates_content_item():
    raw = {
        "id": "sp_x001",
        "text": "New perovskite tandem cells hit 33.7% efficiency in certified lab tests #solar2026",
        "url": "https://x.com/solarnews/status/sp_x001",
        "author_handle": "solarnews",
        "date": "2026-02-12",
        "why_relevant": "Breaking efficiency record announcement",
        "relevance": 0.88,
        "engagement": {
            "likes": 2100,
            "reposts": 380,
            "replies": 95,
            "quotes": 42,
        },
        "is_repost": False,
        "language": "en",
    }

    item = from_x_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.X
    assert item.headline == raw["text"]
    assert item.author == "solarnews"
    assert item.published == "2026-02-12"
    assert item.date_trust == "high"
    # Signals
    assert item.signals is not None
    assert item.signals.likes == 2100
    assert item.signals.reposts == 380
    assert item.signals.replies == 95
    assert item.signals.quotes == 42
    assert item.signals.composite is not None
    expected_composite = (
        0.45 * math.log1p(2100)
        + 0.28 * math.log1p(380)
        + 0.17 * math.log1p(95)
        + 0.10 * math.log1p(42)
    )
    assert abs(item.signals.composite - expected_composite) < 1e-9
    # Meta
    assert item.meta["is_repost"] is False
    assert item.meta["language"] == "en"


# ---------------------------------------------------------------------------
# from_youtube_raw
# ---------------------------------------------------------------------------

def test_from_youtube_raw_creates_content_item():
    raw = {
        "id": "sp_yt001",
        "title": "How Perovskite Tandems Will Change Solar Forever",
        "url": "https://youtube.com/watch?v=sp_yt001",
        "channel_name": "JustHaveFun Engineering",
        "description": "Deep dive into perovskite-silicon tandem technology.",
        "date": "2026-02-05",
        "views": 185000,
        "likes": 4200,
        "relevance": 0.82,
        "why_relevant": "In-depth technical explainer on tandem cells",
        "duration_seconds": 912,
    }

    item = from_youtube_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.YOUTUBE
    assert item.headline == raw["title"]
    assert item.author == "JustHaveFun Engineering"
    assert item.body == raw["description"]
    assert item.published == "2026-02-05"
    assert item.date_trust == "high"
    # Signals
    assert item.signals is not None
    assert item.signals.views == 185000
    assert item.signals.likes == 4200
    expected_composite = 0.62 * math.log1p(185000) + 0.38 * math.log1p(4200)
    assert abs(item.signals.composite - expected_composite) < 1e-9
    # Meta
    assert item.meta["duration_seconds"] == 912


# ---------------------------------------------------------------------------
# from_linkedin_raw
# ---------------------------------------------------------------------------

def test_from_linkedin_raw_creates_content_item():
    raw = {
        "id": "sp_li001",
        "text": "Excited to announce our lab's new perovskite stability record -- 1500 hours at 85C",
        "url": "https://linkedin.com/posts/sp_li001",
        "author_name": "Dr. Elena Vasquez",
        "author_title": "Director of PV Research, SunTech Labs",
        "date": "2026-02-08",
        "reactions": 620,
        "comments": 41,
        "relevance": 0.79,
        "why_relevant": "Primary researcher sharing first-hand lab results",
    }

    item = from_linkedin_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.LINKEDIN
    assert item.headline == raw["text"]
    assert item.author == "Dr. Elena Vasquez"
    assert item.published == "2026-02-08"
    assert item.date_trust == "high"
    # Signals
    assert item.signals is not None
    assert item.signals.reactions == 620
    assert item.signals.comments == 41
    expected_composite = 0.55 * math.log1p(620) + 0.45 * math.log1p(41)
    assert abs(item.signals.composite - expected_composite) < 1e-9
    # Meta
    assert item.meta["author_title"] == "Director of PV Research, SunTech Labs"


# ---------------------------------------------------------------------------
# from_web_raw
# ---------------------------------------------------------------------------

def test_from_web_raw_creates_content_item_with_no_signals():
    raw = {
        "id": "sp_w001",
        "title": "Solar Panel Efficiency Hits New Record in 2026",
        "url": "https://pv-magazine.com/2026/02/07/solar-panel-record",
        "source_domain": "pv-magazine.com",
        "snippet": "Researchers achieved 33.7% tandem cell efficiency...",
        "date": "2026-02-07",
        "date_confidence": "high",
        "relevance": 0.75,
        "why_relevant": "Trade press coverage of the record",
        "language": "en",
    }

    item = from_web_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.WEB
    assert item.headline == raw["title"]
    assert item.author == "pv-magazine.com"
    assert item.body == raw["snippet"]
    assert item.signals is None
    assert item.published == "2026-02-07"
    assert item.date_trust == "high"  # from date_confidence in raw
    assert item.meta["source_domain"] == "pv-magazine.com"
    assert item.meta["language"] == "en"


# ---------------------------------------------------------------------------
# filter_by_date
# ---------------------------------------------------------------------------

def _make_item(item_id, published):
    return ContentItem(
        item_id=item_id,
        source=Source.REDDIT,
        headline="Solar efficiency " + item_id,
        permalink="https://example.com/" + item_id,
        published=published,
    )


def test_filter_by_date_excludes_outside_range():
    items = [
        _make_item("in1", "2026-02-01"),
        _make_item("early", "2025-12-15"),
        _make_item("in2", "2026-02-15"),
        _make_item("late", "2026-03-10"),
    ]

    filtered = filter_by_date(items, START, END)

    ids = [i.item_id for i in filtered]
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
    assert filtered[0].item_id == "dated"


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
    assert result[0]["id"] == "d1"
    assert result[1]["id"] == "d2"


# ---------------------------------------------------------------------------
# ContentItem.to_dict
# ---------------------------------------------------------------------------

def test_content_item_to_dict():
    sig = Signals(upvotes=340, comments=87, vote_ratio=0.92, composite=5.5)
    item = ContentItem(
        item_id="td001",
        source=Source.REDDIT,
        headline="Solar panel efficiency improvements 2026",
        permalink="https://reddit.com/r/solar/td001",
        author="solar",
        published="2026-02-10",
        date_trust="high",
        signals=sig,
        relevance=0.91,
        rationale="High relevance to query",
    )

    d = item.to_dict()

    assert isinstance(d, dict)
    assert d["id"] == "td001"
    assert d["source"] == "reddit"
    assert d["headline"] == item.headline
    assert d["signals"]["upvotes"] == 340
    assert d["signals"]["comments"] == 87
    assert d["signals"]["vote_ratio"] == 0.92
    assert d["signals"]["composite"] == 5.5
    assert d["published"] == "2026-02-10"
    assert d["date_trust"] == "high"


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------

def test_build_report_creates_report_with_fields():
    rpt = build_report(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="deep",
        openai_model="gpt-4o",
        xai_model="grok-3",
    )

    assert isinstance(rpt, Report)
    assert rpt.topic == "Solar panel efficiency improvements 2026"
    assert rpt.range_start == START
    assert rpt.range_end == END
    assert rpt.mode == "deep"
    assert rpt.openai_model_used == "gpt-4o"
    assert rpt.xai_model_used == "grok-3"
    assert rpt.generated_at  # non-empty string
    assert rpt.items == []
    assert rpt.errors == {}


# ---------------------------------------------------------------------------
# Report platform properties
# ---------------------------------------------------------------------------

def _reddit_item(item_id):
    return ContentItem(
        item_id=item_id,
        source=Source.REDDIT,
        headline="Reddit solar " + item_id,
        permalink="https://reddit.com/" + item_id,
    )


def _x_item(item_id):
    return ContentItem(
        item_id=item_id,
        source=Source.X,
        headline="X solar " + item_id,
        permalink="https://x.com/" + item_id,
    )


def test_report_reddit_property():
    rpt = build_report(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )
    rpt.items = [_reddit_item("r1"), _x_item("x1"), _reddit_item("r2")]

    reddit_items = rpt.reddit

    assert len(reddit_items) == 2
    assert all(i.source == Source.REDDIT for i in reddit_items)


def test_report_x_property():
    rpt = build_report(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )
    rpt.items = [_reddit_item("r1"), _x_item("x1"), _x_item("x2")]

    x_items = rpt.x

    assert len(x_items) == 2
    assert all(i.source == Source.X for i in x_items)


# ---------------------------------------------------------------------------
# Report error properties
# ---------------------------------------------------------------------------

def test_report_reddit_error_property():
    rpt = build_report(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )

    assert rpt.reddit_error is None

    rpt.reddit_error = "Rate limit exceeded"
    assert rpt.reddit_error == "Rate limit exceeded"
    assert rpt.errors["reddit"] == "Rate limit exceeded"


def test_report_x_error_property():
    rpt = build_report(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )

    assert rpt.x_error is None

    rpt.x_error = "API key invalid"
    assert rpt.x_error == "API key invalid"
    assert rpt.errors["x"] == "API key invalid"


def test_report_error_setter_ignores_none():
    rpt = build_report(
        topic="Solar panel efficiency improvements 2026",
        start=START,
        end=END,
        mode="standard",
    )

    rpt.reddit_error = None

    assert "reddit" not in rpt.errors
