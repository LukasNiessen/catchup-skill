# BriefBot Skill Architecture

This document explains how the `/briefbot` skill works internally, for developers who want to understand, modify, or extend it.

## Overview

The `/briefbot` skill is a research automation tool that discovers trending topics across multiple platforms (Reddit, X/Twitter, YouTube, LinkedIn, and the web) from the past 30 days. It synthesizes findings into actionable insights and prompts.

**Key differentiator**: Percentile-harmonic scoring that combines engagement metrics (upvotes, likes, views) with relevance and recency via weighted harmonic mean.

## Directory Structure

```
briefbot-skill/
├── SKILL.md                        # Skill definition (YAML frontmatter + instructions)
├── ARCHITECTURE.md                 # This file
├── README.md                       # Installation & usage examples
├── SPEC.md                         # Technical specification
├── scripts/
│   ├── briefbot.py                 # Main orchestrator
│   ├── deliver.py                  # Standalone delivery (email/audio/telegram)
│   ├── run_job.py                  # Scheduled job runner
│   ├── setup.py                    # Interactive setup wizard
│   ├── telegram_bot.py             # Telegram bot listener
│   └── briefbot_engine/            # Core package
│       ├── __init__.py
│       ├── content.py              # Unified ContentItem model + factory functions
│       ├── ranking.py              # Percentile-harmonic scoring + SimHash dedup
│       ├── temporal.py             # Date windowing, parsing, freshness scoring
│       ├── config.py               # API key & credential management
│       ├── net.py                  # stdlib-only HTTP client with retry
│       ├── output.py               # Report rendering (JSON/MD/compact)
│       ├── terminal.py             # CLI progress display & spinner
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── registry.py         # Response caching + model selection
│       │   ├── reddit.py           # Reddit search via OpenAI web_search
│       │   ├── twitter.py          # X search via xAI x_search
│       │   ├── youtube.py          # YouTube search via OpenAI web_search
│       │   ├── linkedin.py         # LinkedIn search via OpenAI web_search
│       │   ├── enrich.py           # Reddit thread enrichment (engagement + comments)
│       │   ├── web.py              # Web search fallback
│       │   └── claude_web.py       # Claude web search provider
│       ├── delivery/
│       │   ├── __init__.py
│       │   ├── email.py            # SMTP email with HTML newsletter
│       │   ├── telegram.py         # Telegram message delivery
│       │   ├── audio.py            # TTS audio generation (ElevenLabs / edge-tts)
│       │   └── document.py         # PDF generation
│       ├── scheduling/
│       │   ├── __init__.py
│       │   ├── cron.py             # Cron expression parsing
│       │   ├── jobs.py             # Job registry (CRUD)
│       │   └── platform.py         # OS scheduler (crontab / schtasks)
│       ├── extras/
│       │   ├── __init__.py
├── fixtures/                       # Sample API responses for testing
└── tests/                          # Test suite (pure pytest)
```

## How the Skill is Invoked

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
          ↓
    SKILL.md parsed by Claude Code
          ↓
    Agent dispatches via Bash:
    python scripts/briefbot.py "$ARGUMENTS" --emit=compact
          ↓
    Script runs parallel searches → processes → outputs results
          ↓
    Claude synthesizes findings and waits for user direction
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
class Signals:
    """Platform-agnostic engagement metrics."""
    composite: Optional[float] = None   # Pre-computed aggregate
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
class ContentItem:
    item_id: str
    source: Source
    headline: str           # title/text
    permalink: str          # url
    author: str = ""        # subreddit/handle/channel/domain
    body: str = ""          # description/snippet
    published: Optional[str] = None
    date_trust: str = "low"
    signals: Optional[Signals] = None
    relevance: float = 0.5
    rationale: str = ""
    score: int = 0
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    thread_comments: List[ThreadComment] = field(default_factory=list)
    thread_insights: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
```

**Report** stores all items in a single list with property-based filtering:

```python
@dataclass
class Report:
    topic: str
    range_start: str
    range_end: str
    items: List[ContentItem] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)

    @property
    def reddit(self) -> List[ContentItem]:
        return [i for i in self.items if i.source == Source.REDDIT]
    # ... same for x, youtube, linkedin, web
```

Factory functions convert raw API responses to ContentItem:
- `from_reddit_raw(entry, start, end) -> ContentItem`
- `from_x_raw(entry, start, end) -> ContentItem`
- `from_youtube_raw(entry, start, end) -> ContentItem`
- `from_linkedin_raw(entry, start, end) -> ContentItem`
- `from_web_raw(entry, start, end) -> ContentItem`

## Scoring System (`ranking.py`)

### Percentile-Harmonic Scoring

Instead of linear weighted sums, scoring uses **percentile ranks** combined via **weighted harmonic mean**:

1. Convert raw values (relevance, recency, engagement) to **percentile ranks** (0-100) across the batch
2. Combine dimensions via **weighted harmonic mean** — naturally penalizes items weak in any dimension
3. Apply post-harmonic confidence adjustments (additive penalties/bonuses)

**Dimension weights (platform items)**:
- Relevance: 0.38
- Recency: 0.34
- Engagement: 0.28

**Dimension weights (web items, no engagement)**:
- Relevance: 0.58
- Recency: 0.42

### SimHash Deduplication

Near-duplicate detection uses **SimHash** 64-bit fingerprinting:

1. Tokenize headline into 3-gram shingles
2. Hash each shingle with FNV-1a (64-bit)
3. Aggregate into a single 64-bit fingerprint
4. Compare fingerprints via **Hamming distance** (threshold: ≤10 bits)
5. Keep the higher-scored item from each duplicate pair

## Search Providers

### Reddit (`providers/reddit.py`)

Uses OpenAI's Responses API with `web_search` filtered to `reddit.com`.

### X/Twitter (`providers/twitter.py`)

Uses xAI's Responses API with `x_search` for live Twitter data.



### YouTube (`providers/youtube.py`)

Uses OpenAI's Responses API with `web_search` filtered to `youtube.com`.

### LinkedIn (`providers/linkedin.py`)

Uses OpenAI's Responses API with `web_search` filtered to `linkedin.com`.

### Parallel Execution

All searches run concurrently using `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=4) as executor:
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
      ↓
content.items_from_raw()         # Factory functions → ContentItem list
      ↓
content.filter_by_date()         # Hard filter: exclude out-of-range items
      ↓
ranking.rank_items()             # Percentile-harmonic scoring (all items at once)
      ↓
ranking.deduplicate()            # SimHash fingerprint dedup
      ↓
output.compact()                 # Render for Claude
```

## Provider Registry (`providers/registry.py`)

Unified class managing:
- **Response caching**: JSON files with TTL (default 18 hours)
- **Model selection**: Auto-selects latest OpenAI/xAI models with preference lists
- **Model preference persistence**: Caches selected model for 5 days

## Configuration (`config.py`)

**Config file**: `~/.config/briefbot/.env`

```env
OPENAI_API_KEY=sk-...      # Reddit, YouTube, LinkedIn
XAI_API_KEY=xai-...        # X/Twitter
ELEVENLABS_API_KEY=...     # Premium TTS (optional)
TELEGRAM_BOT_TOKEN=...     # Telegram delivery (optional)
```

**Source modes** (based on available keys):
- Both keys → `both` (Reddit + X + YouTube + LinkedIn)
- OpenAI only → `reddit` (Reddit + YouTube + LinkedIn)
- xAI only → `x` (X/Twitter only)
- Neither → `web` (WebSearch fallback)

## Output Modes (`--emit`)

| Mode | Description |
|------|-------------|
| `compact` | Markdown for Claude synthesis (default) |
| `json` | Full normalized report as JSON |
| `md` | Full human-readable markdown |
| `context` | Compact snippet for embedding |
| `path` | File path only |

## Extension Points

### Adding a New Source

1. Create `briefbot_engine/providers/newplatform.py`:
   - Implement `search_newplatform()` and `parse_response()`

2. Update `content.py`:
   - Add `Source.NEWPLATFORM` enum value
   - Add `from_newplatform_raw()` factory function

3. Update `briefbot.py`:
   - Import new provider
   - Add to parallel execution
   - Feed items through `items_from_raw()` pipeline

4. Update `output.py`:
   - Add rendering for new platform items

5. Update `config.py` (if new API key needed):
   - Add to `load_config()` and `determine_available_platforms()`



