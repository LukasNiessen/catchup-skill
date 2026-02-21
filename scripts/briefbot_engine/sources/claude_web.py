#
# Claude Code CLI Integration: Invokes claude in non-interactive mode for WebSearch
# Used by scheduled jobs to supplement API research with web search results
#

import shutil
import subprocess
from typing import Optional


def find_claude_cli() -> Optional[str]:
    """Finds the claude CLI executable on PATH. Returns path or None."""
    return shutil.which("claude")


def web_search_via_claude(
    topic: str,
    start_date: str,
    end_date: str,
    existing_summary: str = "",
    timeout_seconds: int = 180,
) -> Optional[str]:
    """
    Invokes Claude Code CLI in print mode to perform WebSearch.

    Runs: claude -p --allowedTools WebSearch
    Passes a focused prompt via stdin asking Claude to search the web
    and return structured results.

    Args:
        topic: The research topic.
        start_date: Start of date range (YYYY-MM-DD).
        end_date: End of date range (YYYY-MM-DD).
        existing_summary: Brief summary of API results for context.
        timeout_seconds: Max wait time (default 180s).

    Returns:
        Formatted web search results, or None if unavailable.
    """
    claude_path = find_claude_cli()
    if not claude_path:
        return None

    prompt = _build_prompt(topic, start_date, end_date, existing_summary)

    try:
        result = subprocess.run(
            [claude_path, "-p", "--allowedTools", "WebSearch"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()
        return output if output else None

    except subprocess.TimeoutExpired:
        return None
    except (FileNotFoundError, OSError):
        return None


def _build_prompt(
    topic: str,
    start_date: str,
    end_date: str,
    existing_summary: str,
) -> str:
    """Builds a focused WebSearch prompt for Claude."""
    lines = [
        "You are a research assistant. Your ONLY job is to use WebSearch",
        "to find relevant web pages about a topic, then return structured results.",
        "",
        "Topic: {}".format(topic),
        "Date range: {} to {}".format(start_date, end_date),
        "",
        "Instructions:",
        "1. Run a light WebSearch (3-5 results) to discover key terms and sources",
        "2. Use what you found to run targeted WebSearch queries",
        "3. From the targeted searches, collect 8-15 relevant web pages",
        "4. Skip social domains already covered (Reddit/X/Twitter)",
        "5. Focus on: blogs, news articles, tutorials, documentation, GitHub repos",
        "6. Prefer recent content within the date range",
    ]

    if existing_summary:
        # Truncate to keep prompt size reasonable
        truncated = existing_summary[:2000]
        lines.extend([
            "",
            "I already have this data from Reddit/X/YouTube/LinkedIn APIs.",
            "Find web sources that ADD NEW information beyond what is below:",
            "",
            truncated,
        ])

    lines.extend([
        "",
        "Return ONLY this format, nothing else:",
        "",
        "## Web Sources",
        "",
        "1. **Title** (domain.com) - One sentence summary of the key finding",
        "2. **Title** (domain.com) - One sentence summary",
        "...",
        "",
        "## Key Web Insights",
        "",
        "- Insight 1",
        "- Insight 2",
        "- Insight 3",
        "",
        "No preamble or sign-off. Do not add a separate Sources list.",
    ])

    return "\n".join(lines)
