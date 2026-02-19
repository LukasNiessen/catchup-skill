"""Render research reports as markdown, JSON, and file artifacts."""

import json
from pathlib import Path
from typing import List, Optional

from . import schema

OUTPUT_DIR = Path.home() / ".local" / "share" / "briefbot" / "out"


def _ensure_output_dir():
    """Create the output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _freshness_check(report: schema.Report) -> dict:
    """Count how many items fall within the target date range."""
    reddit_recent = sum(
        1 for item in report.reddit
        if item.date and item.date >= report.range_from
    )
    x_recent = sum(
        1 for item in report.x
        if item.date and item.date >= report.range_from
    )
    youtube_recent = sum(
        1 for item in report.youtube
        if item.date and item.date >= report.range_from
    )
    linkedin_recent = sum(
        1 for item in report.linkedin
        if item.date and item.date >= report.range_from
    )
    web_recent = sum(
        1 for item in report.web
        if item.date and item.date >= report.range_from
    )

    total_recent = reddit_recent + x_recent + youtube_recent + linkedin_recent + web_recent
    total_items = len(report.reddit) + len(report.x) + len(report.youtube) + len(report.linkedin) + len(report.web)

    return {
        "reddit_recent": reddit_recent,
        "x_recent": x_recent,
        "youtube_recent": youtube_recent,
        "linkedin_recent": linkedin_recent,
        "web_recent": web_recent,
        "total_recent": total_recent,
        "total_items": total_items,
        "is_sparse": total_recent < 5,
        "mostly_evergreen": total_items > 0 and total_recent < total_items * 0.3,
    }


def compact(report: schema.Report, max_per_source: int = 15, missing_keys: str = "none") -> str:
    """Produce condensed markdown for Claude to synthesize."""
    lines = []

    lines.append(f"## Research Results: {report.topic}")
    lines.append("")

    freshness = _freshness_check(report)
    if freshness["is_sparse"]:
        lines.append("**\u26a0\ufe0f LIMITED RECENT DATA** - Few discussions from the last 30 days.")
        lines.append(f"Only {freshness['total_recent']} item(s) confirmed from {report.range_from} to {report.range_to}.")
        lines.append("Results below may include older/evergreen content. Be transparent with the user about this.")
        lines.append("")

    if report.mode == "web-only":
        lines.append("**\U0001f310 WEB SEARCH MODE** - Claude will search blogs, docs & news")
        lines.append("")
        lines.append("---")
        lines.append("**\u26a1 Want better results?** Add API keys to unlock Reddit & X data:")
        lines.append("- `OPENAI_API_KEY` \u2192 Reddit threads with real upvotes & comments")
        lines.append("- `XAI_API_KEY` \u2192 X posts with real likes & reposts")
        lines.append("- Edit `~/.config/briefbot/.env` to add keys")
        lines.append("---")
        lines.append("")

    if report.from_cache:
        age_display = f"{report.cache_age_hours:.1f}h old" if report.cache_age_hours else "cached"
        lines.append(f"**\u26a1 CACHED RESULTS** ({age_display}) - use `--refresh` for fresh data")
        lines.append("")

    lines.append(f"**Date Range:** {report.range_from} to {report.range_to}")
    lines.append(f"**Mode:** {report.mode}")
    if report.openai_model_used:
        lines.append(f"**OpenAI Model:** {report.openai_model_used}")
    if report.xai_model_used:
        lines.append(f"**xAI Model:** {report.xai_model_used}")
    lines.append("")

    if report.mode == "reddit-only" and missing_keys == "x":
        lines.append("*\U0001f4a1 Tip: Add XAI_API_KEY for X/Twitter data and better triangulation.*")
        lines.append("")
    elif report.mode == "x-only" and missing_keys == "reddit":
        lines.append("*\U0001f4a1 Tip: Add OPENAI_API_KEY for Reddit data and better triangulation.*")
        lines.append("")

    # Reddit
    if report.reddit_error:
        lines.append("### Reddit Threads")
        lines.append("")
        lines.append(f"**ERROR:** {report.reddit_error}")
        lines.append("")
    elif report.mode in ("both", "reddit-only") and not report.reddit:
        lines.append("### Reddit Threads")
        lines.append("")
        lines.append("*No relevant Reddit threads found for this topic.*")
        lines.append("")
    elif report.reddit:
        lines.append("### Reddit Threads")
        lines.append("")
        for item in report.reddit[:max_per_source]:
            eng = ""
            if item.engagement:
                parts = []
                if item.engagement.score is not None:
                    parts.append(f"{item.engagement.score}pts")
                if item.engagement.num_comments is not None:
                    parts.append(f"{item.engagement.num_comments}cmt")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.date})" if item.date else " (date unknown)"
            conf = f" [date:{item.date_confidence}]" if item.date_confidence != "high" else ""

            lines.append(f"**{item.id}** (score:{item.score}) r/{item.subreddit}{date_str}{conf}{eng}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            lines.append(f"  *{item.why_relevant}*")

            if item.comment_insights:
                lines.append("  Insights:")
                for insight in item.comment_insights[:3]:
                    lines.append(f"    - {insight}")

            lines.append("")

    # X
    if report.x_error:
        lines.append("### X Posts")
        lines.append("")
        lines.append(f"**ERROR:** {report.x_error}")
        lines.append("")
    elif report.mode in ("both", "x-only", "all", "x-web") and not report.x:
        lines.append("### X Posts")
        lines.append("")
        lines.append("*No relevant X posts found for this topic.*")
        lines.append("")
    elif report.x:
        lines.append("### X Posts")
        lines.append("")
        for item in report.x[:max_per_source]:
            eng = ""
            if item.engagement:
                parts = []
                if item.engagement.likes is not None:
                    parts.append(f"{item.engagement.likes}likes")
                if item.engagement.reposts is not None:
                    parts.append(f"{item.engagement.reposts}rt")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.date})" if item.date else " (date unknown)"
            conf = f" [date:{item.date_confidence}]" if item.date_confidence != "high" else ""

            lines.append(f"**{item.id}** (score:{item.score}) @{item.author_handle}{date_str}{conf}{eng}")
            lines.append(f"  {item.text[:200]}...")
            lines.append(f"  {item.url}")
            lines.append(f"  *{item.why_relevant}*")
            lines.append("")

    # YouTube
    if report.youtube_error:
        lines.append("### YouTube Videos")
        lines.append("")
        lines.append(f"**ERROR:** {report.youtube_error}")
        lines.append("")
    elif report.youtube:
        lines.append("### YouTube Videos")
        lines.append("")
        for item in report.youtube[:max_per_source]:
            eng = ""
            if item.engagement:
                parts = []
                if item.engagement.views is not None:
                    parts.append(f"{item.engagement.views:,}views")
                if item.engagement.likes is not None:
                    parts.append(f"{item.engagement.likes:,}likes")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.date})" if item.date else " (date unknown)"
            conf = f" [date:{item.date_confidence}]" if item.date_confidence != "high" else ""

            lines.append(f"**{item.id}** (score:{item.score}) {item.channel_name}{date_str}{conf}{eng}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            lines.append(f"  *{item.why_relevant}*")
            lines.append("")

    # LinkedIn
    if report.linkedin_error:
        lines.append("### LinkedIn Posts")
        lines.append("")
        lines.append(f"**ERROR:** {report.linkedin_error}")
        lines.append("")
    elif report.linkedin:
        lines.append("### LinkedIn Posts")
        lines.append("")
        for item in report.linkedin[:max_per_source]:
            eng = ""
            if item.engagement:
                parts = []
                if item.engagement.reactions is not None:
                    parts.append(f"{item.engagement.reactions}reactions")
                if item.engagement.comments is not None:
                    parts.append(f"{item.engagement.comments}cmt")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.date})" if item.date else " (date unknown)"
            conf = f" [date:{item.date_confidence}]" if item.date_confidence != "high" else ""
            author = item.author_name
            if item.author_title:
                author += f" ({item.author_title})"

            lines.append(f"**{item.id}** (score:{item.score}) {author}{date_str}{conf}{eng}")
            lines.append(f"  {item.text[:200]}...")
            lines.append(f"  {item.url}")
            lines.append(f"  *{item.why_relevant}*")
            lines.append("")

    # Web
    if report.web_error:
        lines.append("### Web Results")
        lines.append("")
        lines.append(f"**ERROR:** {report.web_error}")
        lines.append("")
    elif report.web:
        lines.append("### Web Results")
        lines.append("")
        for item in report.web[:max_per_source]:
            date_str = f" ({item.date})" if item.date else " (date unknown)"
            conf = f" [date:{item.date_confidence}]" if item.date_confidence != "high" else ""

            lines.append(f"**{item.id}** [WEB] (score:{item.score}) {item.source_domain}{date_str}{conf}")
            lines.append(f"  {item.title}")
            lines.append(f"  {item.url}")
            lines.append(f"  {item.snippet[:150]}...")
            lines.append(f"  *{item.why_relevant}*")
            lines.append("")

    return "\n".join(lines)


def context_fragment(report: schema.Report) -> str:
    """Build a reusable context snippet for embedding."""
    lines = []
    lines.append(f"# Context: {report.topic} (Last 30 Days)")
    lines.append("")
    lines.append(f"*Generated: {report.generated_at[:10]} | Sources: {report.mode}*")
    lines.append("")

    lines.append("## Key Sources")
    lines.append("")

    aggregated = []

    for item in report.reddit[:5]:
        aggregated.append((item.score, "Reddit", item.title, item.url))

    for item in report.x[:5]:
        aggregated.append((item.score, "X", f"{item.text[:50]}...", item.url))

    for item in report.youtube[:5]:
        aggregated.append((item.score, "YouTube", f"{item.title[:50]}...", item.url))

    for item in report.linkedin[:5]:
        aggregated.append((item.score, "LinkedIn", f"{item.text[:50]}...", item.url))

    for item in report.web[:5]:
        aggregated.append((item.score, "Web", f"{item.title[:50]}...", item.url))

    aggregated.sort(key=lambda entry: -entry[0])

    for score_val, source, text, url in aggregated[:7]:
        lines.append(f"- [{source}] {text}")

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("*See full report for best practices, prompt pack, and detailed sources.*")
    lines.append("")

    return "\n".join(lines)


def full_report(report: schema.Report) -> str:
    """Produce the complete markdown report with all details."""
    lines = []

    lines.append(f"# {report.topic} - Last 30 Days Research Report")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Date Range:** {report.range_from} to {report.range_to}")
    lines.append(f"**Mode:** {report.mode}")
    lines.append("")

    lines.append("## Models Used")
    lines.append("")
    if report.openai_model_used:
        lines.append(f"- **OpenAI:** {report.openai_model_used}")
    if report.xai_model_used:
        lines.append(f"- **xAI:** {report.xai_model_used}")
    lines.append("")

    # Reddit detailed
    if report.reddit:
        lines.append("## Reddit Threads")
        lines.append("")
        for item in report.reddit:
            lines.append(f"### {item.id}: {item.title}")
            lines.append("")
            lines.append(f"- **Subreddit:** r/{item.subreddit}")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'} (confidence: {item.date_confidence})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.why_relevant}")

            if item.engagement:
                lines.append(f"- **Engagement:** {item.engagement.score or '?'} points, {item.engagement.num_comments or '?'} comments")

            if item.comment_insights:
                lines.append("")
                lines.append("**Key Insights from Comments:**")
                for insight in item.comment_insights:
                    lines.append(f"- {insight}")

            lines.append("")

    # X detailed
    if report.x:
        lines.append("## X Posts")
        lines.append("")
        for item in report.x:
            lines.append(f"### {item.id}: @{item.author_handle}")
            lines.append("")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'} (confidence: {item.date_confidence})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.why_relevant}")

            if item.engagement:
                lines.append(f"- **Engagement:** {item.engagement.likes or '?'} likes, {item.engagement.reposts or '?'} reposts")

            lines.append("")
            lines.append(f"> {item.text}")
            lines.append("")

    # YouTube detailed
    if report.youtube:
        lines.append("## YouTube Videos")
        lines.append("")
        for item in report.youtube:
            lines.append(f"### {item.id}: {item.title}")
            lines.append("")
            lines.append(f"- **Channel:** {item.channel_name}")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'} (confidence: {item.date_confidence})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.why_relevant}")

            if item.engagement:
                lines.append(f"- **Engagement:** {item.engagement.views or '?'} views, {item.engagement.likes or '?'} likes")

            if item.description:
                lines.append("")
                lines.append(f"> {item.description}")

            lines.append("")

    # LinkedIn detailed
    if report.linkedin:
        lines.append("## LinkedIn Posts")
        lines.append("")
        for item in report.linkedin:
            author = item.author_name
            if item.author_title:
                author += f" - {item.author_title}"
            lines.append(f"### {item.id}: {author}")
            lines.append("")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'} (confidence: {item.date_confidence})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.why_relevant}")

            if item.engagement:
                lines.append(f"- **Engagement:** {item.engagement.reactions or '?'} reactions, {item.engagement.comments or '?'} comments")

            lines.append("")
            lines.append(f"> {item.text}")
            lines.append("")

    # Web detailed
    if report.web:
        lines.append("## Web Results")
        lines.append("")
        for item in report.web:
            lines.append(f"### {item.id}: {item.title}")
            lines.append("")
            lines.append(f"- **Source:** {item.source_domain}")
            lines.append(f"- **URL:** {item.url}")
            lines.append(f"- **Date:** {item.date or 'Unknown'} (confidence: {item.date_confidence})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.why_relevant}")
            lines.append("")
            lines.append(f"> {item.snippet}")
            lines.append("")

    # Placeholder sections
    lines.append("## Best Practices")
    lines.append("")
    lines.append("*To be synthesized by Claude*")
    lines.append("")

    lines.append("## Prompt Pack")
    lines.append("")
    lines.append("*To be synthesized by Claude*")
    lines.append("")

    return "\n".join(lines)


def save_artifacts(
    report: schema.Report,
    raw_openai_response: Optional[dict] = None,
    raw_xai_response: Optional[dict] = None,
    raw_enriched_reddit: Optional[list] = None,
    raw_youtube_response: Optional[dict] = None,
    raw_linkedin_response: Optional[dict] = None,
):
    """Write all output artifacts to disk."""
    _ensure_output_dir()

    with open(OUTPUT_DIR / "report.json", "w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / "report.md", "w", encoding="utf-8") as fh:
        fh.write(full_report(report))

    with open(OUTPUT_DIR / "briefbot.context.md", "w", encoding="utf-8") as fh:
        fh.write(context_fragment(report))

    if raw_openai_response:
        with open(OUTPUT_DIR / "raw_openai.json", "w", encoding="utf-8") as fh:
            json.dump(raw_openai_response, fh, indent=2, ensure_ascii=False)

    if raw_xai_response:
        with open(OUTPUT_DIR / "raw_xai.json", "w", encoding="utf-8") as fh:
            json.dump(raw_xai_response, fh, indent=2, ensure_ascii=False)

    if raw_enriched_reddit:
        with open(OUTPUT_DIR / "raw_reddit_threads_enriched.json", "w", encoding="utf-8") as fh:
            json.dump(raw_enriched_reddit, fh, indent=2, ensure_ascii=False)

    if raw_youtube_response:
        with open(OUTPUT_DIR / "raw_youtube.json", "w", encoding="utf-8") as fh:
            json.dump(raw_youtube_response, fh, indent=2, ensure_ascii=False)

    if raw_linkedin_response:
        with open(OUTPUT_DIR / "raw_linkedin.json", "w", encoding="utf-8") as fh:
            json.dump(raw_linkedin_response, fh, indent=2, ensure_ascii=False)


def context_path() -> str:
    """Return the filesystem path to the context fragment file."""
    return str(OUTPUT_DIR / "briefbot.context.md")


# -- Backward-compatible aliases for external callers --
ARTIFACT_DIRECTORY = OUTPUT_DIR
initialize_output_directory = _ensure_output_dir
_evaluate_content_freshness = _freshness_check
generate_compact_output = lambda research_report, maximum_per_source=15, absent_credentials="none": compact(research_report, max_per_source=maximum_per_source, missing_keys=absent_credentials)
generate_context_fragment = context_fragment
generate_comprehensive_report = full_report
persist_all_artifacts = save_artifacts
retrieve_context_filepath = context_path
