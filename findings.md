# BriefBot vs Last30Days: Code Provenance Analysis

**Date:** 2026-02-19
**Methodology:** Exhaustive file-by-file comparison of all shared library modules (`scripts/lib/`), main orchestrator scripts, fixture data, vendored dependencies, and git history. Every function, constant, algorithm, regex pattern, and data structure was compared side-by-side.

---

## Timeline

| Project | Initial Commit | First Commit Date |
|---------|---------------|-------------------|
| **Last30Days** | `5ca4829` "Initial commit: last30days skill" | **2026-01-23** |
| **BriefBot** | `02d0ec3` "Init" | **2026-02-04** |

Last30Days predates BriefBot by **12 days**.

---

## STRONG INDICATORS

These findings, taken together, make it nearly certain that BriefBot was derived from Last30Days.

### 1. Identical Engagement Formulas With Specific Non-Obvious Coefficient Choices

`score.py` in both projects uses the exact same platform-specific engagement formulas with the same arbitrary coefficient choices:

**Reddit engagement** (both files):
```
0.55 * log1p(score) + 0.40 * log1p(comments) + 0.05 * (upvote_ratio or 0.5) * 10
```

**X engagement** (both files):
```
0.55 * log1p(likes) + 0.25 * log1p(reposts) + 0.15 * log1p(replies) + 0.05 * log1p(quotes)
```

These are not standard formulas from any published source. The specific coefficient choices (0.55/0.40/0.05 for Reddit, 0.55/0.25/0.15/0.05 for X), the use of `log1p` for all terms, the `* 10` scaling on upvote_ratio, and the `or 0.5` default are all implementation-specific decisions that two independent developers would not arrive at independently.

The normalization/rescaling algorithm (`_to_pct` / `normalize_to_100`) is also functionally identical: filter valid values, find min/max, rescale to 0-100, return 50 for all-equal edge case, pass through None.

### 2. Identical 8-Stage HTTP Error Handling Architecture

`http.py` in both projects implements the exact same retry architecture with the same specific design decisions in the same order:

1. Same `HTTPError` exception class with `status_code` and `body` attributes
2. Same 4 exception handler types caught in the **same order**: `urllib.error.HTTPError` → `urllib.error.URLError` → `json.JSONDecodeError` → `(OSError, TimeoutError, ConnectionResetError)`
3. Same "skip retry on 4xx except 429" rule
4. Same linear backoff formula: `delay * (attempt + 1)` (not exponential, not jittered -- this specific choice is notable)
5. Same immediate raise on `JSONDecodeError` (no retry)
6. Same final fallback: `raise HTTPError("Request failed with no error details")`
7. Same bare `except:` to catch read failures when reading HTTP error bodies
8. Same unused `urlencode` import in both files (a dead import that was never cleaned up)

Constants: `timeout=30`, `max_retries=3`, `backoff=1.0` -- all identical.

The Reddit JSON function uses identical URL construction: strip trailing `/`, prepend `/` if missing, append `.json`, add `?raw_json=1` query parameter.

### 3. Response Parsing Algorithm Is Structurally Identical Across 4 Files

Both `openai_reddit.py` and `xai_x.py` in each project use the **exact same multi-branch output extraction algorithm** for parsing OpenAI/xAI Responses API output:

1. Check `"output"` key
2. If string → use directly
3. If list → iterate elements:
   - Check for `type == "message"` → iterate `content` blocks → check for `type == "output_text"`
   - Check for `"text"` key in dict elements
   - Handle bare string elements
4. `break` on first found text
5. Legacy `"choices"` format fallback
6. Same regex for JSON extraction: `r'\{[\s\S]*"items"[\s\S]*\}'`
7. Same item validation loop with same field processing, same date regex `r'^\d{4}-\d{2}-\d{2}$'`, same ID prefix patterns (`R{n}`, `X{n}`)

This is a highly specific parsing algorithm with non-obvious design decisions (the 5-level nested check, the specific `break` behavior, the legacy fallback). Two independent implementations would not produce this exact same structure.

### 4. Identical Data Class Hierarchy With Same Fields, Types, and Serialization

`schema.py` defines the same class hierarchy in both projects:

| Class | Shared Fields | Verdict |
|-------|--------------|---------|
| `Engagement` | 8 identical fields (score, num_comments, upvote_ratio, likes, reposts, replies, quotes, views) | Functionally identical |
| `Comment` | 5 identical fields (score, date, author, excerpt, url) | Functionally identical |
| `SubScores` | 3 identical fields (relevance, recency, engagement) | Functionally identical |
| `RedditItem` | All 13 fields identical with same types and defaults | Functionally identical |
| `XItem` | All 11 fields identical | Functionally identical |
| `WebSearchItem` | All 11 fields identical | Functionally identical |
| `Report` | Same structure, same `to_dict()`/`from_dict()` pattern | Functionally identical |

The `to_dict()` methods use the same serialization pattern throughout: check each field for `not None`, add to dict, return `None` when all empty (for `Engagement`). The `from_dict()` classmethod uses the same reconstruction strategy: parse range section, loop-reconstruct each item type, handle nested `Engagement` and `Comment` objects.

The only differences are: BriefBot adds `LinkedInItem` and two extra `Engagement` fields (`reactions`, `comments`); factory function is named `make_report` vs `create_report`; docstrings say "Canonical" vs "Normalized".

### 5. Identical Reddit Enrichment Pipeline With Same Constants and Regex

`reddit_enrich.py` shares the same enrichment pipeline:

- Same URL parsing: `urlparse(url)`, check `"reddit.com" in parsed.netloc`, return `parsed.path`
- Same thread structure parsing: `data[0]` for submission, `data[1]` for comments, same 7 submission fields, same 5 comment fields
- Same top-comments filtering: limit=10, exclusion set `{"[deleted]", "[removed]"}`, sort by score descending
- Same insight extraction: limit=7, candidate pool = `limit * 2`, minimum body length = 30 chars
- Same 4 low-value comment regex patterns (character-for-character identical):
  ```
  r'^(this|same|agreed|exactly|yep|nope|yes|no|thanks|thank you)\.?$'
  r'^lol|lmao|haha'
  r'^\[deleted\]'
  r'^\[removed\]'
  ```
- Same truncation: 150 chars with sentence boundary detection (search for `.!?` after position 50), else append `"..."`
- Same engagement output dict keys: `score`, `num_comments`, `upvote_ratio`
- Same comment output: `body[:200]` as excerpt, URL prefix `"https://reddit.com"`
- Same Reddit selftext truncation: `[:500]`
- Same comment body truncation: `[:300]`

### 6. Model Fixture Files Have Timestamps Offset by Exactly +86400 Seconds

`models_openai_sample.json` and `models_xai_sample.json` contain the **same models in the same order** with every timestamp offset by exactly **+86400 seconds (1 day)**:

| Model | BriefBot `created` | Last30Days `created` | Delta |
|-------|-------------------|---------------------|-------|
| gpt-5.2 | 1704153600 | 1704067200 | +86400 |
| gpt-5.1 | 1701475200 | 1701388800 | +86400 |
| gpt-5 | 1698796800 | 1698710400 | +86400 |
| gpt-5-mini | 1704153600 | 1704067200 | +86400 |
| gpt-4o | 1683244800 | 1683158400 | +86400 |
| gpt-4-turbo | 1680652800 | 1680566400 | +86400 |

The xAI fixture shows the same +86400 pattern across all 3 models (`grok-4-latest`, `grok-4`, `grok-3`).

This is a forensic fingerprint: someone took the original fixtures and added exactly 1 day to every timestamp to make them "different" while preserving the structure. This degree of mechanical precision is a hallmark of automated or deliberate derivation.

### 7. Identical Websearch Date Extraction System

`websearch.py` shares the same date extraction system across both projects:

- Same 3 URL regex patterns: `/YYYY/MM/DD/`, `/YYYY-MM-DD-/`, `/YYYYMMDD/`
- Same year validation range: `2020 <= year <= 2030`
- Same 3 text date patterns: "Month DD, YYYY", "DD Month YYYY", ISO "YYYY-MM-DD"
- Same 25-entry month mapping dict (including uncommon aliases like `"sept"` for 9)
- Same relative date handling: "yesterday" (-1), "today" (0), "N days ago" (limit: 60), "N hours ago" (→ today), "last week" (-7), "this week" (-3)
- Same detection priority: URL ("high") → snippet ("med") → title ("med") → fallback `(None, "low")`
- Same 8 excluded domains: `reddit.com`, `www.reddit.com`, `old.reddit.com`, `twitter.com`, `www.twitter.com`, `x.com`, `www.x.com`, `mobile.twitter.com`
- Same domain extraction: `urlparse().netloc.lower()`, strip `"www."` prefix
- Same result processing pipeline with same truncation limits (title: 200, snippet: 500)
- Same URL deduplication: `.lower().rstrip("/")`

### 8. Identical Deduplication Algorithm With Same Parameters

`dedupe.py` implements the same n-gram Jaccard similarity algorithm:

- Same text normalization: `re.sub(r'[^\w\s]', ' ', text.lower())` then `re.sub(r'\s+', ' ', ...).strip()`
- Same character n-gram extraction with default `n=3`
- Same Jaccard coefficient: `|intersection| / |union|` with zero-union guard
- Same O(n^2) pairwise comparison with default threshold `0.7`
- Same tie-breaking: keep higher-scored item, discard the other
- Same early return: `if len(items) <= 1: return items`
- Same platform-specific convenience wrappers: `dedupe_reddit()`, `dedupe_x()`, `dedupe_youtube()`

### 9. Prompts Are Semantically Identical With Systematic Rewording

The discovery prompts in `openai_reddit.py` and `xai_x.py` request the same information, use the same placeholder variables (`{topic}`, `{from_date}`, `{to_date}`, `{min_items}`, `{max_items}`), specify the same JSON schema with the same fields, and contain the same rules -- but every sentence is reworded:

**Reddit prompt comparison (selected lines):**
| BriefBot | Last30Days |
|----------|------------|
| `"Search Reddit for discussions about: {topic}"` | `"Find Reddit discussion threads about: {topic}"` |
| `"Target {min_items}-{max_items} threads. Err on the side of more."` | `"Find {min_items}-{max_items} threads. Return MORE rather than fewer."` |
| `"must contain /r/ and /comments/"` | same rule, labeled `REQUIRED:` |
| `"Skip any developers.reddit.com or business.reddit.com links"` | same rule, labeled `REJECT:` |

**X prompt comparison (selected lines):**
| BriefBot | Last30Days |
|----------|------------|
| `"Use your X search capability to find posts about: {topic}"` | `"You have access to real-time X (Twitter) data. Search for posts about: {topic}"` |
| `"Return ONLY valid JSON -- no surrounding text:"` | `"IMPORTANT: Return ONLY valid JSON in this exact format, no other text:"` |
| `"Favor substantive posts over link-only shares"` | `"Prefer posts with substantive content, not just links"` |
| `"Seek varied perspectives where possible"` | `"Include diverse voices/accounts if applicable"` |

Every rule has a 1:1 counterpart. The JSON schemas are identical in structure and field names. The semantic equivalence combined with systematic rewording is consistent with LLM-assisted paraphrasing.

### 10. Main Orchestrator Pipeline Follows Same 20+ Step Sequence

Both `briefbot.py` and `last30days.py` follow the same pipeline in the same order:

```
parse args → set debug env var → determine depth → load config → detect platforms →
validate sources → compute date range → identify missing keys → init progress UI →
show promo → select models → determine mode string → call run_research() →
normalize items → date filter → score per-platform → sort/rank → dedupe per-platform →
create Report object → generate context snippet → write artifacts → show completion →
emit output
```

Both use `ThreadPoolExecutor` for concurrent platform queries with the same future-submission pattern. Both have the same `load_fixture()` helper function. Both have the same sparse-results retry logic (threshold: `< 5` items, retry with simplified query via core subject extraction, merge by URL dedup).

The argument parser shares: `--mock`, `--emit` (same 5 choices), `--sources`, `--quick`, `--deep`, `--debug`, `--days` (default 30), `--include-web`. The WebSearch fallback instruction block printed to stdout is nearly word-for-word identical.

### 11. Identical Cache Architecture

`cache.py` shares the same caching system:

- Same SHA-256 key generation with `[:16]` truncation
- Same pipe-delimited key format: `topic|from_date|to_date|sources`
- Same `~/.cache/<name>/` storage layout with `.json` files
- Same `st_mtime`-based TTL validation: `(now_utc - mtime_utc).total_seconds() / 3600`
- Same TTL values: 24 hours (standard), 7 days (model selection)
- Same `model_selection.json` file with `updated_at` ISO timestamp and per-provider keys
- Same error swallowing pattern: `except OSError: pass` on cache write failures, `except (json.JSONDecodeError, OSError)` on cache reads
- Same `load_with_age` returning `(data, hours)` or `(None, None)` tuple
- Same `clear_all`/`clear_cache` using glob `*.json` + unlink

All 12 cache functions map 1:1 with identical logic.

### 12. Identical Date Utility Functions

`dates.py` shares 6 identical functions:

- Same 5 date format strings in the same order (including the uncommon `"%Y-%m-%dT%H:%M:%S.%f%z"`)
- Same `parse_date()` algorithm: try `float()` first (with comment about Reddit timestamps), then loop through format strings with `strptime`
- Same exception tuple: `(ValueError, TypeError, OSError)` -- the inclusion of `OSError` is non-obvious
- Same `timestamp_to_date()`: `datetime.fromtimestamp(ts, timezone.utc).date().isoformat()`
- Same `recency_score()` formula: `int(100 * (1 - age / max_days))` with same edge cases (None→0, negative→100, >=max→0)
- Same `date_window()`/`get_date_range()`: `today - timedelta(days=days)` with default 30

---

## MEDIOCRE INDICATORS

These findings are consistent with derivation but could theoretically arise from shared inspiration, common patterns, or similar requirements.

### 13. Scoring Algorithm Has Same Structure but Tweaked Constants

While the engagement formulas are identical (Strong Indicator #1), the top-level scoring weights differ slightly:

| Weight | BriefBot | Last30Days |
|--------|----------|------------|
| Relevance (social) | 0.42 | 0.45 |
| Recency (social) | 0.28 | 0.25 |
| Engagement (social) | 0.30 | 0.30 |
| Relevance (web) | 0.52 | 0.55 |
| Recency (web) | 0.48 | 0.45 |
| Web source penalty | 12 | 15 |
| Missing engagement penalty | 12 | 3 |
| Date "low" penalty | 10 | 5 |
| Date "med" penalty | 5 | 2 |
| Baseline engagement | 32 | 35 |

The overall scoring algorithm structure is identical (compute raw engagement → normalize to 0-100 → weighted sum → apply penalties → clamp), but every tunable constant has been shifted by small amounts. This is consistent with someone taking the original constants and deliberately tweaking them to create surface-level differentiation.

### 14. Content Fixture Files Have Different Data but Same Schema

The content fixture files (`openai_sample.json`, `xai_sample.json`, `reddit_thread_sample.json`) contain completely different sample data (BriefBot uses Zigbee/home automation topics; Last30Days uses Claude Code topics) but follow the **exact same JSON structure** -- same keys, same nesting, same field names, same response format. This suggests the fixtures were regenerated with different content rather than written independently.

### 15. Identical Module Architecture (15+ 1:1 Module Mappings)

Both projects have the same `scripts/lib/` directory with these modules mapping 1:1:

`schema.py`, `score.py`, `normalize.py`, `dedupe.py`, `dates.py`, `cache.py`, `http.py`, `render.py`, `ui.py`, `env.py`, `models.py`, `openai_reddit.py`, `xai_x.py`, `reddit_enrich.py`, `websearch.py`, `bird_x.py`

This is not just similar file names -- each module serves the same purpose, exports the same function set (renamed), and uses the same internal algorithms.

### 16. Identical Depth/Quantity Configuration Tuples

Both projects use the same specific depth presets:

| Platform | Quick | Default | Deep |
|----------|-------|---------|------|
| Reddit | (15, 25) | (30, 50) | (70, 100) |
| X | (8, 12) | (20, 30) | (40, 60) |
| Timeouts | 90s | 120s | 180s |

These specific numeric tuples (why 15/25 and not 10/20 or 20/30?) appear in both `openai_reddit.py` and `xai_x.py`.

### 17. Identical Config Key Management

`env.py` shares the same config architecture:
- Same config file location pattern: `~/.config/<name>/.env`
- Same dotenv parsing algorithm: skip blanks, skip `#` comments, skip lines without `=`, `partition("=")`, strip quotes
- Same merge strategy: environment variables override file values via `os.environ.get(KEY) or file.get(KEY)`
- Same config key names: `OPENAI_API_KEY`, `XAI_API_KEY`, `OPENAI_MODEL_POLICY` (default `"auto"`), `OPENAI_MODEL_PIN`, `XAI_MODEL_POLICY` (default `"latest"`), `XAI_MODEL_PIN`
- Same platform detection logic: check `has_openai` / `has_xai` booleans → return `"both"`, `"reddit"`, `"x"`, or `"web"` via same if/elif chain
- Same `validate_sources()` function with identical error message strings:
  - `"Requested Reddit but only xAI key is available."`
  - `"Requested X but only OpenAI key is available."`

### 18. Identical Markdown Rendering Templates

`render.py` shares the same rendering architecture:
- Same freshness assessment algorithm: count recent items per source, compute `is_sparse` (threshold: `< 5`), compute `mostly_evergreen` (threshold: `< 0.3 * total`)
- Same compact markdown structure: header → sparse warning → cache indicator → date range/mode/models → per-source sections
- Same per-item format: `**{item.id}** (score:{item.score}) source_identifier{date_str}{conf}{eng}`
- Same engagement formatting: `{value}pts`, `{value}cmt`, `{value}likes`, `{value}rt`
- Same date display: `" ({item.date})"` or `" (date unknown)"`
- Same confidence display: `" [date:{conf}]"` only when not `"high"`
- Same X text truncation at 200 chars, web snippets at 150 chars
- Same context snippet: aggregate items as `(score, source_name, text, url)` tuples, sort by `-score`, take top 7
- Same artifact saving: `report.json`, `report.md`, context file, optional raw response files

### 19. Identical Spinner and Progress System

`ui.py` shares the same terminal UI architecture:
- Same braille spinner frames: `['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']`
- Same ANSI color codes (9 codes mapping to the same escape sequences, just renamed: `MAGENTA`↔`PURPLE`, `AZURE`↔`BLUE`, `TEAL`↔`CYAN`, `LIME`↔`GREEN`, `AMBER`↔`YELLOW`, `CRIMSON`↔`RED`)
- Same `IS_TTY` detection via `sys.stderr.isatty()`
- Same spinner algorithm: `\r` + color + frame + reset + message, `time.sleep(0.08)`, threaded on TTY, static with hourglass on non-TTY
- Same thread-join timeout: 0.2 seconds
- Same line-clear width: 80 spaces
- Same Progress class structure: `start_reddit`/`end_reddit`, `start_x`/`end_x`, `start_processing`/`end_processing`, `show_cached`, `show_error`, `show_promo` -- method for method
- Same phase color mapping: `reddit`→YELLOW, `x`→CYAN, `process`→PURPLE, `done`→GREEN, `error`→RED

### 20. Identical OpenAI Model Selection Algorithm

`models.py` shares the same OpenAI model selection flow:
1. Check for `"pinned"` policy → return pin immediately
2. Check cache via `cache.get_cached_model("openai")`
3. Query `https://api.openai.com/v1/models` (same URL in both)
4. Fall back to hardcoded model list on `HTTPError`
5. Filter to mainline models using exclude list: `['mini', 'nano', 'chat', 'codex', 'pro', 'preview', 'turbo']` (identical)
6. Sort by `(version_tuple, created)` descending
7. Pick first, cache it, return it

Same version extraction regex: `r'(\d+(?:\.\d+)*)'` with tuple conversion.

### 21. Identical Filler Word Sets

The `_core_subject` / `_extract_core_subject` function in `openai_reddit.py` uses the same set of filler words to strip from queries (same 18 words: "best", "top", "tips", "how to", "guide", etc.). The same function in `bird_x.py`'s `_extract_core_subject` uses the same aggressive stripping with same max 3-word limit.

### 22. Systematic Renaming Pattern Across All Files

Every shared module shows a consistent renaming pattern. While the direction isn't uniform (sometimes BriefBot is more terse, sometimes more verbose), the pattern is clearly systematic:

| Module | BriefBot | Last30Days |
|--------|----------|------------|
| cache.py | `cache_key`, `load`, `save`, `is_valid`, `clear_all` | `get_cache_key`, `load_cache`, `save_cache`, `is_cache_valid`, `clear_cache` |
| dates.py | `date_window`, `date_confidence` | `get_date_range`, `get_date_confidence` |
| dedupe.py | `normalize`, `ngrams`, `jaccard`, `find_dupes` | `normalize_text`, `get_ngrams`, `jaccard_similarity`, `find_duplicates` |
| http.py | `_debug`, `reddit_json` | `log`, `get_reddit_json` |
| score.py | `_log1p`, `_to_pct`, `score_reddit`, `rank` | `log1p_safe`, `normalize_to_100`, `score_reddit_items`, `sort_items` |
| normalize.py | `filter_dates`, `to_reddit`, `to_x`, `as_dicts` | `filter_by_date_range`, `normalize_reddit_items`, `normalize_x_items`, `items_to_dicts` |
| render.py | `compact`, `context_fragment`, `save_artifacts` | `render_compact`, `render_context_snippet`, `write_outputs` |
| schema.py | `make_report` | `create_report` |

The sheer breadth and consistency of this renaming across 15+ modules strongly suggests a deliberate transformation pass rather than organic independent development.

---

## LIGHT INDICATORS

These are consistent with the overall pattern but individually could arise from common conventions or similar requirements.

### 23. Same Default Values Throughout

Both projects use the same defaults across multiple modules:
- Default research window: 30 days
- Default relevance: 0.5 (Reddit, X, Web)
- Default n-gram size: 3 (dedupe.py)
- Default dedup threshold: 0.7 (dedupe.py)
- Default max top comments: 10 (reddit_enrich.py)
- Default max insights: 7 (reddit_enrich.py)
- Insight candidate pool: `limit * 2`
- Cache TTL: 24 hours standard, 7 days for model selection
- Minimum comment length for insight: 30 chars
- Insight sentence boundary search start: position 50

### 24. Same Sort Tiebreaking Strategy

Both `rank`/`sort_items` functions use the same 4-tuple sort key:
```python
(-score, -int(date.replace("-", "")), source_priority, text)
```
With the same source priority: Reddit=0, X=1, YouTube=2, Web=3/4. Same date fallback: `"0000-00-00"`. Same text extraction: `getattr(item, "title", "") or getattr(item, "text", "")`.

### 25. Same ID Prefix Conventions

Both use the same ID prefix patterns: Reddit items → `R{n}`, X items → `X{n}`, Web items → `W{n}`.

### 26. BriefBot Extends Last30Days' Architecture With New Features

BriefBot adds features that build naturally on top of Last30Days' foundation:
- **LinkedIn** platform support (new `openai_linkedin.py`, additions to schema/score/normalize/render/dedupe)
- **Email delivery** via SMTP (`email_sender.py`)
- **Telegram delivery** via Bot API (`telegram_sender.py`)
- **Audio/TTS** via ElevenLabs or edge-tts (`tts.py`)
- **PDF generation** with 3 backend fallbacks (`pdf.py`)
- **Cron scheduling** with cross-platform support (`scheduler.py`, `cron_parse.py`, `jobs.py`)
- **Setup wizard** (`--setup` flag)
- **Cookie bridge** Chrome extension for X auth (`scripts/lib/cookie-bridge/`)

These additions follow the same architectural patterns established in Last30Days (dataclass schemas, per-platform modules, progressive enhancement), suggesting familiarity with the original codebase's design philosophy.

### 27. Same bird_x.py Vendored Dependency

`bird_x.py` is ~95% identical between both projects. Same `_extract_core_subject()` function, same `is_bird_installed()`, same `is_bird_authenticated()`, same `search_x()`, same `search_handles()`, same `parse_bird_response()`. The vendored `bird-search.mjs` Node.js module is the same version from the same source (`@steipete/bird v0.8.0`).

### 28. Same WebSearch Fallback Instruction Block

Both main orchestrators print nearly identical multi-line instructions when web search is needed:
```
============================================================
### WEBSEARCH REQUIRED ###
============================================================
Topic: {topic}
Date range: {start} to {end}
[instructions to find 8-15 web pages, exclude reddit/x, include blogs/news]
============================================================
```

Only difference: BriefBot says "Claude" while Last30Days says "Assistant".

---

## Summary

| Category | Count | Key Evidence |
|----------|-------|-------------|
| **Strong** | 12 | Identical engagement formulas, identical HTTP error architecture, identical response parsing algorithm, identical data class hierarchy, identical enrichment pipeline, mechanically offset fixture timestamps, identical websearch date extraction, identical dedup algorithm, semantically identical prompts, identical orchestrator pipeline, identical cache system, identical date utilities |
| **Mediocre** | 10 | Tweaked scoring weights, regenerated fixtures, identical module architecture, identical depth tuples, identical config management, identical rendering templates, identical progress UI, identical model selection, identical filler words, systematic renaming across all files |
| **Light** | 6 | Same defaults, same sort tiebreaking, same ID prefixes, features extend original architecture, same vendored dependency, same WebSearch fallback text |

**Overall Assessment:** The evidence overwhelmingly indicates that BriefBot was created by taking the Last30Days codebase and applying a transformation pass that included: renaming functions/variables/constants, rewording prompts and docstrings, slightly tweaking scoring constants, regenerating content fixtures with different topics (while keeping model fixtures nearly identical), and then adding new features (LinkedIn, email, Telegram, TTS, scheduling). The forensic fingerprint of the model fixture timestamps being offset by exactly +86400 seconds is particularly telling -- it reveals a mechanical derivation process rather than independent development.
