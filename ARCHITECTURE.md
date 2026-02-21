# BriefBot Skill Architecture

This document explains how the `/briefbot` skill works internally for developers who want to understand, modify, or extend it.

## Overview

The `/briefbot` skill is a research automation tool that discovers recent topics across multiple platforms (Reddit, X/Twitter, YouTube, LinkedIn, and the web) for the last N days. It normalizes results into a single data model, scores them, and produces a report for Claude to synthesize.

Key differentiator: percentile + power-mean scoring that blends relevance, timeliness, engagement, and credibility into a single score.

## Directory Structure

```
briefbot-skill/
- SKILL.md
- ARCHITECTURE.md
- README.md
- scripts/
  - briefbot.py
  - deliver.py
  - run.sh
  - run_job.py
  - setup.py
  - telegram_bot.py
  - briefbot_engine/
    - analysis.py
    - console.py
    - http_client.py
    - locations.py
    - presenter.py
    - records.py
    - scoring.py
    - settings.py
    - timeframe.py
    - sources/
      - catalog.py
      - reddit_source.py
      - x_posts.py
      - youtube_feed.py
      - linkedin_feed.py
      - hydrate.py
      - webscan.py
      - claude_web.py
    - delivery/
    - scheduling/
- fixtures/
- tests/
```

## How the Skill Is Invoked

### YAML Frontmatter (SKILL.md)

```yaml
---
name: briefbot
description: Research a topic from the last 30 days on Reddit + X + YouTube + LinkedIn + Web
argument-hint: "[topic] for [tool]" or "[topic]"
context: fork
disable-model-invocation: true
allowed-tools: Bash, Read, Write, AskUserQuestion, WebSearch
---
```

### Invocation Flow

```
User: /briefbot [topic] for [tool]
  -> SKILL.md parsed by Claude Code
  -> Agent dispatches via Bash:
     python scripts/briefbot.py "$ARGUMENTS" --view=snapshot
  -> Script runs parallel searches -> processes -> outputs results
  -> Claude synthesizes findings and waits for user direction
```

## Unified Content Model (`records.py`)

All platform results share a single `Signal` object with shared metadata:

```python
class Channel(Enum):
    REDDIT = "reddit"
    X = "x"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    WEB = "web"

@dataclass
class Interaction:
    pulse: Optional[float]
    upvotes: Optional[int]
    comments: Optional[int]
    ratio: Optional[float]
    likes: Optional[int]
    reposts: Optional[int]
    replies: Optional[int]
    quotes: Optional[int]
    views: Optional[int]
    reactions: Optional[int]
    bookmarks: Optional[int]

@dataclass
class Scorecard:
    topicality: int
    freshness: int
    traction: int
    trust: int

@dataclass
class Signal:
    key: str
    channel: Channel
    headline: str
    url: str
    byline: str = ""
    blurb: str = ""
    dated: Optional[str] = None
    time_confidence: str = "low"
    interaction: Optional[Interaction] = None
    topicality: float = 0.5
    rationale: str = ""
    rank: int = 0
    scorecard: Scorecard = field(default_factory=Scorecard)
    thread_notes: List[ThreadNote] = field(default_factory=list)
    notables: List[str] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)
```

Reports store items on a `Brief` object with channel helpers:

```python
@dataclass
class Brief:
    topic: str
    span: Span
    generated_at: str
    mode: str
    items: List[Signal] = field(default_factory=list)

    @property
    def reddit(self) -> List[Signal]:
        return [i for i in self.items if i.channel == Channel.REDDIT]
```

Normalization helpers live in `records.items_from_raw()` and `records.filter_by_date()`.

## Scoring System (`scoring.py`)

### Percentile + Geometric Blend

Scores are derived by percentile-normalizing topicality, freshness, traction, and trust, then blending via a weighted geometric mean. This emphasizes consistent strength across dimensions instead of allowing a single dominant metric to overwhelm the rank.

Platform weights:
- Topicality: 0.38
- Freshness: 0.27
- Traction: 0.23
- Trust: 0.12

Web weights:
- Topicality: 0.52
- Freshness: 0.33
- Trust: 0.15

### Jaccard Shingle Deduplication

Near-duplicates are detected using word-shingle Jaccard similarity and suppressed before the final ranking pass.

## Search Providers

- Reddit (`sources/reddit_source.py`): OpenAI Responses API with `web_search` filtered to `reddit.com`
- X/Twitter (`sources/x_posts.py`): xAI Responses API with `x_search`
- YouTube (`sources/youtube_feed.py`): OpenAI Responses API with `web_search` filtered to `youtube.com`
- LinkedIn (`sources/linkedin_feed.py`): OpenAI Responses API with `web_search` filtered to `linkedin.com`
- Web (`sources/webscan.py`): WebSearch fallback with domain exclusions

## Parallel Execution

All searches run concurrently using `ThreadPoolExecutor` with a task registry:

```python
work = [
    ("reddit", _query_reddit),
    ("x", _query_x),
    ("youtube", _query_youtube),
    ("linkedin", _query_linkedin),
]
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(fn, ...): name for name, fn in work}
```

## Processing Pipeline

```
Raw API Responses
  -> records.items_from_raw()
  -> records.filter_by_date()
  -> scoring.rank_items()
  -> scoring.deduplicate()
  -> presenter.render_snapshot()
```

## Configuration (`settings.py`)

Config file: `~/.config/briefbot/briefbot.env` (legacy `~/.config/briefbot/.env` still supported)

```env
OPENAI_API_KEY=sk-...      # Reddit, YouTube, LinkedIn
XAI_API_KEY=xai-...        # X/Twitter
ELEVENLABS_API_KEY=...     # Premium TTS (optional)
TELEGRAM_BOT_TOKEN=...     # Telegram delivery (optional)
```

Source modes (based on available keys):
- Both keys -> `both`
- OpenAI only -> `reddit`
- xAI only -> `x`
- Neither -> `web`

## Output Modes (`--view`)

| Mode | Description |
|------|-------------|
| `snapshot` | Markdown for Claude synthesis (default) |
| `json` | Full normalized report as JSON |
| `md` | Full human-readable markdown |
| `context` | Compact snippet for embedding |
| `path` | File path only |
| `cards` | Compact card-style summary |

## Extension Points

Adding a new source:
1. Create `briefbot_engine/sources/new_platform.py`
2. Add `Channel.NEW_PLATFORM` and a normalizer in `records.items_from_raw()`
3. Wire it into `briefbot.py` query orchestration
4. Add rendering in `presenter.py`
5. Update `settings.resolve_sources()` if new keys or modes are needed
