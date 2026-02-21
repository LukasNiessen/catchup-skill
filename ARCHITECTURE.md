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
- SPEC.md
- scripts/
  - briefbot.py
  - deliver.py
  - run_job.py
  - setup.py
  - telegram_bot.py
  - briefbot_engine/
    - content.py
    - ranking.py
    - temporal.py
    - config.py
    - net.py
    - output.py
    - terminal.py
    - providers/
      - registry.py
      - reddit.py
      - twitter.py
      - youtube.py
      - linkedin.py
      - enrich.py
      - web.py
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
     python scripts/briefbot.py "$ARGUMENTS" --emit=compact
  -> Script runs parallel searches -> processes -> outputs results
  -> Claude synthesizes findings and waits for user direction
```

## Unified Content Model (`content.py`)

All platform results share a single `ContentItem` dataclass:

```python
class Source(Enum):
    REDDIT = "reddit"
    X = "x"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    WEB = "web"

@dataclass
class Engagement:
    composite: Optional[float] = None
    upvotes: Optional[int] = None
    comments: Optional[int] = None
    vote_ratio: Optional[float] = None
    likes: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    quotes: Optional[int] = None
    views: Optional[int] = None
    reactions: Optional[int] = None
    bookmarks: Optional[int] = None

@dataclass
class ScoreBreakdown:
    relevance: int = 0
    timeliness: int = 0
    traction: int = 0
    credibility: int = 0

@dataclass
class ContentItem:
    uid: str
    source: Source
    title: str
    link: str
    author: str = ""
    summary: str = ""
    published: Optional[str] = None
    date_confidence: str = "weak"
    engagement: Optional[Engagement] = None
    relevance: float = 0.5
    reason: str = ""
    score: int = 0
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    comments: List[CommentNote] = field(default_factory=list)
    comment_highlights: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
```

Report stores items with property-based filtering:

```python
@dataclass
class Report:
    topic: str
    window: Window
    generated_at: str
    mode: str
    models: ModelUsage
    items: List[ContentItem] = field(default_factory=list)
    errors: ErrorBag = field(default_factory=ErrorBag)

    @property
    def reddit(self) -> List[ContentItem]:
        return [i for i in self.items if i.source == Source.REDDIT]
```

Factory functions convert raw API responses to ContentItem:
- `from_reddit_raw(entry, start, end) -> ContentItem`
- `from_x_raw(entry, start, end) -> ContentItem`
- `from_youtube_raw(entry, start, end) -> ContentItem`
- `from_linkedin_raw(entry, start, end) -> ContentItem`
- `from_web_raw(entry, start, end) -> ContentItem`

## Scoring System (`ranking.py`)

### Percentile + Power-Mean Scoring

Instead of linear weighted sums, scoring uses percentile ranks combined via a weighted power mean:

1. Convert raw values (relevance, timeliness, traction) to percentile ranks (0-100)
2. Add credibility as a source-weighted adjustment
3. Combine dimensions via weighted power mean, then apply confidence penalties/bonuses

Dimension weights (platform items):
- Relevance: 0.40
- Timeliness: 0.28
- Traction: 0.22
- Credibility: 0.10

Dimension weights (web items):
- Relevance: 0.58
- Timeliness: 0.30
- Credibility: 0.12

### SimHash Deduplication

Near-duplicate detection uses SimHash with a 64-bit fingerprint and Hamming distance threshold <= 10 bits.

## Search Providers

- Reddit (`providers/reddit.py`): OpenAI Responses API with `web_search` filtered to `reddit.com`
- X/Twitter (`providers/twitter.py`): xAI Responses API with `x_search`
- YouTube (`providers/youtube.py`): OpenAI Responses API with `web_search` filtered to `youtube.com`
- LinkedIn (`providers/linkedin.py`): OpenAI Responses API with `web_search` filtered to `linkedin.com`
- Web (`providers/web.py`): WebSearch fallback with domain exclusions

## Parallel Execution

All searches run concurrently using `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {
        executor.submit(_search_reddit, ...): "reddit",
        executor.submit(_search_x, ...): "x",
        executor.submit(_search_youtube, ...): "youtube",
        executor.submit(_search_linkedin, ...): "linkedin",
    }
```

## Processing Pipeline

```
Raw API Responses
  -> content.items_from_raw()
  -> content.filter_by_date()
  -> ranking.rank_items()
  -> ranking.deduplicate()
  -> output.compact()
```

## Configuration (`config.py`)

Config file: `~/.config/briefbot/briefbot.env` (legacy `.env` still supported)

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

## Output Modes (`--emit`)

| Mode | Description |
|------|-------------|
| `compact` | Markdown for Claude synthesis (default) |
| `json` | Full normalized report as JSON |
| `md` | Full human-readable markdown |
| `context` | Compact snippet for embedding |
| `path` | File path only |
| `cards` | Compact card-style summary |

## Extension Points

Adding a new source:
1. Create `briefbot_engine/providers/newplatform.py`
2. Add `Source.NEWPLATFORM` and `from_newplatform_raw()` in `content.py`
3. Wire it into `briefbot.py` parallel execution and normalization
4. Add rendering in `output.py`
5. Add config keys and source resolution in `config.py` if needed
