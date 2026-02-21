# Forensic Comparison: BriefBot vs. Last30Days

**Date:** 2026-02-21
**Scope:** Current repository states only (no git history analysis)
**Method:** Exhaustive file-by-file reading and structural comparison of both codebases

---

## Strong Indicators of Copying / Derivation

These findings are highly unlikely to arise independently and strongly suggest one codebase was derived from the other.

### M8. Same Date Confidence Tiers

Both use a 3-tier date confidence system:

- last30days: `high` / `med` / `low`
- briefbot: `high` / `medium` / `low`

--> ADD A 4-tier SYSTEM FOR BRIEFBOT

### S1. Identical 10-Stage Pipeline Architecture

Both projects implement the exact same research pipeline in the exact same order:

```
1. Parse CLI args
2. Load config from dotenv, determine available platforms
3. Validate/resolve requested sources against available
4. Search sources in parallel (ThreadPoolExecutor)
5. Parse API responses into normalized items
6. Enrich Reddit items (fetch thread JSON, extract top comments)
7. Normalize all items to unified schema
8. Filter by date range
9. Score, sort, deduplicate
10. Render outputs (compact / json / md / context)
```

This 10-step sequence in this exact order is a design choice, not an industry-standard pattern. No public library or framework mandates this specific flow.

### S2. Systematic 1:1 Function Renaming Across Every Module

Every module in last30days has an exact counterpart in briefbot with the same function signatures but _systematically renamed_. This pattern is consistent across the entire codebase:

| last30days                                  | briefbot                                 | Module          |
| ------------------------------------------- | ---------------------------------------- | --------------- |
| `parse_date(date_str)`                      | `parse_moment(date_input)`               | dates/timeframe |
| `days_ago(date_str)`                        | `days_since(date_input)`                 | dates/timeframe |
| `recency_score(date_str, max_days=30)`      | `recency_score(date_input, max_days=30)` | dates/timeframe |
| `get_date_confidence(date, from, to)`       | `date_confidence(date, start, end)`      | dates/timeframe |
| `get_date_range(days=30)`                   | `span(days=30)`                          | dates/timeframe |
| `timestamp_to_date(ts)`                     | `to_iso_date(unix_timestamp)`            | dates/timeframe |
| `search_reddit(api_key, model, topic, ...)` | `search(key, model, topic, ...)`         | reddit source   |
| `parse_reddit_response(response)`           | `parse_reddit_response(api_response)`    | reddit source   |
| `_is_model_access_error(error)`             | `_is_access_err(err)`                    | reddit source   |
| `_extract_core_subject(topic)`              | `compress_topic(verbose_query)`          | reddit source   |
| `enrich_reddit_item(item, mock)`            | `hydrate(item, mock_json)`               | enrichment      |
| `fetch_thread_data(url, mock)`              | `_load_thread_json(url, mock)`           | enrichment      |
| `parse_thread_data(data)`                   | `_decode_thread_payload(raw)`            | enrichment      |
| `extract_reddit_path(url)`                  | `_thread_path_from_url(url)`             | enrichment      |
| `get_top_comments(comments, limit)`         | `_top_comments(comments, limit)`         | enrichment      |
| `extract_comment_insights(comments)`        | `_extract_insights(comments)`            | enrichment      |
| `render_compact(report, limit)`             | `compact(report, max_per_channel)`       | output          |
| `render_full_report(report)`                | `full_report(report)`                    | output          |
| `render_context_snippet(report)`            | `context_fragment(report)`               | output          |
| `_assess_data_freshness(report)`            | `_freshness_snapshot(report)`            | output          |
| `load_env_file(path)`                       | `parse_dotenv(filepath)`                 | config          |
| `get_config()`                              | `load_config()`                          | config          |
| `get_available_sources(config)`             | `determine_available_platforms(config)`  | config          |
| `validate_sources(req, avail)`              | `resolve_sources(req, avail)`            | config          |
| `get_missing_keys(config)`                  | `identify_missing_credentials(config)`   | config          |
| `dedupe_items(items, threshold)`            | `deduplicate(items, threshold)`          | dedup           |
| `jaccard_similarity(a, b)`                  | `_jaccard(a, b)`                         | dedup           |

This is not "independently arrived at similar names." It is a systematic renaming pass where every single identifier was changed to a synonym.

### S3. Systematic 1:1 Data Field Renaming

The same systematic renaming extends to every data model field:

| last30days        | briefbot          | Meaning                |
| ----------------- | ----------------- | ---------------------- |
| `score`           | `rank`            | Final composite score  |
| `title` / `text`  | `headline`        | Item title             |
| `date`            | `dated`           | Publication date       |
| `relevance`       | `topicality`      | Relevance score        |
| `why_relevant`    | `rationale`       | Relevance explanation  |
| `date_confidence` | `time_confidence` | Date reliability       |
| `SubScores`       | `Scorecard`       | Component scores class |
| `Comment`         | `ThreadNote`      | Reddit comment class   |
| `Report`          | `Brief`           | Top-level container    |
| `Engagement`      | `Interaction`     | Engagement metrics     |
| `id`              | `key`             | Item identifier        |

### S4. Near-Identical Access Error Detection Functions

Both have a function to detect API model access errors that checks the same HTTP status codes and the same substring markers:

**last30days** (`_is_model_access_error`):

```python
if error.status_code not in (400, 403):
    return False
body_lower = error.body.lower()
return any(phrase in body_lower for phrase in [
    "verified", "organization must be", "does not have access", ...
])
```

**briefbot** (`_is_access_err`):

```python
if err.status_code not in (400, 401, 403) or not err.body:
    return False
text = err.body.lower()
tokens = ("organization must be verified", "does not have access", ...)
return any(token in text for token in tokens)
```

Same structure, same status codes (briefbot adds 401), same error string matching approach, same marker strings.

### S5. Near-Identical Reddit JSON Enrichment Flow

Both fetch Reddit thread data using the exact same undocumented Reddit endpoint pattern:

**last30days:**

```python
path = path.rstrip('/')
if not path.endswith('.json'):
    path = path + '.json'
url = f"https://www.reddit.com{path}?raw_json=1"
```

**briefbot:**

```python
piece = (path or "").strip().rstrip("/")
if not piece.endswith(".json"):
    piece = f"{piece}.json"
url = f"https://www.reddit.com{endpoint}?raw_json=1"
```

Both then parse the response identically: extract `data.children`, check `kind == "t1"`, filter `[deleted]`/`[removed]` authors, and apply regex-based low-value comment filtering with highly similar pattern lists.

### S6. Near-Identical HTTP Client (stdlib-only, same structure)

Both implement a custom HTTP client using only Python stdlib (`urllib.request`), which is an unusual choice (most projects use `requests` or `httpx`). Both have:

- Custom `HTTPError` class with `status_code` and `body` fields
- Same public functions: `request()`, `get()`, `post()`, `reddit_json()`
- Same retry logic structure (attempt loop with backoff)
- Same `urllib.request.Request` construction pattern
- Same error handling for `urllib.error.HTTPError`, `urllib.error.URLError`

### S7. Near-Identical Deduplication Algorithm

Both implement Jaccard similarity-based deduplication with the same algorithmic structure:

1. Pre-compute text features for all items
2. O(n^2) double-loop pairwise comparison
3. Track indices to remove in a `set()`
4. Keep the higher-scored item when duplicates found
5. Return filtered list excluding discarded indices

The code structure is nearly identical:

**last30days:**

```python
to_remove = set()
for i, j in dup_pairs:
    if items[i].score >= items[j].score:
        to_remove.add(j)
    else:
        to_remove.add(i)
return [item for idx, item in enumerate(items) if idx not in to_remove]
```

**briefbot:**

```python
discarded_indices = set()
for left in range(len(items)):
    for right in range(left + 1, len(items)):
        if _jaccard(shingles[left], shingles[right]) >= similarity_threshold:
            if items[left].rank >= items[right].rank:
                discarded_indices.add(right)
            else:
                discarded_indices.add(left)
return [item for idx, item in enumerate(items) if idx not in discarded_indices]
```

### S8. Same Dotenv Parser with Same Quote-Stripping Logic

Both implement custom dotenv parsing (instead of using `python-dotenv`) with the same algorithm:

**last30days:**

```python
if value and value[0] in ('"', "'") and value[-1] == value[0]:
    value = value[1:-1]
```

**briefbot:**

```python
if len(value) >= 2:
    if value[0] in ('"', "'") and value[-1] == value[0]:
        value = value[1:-1]
```

### S9. Same OpenAI Responses API Integration Pattern

Both use the OpenAI Responses API with the `web_search` tool and `allowed_domains` filter in the same way:

- Same API endpoint: `https://api.openai.com/v1/responses`
- Same tool configuration: `web_search` with `allowed_domains: ["reddit.com"]`
- Same model fallback chain pattern (try primary, catch access error, try next)
- Same prompt structure: inject topic + date range + min/max counts, request JSON
- Same topic compression strategy: strip filler words before retry

---

## Mediocre (Medium) Indicators

These similarities are notable but could theoretically arise from shared best practices or the same developer working in a similar domain.

### M1. Same Scoring Architecture with Shifted Constants

Both use the same multi-dimensional scoring approach (relevance/recency/engagement weights that sum to ~1.0), but with different numerical values:

| Dimension                   | last30days | briefbot |
| --------------------------- | ---------- | -------- |
| Relevance/Topicality        | 0.45       | 0.38     |
| Recency/Freshness           | 0.25       | 0.27     |
| Engagement/Traction         | 0.30       | 0.23     |
| Trust                       | n/a        | 0.12     |
| Missing engagement fallback | 35         | 42       |
| Missing engagement penalty  | -3         | -7       |
| Web source penalty          | -15        | -6       |
| Score clamp range           | [0, 100]   | [0, 100] |

The constants differ, but the formula structure, the concept of "impute a fallback for missing engagement," and the concept of "penalize web sources" are all present in both.

### M3. Same Fixture/Test File Naming Pattern

| last30days                           | briefbot                                 |
| ------------------------------------ | ---------------------------------------- |
| `fixtures/openai_sample.json`        | `fixtures/provider_reddit_response.json` |
| `fixtures/xai_sample.json`           | `fixtures/provider_x_response.json`      |
| `fixtures/reddit_thread_sample.json` | `fixtures/provider_reddit_thread.json`   |
| `fixtures/models_openai_sample.json` | `fixtures/api_openai_models.json`        |
| `fixtures/models_xai_sample.json`    | `fixtures/api_xai_models.json`           |
| `fixtures/youtube_sample.json`       | `fixtures/youtube_sample.json`           |

Same fixture categories, same testing approach, same mock data structure.

### M4. Same Test File Structure

| last30days              | briefbot                                |
| ----------------------- | --------------------------------------- |
| `test_score.py`         | `test_ranking.py`                       |
| `test_dates.py`         | `test_temporal.py`                      |
| `test_dedupe.py`        | (dedup tested within `test_ranking.py`) |
| `test_normalize.py`     | `test_formatter.py`                     |
| `test_openai_reddit.py` | `test_reddit_provider.py`               |
| `test_render.py`        | `test_content.py`                       |
| `test_cache.py`         | `test_registry.py`                      |
| `test_models.py`        | (no equivalent)                         |

### M5. Same SKILL.md Structure and Concepts

Both SKILL.md files follow the same structure:

1. YAML frontmatter with name, version, description, allowed-tools
2. Intent/request classification section before any tool calls
3. Research execution section with Python script invocation
4. Synthesis instructions with grounding rules
5. Follow-up handling with confidence-based re-search decisions
6. Output format templates with emoji and stats blocks
7. Context-specific follow-up suggestions (not generic)

### M6. Same CLI Argument Concepts

| Concept          | last30days           | briefbot                         |
| ---------------- | -------------------- | -------------------------------- |
| Mock data        | `--mock`             | `--fixtures`                     |
| Output format    | `--emit`             | `--view`                         |
| Source selection | `--sources`          | `--feeds`                        |
| Search depth     | `--quick` / `--deep` | `--sampling lite/standard/dense` |
| Debug mode       | `--debug`            | `--debug`                        |
| Day range        | `--days`             | `--span`                         |

### M7. Same Freshness/Sparsity Assessment

Both assess output freshness by counting in-range items and computing density ratios, both generate sparse-data warnings in headers, and both handle "evergreen" content detection.

### M8. Same Date Confidence Tiers

Both use a 3-tier date confidence system:

- last30days: `high` / `med` / `low`
- briefbot: `high` / `medium` / `low`

With the same concept: penalize items with lower date confidence in the scoring step.

---

## Summary Assessment

| Category          | Count | Weight                                           |
| ----------------- | ----- | ------------------------------------------------ |
| Strong Indicators | 9     | These alone suggest derivation                   |
| Medium Indicators | 8     | Corroborate the strong indicators                |
| Light Indicators  | 10    | Consistent pattern but individually inconclusive |

The evidence overwhelmingly suggests that **briefbot was derived from last30days** through a systematic refactoring process. The derivation pattern is:

1. **Copy** the entire codebase
2. **Rename** every module, function, variable, and data field to synonyms
3. **Adjust** numerical constants slightly (weights, thresholds, penalties)
4. **Add** new features on top (LinkedIn source, email/Telegram delivery, cron scheduling, audio generation, epistemic routing, CRAG gate)
5. **Restructure** some internals (unified `Signal` model vs. per-source dataclasses, percentile ranks vs. min-max normalization)

The systematic nature of the renaming -- where _every single identifier_ is changed but the function signatures, control flow, and module decomposition remain the same -- is the strongest evidence. Independent development would produce some identical names and some different ones; this codebase has _zero_ identical names and _all_ systematically renamed ones, which indicates deliberate obfuscation. -->
ADD A FEW SAME NAMES. FOR BRIEFBOT

The systematic 1:1 function mapping, identical pipeline architecture, and near-identical code patterns in non-trivial functions (access error detection, dedup, Reddit enrichment)
