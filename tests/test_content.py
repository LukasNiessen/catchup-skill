"""Tests for briefbot_engine.content -- unified content model and factory functions.

Topic theme: Solar panel efficiency improvements 2026
"""

import math

from briefbot_engine.content import (
    ContentItem,
    Report,
    Engagement,
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
        "uid": "sp_r001",
        "title": "Solar panel efficiency improvements 2026 -- perovskite tandem breakthrough",
        "link": "https://reddit.com/r/solar/comments/sp_r001",
        "community": "solar",
        "posted": "2026-02-10",
        "reason": "Discusses record 33.7% efficiency for perovskite-silicon tandems",
        "signal": 0.91,
        "metrics": {
            "upvotes": 340,
            "comments": 87,
            "vote_ratio": 0.92,
        },
        "comment_cards": [
            {
                "score": 72,
                "posted": "2026-02-10",
                "author": "pvexpert",
                "excerpt": "The durability data at 85C/85%RH is the real story.",
                "link": "https://reddit.com/r/solar/comments/sp_r001/c1",
            }
        ],
        "comment_highlights": ["Durability is the main remaining concern"],
        "flair": "News",
    }

    item = from_reddit_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.REDDIT
    assert item.title == raw["title"]
    assert item.uid == "sp_r001"
    assert item.link == raw["link"]
    assert item.author == "solar"
    assert item.published == "2026-02-10"
    assert item.date_quality == "high"
    assert item.signal == 0.91
    assert item.reason == raw["reason"]
    # Engagement
    assert item.engagement is not None
    assert item.engagement.upvotes == 340
    assert item.engagement.comments == 87
    assert item.engagement.vote_ratio == 0.92
    assert item.engagement.composite is not None
    assert item.engagement.composite > 0
    # Thread comments
    assert len(item.comments) == 1
    assert item.comments[0].author == "pvexpert"
    # Thread highlights
    assert "Durability" in item.comment_highlights[0]
    # Meta
    assert item.meta["subreddit"] == "solar"
    assert item.meta["flair"] == "News"


def test_from_reddit_raw_composite_formula():
    """Verify the Reddit composite formula: 0.48*log1p(upvotes) + 0.37*log1p(comments) + 0.15*(ratio*12)."""
    raw = {
        "uid": "sp_r002",
        "title": "Bifacial panels now standard on utility-scale installs",
        "link": "https://reddit.com/r/solar/comments/sp_r002",
        "community": "solar",
        "metrics": {
            "upvotes": 340,
            "comments": 87,
            "vote_ratio": 0.92,
        },
    }

    item = from_reddit_raw(raw, START, END)

    expected = (
        0.48 * math.log1p(340)
        + 0.37 * math.log1p(87)
        + 0.15 * (0.92 * 12)
    )
    assert abs(item.engagement.composite - expected) < 1e-9


# ---------------------------------------------------------------------------
# from_x_raw
# ---------------------------------------------------------------------------

def test_from_x_raw_creates_content_item():
    raw = {
        "uid": "sp_x001",
        "excerpt": "New perovskite tandem cells hit 33.7% efficiency in certified lab tests #solar2026",
        "link": "https://x.com/solarnews/status/sp_x001",
        "handle": "solarnews",
        "posted": "2026-02-12",
        "reason": "Breaking efficiency record announcement",
        "signal": 0.88,
        "metrics": {
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
    assert item.title == raw["excerpt"]
    assert item.author == "solarnews"
    assert item.published == "2026-02-12"
    assert item.date_quality == "high"
    # Engagement
    assert item.engagement is not None
    assert item.engagement.likes == 2100
    assert item.engagement.reposts == 380
    assert item.engagement.replies == 95
    assert item.engagement.quotes == 42
    assert item.engagement.composite is not None
    expected_composite = (
        0.45 * math.log1p(2100)
        + 0.28 * math.log1p(380)
        + 0.17 * math.log1p(95)
        + 0.10 * math.log1p(42)
    )
    assert abs(item.engagement.composite - expected_composite) < 1e-9
    # Meta
    assert item.meta["is_repost"] is False
    assert item.meta["language"] == "en"


# ---------------------------------------------------------------------------
# from_youtube_raw
# ---------------------------------------------------------------------------

def test_from_youtube_raw_creates_content_item():
    raw = {
        "uid": "sp_yt001",
        "title": "How Perovskite Tandems Will Change Solar Forever",
        "link": "https://youtube.com/watch?v=sp_yt001",
        "channel": "JustHaveFun Engineering",
        "summary": "Deep dive into perovskite-silicon tandem technology.",
        "posted": "2026-02-05",
        "metrics": {"views": 185000, "likes": 4200},
        "signal": 0.82,
        "reason": "In-depth technical explainer on tandem cells",
        "duration_seconds": 912,
    }

    item = from_youtube_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.YOUTUBE
    assert item.title == raw["title"]
    assert item.author == "JustHaveFun Engineering"
    assert item.summary == raw["summary"]
    assert item.published == "2026-02-05"
    assert item.date_quality == "high"
    # Engagement
    assert item.engagement is not None
    assert item.engagement.views == 185000
    assert item.engagement.likes == 4200
    expected_composite = 0.62 * math.log1p(185000) + 0.38 * math.log1p(4200)
    assert abs(item.engagement.composite - expected_composite) < 1e-9
    # Meta
    assert item.meta["duration_seconds"] == 912


# ---------------------------------------------------------------------------
# from_linkedin_raw
# ---------------------------------------------------------------------------

def test_from_linkedin_raw_creates_content_item():
    raw = {
        "uid": "sp_li001",
        "excerpt": "Excited to announce our lab's new perovskite stability record -- 1500 hours at 85C",
        "link": "https://linkedin.com/posts/sp_li001",
        "author": "Dr. Elena Vasquez",
        "role": "Director of PV Research, SunTech Labs",
        "posted": "2026-02-08",
        "metrics": {"reactions": 620, "comments": 41},
        "signal": 0.79,
        "reason": "Primary researcher sharing first-hand lab results",
    }

    item = from_linkedin_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.LINKEDIN
    assert item.title == raw["excerpt"]
    assert item.author == "Dr. Elena Vasquez"
    assert item.published == "2026-02-08"
    assert item.date_quality == "high"
    # Engagement
    assert item.engagement is not None
    assert item.engagement.reactions == 620
    assert item.engagement.comments == 41
    expected_composite = 0.55 * math.log1p(620) + 0.45 * math.log1p(41)
    assert abs(item.engagement.composite - expected_composite) < 1e-9
    # Meta
    assert item.meta["author_title"] == "Director of PV Research, SunTech Labs"


# ---------------------------------------------------------------------------
# from_web_raw
# ---------------------------------------------------------------------------

def test_from_web_raw_creates_content_item_with_no_engagement():
    raw = {
        "uid": "sp_w001",
        "title": "Solar Panel Efficiency Hits New Record in 2026",
        "link": "https://pv-magazine.com/2026/02/07/solar-panel-record",
        "domain": "pv-magazine.com",
        "snippet": "Researchers achieved 33.7% tandem cell efficiency...",
        "posted": "2026-02-07",
        "date_quality": "high",
        "signal": 0.75,
        "reason": "Trade press coverage of the record",
        "language": "en",
    }

    item = from_web_raw(raw, START, END)

    assert isinstance(item, ContentItem)
    assert item.source == Source.WEB
    assert item.title == raw["title"]
    assert item.author == "pv-magazine.com"
    assert item.summary == raw["snippet"]
    assert item.engagement is None
    assert item.published == "2026-02-07"
    assert item.date_quality == "high"
    assert item.meta["source_domain"] == "pv-magazine.com"
    assert item.meta["language"] == "en"


# ---------------------------------------------------------------------------
# filter_by_date
# ---------------------------------------------------------------------------

def _make_item(uid, published):
    return ContentItem(
        uid=uid,
        source=Source.REDDIT,
        title="Solar efficiency " + uid,
        link="https://example.com/" + uid,
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

    ids = [i.uid for i in filtered]
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
    assert filtered[0].uid == "dated"


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
    assert result[0]["uid"] == "d1"
    assert result[1]["uid"] == "d2"


# ---------------------------------------------------------------------------
# ContentItem.to_dict
# ---------------------------------------------------------------------------

def test_content_item_to_dict():
    sig = Engagement(upvotes=340, comments=87, vote_ratio=0.92, composite=5.5)
    item = ContentItem(
        uid="td001",
        source=Source.REDDIT,
        title="Solar panel efficiency improvements 2026",
        link="https://reddit.com/r/solar/td001",
        author="solar",
        published="2026-02-10",
        date_quality="high",
        engagement=sig,
        signal=0.91,
        reason="High relevance to query",
    )

    d = item.to_dict()

    assert isinstance(d, dict)
    assert d["uid"] == "td001"
    assert d["source"] == "reddit"
    assert d["title"] == item.title
    assert d["engagement"]["upvotes"] == 340
    assert d["engagement"]["comments"] == 87
    assert d["engagement"]["vote_ratio"] == 0.92
    assert d["engagement"]["composite"] == 5.5
    assert d["published"] == "2026-02-10"
    assert d["date_quality"] == "high"


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
    assert rpt.generated_at
    assert rpt.items == []
    assert rpt.errors == {}


# ---------------------------------------------------------------------------
# Report platform properties
# ---------------------------------------------------------------------------

def _reddit_item(uid):
    return ContentItem(
        uid=uid,
        source=Source.REDDIT,
        title="Reddit solar " + uid,
        link="https://reddit.com/" + uid,
    )


def _x_item(uid):
    return ContentItem(
        uid=uid,
        source=Source.X,
        title="X solar " + uid,
        link="https://x.com/" + uid,
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
