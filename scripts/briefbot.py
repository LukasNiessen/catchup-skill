#!/usr/bin/env python3
"""Multi-platform research aggregation engine."""

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

# Set to True to skip Bird X search and force xAI API usage
DISABLE_BIRD = True


def _log(message: str):
    """Emit a debug log line to stderr, gated by BRIEFBOT_DEBUG."""
    if os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write(f"[BRIEFBOT] {message}\n")
        sys.stderr.flush()

# Ensure library modules are discoverable
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from lib import (
    bird_x,
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


def load_fixture(name: str) -> dict:
    """Load mock data from the fixtures directory."""
    path = ROOT.parent / "fixtures" / name

    if not path.exists():
        return {}

    with open(path) as f:
        return json.load(f)


def _query_reddit(
    topic: str,
    config: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Query Reddit via OpenAI web search API. Returns (items, response, error)."""
    response = None
    error = None

    if mock:
        response = load_fixture("openai_sample.json")
    else:
        try:
            response = openai_reddit.search(
                config["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                depth=depth,
            )
        except http.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"API error: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"{type(generic_err).__name__}: {generic_err}"

    # Transform raw response into structured items
    items = openai_reddit.parse_reddit_response(response or {})

    # Sparse results trigger automatic retry with simplified query
    has_few_results = len(items) < 5
    should_retry = has_few_results and not mock and error is None

    if should_retry:
        simplified_topic = openai_reddit._core_subject(topic)
        topics_differ = simplified_topic.lower() != topic.lower()

        if topics_differ:
            try:
                supplemental_response = openai_reddit.search(
                    config["OPENAI_API_KEY"],
                    models_picked["openai"],
                    simplified_topic,
                    start_date,
                    end_date,
                    depth=depth,
                )
                supplemental_items = openai_reddit.parse_reddit_response(
                    supplemental_response
                )

                # Merge unique items based on URL
                known_urls = {entry.get("url") for entry in items}

                for supplemental_entry in supplemental_items:
                    if supplemental_entry.get("url") not in known_urls:
                        items.append(supplemental_entry)
            except Exception:
                pass  # Retry failure is non-critical

    return items, response, error


def _query_x(
    topic: str,
    config: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Query X/Twitter via Bird search (primary) or xAI API (fallback). Returns (items, response, error)."""
    response = None
    error = None

    _log("=== _query_x START ===")
    _log(f"  Subject: '{topic}'")
    _log(f"  Date range: {start_date} to {end_date}")
    _log(f"  Depth: {depth}")
    _log(f"  Mock data: {mock}")

    if mock:
        _log("  Using MOCK data for X search")
        response = load_fixture("xai_sample.json")
        items = xai_x.parse_x_response(response or {})
        _log(f"  Mock returned {len(items)} items")
        return items, response, error

    # Determine which X backend to use: Bird (free) > xAI (paid)
    use_bird = config.get("BIRD_X_AVAILABLE", False)
    has_xai = bool(config.get("XAI_API_KEY"))
    xai_key_preview = ""
    if has_xai:
        xai_key = config["XAI_API_KEY"]
        xai_key_preview = f"{xai_key[:8]}...{xai_key[-4:]} ({len(xai_key)} chars)"

    _log(f"  DISABLE_BIRD: {DISABLE_BIRD}")
    _log(f"  Bird available: {use_bird}")
    _log(f"  xAI key present: {has_xai} {xai_key_preview if has_xai else ''}")
    _log(f"  xAI model: {models_picked.get('xai')}")

    if not DISABLE_BIRD and use_bird:
        # Primary path: Bird search (browser cookies, no API key)
        _log("  PATH: Bird search (primary, free)")
        try:
            response = bird_x.search_x(
                topic,
                start_date,
                end_date,
                depth=depth,
            )
            _log("  Bird API call succeeded")
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"Bird: {type(generic_err).__name__}: {generic_err}"
            _log(f"  Bird API call FAILED: {error}")

        items = bird_x.parse_bird_response(response or {})
        _log(f"  Bird parsed {len(items)} items")

        # If Bird returned 0 results and xAI is available, fall back
        if not items and has_xai and error is None:
            _log("  Bird returned 0 results, falling back to xAI API...")
            try:
                response = xai_x.search(
                    config["XAI_API_KEY"],
                    models_picked["xai"],
                    topic,
                    start_date,
                    end_date,
                    depth=depth,
                )
                items = xai_x.parse_x_response(response or {})
                error = None
                _log(f"  xAI fallback returned {len(items)} items")
            except Exception as fallback_err:
                _log(f"  xAI fallback FAILED: {type(fallback_err).__name__}: {fallback_err}")
                pass  # Keep Bird's (empty) result
    elif has_xai:
        # Fallback path: xAI API (paid)
        _log("  PATH: xAI API (paid, direct)")
        _log(f"  Calling xai_x.search(key={xai_key_preview}, model={models_picked.get('xai')}, topic='{topic[:50]}', dates={start_date}->{end_date}, depth={depth})")
        try:
            response = xai_x.search(
                config["XAI_API_KEY"],
                models_picked["xai"],
                topic,
                start_date,
                end_date,
                depth=depth,
            )
            _log(f"  xAI API call succeeded, response keys: {list(response.keys()) if isinstance(response, dict) else type(response).__name__}")
        except http.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"API error: {network_err}"
            _log(f"  xAI API HTTP ERROR: {network_err} (status={getattr(network_err, 'status_code', '?')}, body={(getattr(network_err, 'body', '') or '')[:300]})")
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"{type(generic_err).__name__}: {generic_err}"
            _log(f"  xAI API EXCEPTION: {error}")

        items = xai_x.parse_x_response(response or {})
        _log(f"  xAI parsed {len(items)} items")
    else:
        # No X backend available
        _log("  PATH: NO X BACKEND AVAILABLE (no xAI key, Bird not authenticated)")
        response = {
            "error": "No X search backend available (no xAI key, Bird not authenticated)"
        }
        error = "No X search backend available"
        items = []

    _log(f"=== _query_x END: {len(items)} items, error={error} ===")
    return items, response, error


def _query_youtube(
    topic: str,
    config: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Query YouTube via OpenAI web search API. Returns (items, response, error)."""
    response = None
    error = None

    if mock:
        response = load_fixture("youtube_sample.json")
    else:
        try:
            response = openai_youtube.search(
                config["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                depth=depth,
            )
        except http.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"API error: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"{type(generic_err).__name__}: {generic_err}"

    # Transform raw response into structured items
    items = openai_youtube.parse_youtube_response(response or {})

    return items, response, error


def _query_linkedin(
    topic: str,
    config: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Query LinkedIn via OpenAI web search API. Returns (items, response, error)."""
    response = None
    error = None

    if mock:
        response = load_fixture("linkedin_sample.json")
    else:
        try:
            response = openai_linkedin.search(
                config["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                depth=depth,
            )
        except http.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"API error: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"{type(generic_err).__name__}: {generic_err}"

    # Transform raw response into structured items
    items = openai_linkedin.parse_linkedin_response(response or {})

    return items, response, error


def run_research(
    topic: str,
    platform: str,
    config: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    depth: str = "default",
    mock: bool = False,
    progress: ui.Progress = None,
) -> tuple:
    """Orchestrate the full research pipeline across all platforms. Returns a 14-element tuple."""
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
    requires_web_search = platform in web_search_modes

    # Web-only mode bypasses all API calls - Claude handles everything
    if platform == "web":
        if progress is not None:
            progress.start_web_only()
            progress.end_web_only()

        return (
            reddit_items,
            x_items,
            youtube_items,
            linkedin_items,
            True,
            raw_openai,
            raw_xai,
            raw_youtube,
            raw_linkedin,
            raw_reddit_enriched,
            reddit_error,
            x_error,
            youtube_error,
            linkedin_error,
        )

    # Determine API availability based on configured keys and Bird
    openai_available = bool(config.get("OPENAI_API_KEY"))
    xai_available = bool(config.get("XAI_API_KEY"))
    bird_available = bool(config.get("BIRD_X_AVAILABLE"))
    x_available = xai_available or bird_available

    _log("=== run_research ===")
    _log(f"  Platform: '{platform}'")
    _log(f"  OpenAI available: {openai_available}")
    _log(f"  xAI available: {xai_available}")
    _log(f"  Bird available: {bird_available}")
    _log(f"  X available (xAI or Bird): {x_available}")
    _log(f"  Depth: {depth}")
    _log(f"  Models picked: {models_picked}")

    # Compute which platform searches should execute
    reddit_platforms = ("both", "reddit", "all", "reddit-web")
    x_platforms = ("both", "x", "all", "x-web")
    youtube_platforms = ("all", "youtube")
    linkedin_platforms = ("all", "linkedin")

    should_query_reddit = platform in reddit_platforms and openai_available
    should_query_x = platform in x_platforms and x_available
    should_query_youtube = platform in youtube_platforms and openai_available
    should_query_linkedin = (
        platform in linkedin_platforms and openai_available
    )

    _log(f"  should_query_reddit: {should_query_reddit} (platform '{platform}' in {reddit_platforms} AND openai={openai_available})")
    _log(f"  should_query_x: {should_query_x} (platform '{platform}' in {x_platforms} AND x={x_available})")
    _log(f"  should_query_youtube: {should_query_youtube}")
    _log(f"  should_query_linkedin: {should_query_linkedin}")

    # Prepare future handles for concurrent execution
    reddit_future = None
    x_future = None
    youtube_future = None
    linkedin_future = None

    # Execute all platform queries concurrently via thread pool
    with ThreadPoolExecutor(max_workers=4) as thread_pool:
        # Dispatch Reddit query
        if should_query_reddit:
            if progress is not None:
                progress.start_reddit()

            reddit_future = thread_pool.submit(
                _query_reddit,
                topic,
                config,
                models_picked,
                start_date,
                end_date,
                depth,
                mock,
            )

        # Dispatch X query
        if should_query_x:
            if progress is not None:
                progress.start_x()

            x_future = thread_pool.submit(
                _query_x,
                topic,
                config,
                models_picked,
                start_date,
                end_date,
                depth,
                mock,
            )

        # Dispatch YouTube query
        if should_query_youtube:
            youtube_future = thread_pool.submit(
                _query_youtube,
                topic,
                config,
                models_picked,
                start_date,
                end_date,
                depth,
                mock,
            )

        # Dispatch LinkedIn query
        if should_query_linkedin:
            linkedin_future = thread_pool.submit(
                _query_linkedin,
                topic,
                config,
                models_picked,
                start_date,
                end_date,
                depth,
                mock,
            )

        # Harvest Reddit results
        if reddit_future is not None:
            try:
                reddit_items, raw_openai, reddit_error = reddit_future.result()

                if reddit_error is not None and progress is not None:
                    progress.show_error(f"Reddit error: {reddit_error}")
            except Exception as exc:
                reddit_error = f"{type(exc).__name__}: {exc}"

                if progress is not None:
                    progress.show_error(f"Reddit error: {exc}")

            if progress is not None:
                progress.end_reddit(len(reddit_items))

        # Harvest X results
        if x_future is not None:
            try:
                x_items, raw_xai, x_error = x_future.result()

                if x_error is not None and progress is not None:
                    progress.show_error(f"X error: {x_error}")
            except Exception as exc:
                x_error = f"{type(exc).__name__}: {exc}"

                if progress is not None:
                    progress.show_error(f"X error: {exc}")

            if progress is not None:
                progress.end_x(len(x_items))

        # Harvest YouTube results
        if youtube_future is not None:
            try:
                youtube_items, raw_youtube, youtube_error = youtube_future.result()

                if youtube_error is not None and progress is not None:
                    progress.show_error(f"YouTube error: {youtube_error}")
            except Exception as exc:
                youtube_error = f"{type(exc).__name__}: {exc}"

                if progress is not None:
                    progress.show_error(f"YouTube error: {exc}")

        # Harvest LinkedIn results
        if linkedin_future is not None:
            try:
                linkedin_items, raw_linkedin, linkedin_error = linkedin_future.result()

                if linkedin_error is not None and progress is not None:
                    progress.show_error(f"LinkedIn error: {linkedin_error}")
            except Exception as exc:
                linkedin_error = f"{type(exc).__name__}: {exc}"

                if progress is not None:
                    progress.show_error(f"LinkedIn error: {exc}")

    _log("=== Query results summary ===")
    _log(f"  Reddit: {len(reddit_items)} items, error={reddit_error}")
    _log(f"  X:      {len(x_items)} items, error={x_error}")
    _log(f"  YouTube: {len(youtube_items)} items, error={youtube_error}")
    _log(f"  LinkedIn: {len(linkedin_items)} items, error={linkedin_error}")

    # Augment Reddit items with full thread content
    # This runs sequentially since each item requires individual API call
    if len(reddit_items) > 0:
        if progress is not None:
            progress.start_reddit_enrich(1, len(reddit_items))

        for i, item in enumerate(reddit_items):
            if progress is not None and i > 0:
                progress.update_reddit_enrich(i + 1, len(reddit_items))

            try:
                if mock:
                    thread_data = load_fixture("reddit_thread_sample.json")
                    reddit_items[i] = reddit_enrich.enrich(item, thread_data)
                else:
                    reddit_items[i] = reddit_enrich.enrich(item)
            except Exception as err:
                if progress is not None:
                    url = item.get("url", "unknown")
                    progress.show_error(f"Enrich failed for {url}: {err}")

            raw_reddit_enriched.append(reddit_items[i])

        if progress is not None:
            progress.end_reddit_enrich()

    return (
        reddit_items,
        x_items,
        youtube_items,
        linkedin_items,
        requires_web_search,
        raw_openai,
        raw_xai,
        raw_youtube,
        raw_linkedin,
        raw_reddit_enriched,
        reddit_error,
        x_error,
        youtube_error,
        linkedin_error,
    )


def main():
    """Entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Research a topic from the last N days on Reddit + X + YouTube + LinkedIn"
    )

    parser.add_argument("topic", nargs="?", help="Topic to research")
    parser.add_argument("--mock", action="store_true", help="Use fixtures")
    parser.add_argument(
        "--emit",
        choices=["compact", "json", "md", "context", "path"],
        default="compact",
        help="Output mode",
    )
    parser.add_argument(
        "--sources",
        choices=["auto", "reddit", "x", "youtube", "linkedin", "both", "all"],
        default="auto",
        help="Source selection (auto, reddit, x, youtube, linkedin, both=reddit+x, all=all sources)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Faster research with fewer sources (8-12 each)",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Comprehensive research with more sources (50-70 Reddit, 40-60 X)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to search back (default: 30, e.g., 7 for a week, 1 for today)",
    )
    parser.add_argument(
        "--include-web",
        action="store_true",
        help="Include general web search alongside Reddit/X (lower weighted)",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help="Generate MP3 audio of the research output (uses edge-tts or ElevenLabs)",
    )
    parser.add_argument(
        "--schedule",
        type=str,
        metavar="CRON",
        help='Create a scheduled job with a cron expression (e.g., "0 6 * * *" for daily at 6am)',
    )
    parser.add_argument(
        "--email",
        type=str,
        metavar="ADDRESS",
        help="Email the report to this address (comma-separated for multiple recipients)",
    )
    parser.add_argument(
        "--telegram",
        type=str,
        nargs="?",
        const="__default__",
        metavar="CHAT_ID",
        help="Send via Telegram (optional CHAT_ID overrides config default)",
    )
    parser.add_argument(
        "--list-jobs",
        action="store_true",
        help="List all registered scheduled jobs",
    )
    parser.add_argument(
        "--delete-job",
        type=str,
        metavar="JOB_ID",
        help="Delete a scheduled job by ID (e.g., cu_ABC123)",
    )
    parser.add_argument(
        "--skip-immediate-run",
        action="store_true",
        help="With --schedule: only create the job, don't run research now",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run the interactive setup wizard to configure API keys and services",
    )

    args = parser.parse_args()

    # Handle setup wizard (exit early)
    if args.setup:
        from setup import run_setup

        run_setup()
        return

    # Handle scheduling commands (exit early, no research)
    if args.list_jobs:
        _list_jobs()
        return

    if args.delete_job:
        _delete_job(args.delete_job)
        return

    if args.schedule:
        _create_schedule(args)
        return

    # Activate diagnostic output when requested
    if args.debug:
        os.environ["BRIEFBOT_DEBUG"] = "1"
        # Force http module to recognize debug flag
        from lib import http as http_module

        http_module.DEBUG = True

    # Resolve depth level (mutually exclusive options)
    if args.quick and args.deep:
        print("Error: Cannot use both --quick and --deep", file=sys.stderr)
        sys.exit(1)

    depth = "default"
    if args.quick:
        depth = "quick"
    elif args.deep:
        depth = "deep"

    # Validate topic was provided
    if args.topic is None:
        print("Error: Please provide a topic to research.", file=sys.stderr)
        print("Usage: python3 briefbot.py <topic> [options]", file=sys.stderr)
        sys.exit(1)

    # Retrieve API configuration
    _log("=== main: Loading configuration ===")
    config = env.load_config()

    # Detect Bird X search availability (browser cookies, free)
    config["BIRD_X_AVAILABLE"] = env.is_bird_x_available()
    _log(f"BIRD_X_AVAILABLE: {config['BIRD_X_AVAILABLE']}")

    # Determine which platforms have valid credentials
    platforms = env.determine_available_platforms(config)
    _log(f"Available platforms: '{platforms}'")

    # Mock mode operates without API keys
    if args.mock:
        platform = "both" if args.sources == "auto" else args.sources
    else:
        # Validate requested sources against available credentials
        platform, src_err = env.validate_sources(
            args.sources, platforms, args.include_web
        )

        _log(f"Source validation: platform='{platform}', error={src_err}")

        if src_err is not None:
            # WebSearch fallback is advisory, not fatal
            if "WebSearch fallback" in src_err:
                print(f"Note: {src_err}", file=sys.stderr)
            else:
                print(f"Error: {src_err}", file=sys.stderr)
                sys.exit(1)

    # Compute the date window based on --days argument
    days = args.days
    start_date, end_date = dates.date_window(days)

    # Identify missing API keys for promotional messaging
    missing_keys = env.identify_missing_credentials(config)

    # Initialize the progress display subsystem
    progress = ui.Progress(args.topic, display_header=True)

    # Display promotional content for missing credentials before research begins
    if missing_keys != "none":
        progress.show_promo(missing_keys)

    # Select appropriate models based on API availability
    if args.mock:
        # Substitute mock model listings
        mock_openai_models = load_fixture("models_openai_sample.json").get(
            "data", []
        )
        mock_xai_models = load_fixture("models_xai_sample.json").get(
            "data", []
        )

        models_picked = models.get_models(
            {
                "OPENAI_API_KEY": "mock",
                "XAI_API_KEY": "mock",
                **config,
            },
            mock_openai_models,
            mock_xai_models,
        )
    else:
        models_picked = models.get_models(config)

    _log(f"Models picked: openai={models_picked.get('openai')}, xai={models_picked.get('xai')}")

    # Translate platform to display mode
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
    display_mode = mode_mapping.get(platform, platform)

    # Execute the research pipeline
    (
        reddit_items,
        x_items,
        youtube_items,
        linkedin_items,
        requires_web_search,
        raw_openai,
        raw_xai,
        raw_youtube,
        raw_linkedin,
        raw_reddit_enriched,
        reddit_error,
        x_error,
        youtube_error,
        linkedin_error,
    ) = run_research(
        args.topic,
        platform,
        config,
        models_picked,
        start_date,
        end_date,
        depth,
        args.mock,
        progress,
    )

    # Begin post-processing phase
    progress.start_processing()

    # Standardize item formats across platforms
    normalized_reddit = normalize.to_reddit(
        reddit_items, start_date, end_date
    )
    normalized_x = normalize.to_x(x_items, start_date, end_date)
    normalized_youtube = normalize.to_youtube(
        youtube_items, start_date, end_date
    )
    normalized_linkedin = normalize.to_linkedin(
        linkedin_items, start_date, end_date
    )

    # Apply strict date filtering as final validation layer
    # This ensures no content outside the window survives regardless of API behavior
    filtered_reddit = normalize.filter_dates(
        normalized_reddit, start_date, end_date
    )
    filtered_x = normalize.filter_dates(normalized_x, start_date, end_date)
    filtered_youtube = normalize.filter_dates(
        normalized_youtube, start_date, end_date
    )
    filtered_linkedin = normalize.filter_dates(
        normalized_linkedin, start_date, end_date
    )

    # Compute relevance scores for ranking
    scored_reddit = score.score_reddit(filtered_reddit)
    scored_x = score.score_x(filtered_x)
    scored_youtube = score.score_youtube(filtered_youtube)
    scored_linkedin = score.score_linkedin(filtered_linkedin)

    # Order items by computed score
    sorted_reddit = score.rank(scored_reddit)
    sorted_x = score.rank(scored_x)
    sorted_youtube = score.rank(scored_youtube)
    sorted_linkedin = score.rank(scored_linkedin)

    # Remove duplicate entries
    deduped_reddit = dedupe.dedupe_reddit(sorted_reddit)
    deduped_x = dedupe.dedupe_x(sorted_x)
    deduped_youtube = dedupe.dedupe_youtube(sorted_youtube)
    deduped_linkedin = dedupe.dedupe_linkedin(sorted_linkedin)

    progress.end_processing()

    # Assemble the final report structure
    report = schema.make_report(
        args.topic,
        start_date,
        end_date,
        display_mode,
        models_picked.get("openai"),
        models_picked.get("xai"),
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
    report.context_snippet_md = render.context_fragment(report)

    # Persist all output artifacts
    render.save_artifacts(
        report, raw_openai, raw_xai, raw_reddit_enriched, raw_youtube, raw_linkedin
    )

    # Display completion status
    if platform == "web":
        progress.show_web_only_complete()
    else:
        progress.show_complete(
            len(deduped_reddit),
            len(deduped_x),
            len(deduped_youtube),
            len(deduped_linkedin),
        )

    # Emit final result in requested format
    output_report(
        report,
        args.emit,
        requires_web_search,
        args.topic,
        start_date,
        end_date,
        missing_keys,
        days,
    )


def _list_jobs():
    """Display all registered scheduled jobs."""
    all_jobs = jobs.list_jobs()

    if not all_jobs:
        print("No scheduled jobs registered.")
        print(
            'Create one with: python briefbot.py "topic" --schedule "0 6 * * *" --email you@example.com'
        )
        return

    print(f"Scheduled jobs ({len(all_jobs)}):\n")

    for job in all_jobs:
        try:
            parsed = cron_parse.parse_cron_expression(job["schedule"])
            schedule_desc = cron_parse.describe_schedule(parsed)
        except ValueError:
            schedule_desc = job["schedule"]

        status_indicator = (
            "OK"
            if job.get("last_status") == "success"
            else ("ERR" if job.get("last_status") == "error" else "NEW")
        )

        print(f"  {job['id']} [{status_indicator}]")
        print(f"    Topic:    {job['topic']}")
        print(f"    Schedule: {job['schedule']} ({schedule_desc})")
        if job.get("email"):
            print(f"    Email:    {job['email']}")
        if job.get("args", {}).get("telegram"):
            tg_val = job["args"]["telegram"]
            if tg_val == "__default__":
                print("    Telegram: enabled (default chat)")
            else:
                print(f"    Telegram: chat {tg_val}")
        if job.get("args", {}).get("audio"):
            print("    Audio:    enabled")
        print(f"    Runs:     {job.get('run_count', 0)}")
        if job.get("last_run"):
            print(f"    Last run: {job['last_run']} ({job.get('last_status', 'unknown')})")
        if job.get("last_error"):
            print(f"    Error:    {job['last_error']}")
        print()


def _delete_job(job_id: str):
    """Remove a scheduled job from both the OS scheduler and the registry."""
    job = jobs.get_job(job_id)

    if job is None:
        print(f"Error: Job {job_id} not found.", file=sys.stderr)
        sys.exit(1)

    # Remove from OS scheduler
    try:
        scheduler_msg = scheduler.unregister_job(job)
        print(scheduler_msg)
    except RuntimeError as err:
        print(
            f"Warning: Could not remove from OS scheduler: {err}",
            file=sys.stderr,
        )

    # Remove from registry
    deleted = jobs.delete_job(job_id)
    if deleted:
        print(f"Job {job_id} deleted from registry.")
    else:
        print(f"Warning: Job {job_id} was not in registry.", file=sys.stderr)


def _create_schedule(args):
    """Create a new scheduled job from CLI arguments."""
    # Validate required arguments
    if not args.topic:
        print("Error: Topic is required when creating a schedule.", file=sys.stderr)
        print(
            'Usage: python briefbot.py "topic" --schedule "0 6 * * *" --email you@example.com',
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate cron expression
    try:
        parsed = cron_parse.parse_cron_expression(args.schedule)
        schedule_desc = cron_parse.describe_schedule(parsed)
    except ValueError as err:
        print(f"Error: Invalid schedule: {err}", file=sys.stderr)
        sys.exit(1)

    # Validate SMTP configuration only when email is requested
    if args.email:
        config = env.load_config()
        smtp_error = email_sender.validate_smtp_config(config)
        if smtp_error:
            print(f"Error: {smtp_error}", file=sys.stderr)
            sys.exit(1)

    if not args.email and not args.audio and not args.telegram:
        print(
            "Warning: No --email, --audio, or --telegram specified. The job will run research but produce no output.",
            file=sys.stderr,
        )
        print("Consider adding --audio, --email, and/or --telegram.", file=sys.stderr)

    # Capture current CLI arguments into the job record
    args_dict = {
        "quick": args.quick,
        "deep": args.deep,
        "audio": args.audio,
        "days": args.days,
        "sources": args.sources,
        "include_web": args.include_web,
        "telegram": args.telegram,
    }

    # Create the job
    job = jobs.create_job(
        topic=args.topic,
        schedule=args.schedule,
        email=args.email or "",
        args_dict=args_dict,
    )

    print(f"Created scheduled job: {job['id']}")
    print(f"  Topic:    {job['topic']}")
    print(f"  Schedule: {job['schedule']} ({schedule_desc})")
    if job["email"]:
        print(f"  Email:    {job['email']}")
    if args.telegram:
        if args.telegram == "__default__":
            print("  Telegram: enabled (default chat)")
        else:
            print(f"  Telegram: chat {args.telegram}")
    if args.audio:
        print("  Audio:    enabled")

    # Register with OS scheduler
    runner_path = ROOT / "run_job.py"
    try:
        scheduler_msg = scheduler.register_job(job, runner_path)
        print(f"  {scheduler_msg}")
    except RuntimeError as err:
        print(
            f"\nWarning: Could not register with OS scheduler: {err}",
            file=sys.stderr,
        )
        print(
            f"You can manually run: python {runner_path} {job['id']}",
            file=sys.stderr,
        )

    # Show next occurrence
    try:
        next_fire = cron_parse.next_occurrence(parsed)
        print(f"\n  Next run: {next_fire.strftime('%Y-%m-%d %H:%M')}")
    except ValueError:
        pass


def output_report(
    report: schema.Report,
    output_format: str,
    requires_web_search: bool = False,
    topic: str = "",
    start_date: str = "",
    end_date: str = "",
    missing_keys: str = "none",
    days: int = 30,
):
    """Render and output the research report in the specified format."""
    format_handlers = {
        "compact": lambda: print(
            render.compact(report, missing_keys=missing_keys)
        ),
        "json": lambda: print(json.dumps(report.to_dict(), indent=2)),
        "md": lambda: print(render.full_report(report)),
        "context": lambda: print(report.context_snippet_md),
        "path": lambda: print(render.context_path()),
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
        print(f"Topic: {topic}")
        print(f"Date range: {start_date} to {end_date}")
        print()
        print("Claude: Use your WebSearch tool to find 8-15 relevant web pages.")
        print("EXCLUDE: reddit.com, x.com, twitter.com (already covered above)")
        print(f"INCLUDE: blogs, docs, news, tutorials from the last {days} days")
        print()
        print("After searching, synthesize WebSearch results WITH the Reddit/X")
        print("results above. WebSearch items should rank LOWER than comparable")
        print("Reddit/X items (they lack engagement metrics).")
        print(separator_line)


if __name__ == "__main__":
    main()
