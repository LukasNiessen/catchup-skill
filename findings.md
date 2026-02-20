# BriefBot vs Last30Days: Code Derivation Analysis

> **Date**: 2026-02-20
> **Method**: Exhaustive side-by-side source code comparison of every Python module, SKILL.md, configs, fixtures, and documentation in both repositories
> **Scope**: Current state of both repos only (no git history examined)

---

## Strong Indicators

These findings show code that is structurally identical, shares unique implementation details, or contains near-verbatim copies that cannot be explained by coincidence or common patterns.

### 1. `parse_x_response()` is a near-verbatim copy

**briefbot** `providers/twitter.py:299-421` vs **last30days** `lib/xai_x.py:117-218`

The Last30Days version is the baseline. BriefBot's version adds ~50 lines of `_log()` debug tracing, but the core logic is character-for-character identical:

- Same error-check block: `if "error" in response and response["error"]:`
- Same output-text extraction sequence: `isinstance(output, str)` then `isinstance(output, list)` then iterate for `type == "message"` then iterate content for `type == "output_text"` then fallback to `"text"` key then fallback to `"choices"` legacy format
- Same engagement parsing with identical ternary pattern:
  ```python
  "likes": int(raw_eng.get("likes", 0)) if raw_eng.get("likes") else None,
  "reposts": int(raw_eng.get("reposts", 0)) if raw_eng.get("reposts") else None,
  ```
- Same item normalization dict with identical field names, same `[:500]` text truncation, same `lstrip("@")` on author_handle
- Same ID scheme: `f"X{i+1}"` / `f"X{idx + 1}"` (only variable name differs)
- Same date validation regex: `re.match(r'^\d{4}-\d{2}-\d{2}$', str(item["date"]))`
- Same relevance clamping: `min(1.0, max(0.0, float(item.get("relevance", 0.5))))`

BriefBot refactored JSON extraction into a reusable `_extract_items_blob()` (using `json.JSONDecoder.raw_decode`), but the entire item validation and normalization loop was copied wholesale.

### 2. Reddit enrichment pipeline is structurally identical

**briefbot** `providers/enrich.py` vs **last30days** `lib/reddit_enrich.py`

Both follow the same 6-step pipeline:

1. Extract Reddit path from URL using `urlparse` with `"reddit.com" not in parsed.netloc` guard
2. Fetch thread JSON (with mock_data passthrough)
3. Parse submission data extracting the exact same field set: `score`, `num_comments`, `upvote_ratio`, `created_utc`, `permalink`, `title`, `selftext` (both truncate selftext: briefbot at 640 chars, last30days at 500)
4. Parse comments filtering for `kind == "t1"`, extracting `score`, `created_utc`, `author`, `body` (both truncate: 360 vs 300 chars), `permalink`
5. Get top comments by sorting by score descending, filtering out `[deleted]`/`[removed]` authors
6. Extract insights by skipping non-substantive comments using regex patterns

The non-substantive comment patterns overlap substantially:
- Both match: `this`, `same`, `agreed`, `exactly`, `yep`, `nope`, `yes`, `no`, `thanks`, `thank you`
- Both match: `lol`, `lmao`, `haha`
- Both match: `[deleted]`, `[removed]`
- BriefBot adds: `rofl`, `heh`, `ok`, `okay` (minor additions to the same base list)

The enrichment output structure is identical:
```python
item["engagement"] = {"score": ..., "num_comments": ..., "upvote_ratio": ...}
item["top_comments"] = [{"score": ..., "date": ..., "author": ..., "excerpt": ..., "url": ...}]
item["comment_insights"] = [...]
```

### 3. `reddit_json()` / `get_reddit_json()` is the same function

**briefbot** `net.py:141-152` vs **last30days** `http.py:127-155`

Identical logic, same order:
1. Ensure path starts with `/`
2. Strip trailing `/`
3. Append `.json` if not present
4. Build URL: `f"https://www.reddit.com{path}?raw_json=1"`
5. Set headers: `User-Agent` + `Accept: application/json`
6. Call `get()`

### 4. HTTPError class is structurally identical

**briefbot** `net.py:27-38` vs **last30days** `http.py:26-31`

Both define `__init__(self, message, status_code=None, body=None)` with `self.status_code` and `self.body` attributes. Same superclass call pattern. This is not a standard library class; it was defined specifically for these projects.

### 5. Output rendering (`compact` + `full_report`) follows the same template

**briefbot** `output.py` vs **last30days** `render.py`

The `compact()` / `render_compact()` functions have identical structure:
- Same header format: `## Findings/Research Results: {topic}`
- Same data-freshness check with same sparse-data warning text pattern
- Same web-only mode banner with identical API key promotion text (same emoji usage, same wording about unlocking Reddit & X data, same mention of `.env` file path)
- Same cache indicator format
- Same date range and mode display
- Same missing-keys tip (identical text: `"Tip: Add XAI_API_KEY for X/Twitter data and better triangulation."`)
- Same section ordering: Reddit -> X -> YouTube -> Web
- Same per-item format: `**{id}** [{score}] {source_info}{date}{confidence}{engagement}`
- Same engagement formatting pattern (building `parts` list, joining with comma)
- Same comment insights rendering with `Insights:` label and bullet list

The `full_report()` / `render_full_report()` functions share:
- Same title format: `# {topic} - Last 30 Days Research Report`
- Same "Models Used" section
- Same per-source section structure with identical field labels
- Same placeholder sections at the end: "Best Practices" and "Prompt Pack", both containing identical placeholder text (`"*To be synthesized by assistant/Claude*"`)

### 6. `context_fragment()` / `render_context_snippet()` are the same function

Same output structure:
```markdown
# Context: {topic} (Last 30 Days)
*Generated: {date} | Sources: {mode}*
## Key Sources
- [{source}] {text}
## Summary
*See full report for best practices, prompt pack, and detailed sources.*
```

BriefBot's version aggregates more source types (YouTube, LinkedIn) but the template is identical.

### 7. `save_artifacts()` / `write_outputs()` follow the same pattern

Both write the same set of output files:
- Full report JSON (`data.json` / `report.json`)
- Full markdown report (`summary.md` / `report.md`)
- Context snippet (`briefbot.context.md` / `last30days.context.md`)
- Raw API dumps: `raw_openai.json`, `raw_xai.json`, `raw_reddit_threads_enriched.json`

Same conditional write pattern: `if raw_openai: with open(...) as f: json.dump(...)`

### 8. SKILL.md intent-parsing system is a copy with renames

Both skills define the exact same 3-variable intent classification system:
- `TOPIC`/`SUBJECT` - what to research
- `TARGET_TOOL`/`DESTINATION` - where output will be used
- `QUERY_TYPE`/`INTENT_CLASS` - response mode

Same categories: PROMPTING, RECOMMENDATIONS, NEWS, GENERAL (BriefBot adds KNOWLEDGE).

Same "Common patterns" section with same examples:
- `[topic] for [tool]` -> tool is specified
- `[topic] prompts for [tool]` -> tool is specified
- "best [topic]" -> RECOMMENDATIONS

Same display-before-tools requirement with nearly identical display format:
```
I'll research/map {TOPIC} across Reddit, X, and the web...
Parsed intent/request:
- TOPIC/SUBJECT = ...
- TARGET_TOOL/DESTINATION = ...
- QUERY_TYPE/INTENT_CLASS = ...
Research typically takes 2-8 minutes...
```

Same "IMPORTANT: Do NOT ask about target tool before research." instruction, verbatim.

### 9. `validate_sources()` has the same control flow

**briefbot** `config.py:189-266` vs **last30days** `env.py:146-211`

Same function signature: `(requested, available, include_web) -> (effective, error)`
Same case handling order: web-only fallback -> auto mode -> web -> both -> reddit -> x
Same error messages mentioning missing keys and config file path
Same `include_web` modifier logic that appends `-web` suffix to source strings
Same `"WebSearch fallback"` detection string in the caller

### 10. The `output_report()` / `output_result()` WebSearch handoff block is near-identical

Both functions end with the same WebSearch instruction block:
```
### WEB RESEARCH NEEDED / WEBSEARCH REQUIRED ###
Topic: {topic}
Date range: ...
Use the WebSearch tool now to find 6-12/8-15 diverse web sources.
Skip social media platforms (already covered above).
INCLUDE: blogs, docs, news, tutorials from the last {days} days
After searching, synthesize WebSearch results WITH the Reddit/X
results above. WebSearch items should rank LOWER than comparable
Reddit/X items (they lack engagement metrics).
```

Same separator line pattern, same instructions, same ranking guidance.

---

## Mediocre Indicators

These findings show similar design decisions and patterns that suggest derivation but could conceivably result from solving the same problem independently.

### 1. Scoring dimensions and weights are near-identical

Both use the same three scoring dimensions: relevance, recency, engagement.

| Dimension | Last30Days | BriefBot |
|-----------|-----------|----------|
| Relevance | 0.45 | 0.38 |
| Recency | 0.25 | 0.34 |
| Engagement | 0.30 | 0.28 |

Web-only scoring:

| Dimension | Last30Days | BriefBot |
|-----------|-----------|----------|
| Relevance | 0.55 | 0.58 |
| Recency | 0.45 | 0.42 |
| Source penalty | -15 pts | -9 pts |

BriefBot switched from linear-weighted sum to percentile-harmonic mean, but the conceptual framework (three dimensions with web penalty) is clearly derived from Last30Days.

Both also apply:
- Unknown engagement penalty (3 vs 8 points)
- Date confidence penalty (low: -5 vs -7, med: -2 vs -3)
- Same `max(0, min(100, ...))` score clamping

### 2. `_core_subject()` / `_extract_core_subject()` share the same noise words

Both strip the same filler words from search queries. The noise word lists overlap heavily:
- Shared: `best`, `top`, `how to`, `tips for`, `features`, `tutorial`, `recommendations`, `advice`, `prompting`, `using`, `for`, `with`, `the`, `of`, `in`, `on`

BriefBot converts these to regex patterns (`\bbest\b` etc.) while Last30Days uses a flat word list, but the vocabulary is clearly derived from the same source.

### 3. Date/temporal utilities share the same API surface

**briefbot** `temporal.py` vs **last30days** `dates.py`

- `window()` / `get_date_range()`: same logic (`today - timedelta(days=N)`)
- `interpret()` / `parse_date()`: same approach (try timestamp first, then iterate format list)
- `to_date_str()` / `timestamp_to_date()`: identical implementation (timestamp -> `date().isoformat()`)
- `trust_level()` / `get_date_confidence()`: same logic (check if date falls within query range)
- `elapsed_days()` / `days_ago()`: identical
- `freshness_score()` / `recency_score()`: same 0-100 scale, same None->0, same future->100, same `age >= max_days -> 0` logic. BriefBot adds a `** 0.95` exponent vs Last30Days' linear decay.
- Format lists overlap: both include `%Y-%m-%d`, `%Y-%m-%dT%H:%M:%S`, `%Y-%m-%dT%H:%M:%SZ`, `%Y-%m-%dT%H:%M:%S.%f%z`

### 4. Reddit sparse-results retry logic is the same pattern

Both main orchestrators:
1. Call Reddit search
2. Check if `len(items) < N` (briefbot: 4, last30days: 5)
3. Extract core subject from verbose query
4. Check if core differs from original topic
5. Re-search with simplified query
6. Merge results by URL deduplication: `existing_urls = {item.get("url") for item in items}`

### 5. ThreadPoolExecutor orchestration pattern

Both `run_research()` functions:
1. Initialize empty lists and None raw responses
2. Determine which platforms to query based on `platform`/`sources` string
3. Submit futures to ThreadPoolExecutor
4. Collect results with error handling per-future
5. Call progress display methods at same lifecycle points (`start_reddit`, `end_reddit`, `start_x`, `end_x`, etc.)
6. Run enrichment loop after collection

### 6. Fixture file set matches

| Last30Days | BriefBot |
|-----------|----------|
| `openai_sample.json` | `provider_reddit_response.json` |
| `xai_sample.json` | `provider_x_response.json` |
| `reddit_thread_sample.json` | `provider_reddit_thread.json` |
| `models_openai_sample.json` | `api_openai_models.json` |
| `models_xai_sample.json` | `api_xai_models.json` |

Same set of 5 fixture files covering the same 5 data shapes (Reddit API, X API, Reddit thread enrichment, OpenAI model list, xAI model list).

### 7. DEPTH_SIZES / DEPTH_CONFIG follow the same schema

Both define `{"quick": (min, max), "default": (min, max), "deep": (min, max)}` tuples with similar ranges.

### 8. `_is_model_access_error()` checks the same status codes and strings

Both check HTTP status codes 400/403 and scan the error body for overlapping phrases: `"does not have access"`, `"not available"`, `"not found"`, `"organization must be verified"`.

### 9. Config module: same dotenv parsing logic

Both `parse_dotenv()` / `load_env_file()`:
1. Skip empty lines and `#` comments
2. Partition on `=`
3. Strip quotes from value (same quote-detection logic)
4. Build dict

Both use `os.environ.get(key) or file_settings.get(key)` precedence pattern.

---

## Light Indicators

These are architectural and tooling similarities that are noteworthy in aggregate but individually could be attributed to reasonable engineering choices.

### 1. Both use stdlib-only HTTP

Both implement custom HTTP clients using `urllib.request` rather than `requests` or `httpx`. Both have retry logic with backoff, same debug logging pattern (log method, URL, payload keys, response status + byte count).

### 2. Same directory conventions

- Config: `~/.config/<name>/.env`
- Output: `~/.local/share/<name>/out/`
- Same output file set: JSON report, markdown report, context snippet, plus raw API response dumps

### 3. Identical CLI argument names

Both share: `--mock`, `--emit` (same 5 choices: compact/json/md/context/path), `--sources`, `--quick`, `--deep`, `--debug`, `--days`, `--include-web`

### 4. Both vendor the `bird-search` library

Both include a vendored copy of the same TypeScript/JavaScript bird-search library for X/Twitter GraphQL access, with the same cookie-based authentication approach.

### 5. Same five output modes

Both output exactly 5 modes: `compact`, `json`, `md`, `context`, `path`. The `context` mode produces a reusable snippet; `path` prints the file path to it.

### 6. Same model fallback approach

Both implement model fallback chains for OpenAI and xAI. Both cache model selections. Both have model access error detection with automatic retry using alternative models.

### 7. Same `_log` / `log` debug gating pattern

Both gate debug output on an environment variable (`BRIEFBOT_DEBUG` / `LAST30DAYS_DEBUG`) using identical detection: `os.environ.get(...).lower() in ("1", "true", "yes")` and write to stderr.

### 8. Same Windows console encoding fix

Both `main()` functions start with:
```python
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

### 9. Same `_freshness_check` / `_assess_data_freshness` diagnostic

Both compute per-source recent-item counts and return a dict with `is_sparse` and `mostly_evergreen` boolean flags using similar thresholds.

### 10. Same mode-mapping dictionary

Both map source strings to display modes using the same dictionary pattern:
```python
{"both": "both", "reddit": "reddit-only", "x": "x-only", "web": "web-only", ...}
```

---

## Summary

BriefBot is not an independent implementation. The evidence shows systematic derivation from Last30Days at multiple levels:

- **API-level code** (providers): parse functions are near-verbatim copies with added logging
- **Domain logic** (scoring, dates, enrichment): same algorithms with cosmetic weight adjustments
- **Architecture** (orchestrator, config, output): identical patterns and control flow
- **UX/Skill layer** (SKILL.md): same intent-classification system with variable renames
- **Infrastructure** (HTTP, CLI args, directory layout): identical choices throughout

BriefBot adds features on top (LinkedIn provider, email delivery, Telegram bot, cron scheduling, audio TTS, setup wizard, unified ContentItem model, SimHash deduplication, percentile-harmonic scoring). But the core research pipeline -- from intent parsing through API calls, response parsing, enrichment, scoring, and output rendering -- was lifted from Last30Days with variable renames, added debug logging, and minor constant adjustments.
