# Comparative Analysis: BriefBot vs. Last30Days

**Date:** 2026-02-21
**Scope:** Current repository states only (no git history)
**Method:** File-by-file structural, algorithmic, and textual comparison of all source files

---

## TL;DR

BriefBot's research engine is a systematic rename-and-restructure of Last30Days. Every core library module maps 1:1 to a renamed counterpart. Algorithms, control flow, error handling strings, test inputs, fixture structures, CLI flags, and even the README demo scenario are recognizably the same codebase with variable names swapped. BriefBot adds ~4,000+ lines of genuinely original code (scheduling, delivery, Telegram bot, audio/PDF generation), but the research pipeline foundation is derived from Last30Days.

---

## STRONG INDICATORS

These findings alone would likely be sufficient to establish derivation.

### S1. Perfect 1:1 Module Mapping

Every Last30Days library module has a direct renamed counterpart in BriefBot:

| Last30Days (`scripts/lib/`)  | BriefBot (`scripts/briefbot_engine/`) |
| ---------------------------- | ------------------------------------- |
| `env.py`                     | `config.py`                           |
| `dates.py`                   | `temporal.py`                         |
| `http.py`                    | `net.py`                              |
| `models.py`                  | `providers/registry.py`               |
| `openai_reddit.py`           | `providers/reddit.py`                 |
| `xai_x.py`                   | `providers/twitter.py`                |
| `reddit_enrich.py`           | `providers/enrich.py`                 |
| `normalize.py` + `schema.py` | `content.py`                          |
| `score.py` + `dedupe.py`     | `ranking.py`                          |
| `render.py`                  | `output.py`                           |
| `ui.py`                      | `terminal.py`                         |
| `cache.py`                   | (cache in `providers/registry.py`)    |

No module is missing from this mapping. The only additions are `linkedin.py`, `web.py`, `claude_web.py`, `intent.py`, `paths.py`, and the delivery/scheduling subsystems.

### S2. Verbatim or Near-Verbatim Code Blocks

**Error message (character-for-character identical in both Python scripts):**

```python
# last30days/scripts/last30days.py AND briefbot/scripts/briefbot.py:
print("Error: Cannot use both --quick and --deep", file=sys.stderr)
sys.exit(1)
```

**Error formatting pattern (identical template in both):**

```python
# last30days:
raw_openai = {"error": str(e)}
reddit_error = f"API error: {e}"
reddit_error = f"{type(e).__name__}: {e}"

# briefbot:
response = {"error": str(network_err)}
error = f"API error: {network_err}"
error = f"{type(generic_err).__name__}: {generic_err}"
```

**Logging format strings (identical):**

```python
# last30days AND briefbot:
sys.stderr.write(f"[REDDIT ERROR] {msg}\n")
sys.stderr.write(f"[X ERROR] {msg}\n")
```

**xAI error debug dump (identical including the 1000-char truncation):**

```python
# both:
f"xAI API error: {message}"
f"Full error response: {json.dumps(response, indent=2)[:1000]}"
```

**Cached results message (identical down to the `--refresh` hint):**

```python
# last30days:
f"Using cached results{age_str} - use --refresh for fresh data"

# briefbot:
f"Using cached results{age_display} - use --refresh for fresh data"
```

### S3. Mock Model Loading with Identical Dict-Spread Pattern

```python
# last30days:
selected_models = models.get_models(
    {"OPENAI_API_KEY": "mock", "XAI_API_KEY": "mock", **config},
    mock_openai_models, mock_xai_models,
)

# briefbot:
models_picked = registry.get_models(
    {"OPENAI_API_KEY": "mock", "XAI_API_KEY": "mock", **cfg},
    mock_openai_models, mock_xai_models,
)
```

The dict-spread `{"OPENAI_API_KEY": "mock", "XAI_API_KEY": "mock", **config}` is a distinctive pattern unlikely to arise independently.

### S4. Identical Test Inputs and Expected Outputs

Test files use the **same mock data values**:

- API key: `"fake-key"` (both)
- Model IDs tested: `"gpt-5"`, `"gpt-5.2"`, `"gpt-5.2.1"`, `"gpt-5-mini"`, `"gpt-4"`, `"custom-model"` (both)
- Mock timestamps: `1704067200`, `1701388800`, `1698710400` (both)
- Error body for "unrelated 400" test: `"Invalid JSON in request body"` (both)
- Expected results: identical tuples `(5,)`, `(5, 2)`, `(5, 2, 1)` (both)
- Same test scenario structure: every last30days test has a corresponding briefbot test with renamed function name but same inputs/outputs

### S5. Identical CLI Flags with Same Names, Choices, Defaults, and Help Text

| Flag                 | Both                                                                 |
| -------------------- | -------------------------------------------------------------------- |
| `topic` (positional) | `nargs="?"`, help: `"Topic to research"`                             |
| `--mock`             | `action="store_true"`, help: `"Use fixtures"`                        |
| `--emit`             | choices include `"compact"`, `"json"`, `"md"`, `"context"`, `"path"` |
| `--sources`          | choices include `"auto"`, `"reddit"`, `"x"`, `"both"`                |
| `--quick`            | `action="store_true"`                                                |
| `--deep`             | `action="store_true"`                                                |
| `--debug`            | `action="store_true"`                                                |
| `--days`             | `type=int`, default `30`                                             |

### S6. Identical `run_research()` Function Structure

Both define a `run_research()` function with:

- Same parameter pattern: `(topic, sources, config, models, from_date, to_date, depth="default", mock=False, progress=...)`
- Same variable initialization:

```python
# both:
reddit_items = []
x_items = []
youtube_items = []
raw_openai = None
raw_xai = None
raw_reddit_enriched = []
reddit_error = None
x_error = None
youtube_error = None
```

- Same `ThreadPoolExecutor` submit-and-collect pattern
- Same progress callbacks: `progress.start_reddit()`, `progress.end_reddit(len(items))`, etc.

### S7. Cache Key Generation (Identical Algorithm)

```python
# last30days:
raw = f"{topic}|{from_date}|{to_date}|{mode}"
return hashlib.blake2s(raw.encode(), digest_size=8).hexdigest()

# briefbot:
raw = f"{topic}|{start}|{end}|{platform}"
digest = hashlib.blake2s(raw.encode("utf-8"), digest_size=16).hexdigest()
```

Same pipe-delimited format string, same `blake2s` hash function. Only digest size differs.

### S8. Model Fallback Chain (Identical List Comprehension Pattern)

```python
# last30days:
models_to_try = [model] + [m for m in MODEL_FALLBACK_ORDER if m != model]

# briefbot:
model_candidates = [model] + [candidate for candidate in FALLBACK_MODELS if candidate != model]
```

### S9. Identical Regex for GPT Mainline Check

```python
# both:
re.match(r"^gpt-5(\.\d+)*$", model_id.lower())
```

Same regex, same `.lower()` normalization, same excluded variant list (`"mini"`, `"nano"`, `"chat"`, etc.).

### S10. Reddit Enrichment -- Same Algorithm, Same Fields, Same Defaults

Both parse Reddit thread JSON with:

- Same `data[0]` for submission, `data[1]` for comments
- Same `.get("data", {}).get("children", [])` traversal
- Same `kind == "t1"` check for comments
- Same `"[deleted]"` default for author
- Same skip-pattern words: `"this"`, `"same"`, `"agreed"`, `"exactly"`, `"yep"`, `"nope"`, `"lol"`, `"lmao"`, `"haha"`, `"[deleted]"`, `"[removed]"`
- Same `get_top_comments(limit=10)` sorting by score descending, filtering `{"[deleted]", "[removed]"}`

### S11. Compact Rendering -- Same Section Order and Markdown Format

Both `render_compact()` / `compact()` produce markdown with identical section ordering:

1. Header with topic
2. Sparse data warning
3. Cache indicator
4. Date range and mode metadata
5. Missing key tips
6. Reddit Threads (with engagement, date, confidence, insights `[:3]`)
7. X Posts (with engagement, date, confidence)
8. YouTube Videos
9. Web Results

The per-item format is structurally identical:

```
# last30days:
**{item.id}** (score:{item.score}) r/{item.subreddit}{date_str}{conf_str}{eng_str}
  {item.title}
  {item.url}
  *{item.why_relevant}*
  Insights:
    - {insight}

# briefbot:
**{item.uid}** [{item.score}] r/{subreddit}{date_str}{conf}{eng}
  {item.title}
  {item.link}
  *{item.reason}*
  Insights:
    - {insight}
```

### S12. Terminal UI -- Same Method-for-Method Progress Class

Both `ProgressDisplay`/`Progress` classes have identical method signatures:

`start_reddit()`, `end_reddit(count)`, `start_reddit_enrich(current, total)`, `update_reddit_enrich(current, total)`, `end_reddit_enrich()`, `start_x()`, `end_x(count)`, `start_processing()`, `end_processing()`, `show_complete(reddit, x, youtube)`, `show_cached(age)`, `show_error(message)`, `start_web_only()`, `end_web_only()`, `show_web_only_complete()`, `show_promo(missing)`

Same phase-to-color mapping: `"reddit"` -> yellow/amber, `"x"` -> cyan/azure, `"process"` -> purple/magenta, `"done"` -> green/lime, `"error"` -> red/crimson.

### S13. Fixture Files -- Same Model IDs and Timestamps

- Both `models_openai_sample.json` / `api_openai_models.json`: Same `{"object": "list", "data": [...]}` structure with same model IDs: `gpt-5.2`, `gpt-5.1`, `gpt-5`, `gpt-5-mini`, `gpt-4o`, `gpt-4-turbo`
- Both `models_xai_sample.json` / `api_xai_models.json`: Same model IDs: `grok-4-latest`, `grok-4`, `grok-3`
- Reddit thread fixtures: Both have array of two Listing objects with 8 comments each

---

## MEDIOCRE INDICATORS

Significant but could theoretically arise from similar requirements.

### M1. Systematic Field Renaming Table

A consistent rename mapping applied across ALL modules simultaneously:

| Last30Days              | BriefBot             |
| ----------------------- | -------------------- |
| `id`                    | `uid`                |
| `url`                   | `link`               |
| `date`                  | `posted`             |
| `relevance`             | `signal`             |
| `why_relevant`          | `reason`             |
| `subreddit`             | `community`          |
| `engagement`            | `metrics`            |
| `score` (upvotes)       | `upvotes`            |
| `num_comments`          | `comments`           |
| `upvote_ratio`          | `vote_ratio`         |
| `top_comments`          | `comment_cards`      |
| `comment_insights`      | `comment_highlights` |
| `text` (X posts)        | `excerpt`            |
| `author_handle`         | `handle`             |
| `source_domain`         | `domain`             |
| `from_date` / `to_date` | `start` / `end`      |
| `config`                | `cfg`                |
| `selected_models`       | `models_picked`      |

The uniformity of this mapping across every module suggests mechanical transformation.

### M2. SKILL.md Intent Classification (Same Four Request Types with Same Trigger Phrases)

```
# last30days:
- PROMPTING - "X prompts", "prompting for X"
- RECOMMENDATIONS - "best X", "top X", "what X should I use"
- NEWS - "what's happening with X", "X news"
- GENERAL - anything else

# briefbot:
- PROMPTING - "X prompts", "prompting for X", "X best practices"
- RANKED_CHOICES - "best X", "top X", "what X should I use", "recommended X"
- NEWS - "what's happening with X", "X news", "latest on X"
- GENERAL - community research requests not covered above
```

### M3. SKILL.md Three Critical WebSearch Rules (Same Order, Same Rationale)

1. **Use user's exact wording** -- L30D: "USE THE USER'S EXACT TERMINOLOGY" / BB: "PRESERVE THE USER'S EXACT WORDING"
2. **Exclude reddit/x/twitter** -- L30D: "EXCLUDE reddit.com, x.com, twitter.com (covered by script)" / BB: "SKIP reddit.com, x.com, twitter.com (the script already covers those)"
3. **No sources list** -- L30D: "DO NOT output 'Sources:' list" / BB: "SUPPRESS any 'Sources:' list in output"

### M4. SKILL.md Prompt-Writing Checklist (Same Five Items, Same Order)

1. Format matches what research recommends
2. Directly addresses what the user said they want
3. Uses terminology/patterns from actual research
4. Paste-ready with clearly marked `[PLACEHOLDER]` slots
5. Appropriate length/style for the target tool

Both use the same output template:

```
Here's your prompt for {TARGET_TOOL / USAGE_TARGET}:
---
[THE PROMPT]
---
{explanation of research insight applied}
```

### M5. HTTP Client -- Same stdlib-only Architecture

Both implement a custom HTTP client using `urllib.request` with:

- Custom error class `HTTPError(message, status_code, body)` with same fields
- Same retry loop (catch `urllib.error.HTTPError`, `URLError`, `OSError/TimeoutError`)
- Same "don't retry client errors except rate limits" logic
- Same convenience `get()` and `post()` wrappers
- Same `reddit_json()` function: ensure leading `/`, strip trailing `/`, append `.json`, construct `https://www.reddit.com{path}?raw_json=1`

### M6. Scoring System -- Same Weighted Formula Architecture

Both use multi-factor scoring:

1. Compute raw engagement composites per platform (Reddit: upvotes + comments + ratio; X: likes + reposts + replies + quotes)
2. Normalize to 0-100 percentile
3. Combine via weighted average of relevance + recency + engagement
4. Apply penalty for missing engagement data
5. Apply penalty for low date confidence
6. Clamp to `max(0, min(100, ...))`

### M7. Config System -- Same env-over-file Pattern

Both load config from `~/.config/{skillname}/.env` with:

- Same dotenv parsing (comments, quotes, key=value)
- Environment variables taking precedence
- Same key names: `OPENAI_API_KEY`, `XAI_API_KEY`, `OPENAI_MODEL_POLICY`, `XAI_MODEL_POLICY`
- Same source availability detection: check `has_openai` and `has_xai`, return `'both'`, `'reddit'`, `'x'`, or `'web'`

### M8. Same `validate_sources()` Branching Logic

Both handle: `auto` -> available, `web` -> always succeed, `both` -> check both keys, source-specific -> check matching key. Same mode strings.

### M9. Same Excluded Domains Set

```python
# last30days:
{"reddit.com", "www.reddit.com", "old.reddit.com", "twitter.com", "www.twitter.com", "x.com", "www.x.com"}

# briefbot (superset):
{"reddit.com", "www.reddit.com", "old.reddit.com", "m.reddit.com", "twitter.com", "www.twitter.com", "x.com", "www.x.com", "nitter.net"}
```

### M10. README Demo Scenario -- Same Flow with Substitutions

Both READMEs demonstrate:

1. Research a Google image generation model's prompting techniques
2. Then ask to "make a mockup of an app for moms who [activity]"

L30D: "Nano Banana Pro prompting" then "moms who swim"
BB: "Aurora Canvas prompting" then "moms who cook"

---

## LIGHT INDICATORS

Individually weak, but part of the overall pattern.

### L1. Same `--emit=compact` Flag Name

Unusual flag name for output format selection, shared by both.

### L2. Same Date Utility Function Set

Both implement the exact same set: `get_date_range(30)`, `parse_date()`, `timestamp_to_date()`, `get_date_confidence()`, `days_ago()`, `recency_score(max_days=30)`.

### L3. Same "Store These Variables" Pattern in SKILL.md

Both instruct the agent to store topic, target tool, patterns, and findings with `"unknown"` default.

### L4. Same Grounding Instructions

Both: "ground synthesis in ACTUAL research content, not pre-existing knowledge."

### L5. Same Context Memory Rules

Both: "Do not launch fresh web searches unless the topic changes."

### L6. Same Depth Tier Names

Both use `"quick"`, `"default"`, `"deep"` with min/max result counts.

### L7. Same ANSI Color Class Pattern

Purple/magenta, blue/azure, cyan/teal, green/lime, yellow/amber, red/crimson, bold/emphasized, dim/subdued, reset/normal.

### L8. Same `to_dict()` / `from_dict()` Sparse Serialization Pattern

Both dataclasses use "only include non-None fields" in `to_dict()` and backward-compatible deserialization in `from_dict()`.

### L9. Same Windows UTF-8 Fix

Both detect `sys.platform == "win32"` and call `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.

### L10. No Attribution

Zero mention of Last30Days in any BriefBot documentation, README, TODO, or SCIENCE_BEHIND_BOT.md.

- Verbatim strings (`"Error: Cannot use both --quick and --deep"`), identical format patterns (`f"{type(e).__name__}: {e}"`), identical test data values (`1704067200`, `"fake-key"`)

- the 1:1 module mapping
  - Identical error format strings
  - Identical test data values (timestamps like `1704067200`, mock keys like `"fake-key"`)
  - Identical CLI flag names and help text
  - A perfect 1:1 module mapping with systematic field renaming
  - The same demo scenario (image model prompting -> app mockup for moms)

2. **"Agentic coding" does not launder copyright**: If an AI coding tool was used to rewrite the code, the question is what the AI was given as input. If the AI was instructed to "rewrite this codebase with different variable names" or was given Last30Days code as context, the output is still a derivative work. Copyright law focuses on the _result_, not the _tool_ used to create it. Using a power tool to replicate a sculpture does not make the copy non-infringing.

3. **The systematic renaming is itself evidence**: A developer who was "merely inspired" would not produce a codebase where every field, module, and function has a 1:1 renamed counterpart. The consistency of the renaming table (always `url`->`link`, always `date`->`posted`, always `relevance`->`signal`) suggests mechanical transformation, not independent creative expression.

4. **Merger doctrine does not apply**: While there may be limited ways to call the OpenAI API or parse Reddit JSON, the _specific combination_ of algorithms, the _specific_ prompt-writing checklist, the _specific_ error messages, and the _specific_ scoring formula weights are creative choices with many alternatives. The merger doctrine (which excuses copying when there is only one way to express an idea) does not protect wholesale reproduction of a creative system's particular expression.

5. **However, the original additions help somewhat**: BriefBot's ~4,000 lines of genuinely original code (scheduling, delivery, Telegram bot) show that the author added substantial value. This could mitigate damages but does not negate the infringement of the derived portions. A court might view BriefBot as a partially infringing work where the derived research engine is infringing but the original delivery/scheduling layer is not.

**Bottom line**: The "inspiration only" defense is undermined by the volume and specificity of the textual evidence. Ideas are not copyrightable, but the particular _expression_ of those ideas is -- and the evidence shows expression-level copying, not mere idea-level inspiration.
