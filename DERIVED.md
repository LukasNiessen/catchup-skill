# Derivation Analysis: SKILL.md (BriefBot) vs SKILL_BAD.md (last30days)

## Verdict: SKILL.md is almost certainly derived from SKILL_BAD.md

Confidence: **Very High (95%+)**

SKILL_BAD.md is `last30days v2.1` by mvanhorn ([github.com/mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill)). SKILL.md is `briefbot v1.0`. The structural, logical, and textual overlap is far too extensive to be coincidental.

---

## Evidence

### 1. Identical Document Flow

Both files follow the exact same sequence:

1. Parse user intent (classify topic + tool + query type)
2. Display parsing to user
3. Run a Python research script in foreground
4. Run WebSearch after script completes
5. Synthesize sources (weight Reddit/X high, web low)
6. Present findings with stats
7. Wait for user response
8. Write a single tailored prompt if requested
9. Stay in "expert mode" for follow-ups
10. Show footer with stats

No two independently written research skills would arrive at this exact 10-step pipeline in this exact order.

### 2. Verbatim / Near-Verbatim Passages

| Section | last30days (SKILL_BAD.md) | briefbot (SKILL.md) |
|---------|--------------------------|---------------------|
| Anti-pattern warning | "If user asks about 'clawdbot skills' and research returns ClawdBot content (self-hosted AI agent), do NOT synthesize this as 'Claude Code skills'" | "If the research was about ClawdBot (a self-hosted AI agent), your summary should be about ClawdBot, not Claude Code" |
| Format matching | "ANTI-PATTERN: Research says 'use JSON prompts with device specs' but you write plain prose. This defeats the entire purpose of the research." | Identical, word-for-word |
| RECOMMENDATIONS bad example pattern | "Skills are powerful. Keep them under 500 lines." as BAD vs specific mention counts as GOOD | Same structure: vague advice as BAD vs "mentioned Nx" as GOOD |
| Expert mode | "After research is complete, you are now an EXPERT" / "DO NOT run new WebSearches" | "Once the research phase is done, you operate as a subject-matter expert" / "SKIP additional WebSearches" |
| Prompt quality checklist | FORMAT MATCHES RESEARCH, addresses user goal, uses research patterns, paste-ready | Same 5 items, same order, nearly same wording |

### 3. Renamed but Identical Variables

| last30days | briefbot | Purpose |
|------------|----------|---------|
| `TOPIC` | `FOCUS_AREA` | The research subject |
| `TARGET_TOOL` | `USAGE_TARGET` | Where output will be used |
| `QUERY_TYPE` | `REQUEST_STYLE` | Classification of request |
| `RECOMMENDATIONS / NEWS / PROMPTING / GENERAL` | `RECOMMENDATIONS / NEWS / PROMPTING / GENERAL` | Same 4 categories (briefbot adds KNOWLEDGE) |

### 4. Same Intent Heuristics

Both use nearly identical pattern-matching rules:
- `[topic] for [tool]` → tool is specified
- `[topic] prompts for [tool]` → tool is specified
- Just `[topic]` → tool unknown, that's OK
- `"best [topic]"` or `"top [topic]"` → RECOMMENDATIONS

BriefBot adds a few more patterns but the base set is copy-pasted.

### 5. Same WebSearch Query Templates

Both organize queries by the same 4 categories with the same structure:
- RECOMMENDATIONS: `best {topic} recommendations`, `{topic} list examples`
- NEWS: `{topic} news 2026`, `{topic} announcement update`
- PROMPTING: `{topic} prompts examples 2026`, `{topic} techniques tips`
- GENERAL: `{topic} 2026`, `{topic} discussion`

### 6. Same Synthesis Weighting Rules

Both specify (in the same order):
1. Weight Reddit/X HIGH
2. Weight WebSearch LOW
3. Cross-source patterns = strongest signal
4. Note contradictions
5. Extract top 3-5 actionable insights

---

## What BriefBot Added (Not in last30days)

These are the genuine additions that differentiate BriefBot:

1. **KNOWLEDGE / TURNED_OFF_SEARCH mode** — direct-answer path that skips research entirely
2. **Configuration wizard** — interactive setup via `setup.py` for API keys, SMTP, Telegram
3. **Delivery pipeline** — `--email`, `--audio`, `--telegram` flags with `deliver.py` script
4. **Scheduled jobs** — CRON-based recurring research with `--schedule`
5. **Telegram bot listener** — receives research requests via Telegram
6. **Branded greeting** — "BriefBot here!" with emojis and personality
7. **"What I learned" + "Key techniques" framework** — structured two-layer synthesis with detailed good/bad examples (the Nano Banana Pro example)
8. **"Try next:" suggestion line** — grey auto-suggestion for CLI
9. **`--days=N`, `--deep`, `--quick`** depth options (last30days also has these but briefbot expanded them)
10. **`##HEREBRO##`** — a leftover marker (line 413) that appears to be a merge/edit artifact, further suggesting manual editing of a source document

---

## What BriefBot Removed

1. **YouTube-specific parsing guidance** — last30days has detailed instructions for counting YouTube items from script output
2. **Citation formatting rules** — last30days has extensive rules about @handles vs publications, URL formatting ("NEVER paste raw URLs"), lead-with-people-not-publications philosophy
3. **Security & Permissions section** — last30days explicitly documents what the skill does/doesn't do
4. **Script path discovery** — last30days has a multi-path search for the skill root; briefbot hardcodes `~/.claude/skills/briefbot/`
5. **Clawdbot metadata block** — last30days has structured metadata for a registry system

---

## Conclusion

BriefBot (SKILL.md) was derived from last30days (SKILL_BAD.md) as its base template. The derivation involved:

1. **Renaming** core variables and the skill identity
2. **Adding** substantial new features (delivery, scheduling, Telegram, knowledge mode, setup wizard)
3. **Expanding** the synthesis guidance with more detailed examples and the two-layer framework
4. **Removing** some last30days-specific details (YouTube parsing, security section, citation philosophy)
5. **Restructuring** the output format (table-based stats, branded greeting, "Try next" suggestions)

The `##HEREBRO##` artifact on line 413 of SKILL.md is likely a leftover section marker from the editing process, further confirming manual derivation rather than independent creation.
