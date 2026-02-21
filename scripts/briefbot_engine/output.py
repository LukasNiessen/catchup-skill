"""Render report views and persist artifacts."""

import json
from pathlib import Path
from typing import Optional

from .content import Report, ContentItem, Source
from . import paths

OUTPUT_DIR = paths.output_dir()


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _freshness_check(report: Report) -> dict:
    counts = {}
    for src in Source:
        counts[src.value] = sum(
            1
            for item in report.items
            if item.source == src
            and item.published
            and item.published >= report.range_start
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


def compact(
    report: Report, max_per_source: int = 15, missing_keys: str = "none"
) -> str:
    lines = [f"## Research Snapshot: {report.topic}", ""]

    freshness = _freshness_check(report)
    if freshness["is_sparse"]:
        lines.append("**Sparse recent activity detected.**")
        lines.append(
            f"Found {freshness['total_recent']} in-range item(s) between {report.range_start} and {report.range_end}."
        )
        if freshness["mostly_evergreen"]:
            lines.append("Most results appear evergreen rather than newly published.")
        lines.append("")

    if report.from_cache:
        age_display = f"{report.cache_age_hours:.1f}h old" if report.cache_age_hours else "cached"
        lines.append(f"**Cache:** {age_display} (`--refresh` for a new run)")
        lines.append("")

    summary_bits = [f"Window: {report.range_start} to {report.range_end}", f"Mode: {report.mode}"]
    if report.openai_model_used:
        summary_bits.append(f"OpenAI={report.openai_model_used}")
    if report.xai_model_used:
        summary_bits.append(f"xAI={report.xai_model_used}")
    lines.append(" | ".join(summary_bits))
    lines.append("")

    if report.mode == "web-only":
        lines.append("Web-only execution: supplement with external sources where possible.")
        lines.append("Add `OPENAI_API_KEY` and/or `XAI_API_KEY` in `~/.config/briefbot/.env` for richer platform data.")
        lines.append("")

    if report.mode == "reddit-only" and missing_keys == "x":
        lines.append("*Tip: add `XAI_API_KEY` to cross-check findings on X.*")
        lines.append("")
    elif report.mode == "x-only" and missing_keys == "reddit":
        lines.append("*Tip: add `OPENAI_API_KEY` to include Reddit/YouTube/LinkedIn evidence.*")
        lines.append("")

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
            if item.engagement:
                parts = []
                if item.engagement.upvotes is not None:
                    parts.append(f"{item.engagement.upvotes}pt")
                if item.engagement.comments is not None:
                    parts.append(f"{item.engagement.comments}c")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_quality}]" if item.date_quality != "high" else ""
            subreddit = item.meta.get("subreddit", item.author)

            lines.append(
                f"**{item.uid}** [{item.score}] r/{subreddit}{date_str}{conf}{eng}"
            )
            lines.append(f"  {item.title}")
            lines.append(f"  {item.link}")
            lines.append(f"  *{item.reason}*")

            if item.comment_highlights:
                lines.append("  Insights:")
                for insight in item.comment_highlights[:3]:
                    lines.append(f"    - {insight}")

            lines.append("")

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
            if item.engagement:
                parts = []
                if item.engagement.likes is not None:
                    parts.append(f"{item.engagement.likes}lk")
                if item.engagement.reposts is not None:
                    parts.append(f"{item.engagement.reposts}rp")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_quality}]" if item.date_quality != "high" else ""

            lines.append(
                f"**{item.uid}** [{item.score}] @{item.author}{date_str}{conf}{eng}"
            )
            lines.append(f"  {item.title[:180]}...")
            lines.append(f"  {item.link}")
            lines.append(f"  *{item.reason}*")
            lines.append("")

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
            if item.engagement:
                parts = []
                if item.engagement.views is not None:
                    parts.append(f"{item.engagement.views:,}views")
                if item.engagement.likes is not None:
                    parts.append(f"{item.engagement.likes:,}likes")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_quality}]" if item.date_quality != "high" else ""

            lines.append(
                f"**{item.uid}** [{item.score}] {item.author}{date_str}{conf}{eng}"
            )
            lines.append(f"  {item.title}")
            lines.append(f"  {item.link}")
            lines.append(f"  *{item.reason}*")
            lines.append("")

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
            if item.engagement:
                parts = []
                if item.engagement.reactions is not None:
                    parts.append(f"{item.engagement.reactions}reactions")
                if item.engagement.comments is not None:
                    parts.append(f"{item.engagement.comments}cmt")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.published})" if item.published else " (no date)"
            conf = f" [{item.date_quality}]" if item.date_quality != "high" else ""
            author = item.author
            author_title = item.meta.get("author_title")
            if author_title:
                author += f" ({author_title})"

            lines.append(
                f"**{item.uid}** [{item.score}] {author}{date_str}{conf}{eng}"
            )
            lines.append(f"  {item.title[:200]}...")
            lines.append(f"  {item.link}")
            lines.append(f"  *{item.reason}*")
            lines.append("")

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
            conf = f" [{item.date_quality}]" if item.date_quality != "high" else ""
            domain = item.meta.get("source_domain", item.author)

            lines.append(
                f"**{item.uid}** [WEB] [{item.score}] {domain}{date_str}{conf}"
            )
            lines.append(f"  {item.title}")
            lines.append(f"  {item.link}")
            lines.append(f"  {item.summary[:120]}...")
            lines.append(f"  *{item.reason}*")
            lines.append("")

    return "\n".join(lines)


def context_fragment(report: Report) -> str:
    """Build a compact context block for downstream prompts."""
    lines = [
        f"# Brief Context: {report.topic}",
        "",
        f"*Generated: {report.generated_at[:10]} | Mode: {report.mode}*",
        "",
        "## Signal Highlights",
        "",
    ]

    aggregated = []
    for item in report.reddit[:5]:
        aggregated.append((item.score, "Reddit", item.title))
    for item in report.x[:5]:
        aggregated.append((item.score, "X", item.title[:60]))
    for item in report.youtube[:5]:
        aggregated.append((item.score, "YouTube", item.title[:60]))
    for item in report.linkedin[:5]:
        aggregated.append((item.score, "LinkedIn", item.title[:60]))
    for item in report.web[:5]:
        aggregated.append((item.score, "Web", item.title[:60]))

    for _score, source, text in sorted(aggregated, key=lambda entry: -entry[0])[:10]:
        lines.append(f"- `{source}` {text}")

    lines.extend(
        [
            "",
            "## Note",
            "",
            "*Open the full report for detailed item analysis and prompt-ready synthesis.*",
            "",
        ]
    )
    return "\n".join(lines)


def full_report(report: Report) -> str:
    """Produce the verbose markdown report."""
    lines = []

    lines.append(f"# {report.topic} - Intelligence Brief")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Date Range:** {report.range_start} to {report.range_end}")
    lines.append(f"**Mode:** {report.mode}")
    lines.append("")

    lines.append("## Models Used")
    lines.append("")
    if report.xai_model_used:
        lines.append(f"- **xAI:** {report.xai_model_used}")
    if report.openai_model_used:
        lines.append(f"- **OpenAI:** {report.openai_model_used}")
    lines.append("")

    reddit_items = report.reddit
    if reddit_items:
        lines.append("## Reddit Threads")
        lines.append("")
        for item in reddit_items:
            lines.append(f"### {item.uid}: {item.title}")
            lines.append("")
            subreddit = item.meta.get("subreddit", item.author)
            lines.append(f"- **Subreddit:** r/{subreddit}")
            lines.append(f"- **URL:** {item.link}")
            lines.append(
                f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_quality})"
            )
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.reason}")

            if item.engagement:
                lines.append(
                    f"- **Engagement:** {item.engagement.upvotes or '?'} points, {item.engagement.comments or '?'} comments"
                )

            if item.comment_highlights:
                lines.append("")
                lines.append("**Key Insights from Comments:**")
                for insight in item.comment_highlights:
                    lines.append(f"- {insight}")

            lines.append("")

    x_items = report.x
    if x_items:
        lines.append("## X Posts")
        lines.append("")
        for item in x_items:
            lines.append(f"### {item.uid}: @{item.author}")
            lines.append("")
            lines.append(f"- **URL:** {item.link}")
            lines.append(
                f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_quality})"
            )
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.reason}")

            if item.engagement:
                lines.append(
                    f"- **Engagement:** {item.engagement.likes or '?'} likes, {item.engagement.reposts or '?'} reposts"
                )

            lines.append("")
            lines.append(f"> {item.title}")
            lines.append("")

    yt_items = report.youtube
    if yt_items:
        lines.append("## YouTube Videos")
        lines.append("")
        for item in yt_items:
            lines.append(f"### {item.uid}: {item.title}")
            lines.append("")
            lines.append(f"- **Channel:** {item.author}")
            lines.append(f"- **URL:** {item.link}")
            lines.append(
                f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_quality})"
            )
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.reason}")

            if item.engagement:
                lines.append(
                    f"- **Engagement:** {item.engagement.views or '?'} views, {item.engagement.likes or '?'} likes"
                )

            if item.summary:
                lines.append("")
                lines.append(f"> {item.summary}")

            lines.append("")

    li_items = report.linkedin
    if li_items:
        lines.append("## LinkedIn Posts")
        lines.append("")
        for item in li_items:
            author = item.author
            author_title = item.meta.get("author_title")
            if author_title:
                author += f" - {author_title}"
            lines.append(f"### {item.uid}: {author}")
            lines.append("")
            lines.append(f"- **URL:** {item.link}")
            lines.append(
                f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_quality})"
            )
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.reason}")

            if item.engagement:
                lines.append(
                    f"- **Engagement:** {item.engagement.reactions or '?'} reactions, {item.engagement.comments or '?'} comments"
                )

            lines.append("")
            lines.append(f"> {item.title}")
            lines.append("")

    web_items = report.web
    if web_items:
        lines.append("## Web Results")
        lines.append("")
        for item in web_items:
            lines.append(f"### {item.uid}: {item.title}")
            lines.append("")
            domain = item.meta.get("source_domain", item.author)
            lines.append(f"- **Source:** {domain}")
            lines.append(f"- **URL:** {item.link}")
            lines.append(
                f"- **Date:** {item.published or 'Unknown'} (confidence: {item.date_quality})"
            )
            lines.append(f"- **Score:** {item.score}/100")
            lines.append(f"- **Relevance:** {item.reason}")
            lines.append("")
            lines.append(f"> {item.summary}")
            lines.append("")

    lines.append("## Applied Practices")
    lines.append("")
    lines.append("*Pending synthesis layer.*")
    lines.append("")

    lines.append("## Prompt Drafts")
    lines.append("")
    lines.append("*Pending synthesis layer.*")
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
    """Write normalized and raw artifacts to OUTPUT_DIR."""
    _ensure_output_dir()

    artifacts = {
        "data.json": report.to_dict(),
        "summary.md": full_report(report),
        "briefbot.context.md": context_fragment(report),
    }
    for filename, payload in artifacts.items():
        path = OUTPUT_DIR / filename
        if filename.endswith(".json"):
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
        else:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(payload)

    raw_payloads = {
        "raw_openai.json": raw_openai_response,
        "raw_xai.json": raw_xai_response,
        "raw_reddit_threads_enriched.json": raw_enriched_reddit,
        "raw_youtube.json": raw_youtube_response,
        "raw_linkedin.json": raw_linkedin_response,
    }
    for filename, payload in raw_payloads.items():
        if not payload:
            continue
        with open(OUTPUT_DIR / filename, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)


def context_path() -> str:
    """Return the filesystem path to the context fragment file."""
    return str(OUTPUT_DIR / "briefbot.context.md")

