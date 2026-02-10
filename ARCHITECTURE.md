# Catchup Skill Architecture

This document explains how the `/catchup` skill works internally, for developers who want to understand, modify, or extend it.

## Overview

The `/catchup` skill is a research automation tool that discovers trending topics across multiple platforms (Reddit, X/Twitter, YouTube, LinkedIn, and the web) from the past 30 days. It synthesizes findings into actionable insights and prompts.

**Key differentiator**: Popularity-weighted ranking that combines engagement metrics (upvotes, likes, views) with relevance and recency scoring.

## Directory Structure

```
catchup-skill/
├── SKILL.md                    # Skill definition (YAML frontmatter + instructions)
├── ARCHITECTURE.md             # This file
├── README.md                   # Installation & usage examples
├── SPEC.md                     # Technical specification
├── scripts/
│   ├── catchup.py              # Main orchestrator
│   └── lib/                    # Modular utilities
│       ├── __init__.py
│       ├── cache.py            # 24-hour TTL caching
│       ├── dates.py            # Date range & recency scoring
│       ├── dedupe.py           # Near-duplicate detection
│       ├── env.py              # API key management
│       ├── http.py             # stdlib-only HTTP client
│       ├── models.py           # Auto-select OpenAI/xAI models
│       ├── normalize.py        # Raw API → canonical schema
│       ├── openai_reddit.py    # Reddit search via OpenAI web_search
│       ├── openai_youtube.py   # YouTube search via OpenAI web_search
│       ├── openai_linkedin.py  # LinkedIn search via OpenAI web_search
│       ├── reddit_enrich.py    # Fetch real Reddit engagement metrics
│       ├── render.py           # Output rendering (JSON/MD/compact)
│       ├── schema.py           # Data classes & validation
│       ├── score.py            # Popularity-aware scoring
│       ├── ui.py               # CLI progress display
│       ├── websearch.py        # Web search fallback
│       └── xai_x.py            # X search via xAI x_search tool
├── fixtures/                   # Sample API responses for testing
└── tests/                      # Test suite
```

## How the Skill is Invoked

### YAML Frontmatter (SKILL.md)

```yaml
---
name: catchup
description: Research a topic from the last 30 days on Reddit + X + YouTube + LinkedIn + Web
argument-hint: "[topic] for [tool]" or "[topic]"
context: fork
agent: Explore
disable-model-invocation: true
allowed-tools: Bash, Read, Write, AskUserQuestion, WebSearch
---
```

**Key configuration**:
- `context: fork` - Spawns a new agent context (isolates the research session)
- `agent: Explore` - Uses the Explore agent persona
- `disable-model-invocation: true` - The skill orchestrates external APIs, not Claude
- `allowed-tools` - Whitelists specific tools for the skill

### Invocation Flow

```
User: /catchup [topic] for [tool]
          ↓
    SKILL.md parsed by Claude Code
          ↓
    Explore agent dispatches via Bash:
    PY=$(python3 -c "" 2>/dev/null && echo python3 || echo python)
    $PY ~/.claude/skills/briefbot/scripts/catchup.py "$ARGUMENTS" --emit=compact
          ↓
    Script runs parallel searches → processes → outputs results
          ↓
    Claude synthesizes findings and waits for user vision
          ↓
    User shares what they want to create
          ↓
    Claude generates tailored prompts using research insights
```

## Search Implementations

### Reddit Search (`openai_reddit.py`)

**Mechanism**: Uses OpenAI's Responses API with the `web_search` tool filtered to `reddit.com`.

```python
# API endpoint
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

# Payload structure
{
    "model": "gpt-4o",  # or auto-selected model
    "tools": [{
        "type": "web_search",
        "filters": {"allowed_domains": ["reddit.com"]}
    }],
    "include": ["web_search_call.action.sources"],
    "input": "<prompt asking for Reddit threads>"
}
```

**Depth configurations** (threads to request):
- `quick`: 15-25 threads
- `default`: 30-50 threads
- `deep`: 70-100 threads

**Key features**:
- Auto-retry with simplified query if <5 results
- Model fallback chain: GPT-5 → GPT-4o → GPT-4o-mini
- Returns JSON with: title, url, subreddit, date, why_relevant, relevance

### X/Twitter Search (`xai_x.py`)

**Mechanism**: Uses xAI's Responses API with the `x_search` tool for live Twitter data.

```python
# API endpoint
XAI_RESPONSES_URL = "https://api.x.ai/v1/responses"

# Payload structure
{
    "model": "grok-4-1-fast",
    "tools": [{"type": "x_search"}],
    "input": [{"role": "user", "content": "<prompt>"}]
}
```

**Depth configurations** (posts to request):
- `quick`: 8-12 posts
- `default`: 20-30 posts
- `deep`: 40-60 posts

**Returns**: JSON with text, url, author_handle, date, engagement (likes, reposts, replies, quotes)

### YouTube Search (`openai_youtube.py`)

**Mechanism**: Uses OpenAI's Responses API with `web_search` filtered to `youtube.com`.

```python
# Payload structure
{
    "model": "gpt-4o",
    "tools": [{
        "type": "web_search",
        "filters": {"allowed_domains": ["youtube.com"]}
    }],
    "input": "<prompt asking for YouTube videos>"
}
```

**Returns**: JSON with title, url, channel_name, date, engagement (views, likes), why_relevant, relevance

### LinkedIn Search (`openai_linkedin.py`)

**Mechanism**: Uses OpenAI's Responses API with `web_search` filtered to `linkedin.com`.

```python
# Payload structure
{
    "model": "gpt-4o",
    "tools": [{
        "type": "web_search",
        "filters": {"allowed_domains": ["linkedin.com"]}
    }],
    "input": "<prompt asking for LinkedIn posts>"
}
```

**Returns**: JSON with text, url, author_name, author_title, date, engagement (reactions, comments), why_relevant, relevance

### Parallel Execution

All searches run concurrently using `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    reddit_future = executor.submit(_search_reddit, ...)
    x_future = executor.submit(_search_x, ...)
    youtube_future = executor.submit(_search_youtube, ...)
    linkedin_future = executor.submit(_search_linkedin, ...)

    # Collect results as they complete
    reddit_items, raw_openai, reddit_error = reddit_future.result()
    x_items, raw_xai, x_error = x_future.result()
    youtube_items, raw_yt, youtube_error = youtube_future.result()
    linkedin_items, raw_li, linkedin_error = linkedin_future.result()
```

## Data Schema (`schema.py`)

### Core Types

**Engagement** - Platform-specific metrics:
```python
@dataclass
class Engagement:
    # Reddit
    score: Optional[int] = None           # Upvotes
    num_comments: Optional[int] = None
    upvote_ratio: Optional[float] = None

    # X/Twitter
    likes: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    quotes: Optional[int] = None

    # YouTube
    views: Optional[int] = None
    # likes shared with X

    # LinkedIn
    reactions: Optional[int] = None
    # comments mapped to replies
```

**Item types**:
- `RedditItem`: id, title, url, subreddit, date, engagement, top_comments, comment_insights
- `XItem`: id, text, url, author_handle, date, engagement
- `YouTubeItem`: id, title, url, channel_name, date, engagement, description
- `LinkedInItem`: id, text, url, author_name, author_title, date, engagement
- `WebSearchItem`: id, title, url, source_domain, snippet, date (no engagement)

**Report** - Container for all results:
```python
@dataclass
class Report:
    topic: str
    range_from: str
    range_to: str
    mode: str  # 'both', 'reddit-only', 'all', etc.
    reddit: List[RedditItem]
    x: List[XItem]
    youtube: List[YouTubeItem]
    linkedin: List[LinkedInItem]
    web: List[WebSearchItem]
```

## Scoring System (`score.py`)

### Formula for Platforms with Engagement

```
OVERALL_SCORE =
    0.45 × RELEVANCE_SCORE +
    0.25 × RECENCY_SCORE +
    0.30 × ENGAGEMENT_SCORE
    - PENALTIES
```

### Engagement Score Formulas

**Reddit**:
```
ENG = 0.55 × log1p(score) + 0.40 × log1p(num_comments) + 0.05 × (upvote_ratio × 10)
```

**X/Twitter**:
```
ENG = 0.55 × log1p(likes) + 0.25 × log1p(reposts) + 0.15 × log1p(replies) + 0.05 × log1p(quotes)
```

**YouTube**:
```
ENG = 0.70 × log1p(views) + 0.30 × log1p(likes)
```

**LinkedIn**:
```
ENG = 0.60 × log1p(reactions) + 0.40 × log1p(comments)
```

### WebSearch (No Engagement)

```
OVERALL_SCORE =
    0.55 × RELEVANCE_SCORE +
    0.45 × RECENCY_SCORE
    - 15 (source penalty)
```

### Penalties Applied

| Condition | Penalty |
|-----------|---------|
| Unknown engagement | -10 points |
| Low date confidence | -10 points |
| Medium date confidence | -5 points |
| WebSearch source | -15 points |

### Recency Scoring

```python
def recency_score(date: str) -> int:
    """0-100 score where today=100, 30 days ago=0"""
    days_ago = (today - date).days
    return max(0, min(100, 100 - (days_ago * 100 / 30)))
```

## Processing Pipeline

```
Raw API Responses
      ↓
normalize.normalize_*_items()    # Parse to canonical schema
      ↓
normalize.filter_by_date_range() # Hard filter: exclude verified old items
      ↓
score.score_*_items()            # Compute popularity scores
      ↓
score.sort_items()               # Rank by score + date + source
      ↓
dedupe.dedupe_*()                # Remove near-duplicates
      ↓
render.render_compact()          # Output for Claude
```

## Configuration (`env.py`)

**Config file location**: `~/.config/catchup/.env`

**Supported variables**:
```env
# API Keys
OPENAI_API_KEY=sk-...    # Required for Reddit, YouTube, LinkedIn
XAI_API_KEY=xai-...      # Required for X/Twitter

# Model selection
OPENAI_MODEL_POLICY=auto  # 'auto' or 'pinned'
OPENAI_MODEL_PIN=gpt-4o   # Manual override
XAI_MODEL_POLICY=latest   # 'latest', 'stable', or 'pinned'
XAI_MODEL_PIN=grok-4-1-fast
```

**Source modes** (based on available keys):
- Both keys → `both` (Reddit + X) or `all` (all sources)
- OpenAI only → `reddit-only` (also enables YouTube/LinkedIn)
- xAI only → `x-only`
- Neither → `web-only` (WebSearch fallback)

## Output Modes (`--emit`)

| Mode | Description |
|------|-------------|
| `compact` | Markdown for Claude synthesis (default, 15 items per source) |
| `json` | Full normalized report as JSON |
| `md` | Full human-readable markdown |
| `context` | Compact snippet for embedding |
| `path` | File path only |

## Reddit Enrichment (`reddit_enrich.py`)

After discovering Reddit threads, the skill fetches real engagement data:

```python
# Public JSON endpoint (no API key needed)
url = f"https://www.reddit.com{path}.json?raw_json=1"
```

**Extracts**:
- Submission: score, num_comments, upvote_ratio, created_utc
- Top comments: author, score, text, permalink
- Comment insights: Key quotes from discussion

## HTTP Client (`http.py`)

**stdlib-only** - No external dependencies (no `requests`).

**Features**:
- User-Agent: `catchup-skill/1.0 (Claude Code Skill)`
- Retry logic: 3 attempts with exponential backoff (1s, 2s, 3s)
- 4xx errors: No retry (except 429 rate limits)
- 5xx errors: Retry with backoff

## Caching (`cache.py`)

- **TTL**: 24 hours
- **Key**: Topic + date range hash
- **Location**: `~/.cache/catchup/`

## Output Location

Generated files go to: `~/.local/share/catchup/out/`
- `report.json` - Full normalized data
- `report.md` - Human-readable report
- `catchup.context.md` - Snippet for other tools
- `raw_*.json` - Raw API responses (debugging)

## Extension Points

### Adding a New Source

1. Create `lib/openai_newplatform.py`:
   - Define `DEPTH_CONFIG` and search prompt
   - Implement `search_newplatform()` and `parse_newplatform_response()`

2. Update `schema.py`:
   - Add `NewPlatformItem` dataclass
   - Add `newplatform: List[NewPlatformItem]` to `Report`

3. Update `score.py`:
   - Add `compute_newplatform_engagement_raw()`
   - Add `score_newplatform_items()`

4. Update `normalize.py`:
   - Add `normalize_newplatform_items()`

5. Update `catchup.py`:
   - Import new module
   - Add to parallel execution
   - Add to processing pipeline

6. Update `render.py`:
   - Add rendering for new platform items

7. Update `env.py` (if new API key needed):
   - Add to `get_config()`
   - Update `get_available_sources()`
