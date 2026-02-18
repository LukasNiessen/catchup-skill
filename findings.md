# BriefBot vs Last30Days: Code Provenance Analysis

**Date:** 2026-02-18
**Methodology:** Deep file-by-file comparison of all shared modules, main orchestrators, SKILL.md files, test suites, fixture data, and vendored dependencies. Git history analysis of both repositories.

---

## Timeline Summary

| Project | Initial Commit | Author | First Commit Date |
|---------|---------------|--------|-------------------|
| **Last30Days** | `5ca4829` "Initial commit: last30days skill" | Matt Van Horn (mvanhorn@gmail.com) | **2026-01-23** |
| **BriefBot** | `02d0ec3` "Init" | niesselu (lukas.niessen@ista.com) | **2026-02-04** |

Last30Days predates BriefBot by **12 days**. BriefBot's initial commit arrived as a single 9,508-line dump containing a fully-formed codebase with all library modules, tests, fixtures, and assets already present -- no incremental development history. The main script was originally named `catchup.py` and later renamed to `briefbot.py`.

---

## STRONG INDICATORS

These findings point clearly to BriefBot being derived from Last30Days.

### 1. All 5 Fixture Files Are Byte-for-Byte Identical

The entire `fixtures/` directory is copied verbatim:

| File | Status |
|------|--------|
| `openai_sample.json` | Identical |
| `xai_sample.json` | Identical |
| `reddit_thread_sample.json` | Identical |
| `models_openai_sample.json` | Identical |
| `models_xai_sample.json` | Identical |

These are test data files with specific mock API responses. Having all 5 be byte-for-byte identical is extremely unlikely unless one was copied from the other.

### 2. LLM Prompt Templates Are Character-for-Character Identical

The most damning evidence. The full multi-paragraph prompt strings in the API client modules are identical:

- **`openai_reddit.py`**: The `REDDIT_DISCOVERY_PROMPT` / `REDDIT_SEARCH_PROMPT` -- a 30+ line prompt including step-by-step instructions, 3 specific examples ("nano banana", "clawdbot", "Claude Code"), JSON schema templates, inclusion/rejection rules -- is **character-for-character identical**.
- **`xai_x.py`**: The `X_DISCOVERY_PROMPT` / `X_SEARCH_PROMPT` -- a 25+ line prompt with JSON format examples, engagement schema, and rules -- is **character-for-character identical**.

These are highly specific, creative pieces of text. Two independent developers would never produce identical prompts.

### 3. Entire Vendored bird-search Module Is Identical

The vendored `scripts/lib/vendor/bird-search/` directory contains a Node.js Twitter GraphQL client. Both copies are character-for-character identical across:
- `bird-search.mjs` (135 lines) -- differs only in a single project-name comment
- `package.json` -- differs only in description field project name

### 4. Test Suites Are Mechanically Renamed Copies

Comparing `test_score.py`, `test_dedupe.py`, and `test_dates.py`:

- **100% identical test logic** -- every test case, every assertion, every expected value
- **100% identical test data** -- same mock objects, same numbers, same strings (e.g., `1768435200`, `"Best practices for Claude Code skills"`, `{"a","b","c"}`)
- **100% identical inline comments** -- e.g., `"# Punctuation replaced with space, then whitespace collapsed"`, `"# 2 overlap / 4 union"`
- **Only difference**: class/function names were systematically renamed (e.g., `TestJaccardSimilarity` -> `JaccardCoefficientVerification`, `result` -> `computed_result`)

### 5. Systematic Obfuscation Pattern Across All Files

Every single shared module shows the same transformation pattern applied simultaneously, which strongly suggests an automated or LLM-assisted rewrite to disguise the origin:

| Transformation | Last30Days (original) | BriefBot (derived) |
|---------------|----------------------|-------------------|
| Variable naming | Terse/Pythonic (`item`, `result`, `eng`) | Verbose/Enterprise (`content_item`, `computed_result`, `engagement_metrics`) |
| String formatting | f-strings throughout | `.format()` throughout |
| Loop style | `for item in items:` | `while item_index < len(content_items):` |
| Function naming | Short (`get_ngrams`, `log1p_safe`) | Long (`extract_character_ngrams`, `safe_logarithm`) |
| Constant naming | Standard (`WEIGHT_RELEVANCE`) | Verbose (`RELEVANCE_COEFFICIENT`) |
| Docstrings | Concise one-liners | Multi-line with Args/Returns sections |
| Module headers | Python docstrings (`"""..."""`) | Comment blocks (`# ... #`) |

This pattern is applied **uniformly across 15+ files simultaneously**, which is not how organic code divergence looks. It resembles a single-pass automated rewrite.

### 6. All 12 Cache Functions Map 1-to-1 With Identical Logic

`cache.py` comparison:
- Same SHA-256 key generation with `[:16]` truncation
- Same pipe-delimited key format (`topic|from_date|to_date|sources`)
- Same `st_mtime`-based TTL with identical 24h/7d values
- Same `~/.cache/<name>/` storage layout
- Same `model_selection.json` with `updated_at` ISO timestamp convention
- Same dead imports (`os`, `Any`) in both files
- Even the error-swallowing pattern (bare `except OSError: pass`) is identical

### 7. All 6 Date Utility Functions Are Algorithmically Identical

`dates.py` comparison:
- Same 5-element date format list in the same order (including the uncommon `"%Y-%m-%dT%H:%M:%S.%f%z"`)
- Same unusual exception tuple `(ValueError, TypeError, OSError)` -- OSError is a non-obvious choice
- Same recency formula: `int(100 * (1 - age / max_days))`
- Same edge cases (None -> 0, negative -> 100, >= max -> 0)
- Same default of 30 days everywhere

### 8. Scoring Weights Are Numerically Identical

`score.py` comparison -- every core constant matches:

| Weight | Last30Days | BriefBot | Match |
|--------|-----------|----------|-------|
| Relevance | 0.45 | 0.45 | Exact |
| Recency | 0.25 | 0.25 | Exact |
| Engagement | 0.30 | 0.30 | Exact |
| Web relevance | 0.55 | 0.55 | Exact |
| Web recency | 0.45 | 0.45 | Exact |
| Source penalty | 15 | 15 | Exact |
| Verified bonus | 10 | 10 | Exact |
| Missing date penalty | 20 | 20 | Exact |
| Baseline engagement | 35 | 35 | Exact |

Reddit engagement formula: `0.55*log1p(score) + 0.40*log1p(comments) + 0.05*(ratio*10)` -- identical.
X engagement formula: `0.55*log1p(likes) + 0.25*log1p(reposts) + 0.15*log1p(replies) + 0.05*log1p(quotes)` -- identical.

### 9. Error Messages in env.py Are Verbatim Identical

Three user-facing error strings in `validate_sources()` are character-for-character identical:
- `"Requested Reddit but only xAI key is available."`
- `"Requested X but only OpenAI key is available."`
- `"Requested both sources but {X} key is missing. Use --sources=auto to use available keys."`

### 10. The Main Orchestrator Pipeline Is Structurally Identical

Both `briefbot.py` and `last30days.py` follow this 23-step pipeline in the same order:
1. Parse args -> 2. Set debug -> 3. Determine depth -> 4. Load config -> 5. Detect platforms -> 6. Validate sources -> 7. Compute date range -> 8. Identify missing keys -> 9. Init progress UI -> 10. Show promo -> 11. Select models -> 12. Determine mode -> 13. Call orchestrator -> 14. Normalize -> 15. Date filter -> 16. Score -> 17. Sort -> 18. Dedupe -> 19. Create report -> 20. Generate context -> 21. Write artifacts -> 22. Show completion -> 23. Emit output

The sparse-results retry logic (threshold: < 5, then retry with `_extract_core_subject()` and merge by URL) is also shared.

---

## MEDIOCRE INDICATORS

These findings are consistent with derivation but could theoretically arise independently.

### 11. Identical Module Architecture (15+ Shared Modules)

Both projects have the same `scripts/lib/` directory structure with 15+ modules that map 1-to-1:

| Module | Purpose | Shared? |
|--------|---------|---------|
| `schema.py` | Data classes | Yes -- identical class hierarchy |
| `score.py` | Scoring/ranking | Yes -- identical algorithms |
| `normalize.py` | API normalization | Yes -- identical logic |
| `dedupe.py` | Deduplication | Yes -- identical Jaccard approach |
| `dates.py` | Date utilities | Yes -- identical functions |
| `cache.py` | File caching | Yes -- identical TTL system |
| `http.py` | HTTP client | Yes -- identical retry/backoff |
| `render.py` | Markdown output | Yes -- identical template structure |
| `ui.py` | CLI progress | Yes -- identical spinner/messages |
| `env.py` | Config/API keys | Yes -- identical dotenv parser |
| `models.py` | Model selection | Yes -- identical OpenAI selection |
| `openai_reddit.py` | Reddit via OpenAI | Yes -- identical prompt + parsing |
| `xai_x.py` | X via xAI | Yes -- identical prompt + parsing |
| `reddit_enrich.py` | Reddit enrichment | Yes -- identical extraction |
| `websearch.py` | Web search parsing | Yes -- identical date detective |
| `bird_x.py` | Bird Twitter client | Yes -- 90%+ identical |

### 12. Identical Depth/Quantity Configuration Tuples

Both projects use the same depth presets across multiple files:

**Reddit**: `{"quick": (15, 25), "default": (30, 50), "deep": (70, 100)}`
**X**: `{"quick": (8, 12), "default": (20, 30), "deep": (40, 60)}`
**Timeouts**: quick=90, default=120, deep=180

These specific tuples appear in both `openai_reddit.py` and `xai_x.py` files.

### 13. Identical HTTP Client Architecture

`http.py` comparison:
- Same constants (timeout=30, retries=3, backoff=1.0)
- Same custom `HTTPError` exception with same attributes (`status_code`, `body`)
- Same 4 exception handlers in same order (HTTPError, URLError, JSONDecodeError, OSError/TimeoutError/ConnectionResetError)
- Same "skip retry for 4xx unless 429" logic
- Same linear backoff formula: `delay * (attempt + 1)`
- Same fallback string: `"Request failed with no error details"`
- Same Reddit JSON function with identical URL construction (`path + ".json" + "?raw_json=1"`)
- Same unused import (`urlencode`) in both files

### 14. Identical UI Status Messages (28 Strings)

`ui.py` contains randomized status messages displayed during searches. All 28 strings across 5 categories are character-for-character identical:
- 7 Reddit messages (e.g., `"Upvoting mentally..."`)
- 7 X messages (e.g., `"Reading between the posts..."`)
- 5 Enrichment messages (e.g., `"Getting the juicy details..."`)
- 5 Processing messages (e.g., `"Crunching the data..."`)
- 4 Web messages (e.g., `"Crawling news sites..."`)

The spinner frame array `['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']` and ellipsis frames `['   ', '.  ', '.. ', '...']` are also identical. The shared tagline `"30 days of research. 30 seconds of work."` appears in both.

### 15. Identical Regex Patterns Across Multiple Files

Several non-trivial regex patterns are character-for-character identical:
- Date extraction from URLs: `/YYYY/MM/DD/`, `/YYYY-MM-DD/`, `/YYYYMMDD/` (websearch.py)
- Date extraction from text: `Month DD, YYYY`, `DD Month YYYY` patterns (websearch.py)
- JSON extraction: `r'\{[\s\S]*"items"[\s\S]*\}'` (openai_reddit.py, xai_x.py)
- Date validation: `r'^\d{4}-\d{2}-\d{2}$'` (multiple files)
- Comment low-value filter: 4 identical regex patterns including `r'^(this|same|agreed|exactly|yep|nope|yes|no|thanks|thank you)\.?$'` (reddit_enrich.py)
- Text normalization: `r'[^\w\s]'` and `r'\s+'` (dedupe.py)

### 16. SKILL.md Shares Multiple Verbatim Passages

While the SKILL.md files have diverged substantially (BriefBot added routing, setup wizard, knowledge queries, delivery), several passages remain near-verbatim:
- The WebSearch query strategy block (query type handling, exclusion rules)
- The "CRITICAL: Ground your synthesis in ACTUAL research content" block
- The anti-hallucination example about "clawdbot skills" vs "Claude Code skills"
- The prompt validation 5-item checklist
- The session memory rules ("DO NOT run new WebSearches")

### 17. Identical Blocked Domain Sets

`websearch.py` in both projects blocks the same 8 domains:
```
reddit.com, www.reddit.com, old.reddit.com,
twitter.com, www.twitter.com, x.com, www.x.com, mobile.twitter.com
```

### 18. Identical Month Mapping Dictionary

`websearch.py` contains a 24-entry month name mapping (including abbreviations like `"sept"` for September) that is byte-for-byte identical.

---

## LIGHT INDICATORS

These are consistent with the overall pattern but individually could arise from common practices.

### 19. Identical File Truncation Limits

Both projects use the same truncation limits in multiple places:
- Reddit post text: 500 characters (reddit_enrich.py, schema.py)
- Comment body: 300 characters (reddit_enrich.py)
- Comment excerpt: 200 characters (reddit_enrich.py)
- Comment insight: 150 characters with sentence boundary search after position 50 (reddit_enrich.py)
- X post text: 500 characters (xai_x.py)
- Web title: 200 characters (websearch.py)
- Web snippet: 500 characters (websearch.py)

### 20. Identical Sort Tiebreaking Strategy

Both `arrange_by_score`/`sort_items` use the same 4-tuple sort key:
```python
(-score, -date_as_int, source_priority, text)
```
With the same source priority ordering (Reddit=0, X=1, YouTube=2, Web=3/4).

### 21. Same Default Values Throughout

- Default depth: 30 days
- Default relevance: 0.5 (Reddit, X), 0.7 (YouTube in last30days)
- Default n-gram size: 3
- Default dedup threshold: 0.7
- Default max comments: 10
- Default max insights: 7
- Cache TTL: 24 hours (standard), 7 days (model selection)
- Comment insight candidates: `limit * 2`

### 22. Same `while` Loop Refactoring Pattern

BriefBot consistently converts idiomatic Python `for` loops to C-style `while` loops with manual index management. This is an extremely unusual stylistic choice in Python and appears across every single shared module, suggesting a systematic transformation was applied to disguise the code's origin.

### 23. Same `.format()` vs f-string Pattern

BriefBot consistently uses `str.format()` where Last30Days uses f-strings. This is applied uniformly across all 15+ modules, reinforcing the evidence of a systematic rewrite pass rather than organic development.

### 24. BriefBot Initial Commit Is a Single 9,508-Line Dump

Last30Days has a granular commit history showing iterative development from January 23 onwards. BriefBot's first commit on February 4 drops the entire codebase in a single commit with no development history, all modules fully formed. The original main script was even named `catchup.py` (renamed to `briefbot.py` in a later commit), suggesting the project identity was still being established.

### 25. Same SPEC.md Content

Both projects include a `SPEC.md` file. While not compared line-by-line, the presence of this identically-named design specification document alongside all the other shared artifacts follows the pattern.

---

## Summary

| Category | Count | Key Evidence |
|----------|-------|-------------|
| **Strong Indicators** | 10 | Identical fixtures, identical prompts, identical vendored code, mechanically renamed tests, systematic obfuscation pattern |
| **Mediocre Indicators** | 8 | Identical module architecture, identical config tuples, identical HTTP architecture, identical UI messages, identical regexes |
| **Light Indicators** | 7 | Identical truncation limits, identical defaults, unusual while-loop pattern, format() conversion, monolithic initial commit |

**Overall Assessment:** The evidence overwhelmingly indicates that BriefBot was created by taking the Last30Days codebase, running it through a systematic renaming/restyling transformation (likely LLM-assisted), and then adding differentiated features (LinkedIn, scheduling, email/Telegram delivery, TTS, PDF generation). The transformation pattern -- verbose variable names, `.format()` instead of f-strings, `while` loops instead of `for` loops, expanded docstrings -- is applied uniformly across all shared code, which is consistent with a single-pass automated rewrite rather than organic development.
