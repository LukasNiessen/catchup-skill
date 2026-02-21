"""Render report views and persist artifacts."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import locations, timeframe
from .records import Brief, Channel, Signal

OUTPUT_DIR = locations.output_dir()


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class FreshnessSnapshot:
    recent_by_channel: dict
    total_recent: int
    total_items: int
    density: float
    sparse: bool
    evergreen: bool


def _freshness_snapshot(report: Brief) -> FreshnessSnapshot:
    counts = {src.value: 0 for src in Channel}
    for item in report.items:
        if not item.dated:
            continue
        if item.dated >= report.span.start:
            counts[item.channel.value] += 1

    total_recent = sum(counts.values())
    total_items = len(report.items)
    density = (total_recent / total_items) if total_items else 0.0
    sparse = total_recent < 3 or density < 0.2
    evergreen = total_items > 0 and density < 0.2

    return FreshnessSnapshot(
        recent_by_channel=counts,
        total_recent=total_recent,
        total_items=total_items,
        density=density,
        sparse=sparse,
        evergreen=evergreen,
    )


def _format_confidence(conf: str) -> str:
    if conf == timeframe.CONFIDENCE_SOLID:
        return "high"
    if conf == timeframe.CONFIDENCE_SOFT:
        return "med"
    if conf == timeframe.CONFIDENCE_UNKNOWN:
        return "unknown"
    return "low"


def compact(
    report: Brief, max_per_channel: int = 12, missing_keys: str = "none"
) -> str:
    lines = [f"## Brief Snapshot — {report.topic}", ""]

    freshness = _freshness_snapshot(report)
    if freshness.sparse:
        lines.append("**Low recent activity detected.**")
        lines.append(
            f"Found {freshness.total_recent} in-range item(s) between {report.span.start} and {report.span.end}."
        )
        if freshness.evergreen:
            lines.append("Most results look evergreen rather than newly published.")
        lines.append("")

    if report.cache.enabled:
        age_display = (
            f"{report.cache.age_hours:.1f}h old" if report.cache.age_hours else "cached"
        )
        lines.append(f"Cache: {age_display} (use `--refresh` for a new run)")
        lines.append("")

    summary_bits = [
        f"Window: {report.span.start} → {report.span.end}",
        f"Mode: {report.mode}",
    ]
    if report.models.openai:
        summary_bits.append(f"OpenAI={report.models.openai}")
    if report.models.xai:
        summary_bits.append(f"xAI={report.models.xai}")
    lines.append(" | ".join(summary_bits))
    lines.append("")

    if report.complexity_class or report.epistemic_stance:
        lines.append("### Query Diagnostics")
        lines.append("")
        if report.complexity_class:
            lines.append(
                f"- Complexity: {report.complexity_class} ({report.complexity_reason})"
            )
        if report.epistemic_stance:
            lines.append(
                f"- Epistemic stance: {report.epistemic_stance} ({report.epistemic_reason})"
            )
        if report.decomposition:
            lines.append("- Decomposition:")
            for idx, subq in enumerate(report.decomposition, start=1):
                lines.append(f"  {idx}. {subq}")
        elif report.complexity_class:
            source = report.decomposition_source or "skipped"
            lines.append(f"- Decomposition: {source}")
        lines.append("")

    if report.mode == "web-only":
        lines.append(
            "Web-only execution: supplement with external sources where possible."
        )
        lines.append(
            "Add `OPENAI_API_KEY` and/or `XAI_API_KEY` in `~/.config/briefbot/briefbot.env` (or legacy `.env`) for richer platform data."
        )
        lines.append("")

    if report.mode == "reddit-only" and missing_keys == "x":
        lines.append("*Tip: add `XAI_API_KEY` to cross-check findings on X.*")
        lines.append("")
    elif report.mode == "x-only" and missing_keys == "reddit":
        lines.append("*Tip: add `OPENAI_API_KEY` to include Reddit/YouTube/LinkedIn evidence.*")
        lines.append("")

    combined = sorted(report.items, key=lambda item: item.rank, reverse=True)
    if combined:
        lines.append("### Top Signals")
        lines.append("")
        for item in combined[: min(8, len(combined))]:
            label = item.channel.value.upper()
            date_str = item.dated or "no date"
            lines.append(f"- [{label}] {item.headline} ({date_str}, score {item.rank})")
        lines.append("")

    def _render_channel(label: str, items: list, err: Optional[str] = None):
        lines.append(f"### {label}")
        lines.append("")
        if err:
            lines.append(f"**ERROR:** {err}")
            lines.append("")
            return
        if not items:
            lines.append("*No matching results found.*")
            lines.append("")
            return
        for item in items[:max_per_channel]:
            eng = ""
            if item.interaction:
                parts = []
                if item.interaction.upvotes is not None:
                    parts.append(f"{item.interaction.upvotes}pt")
                if item.interaction.comments is not None:
                    parts.append(f"{item.interaction.comments}c")
                if item.interaction.likes is not None:
                    parts.append(f"{item.interaction.likes}lk")
                if item.interaction.reposts is not None:
                    parts.append(f"{item.interaction.reposts}rp")
                if item.interaction.views is not None:
                    parts.append(f"{item.interaction.views:,}views")
                if item.interaction.reactions is not None:
                    parts.append(f"{item.interaction.reactions}react")
                if parts:
                    eng = f" [{', '.join(parts)}]"

            date_str = f" ({item.dated})" if item.dated else " (no date)"
            conf = f" [{_format_confidence(item.time_confidence)}]" if item.time_confidence != timeframe.CONFIDENCE_SOLID else ""
            byline = f" — {item.byline}" if item.byline else ""

            lines.append(
                f"**{item.key}** [{item.rank}] {item.headline}{byline}{date_str}{conf}{eng}"
            )
            lines.append(f"  {item.url}")
            if item.rationale:
                lines.append(f"  *{item.rationale}*")
            if item.notables:
                lines.append("  Notes:")
                for note in item.notables[:3]:
                    lines.append(f"    - {note}")
            lines.append("")

    _render_channel("Web Sources", report.web, report.web_error)
    _render_channel("Reddit Threads", report.reddit, report.reddit_error)
    _render_channel("X Posts", report.x, report.x_error)
    _render_channel("YouTube Videos", report.youtube, report.youtube_error)
    _render_channel("LinkedIn Posts", report.linkedin, report.linkedin_error)

    return "\n".join(lines)


def context_fragment(report: Brief) -> str:
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
        aggregated.append((item.rank, "Reddit", item.headline))
    for item in report.x[:5]:
        aggregated.append((item.rank, "X", item.headline[:60]))
    for item in report.youtube[:5]:
        aggregated.append((item.rank, "YouTube", item.headline[:60]))
    for item in report.linkedin[:5]:
        aggregated.append((item.rank, "LinkedIn", item.headline[:60]))
    for item in report.web[:5]:
        aggregated.append((item.rank, "Web", item.headline[:60]))

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


def signal_cards(report: Brief, max_items: int = 8) -> str:
    """Produce a terse card-style view for quick scanning."""
    combined = sorted(report.items, key=lambda item: item.rank, reverse=True)
    lines = [f"# Signal Cards: {report.topic}", ""]
    for item in combined[:max_items]:
        label = item.channel.value.upper()
        date_str = item.dated or "unknown date"
        lines.append(f"- [{label}] {item.headline} ({date_str}, score {item.rank})")
        lines.append(f"  {item.url}")
    return "\n".join(lines)


def full_report(report: Brief) -> str:
    """Produce the verbose markdown report."""
    lines = []

    lines.append(f"# {report.topic} — Intelligence Brief")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Date Range:** {report.span.start} to {report.span.end}")
    lines.append(f"**Mode:** {report.mode}")
    lines.append("")

    lines.append("## Models Used")
    lines.append("")
    if report.models.xai:
        lines.append(f"- **xAI:** {report.models.xai}")
    if report.models.openai:
        lines.append(f"- **OpenAI:** {report.models.openai}")
    lines.append("")

    if report.complexity_class or report.epistemic_stance:
        lines.append("## Query Diagnostics")
        lines.append("")
        if report.complexity_class:
            lines.append(
                f"- **Complexity:** {report.complexity_class} ({report.complexity_reason})"
            )
        if report.epistemic_stance:
            lines.append(
                f"- **Epistemic stance:** {report.epistemic_stance} ({report.epistemic_reason})"
            )
        if report.decomposition:
            lines.append("")
            lines.append("**Decomposition:**")
            for idx, subq in enumerate(report.decomposition, start=1):
                lines.append(f"{idx}. {subq}")
        elif report.complexity_class:
            source = report.decomposition_source or "skipped"
            lines.append(f"- **Decomposition:** {source}")
        lines.append("")

    def _render_verbose(title: str, items: list):
        if not items:
            return
        lines.append(f"## {title}")
        lines.append("")
        for item in items:
            lines.append(f"### {item.key}: {item.headline}")
            lines.append("")
            if item.byline:
                lines.append(f"- **Byline:** {item.byline}")
            lines.append(f"- **URL:** {item.url}")
            lines.append(
                f"- **Date:** {item.dated or 'Unknown'} (confidence: {item.time_confidence})"
            )
            lines.append(f"- **Score:** {item.rank}/100")
            if item.rationale:
                lines.append(f"- **Relevance:** {item.rationale}")

            if item.interaction:
                if item.interaction.upvotes is not None or item.interaction.comments is not None:
                    lines.append(
                        f"- **Engagement:** {item.interaction.upvotes or '?'} points, {item.interaction.comments or '?'} comments"
                    )
                elif item.interaction.likes is not None or item.interaction.reposts is not None:
                    lines.append(
                        f"- **Engagement:** {item.interaction.likes or '?'} likes, {item.interaction.reposts or '?'} reposts"
                    )
                elif item.interaction.views is not None or item.interaction.reactions is not None:
                    lines.append(
                        f"- **Engagement:** {item.interaction.views or '?'} views, {item.interaction.reactions or '?'} reactions"
                    )

            if item.notables:
                lines.append("")
                lines.append("**Highlights:**")
                for insight in item.notables:
                    lines.append(f"- {insight}")

            if item.blurb:
                lines.append("")
                lines.append(f"> {item.blurb}")

            lines.append("")

    _render_verbose("Web Sources", report.web)
    _render_verbose("Reddit Threads", report.reddit)
    _render_verbose("X Posts", report.x)
    _render_verbose("YouTube Videos", report.youtube)
    _render_verbose("LinkedIn Posts", report.linkedin)

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
    report: Brief,
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


# Compatibility aliases for alternate naming conventions
render_compact = compact
render_full_report = full_report
render_context_snippet = context_fragment
_assess_data_freshness = _freshness_snapshot
