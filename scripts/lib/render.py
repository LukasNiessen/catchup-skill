#
# Report Rendering Engine: Formats research data for output display
# Transforms structured report data into human-readable markdown formats
#

import json
from pathlib import Path
from typing import List, Optional

from . import schema

ARTIFACT_DIRECTORY = Path.home() / ".local" / "share" / "briefbot" / "out"


def initialize_output_directory():
    """Creates the output directory if it does not exist."""
    ARTIFACT_DIRECTORY.mkdir(parents=True, exist_ok=True)


# Preserve the original function name for API compatibility
ensure_output_dir = initialize_output_directory


def _evaluate_content_freshness(research_report: schema.Report) -> dict:
    """Evaluates what proportion of results are genuinely from the target period."""
    reddit_fresh_count = 0
    reddit_index = 0
    while reddit_index < len(research_report.reddit):
        reddit_item = research_report.reddit[reddit_index]
        if reddit_item.date and reddit_item.date >= research_report.range_from:
            reddit_fresh_count += 1
        reddit_index += 1

    x_fresh_count = 0
    x_index = 0
    while x_index < len(research_report.x):
        x_item = research_report.x[x_index]
        if x_item.date and x_item.date >= research_report.range_from:
            x_fresh_count += 1
        x_index += 1

    youtube_fresh_count = 0
    youtube_index = 0
    while youtube_index < len(research_report.youtube):
        youtube_item = research_report.youtube[youtube_index]
        if youtube_item.date and youtube_item.date >= research_report.range_from:
            youtube_fresh_count += 1
        youtube_index += 1

    linkedin_fresh_count = 0
    linkedin_index = 0
    while linkedin_index < len(research_report.linkedin):
        linkedin_item = research_report.linkedin[linkedin_index]
        if linkedin_item.date and linkedin_item.date >= research_report.range_from:
            linkedin_fresh_count += 1
        linkedin_index += 1

    web_fresh_count = 0
    web_index = 0
    while web_index < len(research_report.web):
        web_item = research_report.web[web_index]
        if web_item.date and web_item.date >= research_report.range_from:
            web_fresh_count += 1
        web_index += 1

    aggregate_fresh = reddit_fresh_count + x_fresh_count + youtube_fresh_count + linkedin_fresh_count + web_fresh_count
    aggregate_total = len(research_report.reddit) + len(research_report.x) + len(research_report.youtube) + len(research_report.linkedin) + len(research_report.web)

    return {
        "reddit_recent": reddit_fresh_count,
        "x_recent": x_fresh_count,
        "youtube_recent": youtube_fresh_count,
        "linkedin_recent": linkedin_fresh_count,
        "web_recent": web_fresh_count,
        "total_recent": aggregate_fresh,
        "total_items": aggregate_total,
        "is_sparse": aggregate_fresh < 5,
        "mostly_evergreen": aggregate_total > 0 and aggregate_fresh < aggregate_total * 0.3,
    }


# Preserve the original function name for API compatibility
_assess_data_freshness = _evaluate_content_freshness


def generate_compact_output(research_report: schema.Report, maximum_per_source: int = 15, absent_credentials: str = "none") -> str:
    """
    Produces condensed output suitable for synthesis by Claude.

    Args:
        research_report: The report data structure
        maximum_per_source: Upper bound on items per data source
        absent_credentials: Which API keys are missing - 'both', 'reddit', 'x', or 'none'

    Returns:
        Compact markdown representation
    """
    output_lines = []

    # Header section
    output_lines.append("## Research Results: {}".format(research_report.topic))
    output_lines.append("")

    # Evaluate freshness and append warning if sparse
    freshness_metrics = _evaluate_content_freshness(research_report)
    if freshness_metrics["is_sparse"]:
        output_lines.append("**\u26a0\ufe0f LIMITED RECENT DATA** - Few discussions from the last 30 days.")
        output_lines.append("Only {} item(s) confirmed from {} to {}.".format(freshness_metrics['total_recent'], research_report.range_from, research_report.range_to))
        output_lines.append("Results below may include older/evergreen content. Be transparent with the user about this.")
        output_lines.append("")

    # Web-only mode indicator
    if research_report.mode == "web-only":
        output_lines.append("**\U0001f310 WEB SEARCH MODE** - Claude will search blogs, docs & news")
        output_lines.append("")
        output_lines.append("---")
        output_lines.append("**\u26a1 Want better results?** Add API keys to unlock Reddit & X data:")
        output_lines.append("- `OPENAI_API_KEY` \u2192 Reddit threads with real upvotes & comments")
        output_lines.append("- `XAI_API_KEY` \u2192 X posts with real likes & reposts")
        output_lines.append("- Edit `~/.config/last30days/.env` to add keys")
        output_lines.append("---")
        output_lines.append("")

    # Cache status indicator
    if research_report.from_cache:
        if research_report.cache_age_hours:
            age_display = "{:.1f}h old".format(research_report.cache_age_hours)
        else:
            age_display = "cached"
        output_lines.append("**\u26a1 CACHED RESULTS** ({}) - use `--refresh` for fresh data".format(age_display))
        output_lines.append("")

    output_lines.append("**Date Range:** {} to {}".format(research_report.range_from, research_report.range_to))
    output_lines.append("**Mode:** {}".format(research_report.mode))
    if research_report.openai_model_used:
        output_lines.append("**OpenAI Model:** {}".format(research_report.openai_model_used))
    if research_report.xai_model_used:
        output_lines.append("**xAI Model:** {}".format(research_report.xai_model_used))
    output_lines.append("")

    # Coverage hints for partial API availability
    if research_report.mode == "reddit-only" and absent_credentials == "x":
        output_lines.append("*\U0001f4a1 Tip: Add XAI_API_KEY for X/Twitter data and better triangulation.*")
        output_lines.append("")
    elif research_report.mode == "x-only" and absent_credentials == "reddit":
        output_lines.append("*\U0001f4a1 Tip: Add OPENAI_API_KEY for Reddit data and better triangulation.*")
        output_lines.append("")

    # Reddit section
    if research_report.reddit_error:
        output_lines.append("### Reddit Threads")
        output_lines.append("")
        output_lines.append("**ERROR:** {}".format(research_report.reddit_error))
        output_lines.append("")
    elif research_report.mode in ("both", "reddit-only") and not research_report.reddit:
        output_lines.append("### Reddit Threads")
        output_lines.append("")
        output_lines.append("*No relevant Reddit threads found for this topic.*")
        output_lines.append("")
    elif research_report.reddit:
        output_lines.append("### Reddit Threads")
        output_lines.append("")
        item_index = 0
        while item_index < min(len(research_report.reddit), maximum_per_source):
            reddit_item = research_report.reddit[item_index]
            engagement_display = ""
            if reddit_item.engagement:
                engagement_parts = []
                if reddit_item.engagement.score is not None:
                    engagement_parts.append("{}pts".format(reddit_item.engagement.score))
                if reddit_item.engagement.num_comments is not None:
                    engagement_parts.append("{}cmt".format(reddit_item.engagement.num_comments))
                if engagement_parts:
                    engagement_display = " [{}]".format(", ".join(engagement_parts))

            date_display = " ({})".format(reddit_item.date) if reddit_item.date else " (date unknown)"
            confidence_display = " [date:{}]".format(reddit_item.date_confidence) if reddit_item.date_confidence != "high" else ""

            output_lines.append("**{}** (score:{}) r/{}{}{}{}".format(reddit_item.id, reddit_item.score, reddit_item.subreddit, date_display, confidence_display, engagement_display))
            output_lines.append("  {}".format(reddit_item.title))
            output_lines.append("  {}".format(reddit_item.url))
            output_lines.append("  *{}*".format(reddit_item.why_relevant))

            if reddit_item.comment_insights:
                output_lines.append("  Insights:")
                insight_index = 0
                while insight_index < min(len(reddit_item.comment_insights), 3):
                    output_lines.append("    - {}".format(reddit_item.comment_insights[insight_index]))
                    insight_index += 1

            output_lines.append("")
            item_index += 1

    # X section
    if research_report.x_error:
        output_lines.append("### X Posts")
        output_lines.append("")
        output_lines.append("**ERROR:** {}".format(research_report.x_error))
        output_lines.append("")
    elif research_report.mode in ("both", "x-only", "all", "x-web") and not research_report.x:
        output_lines.append("### X Posts")
        output_lines.append("")
        output_lines.append("*No relevant X posts found for this topic.*")
        output_lines.append("")
    elif research_report.x:
        output_lines.append("### X Posts")
        output_lines.append("")
        item_index = 0
        while item_index < min(len(research_report.x), maximum_per_source):
            x_item = research_report.x[item_index]
            engagement_display = ""
            if x_item.engagement:
                engagement_parts = []
                if x_item.engagement.likes is not None:
                    engagement_parts.append("{}likes".format(x_item.engagement.likes))
                if x_item.engagement.reposts is not None:
                    engagement_parts.append("{}rt".format(x_item.engagement.reposts))
                if engagement_parts:
                    engagement_display = " [{}]".format(", ".join(engagement_parts))

            date_display = " ({})".format(x_item.date) if x_item.date else " (date unknown)"
            confidence_display = " [date:{}]".format(x_item.date_confidence) if x_item.date_confidence != "high" else ""

            output_lines.append("**{}** (score:{}) @{}{}{}{}".format(x_item.id, x_item.score, x_item.author_handle, date_display, confidence_display, engagement_display))
            output_lines.append("  {}...".format(x_item.text[:200]))
            output_lines.append("  {}".format(x_item.url))
            output_lines.append("  *{}*".format(x_item.why_relevant))
            output_lines.append("")
            item_index += 1

    # YouTube section
    if research_report.youtube_error:
        output_lines.append("### YouTube Videos")
        output_lines.append("")
        output_lines.append("**ERROR:** {}".format(research_report.youtube_error))
        output_lines.append("")
    elif research_report.youtube:
        output_lines.append("### YouTube Videos")
        output_lines.append("")
        item_index = 0
        while item_index < min(len(research_report.youtube), maximum_per_source):
            youtube_item = research_report.youtube[item_index]
            engagement_display = ""
            if youtube_item.engagement:
                engagement_parts = []
                if youtube_item.engagement.views is not None:
                    engagement_parts.append("{:,}views".format(youtube_item.engagement.views))
                if youtube_item.engagement.likes is not None:
                    engagement_parts.append("{:,}likes".format(youtube_item.engagement.likes))
                if engagement_parts:
                    engagement_display = " [{}]".format(", ".join(engagement_parts))

            date_display = " ({})".format(youtube_item.date) if youtube_item.date else " (date unknown)"
            confidence_display = " [date:{}]".format(youtube_item.date_confidence) if youtube_item.date_confidence != "high" else ""

            output_lines.append("**{}** (score:{}) {}{}{}{}".format(youtube_item.id, youtube_item.score, youtube_item.channel_name, date_display, confidence_display, engagement_display))
            output_lines.append("  {}".format(youtube_item.title))
            output_lines.append("  {}".format(youtube_item.url))
            output_lines.append("  *{}*".format(youtube_item.why_relevant))
            output_lines.append("")
            item_index += 1

    # LinkedIn section
    if research_report.linkedin_error:
        output_lines.append("### LinkedIn Posts")
        output_lines.append("")
        output_lines.append("**ERROR:** {}".format(research_report.linkedin_error))
        output_lines.append("")
    elif research_report.linkedin:
        output_lines.append("### LinkedIn Posts")
        output_lines.append("")
        item_index = 0
        while item_index < min(len(research_report.linkedin), maximum_per_source):
            linkedin_item = research_report.linkedin[item_index]
            engagement_display = ""
            if linkedin_item.engagement:
                engagement_parts = []
                if linkedin_item.engagement.reactions is not None:
                    engagement_parts.append("{}reactions".format(linkedin_item.engagement.reactions))
                if linkedin_item.engagement.comments is not None:
                    engagement_parts.append("{}cmt".format(linkedin_item.engagement.comments))
                if engagement_parts:
                    engagement_display = " [{}]".format(", ".join(engagement_parts))

            date_display = " ({})".format(linkedin_item.date) if linkedin_item.date else " (date unknown)"
            confidence_display = " [date:{}]".format(linkedin_item.date_confidence) if linkedin_item.date_confidence != "high" else ""
            author_display = linkedin_item.author_name
            if linkedin_item.author_title:
                author_display += " ({})".format(linkedin_item.author_title)

            output_lines.append("**{}** (score:{}) {}{}{}{}".format(linkedin_item.id, linkedin_item.score, author_display, date_display, confidence_display, engagement_display))
            output_lines.append("  {}...".format(linkedin_item.text[:200]))
            output_lines.append("  {}".format(linkedin_item.url))
            output_lines.append("  *{}*".format(linkedin_item.why_relevant))
            output_lines.append("")
            item_index += 1

    # Web results section
    if research_report.web_error:
        output_lines.append("### Web Results")
        output_lines.append("")
        output_lines.append("**ERROR:** {}".format(research_report.web_error))
        output_lines.append("")
    elif research_report.web:
        output_lines.append("### Web Results")
        output_lines.append("")
        item_index = 0
        while item_index < min(len(research_report.web), maximum_per_source):
            web_item = research_report.web[item_index]
            date_display = " ({})".format(web_item.date) if web_item.date else " (date unknown)"
            confidence_display = " [date:{}]".format(web_item.date_confidence) if web_item.date_confidence != "high" else ""

            output_lines.append("**{}** [WEB] (score:{}) {}{}{}".format(web_item.id, web_item.score, web_item.source_domain, date_display, confidence_display))
            output_lines.append("  {}".format(web_item.title))
            output_lines.append("  {}".format(web_item.url))
            output_lines.append("  {}...".format(web_item.snippet[:150]))
            output_lines.append("  *{}*".format(web_item.why_relevant))
            output_lines.append("")
            item_index += 1

    return "\n".join(output_lines)


# Preserve the original function name for API compatibility
render_compact = generate_compact_output


def generate_context_fragment(research_report: schema.Report) -> str:
    """
    Produces a reusable context fragment for embedding.

    Args:
        research_report: The report data structure

    Returns:
        Context markdown representation
    """
    output_lines = []
    output_lines.append("# Context: {} (Last 30 Days)".format(research_report.topic))
    output_lines.append("")
    output_lines.append("*Generated: {} | Sources: {}*".format(research_report.generated_at[:10], research_report.mode))
    output_lines.append("")

    output_lines.append("## Key Sources")
    output_lines.append("")

    aggregated_items = []

    item_index = 0
    while item_index < min(len(research_report.reddit), 5):
        reddit_item = research_report.reddit[item_index]
        aggregated_items.append((reddit_item.score, "Reddit", reddit_item.title, reddit_item.url))
        item_index += 1

    item_index = 0
    while item_index < min(len(research_report.x), 5):
        x_item = research_report.x[item_index]
        aggregated_items.append((x_item.score, "X", x_item.text[:50] + "...", x_item.url))
        item_index += 1

    item_index = 0
    while item_index < min(len(research_report.youtube), 5):
        youtube_item = research_report.youtube[item_index]
        aggregated_items.append((youtube_item.score, "YouTube", youtube_item.title[:50] + "...", youtube_item.url))
        item_index += 1

    item_index = 0
    while item_index < min(len(research_report.linkedin), 5):
        linkedin_item = research_report.linkedin[item_index]
        aggregated_items.append((linkedin_item.score, "LinkedIn", linkedin_item.text[:50] + "...", linkedin_item.url))
        item_index += 1

    item_index = 0
    while item_index < min(len(research_report.web), 5):
        web_item = research_report.web[item_index]
        aggregated_items.append((web_item.score, "Web", web_item.title[:50] + "...", web_item.url))
        item_index += 1

    aggregated_items.sort(key=lambda entry: -entry[0])

    display_index = 0
    while display_index < min(len(aggregated_items), 7):
        score_val, source_name, content_text, item_url = aggregated_items[display_index]
        output_lines.append("- [{}] {}".format(source_name, content_text))
        display_index += 1

    output_lines.append("")
    output_lines.append("## Summary")
    output_lines.append("")
    output_lines.append("*See full report for best practices, prompt pack, and detailed sources.*")
    output_lines.append("")

    return "\n".join(output_lines)


# Preserve the original function name for API compatibility
render_context_snippet = generate_context_fragment


def generate_comprehensive_report(research_report: schema.Report) -> str:
    """
    Produces the complete markdown report with all details.

    Args:
        research_report: The report data structure

    Returns:
        Full markdown report
    """
    output_lines = []

    output_lines.append("# {} - Last 30 Days Research Report".format(research_report.topic))
    output_lines.append("")
    output_lines.append("**Generated:** {}".format(research_report.generated_at))
    output_lines.append("**Date Range:** {} to {}".format(research_report.range_from, research_report.range_to))
    output_lines.append("**Mode:** {}".format(research_report.mode))
    output_lines.append("")

    output_lines.append("## Models Used")
    output_lines.append("")
    if research_report.openai_model_used:
        output_lines.append("- **OpenAI:** {}".format(research_report.openai_model_used))
    if research_report.xai_model_used:
        output_lines.append("- **xAI:** {}".format(research_report.xai_model_used))
    output_lines.append("")

    # Reddit detailed section
    if research_report.reddit:
        output_lines.append("## Reddit Threads")
        output_lines.append("")
        item_index = 0
        while item_index < len(research_report.reddit):
            reddit_item = research_report.reddit[item_index]
            output_lines.append("### {}: {}".format(reddit_item.id, reddit_item.title))
            output_lines.append("")
            output_lines.append("- **Subreddit:** r/{}".format(reddit_item.subreddit))
            output_lines.append("- **URL:** {}".format(reddit_item.url))
            output_lines.append("- **Date:** {} (confidence: {})".format(reddit_item.date or 'Unknown', reddit_item.date_confidence))
            output_lines.append("- **Score:** {}/100".format(reddit_item.score))
            output_lines.append("- **Relevance:** {}".format(reddit_item.why_relevant))

            if reddit_item.engagement:
                output_lines.append("- **Engagement:** {} points, {} comments".format(reddit_item.engagement.score or '?', reddit_item.engagement.num_comments or '?'))

            if reddit_item.comment_insights:
                output_lines.append("")
                output_lines.append("**Key Insights from Comments:**")
                insight_index = 0
                while insight_index < len(reddit_item.comment_insights):
                    output_lines.append("- {}".format(reddit_item.comment_insights[insight_index]))
                    insight_index += 1

            output_lines.append("")
            item_index += 1

    # X detailed section
    if research_report.x:
        output_lines.append("## X Posts")
        output_lines.append("")
        item_index = 0
        while item_index < len(research_report.x):
            x_item = research_report.x[item_index]
            output_lines.append("### {}: @{}".format(x_item.id, x_item.author_handle))
            output_lines.append("")
            output_lines.append("- **URL:** {}".format(x_item.url))
            output_lines.append("- **Date:** {} (confidence: {})".format(x_item.date or 'Unknown', x_item.date_confidence))
            output_lines.append("- **Score:** {}/100".format(x_item.score))
            output_lines.append("- **Relevance:** {}".format(x_item.why_relevant))

            if x_item.engagement:
                output_lines.append("- **Engagement:** {} likes, {} reposts".format(x_item.engagement.likes or '?', x_item.engagement.reposts or '?'))

            output_lines.append("")
            output_lines.append("> {}".format(x_item.text))
            output_lines.append("")
            item_index += 1

    # YouTube detailed section
    if research_report.youtube:
        output_lines.append("## YouTube Videos")
        output_lines.append("")
        item_index = 0
        while item_index < len(research_report.youtube):
            youtube_item = research_report.youtube[item_index]
            output_lines.append("### {}: {}".format(youtube_item.id, youtube_item.title))
            output_lines.append("")
            output_lines.append("- **Channel:** {}".format(youtube_item.channel_name))
            output_lines.append("- **URL:** {}".format(youtube_item.url))
            output_lines.append("- **Date:** {} (confidence: {})".format(youtube_item.date or 'Unknown', youtube_item.date_confidence))
            output_lines.append("- **Score:** {}/100".format(youtube_item.score))
            output_lines.append("- **Relevance:** {}".format(youtube_item.why_relevant))

            if youtube_item.engagement:
                output_lines.append("- **Engagement:** {} views, {} likes".format(youtube_item.engagement.views or '?', youtube_item.engagement.likes or '?'))

            if youtube_item.description:
                output_lines.append("")
                output_lines.append("> {}".format(youtube_item.description))

            output_lines.append("")
            item_index += 1

    # LinkedIn detailed section
    if research_report.linkedin:
        output_lines.append("## LinkedIn Posts")
        output_lines.append("")
        item_index = 0
        while item_index < len(research_report.linkedin):
            linkedin_item = research_report.linkedin[item_index]
            author_display = linkedin_item.author_name
            if linkedin_item.author_title:
                author_display += " - {}".format(linkedin_item.author_title)
            output_lines.append("### {}: {}".format(linkedin_item.id, author_display))
            output_lines.append("")
            output_lines.append("- **URL:** {}".format(linkedin_item.url))
            output_lines.append("- **Date:** {} (confidence: {})".format(linkedin_item.date or 'Unknown', linkedin_item.date_confidence))
            output_lines.append("- **Score:** {}/100".format(linkedin_item.score))
            output_lines.append("- **Relevance:** {}".format(linkedin_item.why_relevant))

            if linkedin_item.engagement:
                output_lines.append("- **Engagement:** {} reactions, {} comments".format(linkedin_item.engagement.reactions or '?', linkedin_item.engagement.comments or '?'))

            output_lines.append("")
            output_lines.append("> {}".format(linkedin_item.text))
            output_lines.append("")
            item_index += 1

    # Web detailed section
    if research_report.web:
        output_lines.append("## Web Results")
        output_lines.append("")
        item_index = 0
        while item_index < len(research_report.web):
            web_item = research_report.web[item_index]
            output_lines.append("### {}: {}".format(web_item.id, web_item.title))
            output_lines.append("")
            output_lines.append("- **Source:** {}".format(web_item.source_domain))
            output_lines.append("- **URL:** {}".format(web_item.url))
            output_lines.append("- **Date:** {} (confidence: {})".format(web_item.date or 'Unknown', web_item.date_confidence))
            output_lines.append("- **Score:** {}/100".format(web_item.score))
            output_lines.append("- **Relevance:** {}".format(web_item.why_relevant))
            output_lines.append("")
            output_lines.append("> {}".format(web_item.snippet))
            output_lines.append("")
            item_index += 1

    # Placeholder sections
    output_lines.append("## Best Practices")
    output_lines.append("")
    output_lines.append("*To be synthesized by Claude*")
    output_lines.append("")

    output_lines.append("## Prompt Pack")
    output_lines.append("")
    output_lines.append("*To be synthesized by Claude*")
    output_lines.append("")

    return "\n".join(output_lines)


# Preserve the original function name for API compatibility
render_full_report = generate_comprehensive_report


def persist_all_artifacts(
    research_report: schema.Report,
    raw_openai_response: Optional[dict] = None,
    raw_xai_response: Optional[dict] = None,
    raw_enriched_reddit: Optional[list] = None,
    raw_youtube_response: Optional[dict] = None,
    raw_linkedin_response: Optional[dict] = None,
):
    """
    Writes all output artifacts to the file system.

    Args:
        research_report: The report data structure
        raw_openai_response: Unprocessed OpenAI API response for Reddit
        raw_xai_response: Unprocessed xAI API response for X
        raw_enriched_reddit: Enriched Reddit thread data
        raw_youtube_response: Unprocessed OpenAI API response for YouTube
        raw_linkedin_response: Unprocessed OpenAI API response for LinkedIn
    """
    initialize_output_directory()

    # Write structured JSON report
    file_handle = open(ARTIFACT_DIRECTORY / "report.json", 'w', encoding="utf-8")
    json.dump(research_report.to_dict(), file_handle, indent=2, ensure_ascii=False)
    file_handle.close()

    # Write markdown report
    file_handle = open(ARTIFACT_DIRECTORY / "report.md", 'w', encoding="utf-8")
    file_handle.write(generate_comprehensive_report(research_report))
    file_handle.close()

    # Write context fragment
    file_handle = open(ARTIFACT_DIRECTORY / "briefbot.context.md", 'w', encoding="utf-8")
    file_handle.write(generate_context_fragment(research_report))
    file_handle.close()

    # Write raw API responses if available
    if raw_openai_response:
        file_handle = open(ARTIFACT_DIRECTORY / "raw_openai.json", 'w', encoding="utf-8")
        json.dump(raw_openai_response, file_handle, indent=2, ensure_ascii=False)
        file_handle.close()

    if raw_xai_response:
        file_handle = open(ARTIFACT_DIRECTORY / "raw_xai.json", 'w', encoding="utf-8")
        json.dump(raw_xai_response, file_handle, indent=2, ensure_ascii=False)
        file_handle.close()

    if raw_enriched_reddit:
        file_handle = open(ARTIFACT_DIRECTORY / "raw_reddit_threads_enriched.json", 'w', encoding="utf-8")
        json.dump(raw_enriched_reddit, file_handle, indent=2, ensure_ascii=False)
        file_handle.close()

    if raw_youtube_response:
        file_handle = open(ARTIFACT_DIRECTORY / "raw_youtube.json", 'w', encoding="utf-8")
        json.dump(raw_youtube_response, file_handle, indent=2, ensure_ascii=False)
        file_handle.close()

    if raw_linkedin_response:
        file_handle = open(ARTIFACT_DIRECTORY / "raw_linkedin.json", 'w', encoding="utf-8")
        json.dump(raw_linkedin_response, file_handle, indent=2, ensure_ascii=False)
        file_handle.close()


# Preserve the original function name for API compatibility
write_outputs = persist_all_artifacts


def retrieve_context_filepath() -> str:
    """Returns the filesystem path to the context fragment file."""
    return str(ARTIFACT_DIRECTORY / "briefbot.context.md")


# Preserve the original function name for API compatibility
get_context_path = retrieve_context_filepath
