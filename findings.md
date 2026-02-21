# Comparative Analysis: BriefBot vs Last30Days

**Date of analysis:** 2026-02-21
**Method:** Full source-code comparison of current repo states (no git history examined)
**Scope:** SKILL.md instruction files, Python engine code, architecture, data models, CLI design, output formatting

---

## Strong Indicators

These are findings where the similarity is so specific and structural that coincidence is highly unlikely.

### S1. Identical Pipeline Architecture in SKILL.md

Both skills follow the **exact same execution pipeline** in the same order:

1. YAML frontmatter with `allowed-tools: Bash, Read, Write, AskUserQuestion, WebSearch`
2. Parse user intent into named variables before any tool calls
3. Display parsed intent to user before research
4. Run Python script in **foreground** (explicitly: "do NOT use run_in_background")
5. After script finishes, run WebSearch to supplement
6. Synthesize all sources with weight hierarchy (Reddit/X > YouTube > Web)
7. Display results by query type
8. Show stats block with engagement totals
9. Invitation with specific follow-up suggestions
10. Wait for user response; answer from research, no new searches

This is not a generic "research skill" pattern. The specific combination of steps, the explicit foreground instruction, the two-phase (Python + WebSearch) architecture, and the exact ordering are distinctive enough to constitute a signature.

### S2. Same Intent Classification System (Renamed)

| last30days        | briefbot         | Notes                  |
| ----------------- | ---------------- | ---------------------- |
| `TOPIC`           | `FOCUS_AREA`     | Same concept, renamed  |
| `TARGET_TOOL`     | `USAGE_TARGET`   | Same concept, renamed  |
| `QUERY_TYPE`      | `REQUEST_STYLE`  | Same concept, renamed  |
| `PROMPTING`       | `PROMPTING`      | Identical category     |
| `RECOMMENDATIONS` | `RANKED_CHOICES` | Same category, renamed |
| `NEWS`            | `NEWS`           | Identical category     |
| `GENERAL`         | `GENERAL`        | Identical category     |

Briefbot adds `PAPER`, `CELEBRITY`, `KNOWLEDGE`, and `MOOD` — extensions beyond the original four, but the core 4-type system is a 1:1 mapping.

### S3. Nearly Identical WebSearch Query Templates

Side-by-side comparison (last30days left, briefbot right):

**PROMPTING:**

- `{TOPIC} prompts examples 2026` vs `{FOCUS_AREA} prompt examples 2026`
- `{TOPIC} techniques tips` vs `{FOCUS_AREA} prompt framework`

**NEWS:**

- `{TOPIC} news 2026` vs `{FOCUS_AREA} latest news 2026`
- `{TOPIC} announcement update` vs `{FOCUS_AREA} breaking updates this week`

**RECOMMENDATIONS / RANKED_CHOICES:**

- `best {TOPIC} recommendations` vs `best {FOCUS_AREA} 2026`
- `most popular {TOPIC}` vs `most used {FOCUS_AREA} by teams`

**GENERAL:**

- `{TOPIC} 2026` vs `{FOCUS_AREA} 2026` (identical pattern)
- `{TOPIC} discussion` vs `{FOCUS_AREA} community discussion`

Both also share the **identical exclusion rule**: "SKIP reddit.com, x.com, twitter.com (the script already covers those)" and the **identical inclusion priority**: "blogs, tutorials, docs, news, GitHub repos."

### S4. Report Dataclass — Same Fields, Same Structure

Both `Report` classes contain these fields (names differ slightly but semantics are 1:1):

| last30days `Report`             | briefbot `Report`                    |
| ------------------------------- | ------------------------------------ |
| `topic`                         | `topic`                              |
| `range_from` / `range_to`       | `range_start` / `range_end`          |
| `generated_at`                  | `generated_at`                       |
| `mode`                          | `mode`                               |
| `openai_model_used`             | `openai_model_used`                  |
| `xai_model_used`                | `xai_model_used`                     |
| `reddit: List[RedditItem]`      | `items` filtered by `Source.REDDIT`  |
| `x: List[XItem]`                | `items` filtered by `Source.X`       |
| `youtube: List[YouTubeItem]`    | `items` filtered by `Source.YOUTUBE` |
| `web: List[WebSearchItem]`      | `items` filtered by `Source.WEB`     |
| `best_practices: List[str]`     | `best_practices: List[str]`          |
| `prompt_pack: List[str]`        | `prompt_pack: List[str]`             |
| `context_snippet_md: str`       | `context_snippet_md: str`            |
| `reddit_error`, `x_error`, etc. | `errors: Dict[str, str]`             |
| `from_cache: bool`              | `from_cache: bool`                   |
| `cache_age_hours`               | `cache_age_hours`                    |

The `best_practices`, `prompt_pack`, and `context_snippet_md` fields are particularly distinctive — they are not standard for a "research report" dataclass and appear in both with identical names and types.

### S5. Same Engagement Scoring Formula (log1p with Nearly Identical Weights)

**Reddit engagement:**

- last30days: `0.55*log1p(score) + 0.40*log1p(comments) + 0.05*(ratio*10)`
- briefbot: `0.48*log1p(upvotes) + 0.37*log1p(comments) + 0.15*(ratio*12)`

**X engagement:**

- last30days: `0.55*log1p(likes) + 0.25*log1p(reposts) + 0.15*log1p(replies) + 0.05*log1p(quotes)`
- briefbot: `0.45*log1p(likes) + 0.28*log1p(reposts) + 0.17*log1p(replies) + 0.10*log1p(quotes)`

Both use the same `math.log1p()` approach with four weighted components for X and three for Reddit. The weight ordering is identical (likes > reposts > replies > quotes). Both include a `safe_log1p` wrapper handling None/negative values identically.

### S6. Same Reddit Provider Architecture

Both use OpenAI's Responses API at `https://api.openai.com/v1/responses` with:

- `"tools": [{"type": "web_search", "filters": {"allowed_domains": ["reddit.com"]}}]`
- `"include": ["web_search_call.action.sources"]`
- Model fallback chains (briefbot: gpt-4o-mini → gpt-4o; last30days: gpt-4.1 → gpt-4o → gpt-4o-mini)
- Same error detection logic checking for "verified", "does not have access", "not available" in HTTP 400/403 responses
- Same depth configurations (quick/default/deep with min/max targets)
- Same search prompt structure: "extract core subject → search broadly → include all matches → return JSON"

### S7. Same Output Emit Modes

Both support the **exact same five modes** with the same names:

- `compact` (default) — markdown for synthesis
- `json` — full normalized data
- `md` — human-readable markdown
- `context` — compact snippet for embedding
- `path` — file path only

### S8. Same CLI Flags and Semantics

| Flag          | last30days                   | briefbot                     |
| ------------- | ---------------------------- | ---------------------------- |
| `--quick`     | 8-12 sources                 | 6-10 sources                 |
| `--deep`      | 50-70 sources                | 50-80 sources                |
| `--days=N`    | Lookback N days (default 30) | Lookback N days (default 30) |
| `--emit=MODE` | Output format                | Output format                |
| `--sources=`  | Source selection             | Source selection             |
| `--mock`      | Test fixtures                | Test fixtures                |
| `--debug`     | Verbose logging              | Verbose logging              |

### S9. Same Prompt Delivery Format

Both SKILL.md files specify this exact output structure for delivering prompts:

```
Here's your prompt for {TARGET_TOOL / USAGE_TARGET}:

---

[The actual prompt]

---

This uses [explanation of research insight applied].
```

Both also specify: "write ONE perfect prompt", "format must match what the research recommends", and warn against writing prose when research says JSON.

### S10. Same "Nano Banana Pro" Example Throughout

Both skills use "nano banana pro" as the primary worked example in SKILL.md, README.md, and argument hints. While this could reflect a shared interest in the topic, using the same niche example across both codebases is notable.

### S11. Same Freshness Assessment Function

Both `output.py` (briefbot) and `render.py` (last30days) contain a freshness check function that:

1. Counts recent items per source
2. Returns a dict with `reddit_recent`, `x_recent`, `web_recent`, `total_recent`, `total_items`, `is_sparse`, `mostly_evergreen`
3. `is_sparse` = total_recent < N (4 vs 5)
4. `mostly_evergreen` = total_recent < total_items \* 0.25 (vs 0.3)

The field names in the returned dict are **identical** across both projects.

### S12. Same Date Confidence System

Both use a three-tier system with identical names:

- `"high"` — date falls within search window
- `"med"` — date parsed but uncertain
- `"low"` — date missing or outside range

Both implement this via a function that takes `(date_str, from_date, to_date)` and returns the confidence string.

### S13. Same Follow-Up Conversation Rules

Both SKILL.md files contain nearly identical instructions:

- "DO NOT run new WebSearches — you already have the research"
- "Answer from what you learned"
- "Only do new research if the user explicitly asks about a DIFFERENT topic"
- "If they ask a question → answer from research, no new searches, no prompt"
- "If they describe something to create → write ONE perfect prompt"
- "Only produce 2-3 alternatives when explicitly asked"

---

## Mediocre Indicators

These findings show meaningful similarity but could plausibly arise from shared domain knowledge or common patterns.

### M1. Same Config File Pattern

Both store configuration at `~/.config/{skillname}/.env` with:

- Same dotenv parsing (comments, quotes, key=value)
- Environment variables taking precedence over file values
- Same key names: `OPENAI_API_KEY`, `XAI_API_KEY`, `OPENAI_MODEL_POLICY`, `XAI_MODEL_POLICY`
- Same default values: `OPENAI_MODEL_POLICY=auto`, `XAI_MODEL_POLICY=latest`

### M2. Same `validate_sources()` Function Signature and Logic

Both have a function: `validate_sources(requested, available, include_web) → (effective_sources, error_message)`

Both handle the same cases:

- `auto` maps to available platforms
- `web` always succeeds
- `both` checks if both keys exist
- Source-specific requests check for matching keys
- Same mode strings: "both", "reddit", "x", "web", "all", "reddit-web", "x-web"

### M3. Same Three-Factor Scoring Architecture

Both score items on three dimensions:

1. Relevance (model-provided signal, 0-1 scaled to 0-100)
2. Recency (days-ago based score, 0-100)
3. Engagement (log-normalized, 0-100)

Both apply:

- Separate scoring for web items (no engagement dimension)
- Source penalty for web items
- Date confidence penalties (low → penalty, high → bonus for web)
- `max(0, min(100, score))` clamping

### M4. Same ScoreParts / SubScores Concept

Both have a dataclass tracking per-dimension scores:

- last30days: `SubScores(relevance, recency, engagement)`
- briefbot: `ScoreParts(signal, freshness, engagement)`

Same fields, renamed.

### M5. Same Source Priority in Sorting

Both sort by: score (desc) → date (desc) → source priority (Reddit=0, X=1, YouTube=2, Web=3/4) → text (alphabetical tiebreaker).

### M6. Both Use ThreadPoolExecutor(max_workers=4) for Parallel Searches

Both launch Reddit, X, YouTube, and web searches in parallel using Python's `concurrent.futures.ThreadPoolExecutor`.

### M7. Same Stats Block Content

Both display engagement totals per platform with item counts. Briefbot uses a table format, last30days uses a tree format with emoji, but the content shown is the same: N threads/posts/videos, sum of upvotes/likes/views, top voices.

### M8. Same "Grounding" Instruction

Both SKILL.md files contain a nearly identical "grounding" section telling the assistant to:

- Use research content as the only source of truth
- Not conflate similar-named projects
- Use exact product names, @handles, subreddit names as they appear
- Not project pre-existing knowledge onto results

### M9. Same `to_dict()` / `from_dict()` Serialization Pattern

Both Report classes have `to_dict()` and `from_dict()` class methods with the same structure:

- `to_dict()` serializes nested objects
- `from_dict()` reconstructs from dict with engagement and comment reconstruction
- Both handle the `range` field as a nested dict: `{"from": ..., "to": ...}`

---

## Light Indicators

These are similarities that are common in the domain or could arise independently.

### L1. Both Use Python Dataclasses for Domain Models

Standard Python practice; not distinctive.

### L2. Both Parse Dates with Multiple strptime Formats

Common pattern for handling API responses.

### L3. Both Have README Examples with Worked Scenarios

Standard documentation practice.

### L4. Both Use stderr for Logging

Common pattern for CLI tools that output data on stdout.

### L5. Different Deduplication Algorithms

last30days uses Jaccard similarity on character n-grams (threshold 0.7). Briefbot uses SimHash with FNV-1a and Hamming distance (threshold 10 bits). Different approaches, though both serve the same purpose and both keep the higher-scored item.

### L6. Different HTTP Clients (Both stdlib-based)

Both implement HTTP without external dependencies, but the implementations differ: briefbot's `net.py` has a `RetryPolicy` class with configurable backoff; last30days' `http.py` has simpler retry logic.

### L7. Briefbot Has Substantial Original Additions

Features not present in last30days:

- LinkedIn as a 5th source
- Email delivery with HTML newsletter and PDF attachment
- Telegram bot listener (receive and respond to messages)
- Audio generation (ElevenLabs / edge-tts)
- CRON scheduling with job registry
- Setup wizard (interactive config)
- KNOWLEDGE query type (direct-answer, no search)
- MOOD system (hyped, skeptical, urgent, curious, neutral)
- Evidence-Weighted Triangulation (EWT) framework
- Harmonic mean scoring (vs linear weighted sum)
- `> **Try next:**` auto-suggestion system

These additions represent significant engineering effort beyond what last30days provides.

### L8. Unified vs Per-Source Item Models

last30days uses separate `RedditItem`, `XItem`, `YouTubeItem`, `WebSearchItem` classes. Briefbot unifies these into a single `ContentItem` with a `Source` enum. This is a structural refactoring, not just renaming.

---

## Summary Statistics

| Metric                           | Similarity Level                       |
| -------------------------------- | -------------------------------------- |
| Pipeline architecture (SKILL.md) | Near-identical                         |
| Intent classification system     | 1:1 mapping (renamed)                  |
| WebSearch query templates        | Near-identical                         |
| Data model (Report)              | Identical fields                       |
| Scoring approach                 | Same algorithm family, tweaked weights |
| Provider architecture (Reddit)   | Same API, same pattern                 |
| CLI flags                        | Same set                               |
| Config system                    | Same pattern                           |
| Output modes                     | Identical set                          |
| Follow-up rules                  | Near-identical                         |
| Additional features              | Substantial original work              |
