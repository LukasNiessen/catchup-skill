# BriefBot vs Last30Days: Derivation Analysis

> **Date**: 2026-02-19
> **Method**: Side-by-side source code comparison of current repo states
> **Scope**: All source files, tests, fixtures, configs, and skill definitions

---

## STRONG INDICATORS

These findings represent clear, unambiguous evidence that BriefBot was derived from Last30Days.

### 1. Identical Directory and Module Structure

Both projects share the exact same `scripts/lib/` module layout, test file names, and fixture file names:

| Module | Last30Days | BriefBot |
|--------|-----------|----------|
| schema.py | Yes | Yes |
| score.py | Yes | Yes |
| dates.py | Yes | Yes |
| dedupe.py | Yes | Yes |
| cache.py | Yes | Yes |
| http.py | Yes | Yes |
| models.py | Yes | Yes |
| normalize.py | Yes | Yes |
| openai_reddit.py | Yes | Yes |
| xai_x.py | Yes | Yes |
| reddit_enrich.py | Yes | Yes |
| render.py | Yes | Yes |
| websearch.py | Yes | Yes |
| env.py | Yes | Yes |
| ui.py | Yes | Yes |
| bird_x.py | Yes | Yes |

Tests: `test_cache.py`, `test_dates.py`, `test_dedupe.py`, `test_models.py`, `test_normalize.py`, `test_openai_reddit.py`, `test_render.py`, `test_score.py` -- all present in both with identical names.

Fixtures: `models_openai_sample.json`, `models_xai_sample.json`, `openai_sample.json`, `reddit_thread_sample.json`, `xai_sample.json` -- all present in both, same file names, same JSON structure, only content values differ (different IDs, different topic nouns).


### 2. Schema Dataclasses Are Structurally Identical

`schema.py` is the data backbone. BriefBot's version is a near-exact copy with additions:

**Engagement class**: Same 8 fields in same order (`score`, `num_comments`, `upvote_ratio`, `likes`, `reposts`, `replies`, `quotes`, `views`). BriefBot adds `reactions`, `comments`, `bookmarks`. The `to_dict()` method is identical line-for-line for shared fields.

**Comment class**: Byte-for-byte identical (fields: `score`, `date`, `author`, `excerpt`, `url`; same `to_dict()` body).

**SubScores class**: Byte-for-byte identical (fields: `relevance`, `recency`, `engagement`; same `to_dict()` body).

**RedditItem**: Same 13 fields, same types, same defaults (`relevance=0.5`, `date_confidence="low"`). BriefBot adds one extra field: `flair`. The `to_dict()` method is identical except for the added field.

**XItem**: Same 10 fields, same types, same defaults. BriefBot adds `is_repost` and `language`.

**WebSearchItem**: Byte-for-byte identical structure (same fields, same defaults). BriefBot adds `language`.

**YouTubeItem**: Same structure, BriefBot renames `transcript_snippet` to `description` and changes default `date_confidence` from `"high"` to `"low"` and default `relevance` from `0.7` to `0.5`. BriefBot adds `duration_seconds`.

**Report class**: Same core fields (`topic`, `range_from`, `range_to`, `generated_at`, `mode`, `openai_model_used`, `xai_model_used`, `reddit`, `x`, `youtube`, `web`, `best_practices`, `prompt_pack`, `context_snippet_md`, `*_error`, `from_cache`, `cache_age_hours`). BriefBot adds `linkedin`, `linkedin_error`, `search_duration_seconds`, `item_count`. The `to_dict()` and `from_dict()` methods follow the exact same logic pattern.

**Factory function**: Last30Days has `create_report()`, BriefBot renamed to `make_report()` -- same logic, different parameter names (`from_date`→`start`, `to_date`→`end`).


### 3. Tests Use the Same Test Data and Assertions

**test_score.py**: Both test suites test the same functions with the same test data:
- Both use `Engagement(score=100, num_comments=50, upvote_ratio=0.9)` for Reddit engagement tests
- Both use `Engagement(likes=100, reposts=25, replies=15, quotes=5)` for X engagement tests
- Both use the same RedditItem with `url="https://reddit.com/r/test/1"`, `relevance=0.9` vs a second item with `url="https://reddit.com/r/test/2"`, `relevance=0.5`
- Both assert `result[0].score > result[1].score` with the same comment: "Higher relevance and engagement should score higher"
- Rank/sort test uses identical items: `id="R1", title="Low", score=30`, `id="R2", title="High", score=90`, `id="R3", title="Mid", score=60`

**test_dedupe.py**: Both test suites use:
- Normalize test: `"HELLO World"` → `"hello world"`, `"Hello, World!"`, `"hello    world"`
- N-gram test: `"ab"` with n=3, `"hello"` with n=3 checking for `"hel"`, `"ell"`, `"llo"`
- Jaccard test: `{"a","b","c"}` vs itself, vs `{"d","e","f"}`, vs `{"b","c","d"}` with comment `# 2 overlap / 4 union`
- Duplicate detection: `"Completely different topic A"` / `"Another unrelated subject B"` for no-dupes, and `"Best practices for Claude Code skills"` / `"Best practices for Claude Code skills guide"` for finding dupes
- Deduplication: `"Best practices for skills"` (score=90) vs `"Best practices for skills guide"` (score=50); `"Topic about apples"` vs `"Discussion of oranges"`

These test strings are too specific and numerous to be coincidental.


### 4. API Response Parsing Logic Is Functionally Identical

`parse_reddit_response()` and `parse_x_response()` in both projects follow the exact same control flow:

1. Check `api_response.get("error")` → extract error message the same way
2. Initialize `output_text = ""`
3. Check `"output"` in response → if string, use directly; if list, iterate looking for `type == "message"` → iterate `content` for `type == "output_text"`; also check for `"text"` key or string elements
4. Fallback to `"choices"` format (legacy)
5. Regex extract JSON: `r'\{[^{}]*"items"\s*:\s*\[[\s\S]*?\]\s*\}'` (BriefBot) vs `r'\{[\s\S]*"items"[\s\S]*\}'` (Last30Days) -- slightly different regex but same intent
6. Validate items: check `isinstance(raw, dict)`, check URL contains `"reddit.com"`, build clean dict with `f"R{i+1}"` IDs
7. Same validation: strip subreddit prefix `lstrip("r/")`, clamp relevance `min(1.0, max(0.0, ...))`, validate date format `r'^\d{4}-\d{2}-\d{2}$'`

Even the warning message is identical: `f"[REDDIT WARNING] No output text found in OpenAI response. Keys present: {list(response.keys())}"` appears verbatim in both.


### 5. Fixture Files Have Identical Structure

All 5 fixture files exist in both projects with the same JSON schema and same number of lines. The diffs show only cosmetic changes: different response IDs (e.g., `"resp_bb_zigbee_001"` vs `"resp_mock123"`), different topic nouns, and slightly different timestamps. The structural scaffolding (nesting, key names, array layout) is preserved exactly.


### 6. SKILL.md Intent Parsing Is Heavily Derived

Both SKILL.md files contain the same intent-parsing framework:
- Same variable scheme: `TOPIC`, `TARGET_TOOL`, `QUERY_TYPE`
- Same query types: PROMPTING, RECOMMENDATIONS, NEWS, GENERAL (BriefBot adds KNOWLEDGE)
- Same common patterns section with near-identical wording: `"[topic] for [tool]"`, `"[topic] prompts for [tool]"`, `"Just [topic]"`, `"best [topic]"`, `"what are the best [topic]"`
- Same instruction: "**IMPORTANT: Do NOT ask about target tool before research.**"
- Same display format template with `TOPIC`, `TARGET_TOOL`, `QUERY_TYPE`
- Same "2-8 minutes" time estimate
- BriefBot's intro text: "I'll **investigate** {TOPIC}..." vs Last30Days: "I'll **research** {TOPIC}..." (verb change, otherwise identical template)


### 7. Websearch Date Extraction Uses Same 3-Pattern Stack

Both `websearch.py` files use the same three URL date patterns in the same order:
1. `/YYYYMMDD/` compact
2. `/YYYY/MM/DD/` slashed
3. `/YYYY-MM-DD-` hyphenated

Both use the same text date extraction with the same month regex pattern, the same relative date parsing ("yesterday", "today", "N days ago", "N hours ago", "last week", "this week", "last month"), and the same confidence hierarchy (URL→high, snippet→med, title→low/med).

The excluded domains list is nearly identical: both exclude `reddit.com`, `www.reddit.com`, `old.reddit.com`, `twitter.com`, `www.twitter.com`, `x.com`, `www.x.com`. BriefBot adds `m.reddit.com` and `nitter.net`; Last30Days has `mobile.twitter.com`.

---

## MEDIOCRE INDICATORS

These findings show a systematic pattern of renaming and minor tweaking consistent with creating a fork intended to look different while preserving the same logic.

### 8. Systematic Function Renaming Across Every Module

Every module shows the same pattern: functions are renamed but the logic, parameter handling, and return types remain the same.

| Last30Days | BriefBot | Module |
|-----------|----------|--------|
| `log1p_safe()` | `_log1p()` | score.py |
| `compute_reddit_engagement_raw()` | `_reddit_engagement()` | score.py |
| `compute_x_engagement_raw()` | `_x_engagement()` | score.py |
| `compute_youtube_engagement_raw()` | `_youtube_engagement()` | score.py |
| `normalize_to_100()` | `_to_pct()` | score.py |
| `score_reddit_items()` | `score_reddit()` | score.py |
| `score_x_items()` | `score_x()` | score.py |
| `score_youtube_items()` | `score_youtube()` | score.py |
| `score_websearch_items()` | `score_web()` | score.py |
| `sort_items()` | `rank()` | score.py |
| `normalize_text()` | `normalize()` | dedupe.py |
| `get_ngrams()` | `ngrams()` | dedupe.py |
| `jaccard_similarity()` | `jaccard()` | dedupe.py |
| `get_item_text()` | `_text_of()` | dedupe.py |
| `find_duplicates()` | `find_dupes()` | dedupe.py |
| `dedupe_items()` | `deduplicate()` | dedupe.py |
| `get_date_range()` | `date_window()` | dates.py |
| `get_date_confidence()` | `date_confidence()` | dates.py |
| `load_env_file()` | `parse_dotenv()` | env.py |
| `get_config()` | `load_config()` | env.py |
| `get_available_sources()` | `determine_available_platforms()` | env.py |
| `get_missing_keys()` | `identify_missing_credentials()` | env.py |
| `select_openai_model()` | `choose_openai_model()` | models.py |
| `select_xai_model()` | `choose_xai_model()` | models.py |
| `parse_version()` | `extract_version_tuple()` | models.py |
| `is_mainline_openai_model()` | `is_standard_gpt_model()` | models.py |
| `search_reddit()` | `search()` | openai_reddit.py |
| `_extract_core_subject()` | `_core_subject()` | openai_reddit.py |
| `_is_model_access_error()` | `_is_access_err()` | openai_reddit.py |
| `_log_error()` | `_err()` | openai_reddit.py / xai_x.py |
| `_log_info()` | `_info()` | openai_reddit.py |
| `search_x()` | `search()` | xai_x.py |
| `extract_reddit_path()` | `_parse_url()` | reddit_enrich.py |
| `fetch_thread_data()` | `_fetch_thread()` | reddit_enrich.py |
| `parse_thread_data()` | `_parse_thread()` | reddit_enrich.py |
| `get_top_comments()` | `_top_comments()` | reddit_enrich.py |
| `extract_comment_insights()` | `_extract_insights()` | reddit_enrich.py |
| `enrich_reddit_item()` | `enrich()` | reddit_enrich.py |
| `ensure_cache_dir()` | `_ensure_dir()` | cache.py |
| `get_cache_key()` | `cache_key()` | cache.py |
| `get_cache_path()` | `cache_path()` | cache.py |
| `is_cache_valid()` | `is_valid()` | cache.py |
| `load_cache()` | `load()` | cache.py |
| `save_cache()` | `save()` | cache.py |
| `load_cache_with_age()` | `load_with_age()` | cache.py |
| `get_cache_age_hours()` | `age_hours()` | cache.py |
| `clear_cache()` | `clear_all()` | cache.py |
| `load_model_cache()` | `_load_model_prefs()` | cache.py |
| `save_model_cache()` | `_save_model_prefs()` | cache.py |
| `filter_by_date_range()` | `filter_dates()` | normalize.py |
| `normalize_reddit_items()` | `to_reddit()` | normalize.py |
| `normalize_x_items()` | `to_x()` | normalize.py |
| `normalize_youtube_items()` | `to_youtube()` | normalize.py |
| `items_to_dicts()` | `as_dicts()` | normalize.py |
| `extract_date_from_url()` | `_date_from_url()` | websearch.py |
| `extract_date_from_snippet()` | `_date_from_text()` | websearch.py |
| `extract_date_signals()` | `_detect_date()` | websearch.py |
| `extract_domain()` | `_domain()` | websearch.py |
| `is_excluded_domain()` | `_is_excluded()` | websearch.py |
| `parse_websearch_results()` | `process_results()` | websearch.py |
| `normalize_websearch_items()` | `to_items()` | websearch.py |
| `dedupe_websearch()` | `dedup_urls()` | websearch.py |

This is not two independent implementations arriving at similar names. This is a systematic bulk rename across the entire codebase.


### 9. Config Paths Follow Exact Same Pattern

| Aspect | Last30Days | BriefBot |
|--------|-----------|----------|
| Config dir | `~/.config/last30days/` | `~/.config/briefbot/` |
| Config file | `~/.config/last30days/.env` | `~/.config/briefbot/.env` |
| Cache dir | `~/.cache/last30days/` | `~/.cache/briefbot/` |
| Debug env var | `LAST30DAYS_DEBUG` | `BRIEFBOT_DEBUG` |
| User-Agent | `last30days-skill/2.1 (Assistant Skill)` | `briefbot-skill/1.0 (Claude Code Skill)` |

Same `os.environ.get("...DEBUG", "").lower() in ("1", "true", "yes")` check in both.


### 10. Scoring Weights Are Slightly Tweaked From the Same Formula

| Weight | Last30Days | BriefBot |
|--------|-----------|----------|
| Relevance (engagement sources) | 0.45 | 0.38 |
| Recency (engagement sources) | 0.25 | 0.34 |
| Engagement (engagement sources) | 0.30 | 0.28 |
| WebSearch relevance | 0.55 | 0.58 |
| WebSearch recency | 0.45 | 0.42 |
| Unknown engagement penalty | 3 | 8 |
| Low date confidence penalty | 5 | 7 |
| Med date confidence penalty | 2 | 3 |
| Web source penalty | 15 | 9 |
| Web verified date bonus | 10 | 11 |
| Web no-date penalty | 20 | 14 |
| Baseline engagement | 35 | 45 |

The formula `total = W_rel * relevance + W_rec * recency + W_eng * engagement` is identical in structure. The small weight adjustments look like deliberate tuning to differentiate.


### 11. Reddit Engagement Formula: Same Structure, Different Coefficients

| Component | Last30Days | BriefBot |
|-----------|-----------|----------|
| score weight | 0.55 | 0.48 |
| comments weight | 0.40 | 0.37 |
| ratio multiplier | × 10 | × 12 |
| ratio weight | 0.05 | 0.15 |

Same formula: `a * log1p(score) + b * log1p(comments) + c * (ratio * k)`. Same None/null guard pattern. Same conditional: `if eng.score is None and eng.num_comments is None: return None`.


### 12. X Engagement Formula: Same Structure, Different Coefficients

| Component | Last30Days | BriefBot |
|-----------|-----------|----------|
| likes weight | 0.55 | 0.45 |
| reposts weight | 0.25 | 0.28 |
| replies weight | 0.15 | 0.17 |
| quotes weight | 0.05 | 0.10 |

Same formula: `a * log1p(likes) + b * log1p(reposts) + c * log1p(replies) + d * log1p(quotes)`.


### 13. Backward-Compatibility Aliases Reveal Renaming Process

BriefBot's `env.py` ends with:
```python
# -- Backward-compatible aliases for external callers --
SETTINGS_DIRECTORY = CONFIG_DIR
SETTINGS_FILEPATH = CONFIG_FILE
parse_environment_file = parse_dotenv
assemble_configuration = load_config
```

BriefBot's `http.py` ends with:
```python
# Backward compat aliases for out-of-scope callers (models.py etc.)
def perform_get_request(url, request_headers=None, **kw):
    return get(url, headers=request_headers, **kw)
def perform_post_request(url, json_payload=None, request_headers=None, **kw):
    return post(url, json_payload, headers=request_headers, **kw)
fetch_reddit_thread_data = reddit_json
```

These aliases suggest an intermediate rename phase where function names were changed but not all callers were updated simultaneously. This is consistent with a fork-and-rename workflow.


### 14. HTTP Client Is the Same Stdlib-Only Approach

Both use `urllib.request` (no `requests` library) with:
- Custom `HTTPError` class with `status_code` and `body` attributes
- Same `request()` function signature: `method, url, headers, json_body/json_data, timeout, retries`
- Same retry logic: don't retry 4xx except 429 (BriefBot also retries 503)
- Same error handling chain: HTTPError → URLError → JSONDecodeError → OSError/TimeoutError
- Same convenience wrappers: `get()`, `post()`, `reddit_json()`/`get_reddit_json()`
- Same reddit URL normalization: strip trailing slash, append `.json`, add `?raw_json=1`


### 15. Reddit Enrichment Pipeline Is the Same 5-Step Process

Both `reddit_enrich.py`:
1. Extract path from URL (same `urlparse` check for `"reddit.com"`)
2. Fetch thread JSON (same `http.reddit_json(path)` call)
3. Parse into `{"submission": {...}, "comments": [...]}` (same Reddit JSON structure: `data.children[0].data` for submission, `data.children` + `kind == "t1"` for comments)
4. Get top N comments sorted by score, excluding `[deleted]`/`[removed]`
5. Extract insights: skip short (<25/30 chars), skip low-value patterns (same regex list: "yep", "nope", "same", "agreed", "lol", etc.), truncate at sentence boundary (same logic: look for `.!?` after position 50/65)

BriefBot's `_extract_insights()` uses `limit * 3` candidates, Last30Days uses `limit * 2` -- minor tweak.

---

## LIGHT INDICATORS

These are differences or additions in BriefBot that could represent genuine new development on top of the derived base, or could also be part of a differentiation effort.

### 16. BriefBot Adds LinkedIn as a Source

BriefBot includes `LinkedInItem` dataclass, `openai_linkedin.py` module, `_linkedin_engagement()` scoring, `to_linkedin()` normalization, and `dedupe_linkedin()`. Last30Days has no LinkedIn support. This is new functionality.

### 17. BriefBot Adds Delivery Features

BriefBot includes modules not present in Last30Days:
- `email_sender.py` -- SMTP email delivery
- `telegram_sender.py` / `telegram_bot.py` -- Telegram delivery and listener
- `deliver.py` -- Unified delivery dispatch
- `scheduler.py` / `jobs.py` -- Scheduled job management
- `run_job.py` -- Cron job executor
- `setup.py` -- Interactive configuration wizard
- `cron_parse.py` -- Cron expression parser
- `tts.py` -- Text-to-speech audio generation
- `pdf.py` -- PDF generation
- `chrome_cookies.py` -- Chrome cookie extraction
- `claude_search.py` -- Claude search integration

### 18. BriefBot Adds a KNOWLEDGE Query Type

BriefBot's SKILL.md includes a 5th query type: KNOWLEDGE ("explain [topic]", "what is [topic]"). Last30Days only has PROMPTING, RECOMMENDATIONS, NEWS, GENERAL.

### 19. Dedupe Uses Different N-Gram Size and Threshold

| Parameter | Last30Days | BriefBot |
|-----------|-----------|----------|
| N-gram size | 3 | 4 |
| Default threshold | 0.7 | 0.65 |
| Stop word removal | No | Yes |
| Jaccard denominator | `intersection / union` | `intersection / (union + 1e-10)` |

Same algorithm, different tuning parameters. BriefBot adds stop word removal to the normalization step.

### 20. Recency Score Formula Differs Slightly

- **Last30Days**: `int(100 * (1 - age / max_days))` (linear decay)
- **BriefBot**: `int(100 * ((max_days - age) / max_days) ** 0.95)` (slightly sub-linear decay)

Same 0-100 range, same edge cases (None→0, negative→100, ≥max_days→0).

### 21. Different Model Fallback Lists in xai_x.py

BriefBot's xai_x.py has a more sophisticated fallback strategy: hardcoded list → dynamic API discovery via `models.discover_xai_models()` → dynamic candidates. Last30Days's version is simpler with no 403 fallback chain in xai_x.py (though the model selection is done in models.py).

### 22. BriefBot's models.py Has More Verbose Logging

BriefBot's model selection functions include extensive `_log()` debug output for every step. Last30Days's version is more concise with fewer debug lines.

### 23. BriefBot Adds `cache_stats()` and `clear_all()` Preserves Model Prefs

BriefBot's cache.py adds a `cache_stats()` function and its `clear_all()` preserves `model_prefs.json`. Last30Days's `clear_cache()` deletes everything.

---

## Summary

| Category | Count |
|----------|-------|
| Strong indicators | 7 |
| Mediocre indicators | 8 |
| Light indicators | 8 |

The evidence overwhelmingly indicates that **BriefBot is a systematic fork of Last30Days** with three types of modifications applied:

1. **Bulk rename**: Every function, variable, constant, config path, and error message has been renamed following a consistent pattern (shorter names, underscore-prefixed private functions, different verb choices).

2. **Coefficient tweaks**: Scoring weights, thresholds, penalties, and algorithm parameters have been adjusted by small amounts (e.g., 0.45→0.38, 0.55→0.48, 0.7→0.65) to differentiate numerically while preserving the same formulas.

3. **Feature additions**: LinkedIn support, delivery mechanisms (email/Telegram/TTS/PDF), scheduled jobs, knowledge query type, and a configuration wizard have been added on top of the derived base.

The core research pipeline -- schema, scoring, deduplication, date handling, caching, HTTP client, API integrations (OpenAI Reddit + xAI X), Reddit enrichment, web search processing, and the SKILL.md routing framework -- is functionally identical between the two projects.
