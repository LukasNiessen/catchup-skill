# BriefBot Derivation Analysis: Was It Copied From Last30Days?

> **Date**: 2026-02-20
> **Method**: Exhaustive side-by-side source code comparison of every file in both repositories
> **Scope**: All `.py` source files, tests, fixtures, configs, SKILL.md, README.md, and documentation
> **Note**: Git history was explicitly excluded; only current repo states were compared.

---

## STRONG INDICATORS

These findings represent clear, unambiguous evidence that BriefBot's core engine was derived from Last30Days by systematic copying and renaming.

---

### 1. The `parse_reddit_response()` Function Is a Line-by-Line Copy

This is the single most damning piece of evidence. Both functions follow an **identical 7-step control flow** that would be astronomically unlikely to arise independently:

**Step 1 — Error check** (identical logic):

```python
# BriefBot (reddit.py:188)                    # Last30Days (openai_reddit.py:297)
if api_response.get("error"):                  if "error" in response and response["error"]:
    err_data = api_response["error"]               error = response["error"]
    err_msg = (                                     err_msg = error.get("message", str(error))
        err_data.get("message", str(err_data))          if isinstance(error, dict) else str(error)
        if isinstance(err_data, dict)
        else str(err_data)
    )
```

**Step 2 — Output text extraction** (identical nested traversal):
Both iterate `response["output"]`, check `isinstance(output, str)`, then `isinstance(output, list)`, then for each element check `elem.get("type") == "message"` → iterate `content` → check `block.get("type") == "output_text"` → extract `block.get("text", "")`. Both also check for `"text"` key and bare string elements. Both break on first found text.

**Step 3 — Legacy fallback** (identical):

```python
# Both:
if not output_text and "choices" in response:
    for choice in response["choices"]:
        if "message" in choice:
            output_text = choice["message"].get("content", "")
            break
```

**Step 4 — Warning message** (nearly identical):

```python
# BriefBot:
f"[WARNING REDDIT] No output text found in the response from OpenAI. Keys present: {list(api_response.keys())}"
# Last30Days:
f"[REDDIT WARNING] No output text found in OpenAI response. Keys present: {list(response.keys())}"
```

**Step 5 — JSON extraction** (same intent, slightly different regex):

```python
# BriefBot:
match = re.search(r'\{[^{}]*"items"\s*:\s*\[[\s\S]*?\]\s*\}', output_text)
# Last30Days:
json_match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', output_text)
```

**Step 6 — Item validation** (identical logic):
Both check `isinstance(raw, dict)`, check `"reddit.com" in url`, build a clean dict with `f"R{i+1}"` IDs, strip subreddit with `.lstrip("r/")`, clamp relevance with `min(1.0, max(0.0, float(...)))`, and validate dates with `re.match(r'^\d{4}-\d{2}-\d{2}$', ...)`.

**Verdict**: This function has too many identical micro-decisions (the nested output traversal, the legacy `choices` fallback, the `f"R{i+1}"` ID scheme, the `.lstrip("r/")` call, the identical warning format) to be independent work.

---

### 2. The `_core_subject()` / `_extract_core_subject()` Filler Word Lists Are Near-Identical

**BriefBot** (`reddit.py:89-110`):

```python
filler = {
    "best", "top", "how to", "tips for", "review", "features",
    "killer", "comparison", "overview", "recommendations", "advice",
    "tutorial", "prompting", "using", "for", "with", "the", "of", "in", "on",
}
```

**Last30Days** (`openai_reddit.py:98-100`):

```python
noise = ['best', 'top', 'how to', 'tips for', 'practices', 'features',
         'killer', 'guide', 'tutorial', 'recommendations', 'advice',
         'prompting', 'using', 'for', 'with', 'the', 'of', 'in', 'on']
```

19 of 20 BriefBot words appear in the Last30Days list. Both lists share the unusual inclusion of multi-word entries like `"how to"` and `"tips for"` (which wouldn't normally be matched by `.split()` — this is actually a bug in both codebases, and **sharing the same bug is strong copy evidence**). Both functions cap output at 3 words: `kept[:3]` / `result[:3]`.

---

### 3. The Reddit Enrichment Pipeline Is Functionally Identical (5 Functions, Same Structure)

Comparing `briefbot_engine/providers/enrich.py` vs `last30days-skill/scripts/lib/reddit_enrich.py`:

| Function           | BriefBot              | Last30Days                   | Identical?                                                                                                                                                                                                                                        |
| ------------------ | --------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| URL parser         | `_parse_url()`        | `extract_reddit_path()`      | Yes — same `urlparse` + `"reddit.com" not in parsed.netloc` check                                                                                                                                                                                 |
| Thread fetcher     | `_fetch_thread()`     | `fetch_thread_data()`        | Yes — same mock check, same path extraction, same error handling                                                                                                                                                                                  |
| Thread parser      | `_parse_thread()`     | `parse_thread_data()`        | Yes — same `{"submission": None, "comments": []}` structure, same `data.children[0].data` traversal, same `kind != "t1"` filter, same fields extracted (`score`, `num_comments`, `upvote_ratio`, `created_utc`, `permalink`, `title`, `selftext`) |
| Top comments       | `_top_comments()`     | `get_top_comments()`         | Yes — same `[deleted]`/`[removed]` exclusion set, same score sort                                                                                                                                                                                 |
| Insight extraction | `_extract_insights()` | `extract_comment_insights()` | Yes — same skip patterns (`yep`, `nope`, `same`, `agreed`, `lol`/`lmao`), same min-length check, same sentence-boundary truncation logic (scan for `.!?` after position 50/65)                                                                    |

The enrichment function `enrich()` / `enrich_reddit_item()` follows the exact same flow:

1. Fetch thread data
2. Parse submission + comments
3. Set `item["engagement"]` = `{"score": ..., "num_comments": ..., "upvote_ratio": ...}`
4. Set `item["date"]` from `created_utc`
5. Build `item["top_comments"]` list with `{"score", "date", "author", "excerpt", "url"}` dicts
6. Set `item["comment_insights"]`

Minor differences are only in truncation limits (BriefBot: `selftext[:600]`, `body[:350]`, `excerpt[:250]`; Last30Days: `selftext[:500]`, `body[:300]`, `excerpt[:200]`).

---

### 4. The HTTP Client Is Structurally Identical With Same Error Handling Chain

Comparing `briefbot_engine/net.py` vs `lib/http.py`:

Both are stdlib-only (`urllib.request`, no `requests`). Both define:

- A custom `HTTPError` class with `status_code` and `body` attributes — **same constructor signature**
- A `request()` function with same parameter names: `method, url, headers, json_body/json_data, timeout, retries`
- Same `headers.setdefault("User-Agent", ...)` and `headers.setdefault("Content-Type", "application/json")` pattern
- Same debug logging: `f"{method} {url}"` and `f"Payload keys: {list(json_body.keys())}"`
- Same response logging: `f"Response: {resp.status} ({len(body)} bytes)"`
- Same error handling chain (in same order): `urllib.error.HTTPError` → read body → log `f"HTTP Error {e.code}: {e.reason}"` → log `f"Error body: {body[:500]}"` → create `HTTPError(f"HTTP {e.code}: {e.reason}", e.code, body)` → check `400 <= e.code < 500 and e.code != 429` → `urllib.error.URLError` → `json.JSONDecodeError` → `OSError/TimeoutError/ConnectionResetError`
- Same convenience wrappers: `get()`, `post()`
- Same `reddit_json()` / `get_reddit_json()` function with identical URL construction: strip trailing `/`, append `.json`, add `?raw_json=1`

The debug format strings are **character-for-character identical** in multiple places.

---

### 5. The `_is_access_err()` / `_is_model_access_error()` Functions Are Identical

**BriefBot** (`reddit.py:26-39`):

```python
def _is_access_err(err: net.HTTPError) -> bool:
    if err.status_code != 400 or not err.body:
        return False
    lowered = err.body.lower()
    indicators = ["verified", "organization must be", "does not have access", "not available", "not found"]
    return any(term in lowered for term in indicators)
```

**Last30Days** (`openai_reddit.py:26-40`):

```python
def _is_model_access_error(error: http.HTTPError) -> bool:
    if error.status_code not in (400, 403):
        return False
    if not error.body:
        return False
    body_lower = error.body.lower()
    return any(phrase in body_lower for phrase in [
        "verified", "organization must be", "does not have access", "not available", "not found",
    ])
```

The 5 indicator strings are **identical and in the same order**. The only difference is Last30Days also checks for status 403.

---

### 6. The SKILL.md Intent-Parsing Framework Is Heavily Derived

Both SKILL.md files contain:

- Same variable scheme: `TOPIC`, `TARGET_TOOL`, `QUERY_TYPE`
- Same query types: PROMPTING, RECOMMENDATIONS, NEWS, GENERAL (BriefBot adds KNOWLEDGE)
- Same pattern examples, nearly verbatim:
  - `"[topic] for [tool]"` → both use this exact pattern
  - `"[topic] prompts for [tool]"` → both use this exact pattern
  - `"Just [topic]"` → both note tool is not specified
  - `"best [topic]"` or `"top [topic]"` → RECOMMENDATIONS
  - `"what are the best [topic]"` → RECOMMENDATIONS
- Same instruction: `"IMPORTANT: Do NOT ask about target tool before research."`
- Same display template format showing TOPIC, TARGET_TOOL, QUERY_TYPE before running tools
- BriefBot's intro: `"I'll investigate {TOPIC} across Reddit, X, and the web..."` vs Last30Days: `"I'll research {TOPIC} across Reddit, X, and the web..."` — only the verb changes

---

### 7. The Comment/ThreadComment Dataclass Is Byte-for-Byte Identical

**BriefBot** (`content.py:46-63`, named `ThreadComment`):

```python
@dataclass
class ThreadComment:
    score: int
    date: Optional[str]
    author: str
    excerpt: str
    url: str
    def to_dict(self):
        return {"score": self.score, "date": self.date, "author": self.author,
                "excerpt": self.excerpt, "url": self.url}
```

**Last30Days** (`schema.py:46-62`, named `Comment`):

```python
@dataclass
class Comment:
    score: int
    date: Optional[str]
    author: str
    excerpt: str
    url: str
    def to_dict(self):
        return {'score': self.score, 'date': self.date, 'author': self.author,
                'excerpt': self.excerpt, 'url': self.url}
```

Same 5 fields, same types, same order, same `to_dict()` body. Only the class name and quote style differ.

---

### 8. The ScoreBreakdown/SubScores Dataclass Is Byte-for-Byte Identical

**BriefBot** (`content.py:66-79`, named `ScoreBreakdown`):

```python
@dataclass
class ScoreBreakdown:
    relevance: int = 0
    recency: int = 0
    engagement: int = 0
    def to_dict(self):
        return {"relevance": self.relevance, "recency": self.recency, "engagement": self.engagement}
```

**Last30Days** (`schema.py:65-77`, named `SubScores`):

```python
@dataclass
class SubScores:
    relevance: int = 0
    recency: int = 0
    engagement: int = 0
    def to_dict(self):
        return {'relevance': self.relevance, 'recency': self.recency, 'engagement': self.engagement}
```

Identical in every way except the class name.

---

### 9. The Model Access Error Detection Uses the Same 5 Indicator Strings

In both the Reddit and X provider files, both projects check for model access errors using the exact same 5 strings:
`"verified"`, `"organization must be"`, `"does not have access"`, `"not available"`, `"not found"`

These strings appear nowhere in OpenAI's public documentation as a recommended set. This is an ad-hoc list someone built by encountering errors — finding the same 5 strings in the same order is strong evidence of copying.

---

### 10. The `TODO.md` Contains "Remove all traces"

BriefBot's `TODO.md` line 21 reads: **`- Remove all traces`**

This is an explicit admission in the project's own backlog that there are "traces" to be removed — consistent with a fork that hasn't been fully sanitized.

---

## MEDIOCRE INDICATORS

These findings show systematic patterns consistent with a fork-and-rename workflow, but individually might be explainable by shared conventions or the same developer writing both.

---

### 11. Scoring Formulas Use Same Structure With Tweaked Coefficients

Both projects compute engagement scores using `log1p`-weighted formulas:

**Reddit engagement**:
| Weight | Last30Days | BriefBot |
|--------|-----------|----------|
| score/upvotes | 0.55 | 0.48 |
| comments | 0.40 | 0.37 |
| ratio multiplier | ×10 | ×12 |
| ratio weight | 0.05 | 0.15 |

**X engagement**:
| Weight | Last30Days | BriefBot |
|--------|-----------|----------|
| likes | 0.55 | 0.45 |
| reposts | 0.25 | 0.28 |
| replies | 0.15 | 0.17 |
| quotes | 0.05 | 0.10 |

Both use `log1p()` for all metrics. Both have the same null guards (`if engagement is None: return None`, `if likes is None and reposts is None: return None`). The formulas are identical in structure with only coefficient values adjusted.

---

### 12. Scoring Weights Are Systematically Tweaked by Small Amounts

| Weight                | Last30Days | BriefBot | Delta |
| --------------------- | ---------- | -------- | ----- |
| Relevance (platform)  | 0.45       | 0.38     | -0.07 |
| Recency (platform)    | 0.25       | 0.34     | +0.09 |
| Engagement (platform) | 0.30       | 0.28     | -0.02 |
| Web relevance         | 0.55       | 0.58     | +0.03 |
| Web recency           | 0.45       | 0.42     | -0.03 |
| Unknown eng. penalty  | 3          | 8        | +5    |
| Low date penalty      | 5          | 7        | +2    |
| Med date penalty      | 2          | 3        | +1    |
| Web source penalty    | 15         | 9        | -6    |
| Baseline engagement   | 35         | 45       | +10   |

Every single weight has been adjusted by a small amount. If the projects were truly independent, you'd expect at least some weights to be identical by coincidence, or entirely different formulas. The pattern of uniform small deltas across all coefficients is consistent with deliberate differentiation of a copy.

---

### 13. The `sort_items()` / `_sort_by_score()` Functions Use Identical Sort Keys

Both use a multi-key sort:

1. Primary: `-item.score` (descending)
2. Secondary: `-int(date.replace("-", ""))` (descending, with `"0000-00-00"` fallback for None)
3. Tertiary: source priority (Reddit=0, X=1, YouTube=2, Web=3/4)
4. Quaternary: title/headline text for stability

The date sort trick — converting `"2026-02-20"` to `-20260220` for numeric descending sort — is unusual and identical in both.

---

### 14. The `Engagement` / `Signals` Dataclass Uses Same Fields in Same Order

Last30Days `Engagement` has: `score, num_comments, upvote_ratio, likes, reposts, replies, quotes, views`
BriefBot `Signals` has: `composite, upvotes, comments, vote_ratio, likes, reposts, replies, quotes, views, reactions, bookmarks`

The shared fields are in the same conceptual order (Reddit fields first, then X fields, then YouTube). BriefBot renames `score`→`upvotes`, `num_comments`→`comments`, `upvote_ratio`→`vote_ratio`, and adds `composite`, `reactions`, `bookmarks`. Both use `Optional[int]` for all count fields and `Optional[float]` for ratio.

Both `to_dict()` methods iterate fields and only include non-None values, returning `None` if empty — the same pattern of `d = {}; for field: if val is not None: d[key] = val; return d if d else None`.

---

### 15. Config/Env Management Follows Exact Same Architecture

| Aspect                | Last30Days                                 | BriefBot                                   |
| --------------------- | ------------------------------------------ | ------------------------------------------ |
| Config dir            | `~/.config/last30days/`                    | `~/.config/briefbot/`                      |
| Config file           | `.env` inside config dir                   | `.env` inside config dir                   |
| Parse function        | `load_env_file()`                          | `parse_dotenv()`                           |
| Config builder        | `get_config()`                             | `load_config()`                            |
| Debug env var         | `LAST30DAYS_DEBUG`                         | `BRIEFBOT_DEBUG`                           |
| Platform detection    | `get_available_sources()`                  | `determine_available_platforms()`          |
| Missing key detection | `get_missing_keys()`                       | `identify_missing_credentials()`           |
| Source validation     | `validate_sources()`                       | `validate_sources()`                       |
| User-Agent            | `"last30days-skill/2.1 (Assistant Skill)"` | `"briefbot-skill/1.0 (Claude Code Skill)"` |

Both `.env` parsers use the same logic: strip whitespace, skip `#` comments, partition on `=`, strip quotes with `value[0] in ('"', "'") and value[-1] == value[0]`.

Both `validate_sources()` functions handle the same set of cases (`auto`, `web`, `both`, `reddit`, `x`) with the same logic flow and same error messages (e.g., "Requested both sources but {missing} key is missing").

---

### 16. The `log1p_safe()` / `_safe_log1p()` Functions Are Identical

**Last30Days** (`score.py:27-31`):

```python
def log1p_safe(x):
    if x is None or x < 0:
        return 0.0
    return math.log1p(x)
```

**BriefBot** (`content.py:362-366`):

```python
def _safe_log1p(val):
    if val is None or val < 0:
        return 0.0
    return math.log1p(val)
```

Same logic, same guard, same return value, renamed.

---

### 17. The OpenAI API Call Structure Is Identical

Both Reddit search functions construct the same payload:

```python
payload = {
    "model": current_model,
    "tools": [{"type": "web_search", "filters": {"allowed_domains": ["reddit.com"]}}],
    "include": ["web_search_call.action.sources"],
    "input": prompt_text,
}
```

Both use a model fallback chain: `[selected_model] + [m for m in FALLBACK_ORDER if m != selected_model]`. Both iterate through models, catch `HTTPError`, check `_is_access_err()`, log `f"Model {current_model} not accessible, trying fallback..."`, and raise the last error if all fail.

---

### 18. The Search Prompt Templates Share Structural DNA

Both Reddit prompts instruct the model to:

1. Distill the core subject from the query (with the same examples: "killer features of clawdbot" → "clawdbot")
2. Search with `site:reddit.com`
3. Return JSON with `{"items": [{"title", "url", "subreddit", "date", "why_relevant", "relevance"}]}`
4. Require URLs to contain `/r/` and `/comments/`
5. Reject `developers.reddit.com` and `business.reddit.com`
6. Use `{min_items}` to `{max_items}` range from depth config

Both X prompts return JSON with `{"items": [{"text", "url", "author_handle", "date", "engagement": {"likes", "reposts", "replies", "quotes"}, "why_relevant", "relevance"}]}`.

The field names in the JSON schemas are **identical** across both projects.

---

## LIGHT INDICATORS

These are suggestive but individually could be coincidental or represent common patterns. They become significant only in the context of the strong and mediocre indicators above.

---

### 19. BriefBot's Architecture Refactoring Adds a Unified Content Model

BriefBot consolidates Last30Days' separate `RedditItem`, `XItem`, `WebSearchItem`, `YouTubeItem` classes into a single `ContentItem` class with a `Source` enum. This is a genuine architectural improvement, but it's built **on top of** all the same fields and semantics. The factory functions (`from_reddit_raw`, `from_x_raw`, etc.) map the exact same raw dict keys that Last30Days uses.

---

### 20. BriefBot Replaces Jaccard Deduplication With SimHash

Last30Days uses character n-gram Jaccard similarity. BriefBot uses 64-bit SimHash with FNV-1a hashing and Hamming distance. This is a genuinely different algorithm — but both follow the same outer pattern: compute fingerprint for each item → pairwise comparison → keep higher-scored item from each duplicate pair → return filtered list.

---

### 21. BriefBot Replaces Linear Scoring With Percentile-Harmonic

Last30Days uses `total = W*relevance + W*recency + W*engagement` (linear weighted sum with min-max normalization).
BriefBot uses percentile ranks combined via weighted harmonic mean (penalizes items weak in any dimension).

This is a genuine algorithmic difference — but the surrounding scaffolding is identical: same 3-dimension breakdown (relevance/recency/engagement), same web-specific 2-dimension formula, same post-score confidence penalties, same `max(0, min(100, round(total)))` clamping.

---

### 22. BriefBot Adds LinkedIn, Delivery, and Scheduling Features

These are genuinely new:

- LinkedIn as a source (new provider, new engagement formula, new dataclass fields)
- Email delivery via SMTP with HTML newsletters
- Telegram bot integration
- Audio generation (ElevenLabs / edge-tts)
- PDF generation
- Cron-based scheduling with OS integration
- Configuration wizard

These features have no counterpart in Last30Days and represent real additional development.

---

### 23. The Recency Scoring Decay Curve Differs Slightly

- **Last30Days**: `int(100 * (1 - age / max_days))` — linear decay
- **BriefBot**: `int(100 * ((max_days - age) / max_days) ** 0.95)` — slightly sub-linear decay (exponent 0.95)

Same function signature, same edge cases (None→0, negative→100, ≥max_days→0), same 0-100 range. The `** 0.95` exponent is a minor tweak to the same formula.

---

### 24. Both Use the Same `depth` System With Similar Size Ranges

**Reddit depth configs:**
| Depth | Last30Days | BriefBot |
|-------|-----------|----------|
| quick | (15, 25) | (12, 20) |
| default | (30, 50) | (25, 45) |
| deep | (70, 100) | (55, 85) |

**X depth configs:**
| Depth | Last30Days | BriefBot |
|-------|-----------|----------|
| quick | (8, 12) | (10, 15) |
| default | (20, 30) | (18, 28) |
| deep | (40, 60) | (35, 55) |

Same 3-tier system, same variable names (`"quick"`, `"default"`, `"deep"`), numbers adjusted.

---

### 25. The Date Handling Shares the Same Parsing Approach

Both `temporal.py` / `dates.py`:

- Try `float()` for Unix timestamps first
- Then try a list of `strftime` format strings (same formats in slightly different order)
- Same `timestamp_to_date()` / `to_date_str()` function: `datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()`
- Same `trust_level()` / `get_date_confidence()`: parse date, parse range bounds, check `start <= parsed <= end`
- Same `elapsed_days()` / `days_ago()`: parse date, compute `(today - parsed).days`

---

### 26. The `window()` / `get_date_range()` Function Is Identical

**BriefBot** (`temporal.py:37-41`):

```python
def window(days=30):
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days)
    return start.isoformat(), today.isoformat()
```

**Last30Days** (`dates.py:7-15`):

```python
def get_date_range(days=30):
    today = datetime.now(timezone.utc).date()
    from_date = today - timedelta(days=days)
    return from_date.isoformat(), today.isoformat()
```

Same logic, different variable name (`start` vs `from_date`).

---

## Summary

| Category                | Count | Description                                                                            |
| ----------------------- | ----- | -------------------------------------------------------------------------------------- |
| **Strong indicators**   | 10    | Identical code blocks, shared bugs, same ad-hoc string lists, "Remove all traces" TODO |
| **Mediocre indicators** | 8     | Systematically tweaked coefficients, identical architecture, same config patterns      |
| **Light indicators**    | 8     | Different algorithms atop same scaffolding, new features added, minor formula tweaks   |

### Overall Assessment

The evidence strongly indicates that **BriefBot was built by forking Last30Days and applying three layers of modification**:

1. **Systematic renaming**: Every function, class, variable, config path, and error string has been renamed following a consistent pattern (shorter names, different verbs, underscore-prefixed private functions). This is visible across the entire codebase without exception.

2. **Coefficient tuning**: Every numerical constant — scoring weights, engagement coefficients, depth sizes, penalties, bonuses, thresholds — has been adjusted by a small amount. No single weight is left unchanged from the original.

3. **Feature additions**: LinkedIn support, delivery mechanisms (email/Telegram/audio/PDF), scheduled jobs, a configuration wizard, and a KNOWLEDGE query type were added on top of the derived base.

The core research pipeline — API integration (OpenAI Responses + xAI), response parsing, Reddit enrichment, engagement scoring, date handling, deduplication, HTTP client, configuration management, and the SKILL.md agent framework — is functionally identical between the two projects. The `TODO.md` entry "Remove all traces" is consistent with an incomplete effort to disguise the derivation.
