# Dragon Fork Analysis: BriefBot vs. last30days

**Analysis date:** 2026-02-18
**Repositories compared:**
- **Subject:** `briefbot-skill` (BriefBot)
- **Reference:** `last30days-skill` v2.1 (by mvanhorn)

**Methodology:** Full forensic comparison of directory structure, function names, constants, algorithms, environment variables, string formatting, iteration patterns, comment styles, and git history across both codebases.

---

## Verdict

BriefBot is a **systematic rename and cosmetic rewrite** of the last30days codebase. The evidence is not circumstantial -- the original project's fingerprints are embedded throughout BriefBot in environment variables, User-Agent strings, cache paths, scoring constants, function aliases, and algorithmic details that are identical down to decimal places. The rewrite follows a mechanical transformation pattern: f-strings converted to `.format()`, for-loops converted to while-loops, short variable names inflated to verbose alternatives, and function names replaced with synonyms while preserving the originals as aliases.

---

## Category 1: Irrefutable Indicators

These are forensic artifacts where the original project's identity is literally still present in BriefBot's code. No independent development could produce these.

### 1.1 `LAST30DAYS_DEBUG` environment variable throughout BriefBot

BriefBot -- a project called "BriefBot" -- uses `LAST30DAYS_DEBUG` as its debug flag across **every single module**:

| BriefBot file | Line | Code |
|---|---|---|
| `scripts/briefbot.py` | 37 | `os.environ.get("LAST30DAYS_DEBUG", "").lower() in ("1", "true", "yes")` |
| `scripts/lib/env.py` | 14 | `os.environ.get("LAST30DAYS_DEBUG", "").lower() in ("1", "true", "yes")` |
| `scripts/lib/xai_x.py` | 23 | `os.environ.get("LAST30DAYS_DEBUG", "").lower() in ("1", "true", "yes")` |
| `scripts/lib/models.py` | 16 | `os.environ.get("LAST30DAYS_DEBUG", "").lower() in ("1", "true", "yes")` |
| `scripts/lib/http.py` | 22 | `os.environ.get("LAST30DAYS_DEBUG", "")` |

last30days uses the same variable: `LAST30DAYS_DEBUG`. A project named "BriefBot" would use `BRIEFBOT_DEBUG` if developed independently.

### 1.2 User-Agent string identifies last30days

BriefBot's HTTP client (`scripts/lib/http.py`, line 19) sends:
```
CLIENT_IDENTIFIER = "last30days-skill/1.0 (Claude Code Skill)"
```

last30days's HTTP client sends:
```
CLIENT_IDENTIFIER = "last30days-skill/2.1 (Assistant Skill)"
```

BriefBot literally identifies itself as `last30days-skill` to every API server it contacts. The version is `1.0` vs `2.1`, indicating BriefBot was forked from an earlier version.

### 1.3 Cache directory still named `last30days`

BriefBot's `scripts/lib/cache.py` (line 14):
```python
STORAGE_DIRECTORY = Path.home() / ".cache" / "last30days"
```

This resolves to `~/.cache/last30days` -- the original project's cache path. The config directory was renamed to `~/.config/briefbot/` but the cache directory was missed.

### 1.4 Function aliases preserve original last30days names exactly

BriefBot contains dozens of lines with this comment pattern:
```python
# Preserve the original function name for API compatibility
```

The "original" names are the exact function names from last30days. BriefBot renamed them to verbose synonyms and kept aliases pointing back:

| BriefBot verbose name | Alias (= last30days name) | File |
|---|---|---|
| `assemble_configuration()` | `get_config` | env.py |
| `parse_environment_file()` | `load_env_file` | env.py |
| `determine_available_platforms()` | `get_available_sources` | env.py |
| `identify_missing_credentials()` | `get_missing_keys` | env.py |
| `settings_file_exists()` | `config_exists` | env.py |
| `execute_http_request()` | `request` | http.py |
| `perform_get_request()` | `get` | http.py |
| `perform_post_request()` | `post` | http.py |
| `fetch_reddit_thread_data()` | `get_reddit_json` | http.py |
| `emit_debug_message()` | `log` | http.py |
| `safe_logarithm()` | `log1p_safe` | score.py |
| `calculate_reddit_engagement_value()` | `compute_reddit_engagement_raw` | score.py |
| `calculate_x_engagement_value()` | `compute_x_engagement_raw` | score.py |
| `calculate_youtube_engagement_value()` | `compute_youtube_engagement_raw` | score.py |
| `scale_to_percentage()` | `normalize_to_100` | score.py |
| `compute_reddit_scores()` | `score_reddit_items` | score.py |
| `compute_x_scores()` | `score_x_items` | score.py |
| `compute_youtube_scores()` | `score_youtube_items` | score.py |
| `compute_websearch_scores()` | `score_websearch_items` | score.py |
| `arrange_by_score()` | `sort_items` | score.py |
| `standardize_text()` | `normalize_text` | dedupe.py |
| `extract_character_ngrams()` | `get_ngrams` | dedupe.py |
| `compute_jaccard_coefficient()` | `jaccard_similarity` | dedupe.py |
| `extract_comparable_text()` | `get_item_text` | dedupe.py |
| `identify_duplicate_pairs()` | `find_duplicates` | dedupe.py |
| `remove_near_duplicates()` | `dedupe_items` | dedupe.py |
| `compute_cache_identifier()` | `get_cache_key` | cache.py |
| `resolve_cache_filepath()` | `get_cache_path` | cache.py |
| `verify_cache_validity()` | `is_cache_valid` | cache.py |
| `compute_date_window()` | `get_date_range` | dates.py |
| `interpret_date_string()` | `parse_date` | dates.py |
| `convert_timestamp_to_date()` | `timestamp_to_date` | dates.py |
| `assess_date_reliability()` | `get_date_confidence` | dates.py |
| `calculate_age_in_days()` | `days_ago` | dates.py |
| `compute_recency_score()` | `recency_score` | dates.py |

Every single alias matches a function name in last30days. This is not coincidence -- it is the original API surface preserved during a rename operation.

### 1.5 Identical scoring constants to the decimal

| Constant | BriefBot | last30days |
|---|---|---|
| Relevance weight | `0.45` | `0.45` |
| Recency weight | `0.25` | `0.25` |
| Engagement weight | `0.30` | `0.30` |
| Web relevance weight | `0.55` | `0.55` |
| Web recency weight | `0.45` | `0.45` |
| Web source penalty | `15` | `15` |
| Baseline engagement | `35` | `35` |
| Missing engagement penalty | `10` | `3` (minor divergence) |
| Verified date bonus | `10` | `10` |
| Missing date penalty | `20` | `20` |

9 of 10 constants are **byte-identical**. These are arbitrary design choices (why 0.45 and not 0.40 or 0.50?) that would never independently converge.

### 1.6 Identical engagement formulas

**Reddit formula (both repos):**
```
0.55 * log1p(score) + 0.40 * log1p(num_comments) + 0.05 * (upvote_ratio * 10)
```

**X formula (both repos):**
```
0.55 * log1p(likes) + 0.25 * log1p(reposts) + 0.15 * log1p(replies) + 0.05 * log1p(quotes)
```

The coefficient sets `[0.55, 0.40, 0.05]` and `[0.55, 0.25, 0.15, 0.05]` are distinctive multi-decimal weight vectors. Independent derivation of these exact values is statistically implausible.

### 1.7 Identical fixture filenames

| Fixture file | BriefBot | last30days |
|---|---|---|
| `openai_sample.json` | Present | Present |
| `xai_sample.json` | Present | Present |
| `models_openai_sample.json` | Present | Present |
| `models_xai_sample.json` | Present | Present |
| `reddit_thread_sample.json` | Present | Present |

Same filenames, same directory structure (`fixtures/`), same purpose.

---

## Category 2: Clear Indicators

Structural and algorithmic matches that are highly unlikely to arise independently but don't contain the original project's literal name.

### 2.1 Identical module-for-module library structure

Both repos have `scripts/lib/` with these modules:

| Module | BriefBot | last30days | Purpose |
|---|---|---|---|
| `env.py` | Yes | Yes | Config + API key management |
| `http.py` | Yes | Yes | stdlib-only HTTP client |
| `cache.py` | Yes | Yes | TTL-based disk cache |
| `dates.py` | Yes | Yes | Date parsing + confidence |
| `models.py` | Yes | Yes | Model selection + fallback |
| `schema.py` | Yes | Yes | Dataclass definitions |
| `normalize.py` | Yes | Yes | Raw API to canonical schema |
| `score.py` | Yes | Yes | Engagement-weighted scoring |
| `dedupe.py` | Yes | Yes | Near-duplicate detection |
| `render.py` | Yes | Yes | Output formatting |
| `ui.py` | Yes | Yes | Terminal progress display |
| `websearch.py` | Yes | Yes | Web search normalization |
| `xai_x.py` | Yes | Yes | xAI API for X search |
| `bird_x.py` | Yes | Yes | Vendored Bird X search |
| `openai_reddit.py` | Yes | Yes | OpenAI API for Reddit |
| `reddit_enrich.py` | Yes | Yes | Thread content enrichment |
| `vendor/bird-search/` | Yes | Yes | @steipete/bird v0.8.0 |

17 of 17 core modules match. BriefBot adds delivery modules (email_sender, telegram_sender, tts, pdf, scheduler, jobs, cron_parse) that are genuine additions.

### 2.2 Same HTTPError class structure

**BriefBot:**
```python
class HTTPError(Exception):
    def __init__(self, description, status_code=None, response_body=None):
        super().__init__(description)
        self.status_code = status_code
        self.body = response_body
```

**last30days:**
```python
class HTTPError(Exception):
    def __init__(self, message, status_code=None, body=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
```

Same class, same attributes (`status_code`, `body`), same inheritance. BriefBot renamed `message` to `description` and `body` to `response_body` in the constructor signature but kept `self.body` as the attribute name.

### 2.3 Same retry logic with same constants

| Parameter | BriefBot | last30days |
|---|---|---|
| Max retries | 3 | 3 |
| Backoff base | 1.0s | 1.0s |
| Backoff formula | `base * (attempt + 1)` | `base * (attempt + 1)` |
| Skip 4xx except 429 | Yes | Yes |
| Default timeout | 30s | 30s |

### 2.4 Same scoring pipeline in same order

Both orchestrators execute:
```
normalize_*_items() -> filter_by_date_range() -> score_*_items() -> sort_items() -> dedupe_*()
```
This 5-stage pipeline with the same function names (via aliases in BriefBot) in the same order is a distinctive architectural fingerprint.

### 2.5 Same `_execute_*_query()` return pattern

Both repos use `(items, raw_response, error_message)` as the return tuple from platform query functions. This three-element tuple contract is a specific API design choice.

### 2.6 Same CLI flags and output modes

| Flag/Mode | BriefBot | last30days |
|---|---|---|
| `--mock` | Yes | Yes |
| `--quick` | Yes | Yes |
| `--deep` | Yes | Yes |
| `--debug` | Yes | Yes |
| `--days=N` | Yes | Yes |
| `--sources=` | Yes | Yes |
| `--include-web` | Yes | Yes |
| `--emit=compact` | Yes | Yes |
| `--emit=json` | Yes | Yes |
| `--emit=md` | Yes | Yes |
| `--emit=context` | Yes | Yes |
| `--emit=path` | Yes | Yes |

### 2.7 Same vendored dependency

Both vendor `@steipete/bird v0.8.0` in `scripts/lib/vendor/bird-search/` with the same Node.js CLI wrapper pattern and the same `DISABLE_BIRD = True` toggle at the module level.

### 2.8 Systematic rewrite patterns (obfuscation fingerprints)

BriefBot applies three mechanical transformations that last30days does not use:

**a) All f-strings converted to `.format()`**

last30days: `f"[DEBUG] {msg}\n"` / BriefBot: `"[DEBUG] {}\n".format(msg)`

This conversion is applied across every single file in BriefBot without exception, while last30days uses f-strings throughout. This is consistent with a search-and-replace rewrite, not independent development.

**b) For-loops converted to while-loops**

last30days:
```python
for i, item in enumerate(items):
```

BriefBot:
```python
item_index = 0
while item_index < len(items):
    item = items[item_index]
    item_index += 1
```

This non-idiomatic Python pattern appears throughout BriefBot's score.py, render.py, normalize.py, dates.py, and dedupe.py. last30days uses standard for-loops. The while-loop pattern is a deliberate cosmetic transformation.

**c) Variable name inflation**

| last30days | BriefBot |
|---|---|
| `topic` | `subject_matter` |
| `config` | `configuration` |
| `from_date` | `range_start` |
| `to_date` | `range_end` |
| `msg` | `message_content` |
| `retries` | `retry_limit` |
| `attempt` | `attempt_number` |
| `items` | `content_items` / `extracted_items` |
| `threshold` | `similarity_threshold` |
| `err` | `generic_err` / `network_err` |

### 2.9 Same dedupe algorithm and threshold

Both use Jaccard similarity on character 3-grams with a 0.7 (70%) threshold. This is a specific algorithmic choice (not the only way to deduplicate) with an arbitrary threshold value that matches exactly.

### 2.10 Same cache architecture

| Parameter | BriefBot | last30days |
|---|---|---|
| Standard TTL | 24 hours | 24 hours |
| Model cache TTL | 7 days | 7 days |
| Cache key method | SHA256, 16-char hex | SHA256, 16-char hex |
| Cache key input | `topic\|from\|to\|sources` | `topic\|from\|to\|sources` |
| Model cache file | `model_selection.json` | `model_selection.json` |

### 2.11 Same date format support list

Both repos support the exact same 5 date formats in the same order:
```
%Y-%m-%d
%Y-%m-%dT%H:%M:%S
%Y-%m-%dT%H:%M:%SZ
%Y-%m-%dT%H:%M:%S%z
%Y-%m-%dT%H:%M:%S.%f%z
```

---

## Category 3: Subtle Indicators

Patterns that individually could be coincidental but collectively reinforce the conclusion.

### 3.1 Same `available_platforms` return value set

Both `determine_available_platforms()` / `get_available_sources()` return exactly `"both"`, `"reddit"`, `"x"`, or `"web"` -- the same 4-value enum with the same string labels.

### 3.2 Same `validate_sources()` logic flow

Both implementations handle: auto mode, web-only fallback, explicit source requests, and `include_web` modifier with the same compound return strings: `"reddit-web"`, `"x-web"`, `"all"`.

### 3.3 Same random UI status messages

BriefBot's `ui.py` contains many of the same random status messages:

| Message | BriefBot | last30days |
|---|---|---|
| "Diving into Reddit threads..." | Yes | Yes |
| "Reading the timeline..." | Yes | Yes |
| "Finding the hot takes..." | Yes | Yes |
| "Checking what X is buzzing about..." | Yes | Yes |
| "Getting the juicy details..." | Yes | Yes |
| "Reading between the posts..." | Yes | Yes |

These creative phrases are author-specific. Independent development would not produce the same colloquial wording.

### 3.4 Same ANSI color code assignments

| Color name (BriefBot) | Code | Color name (last30days) | Code |
|---|---|---|---|
| MAGENTA | `\033[95m` | PURPLE | `\033[95m` |
| AZURE | `\033[94m` | BLUE | `\033[94m` |
| TEAL | `\033[96m` | CYAN | `\033[96m` |
| LIME | `\033[92m` | GREEN | `\033[92m` |
| AMBER | `\033[93m` | YELLOW | `\033[93m` |
| CRIMSON | `\033[91m` | RED | `\033[91m` |

Same 6 ANSI codes, same order, same class structure. BriefBot renamed the color names (PURPLE to MAGENTA, BLUE to AZURE, etc.) -- the same cosmetic rename pattern seen throughout.

### 3.5 Same API endpoints

Both repos use:
- `https://api.x.ai/v1/responses` (xAI)
- `https://api.openai.com/v1/responses` (OpenAI Responses API, not chat completions)
- `https://api.x.ai/v1/models` (model listing)
- `https://api.openai.com/v1/models` (model listing)

### 3.6 Same dataclass field names

Both `Engagement` dataclasses use identical field names: `score`, `num_comments`, `upvote_ratio`, `likes`, `reposts`, `replies`, `quotes`, `views`. The `Comment` and `SubScores` dataclasses also match field-for-field.

### 3.7 Same module header comment style (transformed)

last30days: Brief docstrings
```python
"""HTTP utilities for last30days skill (stdlib only)."""
```

BriefBot: Elaborate block comments
```python
#
# Network Layer: HTTP client implementation for the BriefBot skill
# Uses only standard library modules for maximum compatibility
#
```

The information is the same ("HTTP", "stdlib only"), but BriefBot wraps it in a distinctive `# Category: Description` format applied uniformly across all modules. This is a cosmetic layer added during the rewrite.

### 3.8 Same config file format and key names

Both parse `.env` files with the same logic: skip `#` comments, split on `=`, strip quotes. Both handle these exact keys: `OPENAI_API_KEY`, `XAI_API_KEY`, `OPENAI_MODEL_POLICY`, `OPENAI_MODEL_PIN`, `XAI_MODEL_POLICY`, `XAI_MODEL_PIN`.

### 3.9 Same error message formatting pattern

Both repos format errors identically:
```python
"API error: {}".format(err)          # BriefBot
f"API error: {e}"                    # last30days

"{}: {}".format(type(e).__name__, e) # BriefBot
f"{type(e).__name__}: {e}"           # last30days
```

Same structure, different string formatting method -- consistent with systematic f-string to .format() conversion.

### 3.10 Version evidence in User-Agent

BriefBot's User-Agent says `last30days-skill/1.0` while last30days is at `2.1`. This suggests BriefBot was forked from an earlier version (v1.x) and has not tracked upstream changes to the version number. The delivery features (email, Telegram, TTS, scheduling) were added on top of the forked v1.x base.

### 3.11 Same `--emit=path` output mode

Both support a `path` output mode that prints the filesystem path to the context file. This is an unusual output mode specific to Claude Code skill integration -- not a standard CLI pattern.

### 3.12 Same Windows console encoding fix

Both repos contain this identical block in all entry points:
```python
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

---

## What BriefBot genuinely added

For completeness, these features appear to be original additions not present in last30days:

- Email delivery (`email_sender.py`, SMTP integration)
- Telegram bot integration (`telegram_bot.py`, `telegram_sender.py`)
- Text-to-speech audio (`tts.py`, ElevenLabs/edge-tts)
- PDF generation (`pdf.py`)
- Job scheduling (`scheduler.py`, `jobs.py`, `cron_parse.py`)
- Interactive setup wizard (`setup.py`)
- LinkedIn search (`openai_linkedin.py`)
- Cookie bridge Chrome extension (`cookie-bridge/`)

These delivery and scheduling features constitute genuine new functionality built on top of the forked research engine.

---

## Summary of evidence count

| Category | Count |
|---|---|
| **Irrefutable indicators** (original project name in code) | 7 |
| **Clear indicators** (structural/algorithmic matches) | 11 |
| **Subtle indicators** (patterns reinforcing the conclusion) | 12 |
| **Total findings** | **30** |
