#!/usr/bin/env python3
#
# BriefBot Module: Multi-platform content aggregation engine
# Retrieves and consolidates recent discussions from Reddit, X, YouTube, and LinkedIn
#
# Invocation pattern:
#     python briefbot.py <subject_matter> [flags]
#
# Supported flags:
#     --mock              Substitute fixture data for live API responses
#     --emit=MODE         Select output format: compact|json|md|context|path (compact is default)
#     --sources=MODE      Platform filter: auto|reddit|x|youtube|linkedin|both|all (auto is default)
#     --quick             Streamlined mode - reduced result set (8-12 per platform)
#     --deep              Exhaustive mode - expanded result set (50-70 Reddit, 40-60 X)
#     --debug             Activate detailed diagnostic output
#     --audio             Generate MP3 audio of the research output
#

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Fix Windows console encoding (cp1252 cannot handle emoji/box-drawing chars)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure library modules are discoverable
MODULE_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MODULE_ROOT))

from lib import (
    cron_parse,
    dates,
    dedupe,
    email_sender,
    env,
    http,
    jobs,
    models,
    normalize,
    openai_linkedin,
    openai_reddit,
    openai_youtube,
    reddit_enrich,
    render,
    scheduler,
    schema,
    score,
    ui,
    websearch,
    xai_x,
)


def retrieve_fixture_data(fixture_identifier: str) -> dict:
    """
    Fetches mock data from the fixtures directory.

    This helper enables testing without live API calls by loading
    pre-recorded response samples from disk.
    """
    fixture_location = MODULE_ROOT.parent / "fixtures" / fixture_identifier

    if not fixture_location.exists():
        return {}

    with open(fixture_location) as file_handle:
        return json.load(file_handle)


def _execute_reddit_query(
    subject_matter: str,
    configuration: dict,
    model_selection: dict,
    start_date: str,
    end_date: str,
    thoroughness: str,
    use_mock_data: bool,
) -> tuple:
    """
    Queries Reddit content via the OpenAI web search API.

    Designed to execute within a thread pool for concurrent operation.

    Returns a three-element tuple containing:
        - List of Reddit discussion items
        - Raw API response payload
        - Error message (None if successful)
    """
    api_response = None
    failure_message = None

    if use_mock_data:
        api_response = retrieve_fixture_data("openai_sample.json")
    else:
        try:
            api_response = openai_reddit.search_reddit(
                configuration["OPENAI_API_KEY"],
                model_selection["openai"],
                subject_matter,
                start_date,
                end_date,
                depth=thoroughness,
            )
        except http.HTTPError as network_err:
            api_response = {"error": str(network_err)}
            failure_message = "API error: {}".format(network_err)
        except Exception as generic_err:
            api_response = {"error": str(generic_err)}
            failure_message = "{}: {}".format(type(generic_err).__name__, generic_err)

    # Transform raw response into structured items
    discussion_items = openai_reddit.parse_reddit_response(api_response or {})

    # Sparse results trigger automatic retry with simplified query
    has_few_results = len(discussion_items) < 5
    should_retry = has_few_results and not use_mock_data and failure_message is None

    if should_retry:
        simplified_subject = openai_reddit._extract_core_subject(subject_matter)
        subjects_differ = simplified_subject.lower() != subject_matter.lower()

        if subjects_differ:
            try:
                supplemental_response = openai_reddit.search_reddit(
                    configuration["OPENAI_API_KEY"],
                    model_selection["openai"],
                    simplified_subject,
                    start_date,
                    end_date,
                    depth=thoroughness,
                )
                supplemental_items = openai_reddit.parse_reddit_response(supplemental_response)

                # Merge unique items based on URL
                known_urls = {entry.get("url") for entry in discussion_items}

                for supplemental_entry in supplemental_items:
                    url_is_new = supplemental_entry.get("url") not in known_urls
                    if url_is_new:
                        discussion_items.append(supplemental_entry)
            except Exception:
                pass  # Retry failure is non-critical

    return discussion_items, api_response, failure_message


def _execute_x_query(
    subject_matter: str,
    configuration: dict,
    model_selection: dict,
    start_date: str,
    end_date: str,
    thoroughness: str,
    use_mock_data: bool,
) -> tuple:
    """
    Queries X/Twitter content via the xAI API.

    Designed to execute within a thread pool for concurrent operation.

    Returns a three-element tuple containing:
        - List of X post items
        - Raw API response payload
        - Error message (None if successful)
    """
    api_response = None
    failure_message = None

    if use_mock_data:
        api_response = retrieve_fixture_data("xai_sample.json")
    else:
        try:
            api_response = xai_x.search_x(
                configuration["XAI_API_KEY"],
                model_selection["xai"],
                subject_matter,
                start_date,
                end_date,
                depth=thoroughness,
            )
        except http.HTTPError as network_err:
            api_response = {"error": str(network_err)}
            failure_message = "API error: {}".format(network_err)
        except Exception as generic_err:
            api_response = {"error": str(generic_err)}
            failure_message = "{}: {}".format(type(generic_err).__name__, generic_err)

    # Transform raw response into structured items
    post_items = xai_x.parse_x_response(api_response or {})

    return post_items, api_response, failure_message


def _execute_youtube_query(
    subject_matter: str,
    configuration: dict,
    model_selection: dict,
    start_date: str,
    end_date: str,
    thoroughness: str,
    use_mock_data: bool,
) -> tuple:
    """
    Queries YouTube content via the OpenAI web search API.

    Designed to execute within a thread pool for concurrent operation.

    Returns a three-element tuple containing:
        - List of YouTube video items
        - Raw API response payload
        - Error message (None if successful)
    """
    api_response = None
    failure_message = None

    if use_mock_data:
        api_response = retrieve_fixture_data("youtube_sample.json")
    else:
        try:
            api_response = openai_youtube.search_youtube(
                configuration["OPENAI_API_KEY"],
                model_selection["openai"],
                subject_matter,
                start_date,
                end_date,
                depth=thoroughness,
            )
        except http.HTTPError as network_err:
            api_response = {"error": str(network_err)}
            failure_message = "API error: {}".format(network_err)
        except Exception as generic_err:
            api_response = {"error": str(generic_err)}
            failure_message = "{}: {}".format(type(generic_err).__name__, generic_err)

    # Transform raw response into structured items
    video_items = openai_youtube.parse_youtube_response(api_response or {})

    return video_items, api_response, failure_message


def _execute_linkedin_query(
    subject_matter: str,
    configuration: dict,
    model_selection: dict,
    start_date: str,
    end_date: str,
    thoroughness: str,
    use_mock_data: bool,
) -> tuple:
    """
    Queries LinkedIn content via the OpenAI web search API.

    Designed to execute within a thread pool for concurrent operation.

    Returns a three-element tuple containing:
        - List of LinkedIn post items
        - Raw API response payload
        - Error message (None if successful)
    """
    api_response = None
    failure_message = None

    if use_mock_data:
        api_response = retrieve_fixture_data("linkedin_sample.json")
    else:
        try:
            api_response = openai_linkedin.search_linkedin(
                configuration["OPENAI_API_KEY"],
                model_selection["openai"],
                subject_matter,
                start_date,
                end_date,
                depth=thoroughness,
            )
        except http.HTTPError as network_err:
            api_response = {"error": str(network_err)}
            failure_message = "API error: {}".format(network_err)
        except Exception as generic_err:
            api_response = {"error": str(generic_err)}
            failure_message = "{}: {}".format(type(generic_err).__name__, generic_err)

    # Transform raw response into structured items
    article_items = openai_linkedin.parse_linkedin_response(api_response or {})

    return article_items, api_response, failure_message


def orchestrate_research(
    subject_matter: str,
    platform_selection: str,
    configuration: dict,
    model_selection: dict,
    start_date: str,
    end_date: str,
    thoroughness: str = "default",
    use_mock_data: bool = False,
    status_tracker: ui.ProgressDisplay = None,
) -> tuple:
    """
    Orchestrates the complete research pipeline across all platforms.

    This function coordinates parallel API queries, collects results,
    enriches Reddit data with thread content, and handles errors gracefully.

    Returns a 14-element tuple containing:
        - reddit_items: Processed Reddit discussions
        - x_items: Processed X/Twitter posts
        - youtube_items: Processed YouTube videos
        - linkedin_items: Processed LinkedIn articles
        - requires_web_search: Boolean indicating if Claude should do WebSearch
        - raw_openai: Raw Reddit API response
        - raw_xai: Raw X API response
        - raw_youtube: Raw YouTube API response
        - raw_linkedin: Raw LinkedIn API response
        - raw_reddit_enriched: Enriched Reddit thread data
        - reddit_error: Reddit search error message
        - x_error: X search error message
        - youtube_error: YouTube search error message
        - linkedin_error: LinkedIn search error message
    """
    # Initialize all result containers
    reddit_items = []
    x_items = []
    youtube_items = []
    linkedin_items = []
    raw_openai = None
    raw_xai = None
    raw_youtube = None
    raw_linkedin = None
    raw_reddit_enriched = []
    reddit_error = None
    x_error = None
    youtube_error = None
    linkedin_error = None

    # Determine if supplemental web search is warranted
    web_search_modes = ("all", "web", "reddit-web", "x-web")
    requires_web_search = platform_selection in web_search_modes

    # Web-only mode bypasses all API calls - Claude handles everything
    if platform_selection == "web":
        if status_tracker is not None:
            status_tracker.start_web_only()
            status_tracker.end_web_only()

        return (
            reddit_items, x_items, youtube_items, linkedin_items, True,
            raw_openai, raw_xai, raw_youtube, raw_linkedin, raw_reddit_enriched,
            reddit_error, x_error, youtube_error, linkedin_error
        )

    # Determine API availability based on configured keys
    openai_available = bool(configuration.get("OPENAI_API_KEY"))
    xai_available = bool(configuration.get("XAI_API_KEY"))

    # Compute which platform searches should execute
    reddit_platforms = ("both", "reddit", "all", "reddit-web")
    x_platforms = ("both", "x", "all", "x-web")
    youtube_platforms = ("all", "youtube")
    linkedin_platforms = ("all", "linkedin")

    should_query_reddit = platform_selection in reddit_platforms and openai_available
    should_query_x = platform_selection in x_platforms and xai_available
    should_query_youtube = platform_selection in youtube_platforms and openai_available
    should_query_linkedin = platform_selection in linkedin_platforms and openai_available

    # Prepare future handles for concurrent execution
    reddit_future = None
    x_future = None
    youtube_future = None
    linkedin_future = None

    # Execute all platform queries concurrently via thread pool
    with ThreadPoolExecutor(max_workers=4) as thread_pool:
        # Dispatch Reddit query
        if should_query_reddit:
            if status_tracker is not None:
                status_tracker.start_reddit()

            reddit_future = thread_pool.submit(
                _execute_reddit_query, subject_matter, configuration, model_selection,
                start_date, end_date, thoroughness, use_mock_data
            )

        # Dispatch X query
        if should_query_x:
            if status_tracker is not None:
                status_tracker.start_x()

            x_future = thread_pool.submit(
                _execute_x_query, subject_matter, configuration, model_selection,
                start_date, end_date, thoroughness, use_mock_data
            )

        # Dispatch YouTube query
        if should_query_youtube:
            youtube_future = thread_pool.submit(
                _execute_youtube_query, subject_matter, configuration, model_selection,
                start_date, end_date, thoroughness, use_mock_data
            )

        # Dispatch LinkedIn query
        if should_query_linkedin:
            linkedin_future = thread_pool.submit(
                _execute_linkedin_query, subject_matter, configuration, model_selection,
                start_date, end_date, thoroughness, use_mock_data
            )

        # Harvest Reddit results
        if reddit_future is not None:
            try:
                reddit_items, raw_openai, reddit_error = reddit_future.result()

                if reddit_error is not None and status_tracker is not None:
                    status_tracker.show_error("Reddit error: {}".format(reddit_error))
            except Exception as exc:
                reddit_error = "{}: {}".format(type(exc).__name__, exc)

                if status_tracker is not None:
                    status_tracker.show_error("Reddit error: {}".format(exc))

            if status_tracker is not None:
                status_tracker.end_reddit(len(reddit_items))

        # Harvest X results
        if x_future is not None:
            try:
                x_items, raw_xai, x_error = x_future.result()

                if x_error is not None and status_tracker is not None:
                    status_tracker.show_error("X error: {}".format(x_error))
            except Exception as exc:
                x_error = "{}: {}".format(type(exc).__name__, exc)

                if status_tracker is not None:
                    status_tracker.show_error("X error: {}".format(exc))

            if status_tracker is not None:
                status_tracker.end_x(len(x_items))

        # Harvest YouTube results
        if youtube_future is not None:
            try:
                youtube_items, raw_youtube, youtube_error = youtube_future.result()

                if youtube_error is not None and status_tracker is not None:
                    status_tracker.show_error("YouTube error: {}".format(youtube_error))
            except Exception as exc:
                youtube_error = "{}: {}".format(type(exc).__name__, exc)

                if status_tracker is not None:
                    status_tracker.show_error("YouTube error: {}".format(exc))

        # Harvest LinkedIn results
        if linkedin_future is not None:
            try:
                linkedin_items, raw_linkedin, linkedin_error = linkedin_future.result()

                if linkedin_error is not None and status_tracker is not None:
                    status_tracker.show_error("LinkedIn error: {}".format(linkedin_error))
            except Exception as exc:
                linkedin_error = "{}: {}".format(type(exc).__name__, exc)

                if status_tracker is not None:
                    status_tracker.show_error("LinkedIn error: {}".format(exc))

    # Augment Reddit items with full thread content
    # This runs sequentially since each item requires individual API call
    if len(reddit_items) > 0:
        if status_tracker is not None:
            status_tracker.start_reddit_enrich(1, len(reddit_items))

        item_index = 0
        while item_index < len(reddit_items):
            current_item = reddit_items[item_index]

            if status_tracker is not None and item_index > 0:
                status_tracker.update_reddit_enrich(item_index + 1, len(reddit_items))

            try:
                if use_mock_data:
                    mock_thread_data = retrieve_fixture_data("reddit_thread_sample.json")
                    reddit_items[item_index] = reddit_enrich.enrich_reddit_item(
                        current_item, mock_thread_data
                    )
                else:
                    reddit_items[item_index] = reddit_enrich.enrich_reddit_item(current_item)
            except Exception as enrichment_err:
                # Enrichment failure is non-fatal - preserve original item
                if status_tracker is not None:
                    item_url = current_item.get("url", "unknown")
                    status_tracker.show_error(
                        "Enrich failed for {}: {}".format(item_url, enrichment_err)
                    )

            raw_reddit_enriched.append(reddit_items[item_index])
            item_index += 1

        if status_tracker is not None:
            status_tracker.end_reddit_enrich()

    return (
        reddit_items, x_items, youtube_items, linkedin_items, requires_web_search,
        raw_openai, raw_xai, raw_youtube, raw_linkedin, raw_reddit_enriched,
        reddit_error, x_error, youtube_error, linkedin_error
    )


def bootstrap():
    """
    Entry point for command-line execution.

    Parses arguments, validates configuration, runs the research pipeline,
    processes results through normalization/scoring/deduplication, and
    outputs the final report in the requested format.
    """
    argument_parser = argparse.ArgumentParser(
        description="Research a topic from the last N days on Reddit + X + YouTube + LinkedIn"
    )

    argument_parser.add_argument(
        "topic",
        nargs="?",
        help="Topic to research"
    )
    argument_parser.add_argument(
        "--mock",
        action="store_true",
        help="Use fixtures"
    )
    argument_parser.add_argument(
        "--emit",
        choices=["compact", "json", "md", "context", "path"],
        default="compact",
        help="Output mode",
    )
    argument_parser.add_argument(
        "--sources",
        choices=["auto", "reddit", "x", "youtube", "linkedin", "both", "all"],
        default="auto",
        help="Source selection (auto, reddit, x, youtube, linkedin, both=reddit+x, all=all sources)",
    )
    argument_parser.add_argument(
        "--quick",
        action="store_true",
        help="Faster research with fewer sources (8-12 each)",
    )
    argument_parser.add_argument(
        "--deep",
        action="store_true",
        help="Comprehensive research with more sources (50-70 Reddit, 40-60 X)",
    )
    argument_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    argument_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to search back (default: 30, e.g., 7 for a week, 1 for today)",
    )
    argument_parser.add_argument(
        "--include-web",
        action="store_true",
        help="Include general web search alongside Reddit/X (lower weighted)",
    )
    argument_parser.add_argument(
        "--audio",
        action="store_true",
        help="Generate MP3 audio of the research output (uses edge-tts or ElevenLabs)",
    )
    argument_parser.add_argument(
        "--schedule",
        type=str,
        metavar="CRON",
        help='Create a scheduled job with a cron expression (e.g., "0 6 * * *" for daily at 6am)',
    )
    argument_parser.add_argument(
        "--email",
        type=str,
        metavar="ADDRESS",
        help="Email the report to this address (comma-separated for multiple recipients)",
    )
    argument_parser.add_argument(
        "--list-jobs",
        action="store_true",
        help="List all registered scheduled jobs",
    )
    argument_parser.add_argument(
        "--delete-job",
        type=str,
        metavar="JOB_ID",
        help="Delete a scheduled job by ID (e.g., cu_ABC123)",
    )
    argument_parser.add_argument(
        "--skip-immediate-run",
        action="store_true",
        help="With --schedule: only create the job, don't run research now",
    )

    cli_args = argument_parser.parse_args()

    # Handle scheduling commands (exit early, no research)
    if cli_args.list_jobs:
        _handle_list_jobs()
        return

    if cli_args.delete_job:
        _handle_delete_job(cli_args.delete_job)
        return

    if cli_args.schedule:
        _handle_create_schedule(cli_args)
        return

    # Activate diagnostic output when requested
    if cli_args.debug:
        os.environ["LAST30DAYS_DEBUG"] = "1"
        # Force http module to recognize debug flag
        from lib import http as http_module
        http_module.DEBUG = True

    # Resolve thoroughness level (mutually exclusive options)
    if cli_args.quick and cli_args.deep:
        print("Error: Cannot use both --quick and --deep", file=sys.stderr)
        sys.exit(1)

    thoroughness = "default"
    if cli_args.quick:
        thoroughness = "quick"
    elif cli_args.deep:
        thoroughness = "deep"

    # Validate topic was provided
    if cli_args.topic is None:
        print("Error: Please provide a topic to research.", file=sys.stderr)
        print("Usage: python3 last30days.py <topic> [options]", file=sys.stderr)
        sys.exit(1)

    # Retrieve API configuration
    configuration = env.get_config()

    # Determine which platforms have valid credentials
    available_platforms = env.get_available_sources(configuration)

    # Mock mode operates without API keys
    if cli_args.mock:
        platform_selection = "both" if cli_args.sources == "auto" else cli_args.sources
    else:
        # Validate requested sources against available credentials
        platform_selection, validation_error = env.validate_sources(
            cli_args.sources, available_platforms, cli_args.include_web
        )

        if validation_error is not None:
            # WebSearch fallback is advisory, not fatal
            if "WebSearch fallback" in validation_error:
                print("Note: {}".format(validation_error), file=sys.stderr)
            else:
                print("Error: {}".format(validation_error), file=sys.stderr)
                sys.exit(1)

    # Compute the date window based on --days argument
    day_count = cli_args.days
    start_date, end_date = dates.get_date_range(day_count)

    # Identify missing API keys for promotional messaging
    absent_credentials = env.get_missing_keys(configuration)

    # Initialize the progress display subsystem
    status_tracker = ui.ProgressDisplay(cli_args.topic, display_header=True)

    # Display promotional content for missing credentials before research begins
    if absent_credentials != "none":
        status_tracker.show_promo(absent_credentials)

    # Select appropriate models based on API availability
    if cli_args.mock:
        # Substitute mock model listings
        mock_openai_models = retrieve_fixture_data("models_openai_sample.json").get("data", [])
        mock_xai_models = retrieve_fixture_data("models_xai_sample.json").get("data", [])

        model_selection = models.get_models(
            {
                "OPENAI_API_KEY": "mock",
                "XAI_API_KEY": "mock",
                **configuration,
            },
            mock_openai_models,
            mock_xai_models,
        )
    else:
        model_selection = models.get_models(configuration)

    # Translate platform selection to display mode
    mode_mapping = {
        "all": "all",
        "both": "both",
        "reddit": "reddit-only",
        "reddit-web": "reddit-web",
        "x": "x-only",
        "x-web": "x-web",
        "youtube": "youtube-only",
        "linkedin": "linkedin-only",
        "web": "web-only",
    }
    display_mode = mode_mapping.get(platform_selection, platform_selection)

    # Execute the research pipeline
    (
        reddit_items, x_items, youtube_items, linkedin_items, requires_web_search,
        raw_openai, raw_xai, raw_youtube, raw_linkedin, raw_reddit_enriched,
        reddit_error, x_error, youtube_error, linkedin_error
    ) = orchestrate_research(
        cli_args.topic,
        platform_selection,
        configuration,
        model_selection,
        start_date,
        end_date,
        thoroughness,
        cli_args.mock,
        status_tracker,
    )

    # Begin post-processing phase
    status_tracker.start_processing()

    # Standardize item formats across platforms
    normalized_reddit = normalize.normalize_reddit_items(reddit_items, start_date, end_date)
    normalized_x = normalize.normalize_x_items(x_items, start_date, end_date)
    normalized_youtube = normalize.normalize_youtube_items(youtube_items, start_date, end_date)
    normalized_linkedin = normalize.normalize_linkedin_items(linkedin_items, start_date, end_date)

    # Apply strict date filtering as final validation layer
    # This ensures no content outside the window survives regardless of API behavior
    filtered_reddit = normalize.filter_by_date_range(normalized_reddit, start_date, end_date)
    filtered_x = normalize.filter_by_date_range(normalized_x, start_date, end_date)
    filtered_youtube = normalize.filter_by_date_range(normalized_youtube, start_date, end_date)
    filtered_linkedin = normalize.filter_by_date_range(normalized_linkedin, start_date, end_date)

    # Compute relevance scores for ranking
    scored_reddit = score.score_reddit_items(filtered_reddit)
    scored_x = score.score_x_items(filtered_x)
    scored_youtube = score.score_youtube_items(filtered_youtube)
    scored_linkedin = score.score_linkedin_items(filtered_linkedin)

    # Order items by computed score
    sorted_reddit = score.sort_items(scored_reddit)
    sorted_x = score.sort_items(scored_x)
    sorted_youtube = score.sort_items(scored_youtube)
    sorted_linkedin = score.sort_items(scored_linkedin)

    # Remove duplicate entries
    deduped_reddit = dedupe.dedupe_reddit(sorted_reddit)
    deduped_x = dedupe.dedupe_x(sorted_x)
    deduped_youtube = dedupe.dedupe_youtube(sorted_youtube)
    deduped_linkedin = dedupe.dedupe_linkedin(sorted_linkedin)

    status_tracker.end_processing()

    # Assemble the final report structure
    report = schema.create_report(
        cli_args.topic,
        start_date,
        end_date,
        display_mode,
        model_selection.get("openai"),
        model_selection.get("xai"),
    )
    report.reddit = deduped_reddit
    report.x = deduped_x
    report.youtube = deduped_youtube
    report.linkedin = deduped_linkedin
    report.reddit_error = reddit_error
    report.x_error = x_error
    report.youtube_error = youtube_error
    report.linkedin_error = linkedin_error

    # Generate the condensed context snippet
    report.context_snippet_md = render.render_context_snippet(report)

    # Persist all output artifacts
    render.write_outputs(
        report, raw_openai, raw_xai, raw_reddit_enriched, raw_youtube, raw_linkedin
    )

    # Display completion status
    if platform_selection == "web":
        status_tracker.show_web_only_complete()
    else:
        status_tracker.show_complete(
            len(deduped_reddit), len(deduped_x),
            len(deduped_youtube), len(deduped_linkedin)
        )

    # Emit final result in requested format
    emit_research_output(
        report, cli_args.emit, requires_web_search,
        cli_args.topic, start_date, end_date, absent_credentials, day_count
    )


def _handle_list_jobs():
    """Displays all registered scheduled jobs."""
    all_jobs = jobs.list_jobs()

    if not all_jobs:
        print("No scheduled jobs registered.")
        print("Create one with: python briefbot.py \"topic\" --schedule \"0 6 * * *\" --email you@example.com")
        return

    print("Scheduled jobs ({}):\n".format(len(all_jobs)))

    for job in all_jobs:
        try:
            parsed = cron_parse.parse_cron_expression(job["schedule"])
            schedule_desc = cron_parse.describe_schedule(parsed)
        except ValueError:
            schedule_desc = job["schedule"]

        status_indicator = "OK" if job.get("last_status") == "success" else (
            "ERR" if job.get("last_status") == "error" else "NEW"
        )

        print("  {} [{}]".format(job["id"], status_indicator))
        print("    Topic:    {}".format(job["topic"]))
        print("    Schedule: {} ({})".format(job["schedule"], schedule_desc))
        if job.get("email"):
            print("    Email:    {}".format(job["email"]))
        if job.get("args", {}).get("audio"):
            print("    Audio:    enabled")
        print("    Runs:     {}".format(job.get("run_count", 0)))
        if job.get("last_run"):
            print("    Last run: {} ({})".format(job["last_run"], job.get("last_status", "unknown")))
        if job.get("last_error"):
            print("    Error:    {}".format(job["last_error"]))
        print()


def _handle_delete_job(job_id: str):
    """Removes a scheduled job from both the OS scheduler and the registry."""
    job = jobs.get_job(job_id)

    if job is None:
        print("Error: Job {} not found.".format(job_id), file=sys.stderr)
        sys.exit(1)

    # Remove from OS scheduler
    try:
        scheduler_msg = scheduler.unregister_job(job)
        print(scheduler_msg)
    except RuntimeError as err:
        print("Warning: Could not remove from OS scheduler: {}".format(err), file=sys.stderr)

    # Remove from registry
    deleted = jobs.delete_job(job_id)
    if deleted:
        print("Job {} deleted from registry.".format(job_id))
    else:
        print("Warning: Job {} was not in registry.".format(job_id), file=sys.stderr)


def _handle_create_schedule(cli_args):
    """Creates a new scheduled job from CLI arguments."""
    # Validate required arguments
    if not cli_args.topic:
        print("Error: Topic is required when creating a schedule.", file=sys.stderr)
        print("Usage: python briefbot.py \"topic\" --schedule \"0 6 * * *\" --email you@example.com", file=sys.stderr)
        sys.exit(1)

    # Validate cron expression
    try:
        parsed = cron_parse.parse_cron_expression(cli_args.schedule)
        schedule_desc = cron_parse.describe_schedule(parsed)
    except ValueError as err:
        print("Error: Invalid schedule: {}".format(err), file=sys.stderr)
        sys.exit(1)

    # Validate SMTP configuration only when email is requested
    if cli_args.email:
        configuration = env.get_config()
        smtp_error = email_sender.validate_smtp_config(configuration)
        if smtp_error:
            print("Error: {}".format(smtp_error), file=sys.stderr)
            sys.exit(1)

    if not cli_args.email and not cli_args.audio:
        print("Warning: No --email or --audio specified. The job will run research but produce no output.", file=sys.stderr)
        print("Consider adding --audio and/or --email.", file=sys.stderr)

    # Capture current CLI arguments into the job record
    args_dict = {
        "quick": cli_args.quick,
        "deep": cli_args.deep,
        "audio": cli_args.audio,
        "days": cli_args.days,
        "sources": cli_args.sources,
        "include_web": cli_args.include_web,
    }

    # Create the job
    job = jobs.create_job(
        topic=cli_args.topic,
        schedule=cli_args.schedule,
        email=cli_args.email or "",
        args_dict=args_dict,
    )

    print("Created scheduled job: {}".format(job["id"]))
    print("  Topic:    {}".format(job["topic"]))
    print("  Schedule: {} ({})".format(job["schedule"], schedule_desc))
    if job["email"]:
        print("  Email:    {}".format(job["email"]))
    if cli_args.audio:
        print("  Audio:    enabled")

    # Register with OS scheduler
    runner_path = MODULE_ROOT / "run_job.py"
    try:
        scheduler_msg = scheduler.register_job(job, runner_path)
        print("  {}".format(scheduler_msg))
    except RuntimeError as err:
        print("\nWarning: Could not register with OS scheduler: {}".format(err), file=sys.stderr)
        print("You can manually run: python {} {}".format(runner_path, job["id"]), file=sys.stderr)

    # Show next occurrence
    try:
        next_fire = cron_parse.next_occurrence(parsed)
        print("\n  Next run: {}".format(next_fire.strftime("%Y-%m-%d %H:%M")))
    except ValueError:
        pass


def emit_research_output(
    report: schema.Report,
    output_format: str,
    requires_web_search: bool = False,
    subject_matter: str = "",
    start_date: str = "",
    end_date: str = "",
    absent_credentials: str = "none",
    day_count: int = 30,
):
    """
    Renders and outputs the research report in the specified format.

    When web search is required, appends instructions for Claude to
    perform supplemental WebSearch queries.
    """
    format_handlers = {
        "compact": lambda: print(render.render_compact(report, absent_credentials=absent_credentials)),
        "json": lambda: print(json.dumps(report.to_dict(), indent=2)),
        "md": lambda: print(render.render_full_report(report)),
        "context": lambda: print(report.context_snippet_md),
        "path": lambda: print(render.get_context_path()),
    }

    handler = format_handlers.get(output_format)
    if handler is not None:
        handler()

    # Append WebSearch instructions when supplemental search is needed
    if requires_web_search:
        separator_line = "=" * 60

        print()
        print(separator_line)
        print("### WEBSEARCH REQUIRED ###")
        print(separator_line)
        print("Topic: {}".format(subject_matter))
        print("Date range: {} to {}".format(start_date, end_date))
        print()
        print("Claude: Use your WebSearch tool to find 8-15 relevant web pages.")
        print("EXCLUDE: reddit.com, x.com, twitter.com (already covered above)")
        print("INCLUDE: blogs, docs, news, tutorials from the last {} days".format(day_count))
        print()
        print("After searching, synthesize WebSearch results WITH the Reddit/X")
        print("results above. WebSearch items should rank LOWER than comparable")
        print("Reddit/X items (they lack engagement metrics).")
        print(separator_line)


if __name__ == "__main__":
    bootstrap()
