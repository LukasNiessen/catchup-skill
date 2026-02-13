# How Web Search Works in BriefBot

## Overview

BriefBot uses a **two-layer architecture** for research: Python handles API-based platform searches, and Claude Code handles web search. Neither layer does the other's job.

## The Two Layers

### Layer 1: Python Script (API Research)

The Python script (`briefbot.py`) calls external APIs directly:

- **Reddit, YouTube, LinkedIn** — via OpenAI's `web_search` tool (requires `OPENAI_API_KEY`)
- **X/Twitter** — via xAI's `x_search` tool (requires `XAI_API_KEY`)

These APIs return structured data with engagement metrics (upvotes, likes, views, etc.), which is why they're weighted higher in the final synthesis.

### Layer 2: Claude Code (Web Search)

Claude Code uses its built-in `WebSearch` tool to find supplementary web pages — blogs, tutorials, news articles, documentation, GitHub repos.

This layer has **no engagement metrics**, so results are weighted lower than API data.

## The Handoff: How Python Tells Claude to Search

The Python script doesn't call any web search API. Instead, it **prints instructions to stdout** that Claude Code reads and acts on.

At the end of its output, the script prints a block like:

```
### WEBSEARCH REQUIRED ###
Topic: [the user's topic]
Claude: Use your WebSearch tool to find 8-15 relevant web pages.
Exclude: reddit.com, x.com, twitter.com
After searching, synthesize WebSearch results WITH the Reddit/X
results above. WebSearch items should rank LOWER than comparable
Reddit/X items (no engagement signals).
```

Claude Code reads this printed text and follows the instructions — it runs WebSearch queries, collects results, and merges them with the API data.

## Why It Works This Way

Claude Code has access to the `WebSearch` tool as part of its runtime environment. Python scripts running in Bash don't have access to Claude's tools. So the architecture splits the work:

- Python does what Python can do (HTTP API calls)
- Claude does what Claude can do (WebSearch, synthesis, user interaction)

The printed instructions are the bridge between the two.

## Modes Based on API Keys

| API Keys Available | What Python Does | What Claude Does |
|---|---|---|
| Both (OpenAI + xAI) | Reddit + X + YouTube + LinkedIn | WebSearch (supplementary) |
| OpenAI only | Reddit + YouTube + LinkedIn | WebSearch (supplementary) |
| xAI only | X only | WebSearch (supplementary) |
| None | Nothing | WebSearch (primary — all research) |

In web-only mode (no API keys), Claude's WebSearch becomes the sole data source. The Python script still runs but returns empty results and signals that WebSearch is required.

## Key Limitation

This architecture **requires Claude Code to be running**. If the Python script is executed standalone (e.g., by a cron job or Task Scheduler), the WebSearch instructions are just printed text that nobody reads — there's no Claude Code to act on them.
