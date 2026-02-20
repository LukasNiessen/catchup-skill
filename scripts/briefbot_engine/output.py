"""Render research reports as markdown, JSON, and file artifacts."""

import json
from pathlib import Path
from typing import List, Optional

from .content import Report, ContentItem, Source

OUTPUT_DIR = Path.home() / ".local" / "share" / "briefbot" / "out"


def _ensure_output_dir():
    """Create the output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _freshness_check(report: Report) -> dict:
    """Count how many items fall within the target date range."""
    counts = {}
    for src in Source:
        counts[src.value] = sum(
            1 for item in report.items
            if item.source == src and item.published and item.published >= report.range_start
        )

    total_recent = sum(counts.values())
    total_items = len(report.items)

    return {
        "reddit_recent": counts.get("reddit", 0),
        "x_recent": counts.get("x", 0),
        "youtube_recent": counts.get("youtube", 0),
        "linkedin_recent": counts.get("linkedin", 0),
        "web_recent": counts.get("web", 0),
        "total_recent": total_recent,
        "total_items": total_items,
        "is_sparse": total_recent < 4,
        "mostly_evergreen": total_items > 0 and total_recent < total_items * 0.25,
    }


def compact(report: Report, max_per_source: int = 15, missing_keys: str = "none") -> str:
    """Produce condensed markdown for Claude to synthesize."""
    lines = []

    lines.append(f"## Findings: {report.topic}")
    lines.append("")

    freshness = _freshness_check(report)
    if freshness["is_sparse"]:
        lines.append("**\u26a0\ufe0f LIMITED RECENT DATA** - Few discussions from the last 30 days.")
        lines.append(f"Only {freshness['total_recent']} item(s) confirmed from {report.range_start} to {report.range_end}.")
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

    lines.append(f"**Date Range:** {report.range_start} to {report.range_end}")
    lines.append(f"**Mode:** {report.mode}")
    if report.openai_model_used:
        lines.append(f"**OpenAI Model:** {report.openai_model_used}")
    if report.xai_model_used:
        lines.append(f"**xAI Model:** {report.xai_model_used}")
    lines.append("")

    # Platform status summary
    if report.mode != "web-only":
        status_parts = []
        if report.mode in ("both", "reddit-only", "all", "reddit-web"):
            if report.reddit_error:
                status_parts.append(f"Reddit=ERROR ({report.reddit_error})")
            else:
                status_parts.append(f"Reddit=OK ({len(report.reddit)} threads)")
        if report.mode in ("both", "x-only", "all", "x-web"):
            if report.x_error:
                status_parts.append(f"X=ERROR ({report.x_error})")
            else:
                status_parts.append(f"X=OK ({len(report.x)} posts)")
        if report.mode in ("all",):
            if report.youtube_error:
                status_parts.append(f"YouTube=ERROR")
            elif report.youtube:
                status_parts.append(f"YouTube=OK ({len(report.youtube)} videos)")
            if report.linkedin_error:
                status_parts.append(f"LinkedIn=ERROR")
            elif report.linkedin:
                status_parts.append(f"LinkedIn=OK ({len(report.linkedin)} posts)")
        if status_parts:
            lines.append(f"**Platform Status:** {' | '.join(status_parts)}")
            lines.append("")

    if report.mode == "reddit-only" and missing_keys == "x":
        lines.append("*\U0001f4a1 Tip: Add XAI_API_KEY for X/Twitter data and better triangulation.*")
        lines.append("")
    elif report.mode == "x-only" and missing_keys == "reddit":
        lines.append("*\U0001f4a1 Tip: Add OPENAI_API_KEY for Reddit data and better triangulation.*")
        lines.append("")

    # Reddit
    reddit_items = report.reddit
    if report.reddit_error:
        lines.append("### Reddit Threads")
        lines.append("")
        lines.append(f"**ERROR:** {report.reddit_error}")
        lines.append("")
    elif report.mode in ("both", "reddit-only") and not reddit_items:
        lines.append("### Reddit Threads")
        lines.append("")
        lines.append("*No relevant Reddit threads found for this topic.*")
        lines.append("")
    elif reddit_items:
        lines.append("### Reddit Threads")
        lines.append("")
        for item in reddit_items[:max_per_source]:
            eng = ""
            if item.signals:
                parts = []
                if item.signals.upvotes is not None:
                    parts.append(f"{item.signals.upvotes}pt")
                if item.signals.comments is not None:
                    parts.append(f"{item.signals.comments}c")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_trust}]" if item.date_trust != "high" else ""
            subreddit = item.meta.get("subreddit", item.author)

            lines.append(f"**{item.item_id}** [{item.score}] r/{subreddit}{date_str}{conf}{eng}")
            lines.append(f"  {item.headline}")
            lines.append(f"  {item.permalink}")
            lines.append(f"  *{item.rationale}*")

            if item.thread_insights:
                lines.append("  Insights:")
                for insight in item.thread_insights[:3]:
                    lines.append(f"    - {insight}")

            lines.append("")

    # X
    x_items = report.x
    if report.x_error:
        lines.append("### X Posts")
        lines.append("")
        lines.append(f"**ERROR:** {report.x_error}")
        lines.append("")
    elif report.mode in ("both", "x-only", "all", "x-web") and not x_items:
        lines.append("### X Posts")
        lines.append("")
        lines.append("*No relevant X posts found for this topic.*")
        lines.append("")
    elif x_items:
        lines.append("### X Posts")
        lines.append("")
        for item in x_items[:max_per_source]:
            eng = ""
            if item.signals:
                parts = []
                if item.signals.likes is not None:
                    parts.append(f"{item.signals.likes}lk")
                if item.signals.reposts is not None:
                    parts.append(f"{item.signals.reposts}rp")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_trust}]" if item.date_trust != "high" else ""

            lines.append(f"**{item.item_id}** [{item.score}] @{item.author}{date_str}{conf}{eng}")
            lines.append(f"  {item.headline[:180]}...")
            lines.append(f"  {item.permalink}")
            lines.append(f"  *{item.rationale}*")
            lines.append("")

    # YouTube
    yt_items = report.youtube
    if report.youtube_error:
        lines.append("### YouTube Videos")
        lines.append("")
        lines.append(f"**ERROR:** {report.youtube_error}")
        lines.append("")
    elif yt_items:
        lines.append("### YouTube Videos")
        lines.append("")
        for item in yt_items[:max_per_source]:
            eng = ""
            if item.signals:
                parts = []
                if item.signals.views is not None:
                    parts.append(f"{item.signals.views:,}views")
                if item.signals.likes is not None:
                    parts.append(f"{item.signals.likes:,}likes")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_trust}]" if item.date_trust != "high" else ""

            lines.append(f"**{item.item_id}** [{item.score}] {item.author}{date_str}{conf}{eng}")
            lines.append(f"  {item.headline}")
            lines.append(f"  {item.permalink}")
            lines.append(f"  *{item.rationale}*")
            lines.append("")

    # LinkedIn
    li_items = report.linkedin
    if report.linkedin_error:
        lines.append("### LinkedIn Posts")
        lines.append("")
        lines.append(f"**ERROR:** {report.linkedin_error}")
        lines.append("")
    elif li_items:
        lines.append("### LinkedIn Posts")
        lines.append("")
        for item in li_items[:max_per_source]:
            eng = ""
            if item.signals:
                parts = []
                if item.signals.reactions is not None:
                    parts.append(f"{item.signals.reactions}reactions")
                if item.signals.comments is not None:
                    parts.append(f"{item.signals.comments}cmt")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_trust}]" if item.date_trust != "high" else ""
            author = item.author
            author_title = item.meta.get("author_title")
            if author_title:
                author += f" ({author_title})"

            lines.append(f"**{item.item_id}** [{item.score}] {author}{date_str}{conf}{eng}")
            lines.append(f"  {item.headline[:200]}...")
            lines.append(f"  {item.permalink}")
            lines.append(f"  *{item.rationale}*")
            lines.append("")

    # Web
    web_items = report.web
    if report.web_error:
        lines.append("### Web Results")
        lines.append("")
        lines.append(f"**ERROR:** {report.web_error}")
        lines.append("")
    elif web_items:
        lines.append("### Web Results")
        lines.append("")
        for item in web_items[:max_per_source]:
            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_trust}]" if item.date_trust != "high" else ""
            domain = item.meta.get("source_domain", item.author)

            lines.append(f"**{item.item_id}** [WEB] [{item.score}] {domain}{date_str}{conf}")
            lines.append(f"  {item.headline}")
            lines.append(f"  {item.permalink}")
            lines.append(f"  {item.body[:120]}...")
            lines.append(f"  *{item.rationale}*")
            lines.append("")

    return "\n".join(lines)


def context_fragment(report: Report) -> str:
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
        aggregated.append((item.score, "Reddit", item.headline, item.permalink))

    for item in report.x[:5]:
        aggregated.append((item.score, "X", f"{item.headline[:50]}...", item.permalink))

    for item in report.youtube[:5]:
        aggregated.append((item.score, "YouTube", f"{item.headline[:50]}...", item.permalink))

    for item in report.linkedin[:5]:
        aggregated.append((item.score, "LinkedIn", f"{item.headline[:50]}...", item.permalink))

    for item in report.web[:5]:
        aggregated.append((item.score, "Web", f"{item.headline[:50]}...", item.permalink))

    aggregated.sort(key=lambda entry: -entry[0])

    for score_val, source, text, url in aggregated[:10]:
        lines.append(f"- [{source}] {text}")

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("*See full report for best practices, prompt pack, and detailed sources.*")
    lines.append("")

    return "\n".join(lines)


def full_report(report: Report) -> str:
    """Produce the complete markdown report with all details."""
    lines = []

    lines.append(f"# {report.topic} - Last 30 Days Research Report")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Date Range:** {report.range_start} to {report.range_end}")
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
    reddit_items = report.reddit
    if reddit_items:
        lines.append("## Reddit Threads")
        lines.append("")
        for item in reddit_items:
            lines.append(f"### {item.item_id}: {item.headline}")
            lines.append("")
            subreddit = item.meta.get("subreddit", item.author)
            lines.append(f"- **Subreddit:** r/{subreddit}")
            lines.append(f"- **URL:** {item.permalink}")
            lines.append(f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_trust})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.rationale}")

            if item.signals:
                lines.append(f"- **Engagement:** {item.signals.upvotes or '?'} points, {item.signals.comments or '?'} comments")

            if item.thread_insights:
                lines.append("")
                lines.append("**Key Insights from Comments:**")
                for insight in item.thread_insights:
                    lines.append(f"- {insight}")

            lines.append("")

    # X detailed
    x_items = report.x
    if x_items:
        lines.append("## X Posts")
        lines.append("")
        for item in x_items:
            lines.append(f"### {item.item_id}: @{item.author}")
            lines.append("")
            lines.append(f"- **URL:** {item.permalink}")
            lines.append(f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_trust})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.rationale}")

            if item.signals:
                lines.append(f"- **Engagement:** {item.signals.likes or '?'} likes, {item.signals.reposts or '?'} reposts")

            lines.append("")
            lines.append(f"> {item.headline}")
            lines.append("")

    # YouTube detailed
    yt_items = report.youtube
    if yt_items:
        lines.append("## YouTube Videos")
        lines.append("")
        for item in yt_items:
            lines.append(f"### {item.item_id}: {item.headline}")
            lines.append("")
            lines.append(f"- **Channel:** {item.author}")
            lines.append(f"- **URL:** {item.permalink}")
            lines.append(f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_trust})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.rationale}")

            if item.signals:
                lines.append(f"- **Engagement:** {item.signals.views or '?'} views, {item.signals.likes or '?'} likes")

            if item.body:
                lines.append("")
                lines.append(f"> {item.body}")

            lines.append("")

    # LinkedIn detailed
    li_items = report.linkedin
    if li_items:
        lines.append("## LinkedIn Posts")
        lines.append("")
        for item in li_items:
            author = item.author
            author_title = item.meta.get("author_title")
            if author_title:
                author += f" - {author_title}"
            lines.append(f"### {item.item_id}: {author}")
            lines.append("")
            lines.append(f"- **URL:** {item.permalink}")
            lines.append(f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_trust})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.rationale}")

            if item.signals:
                lines.append(f"- **Engagement:** {item.signals.reactions or '?'} reactions, {item.signals.comments or '?'} comments")

            lines.append("")
            lines.append(f"> {item.headline}")
            lines.append("")

    # Web detailed
    web_items = report.web
    if web_items:
        lines.append("## Web Results")
        lines.append("")
        for item in web_items:
            lines.append(f"### {item.item_id}: {item.headline}")
            lines.append("")
            domain = item.meta.get("source_domain", item.author)
            lines.append(f"- **Source:** {domain}")
            lines.append(f"- **URL:** {item.permalink}")
            lines.append(f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_trust})")
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.rationale}")
            lines.append("")
            lines.append(f"> {item.body}")
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
    report: Report,
    raw_openai_response: Optional[dict] = None,
    raw_xai_response: Optional[dict] = None,
    raw_enriched_reddit: Optional[list] = None,
    raw_youtube_response: Optional[dict] = None,
    raw_linkedin_response: Optional[dict] = None,
):
    """Write all output artifacts to disk."""
    _ensure_output_dir()

    with open(OUTPUT_DIR / "data.json", "w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / "summary.md", "w", encoding="utf-8") as fh:
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
