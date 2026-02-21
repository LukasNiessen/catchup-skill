#!/usr/bin/env python3
"""Multi-platform research aggregation engine."""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def _configure_stdio_utf8() -> None:
    """Ensure Windows consoles can render unicode output safely."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


_configure_stdio_utf8()


def _log(message: str):
    """Emit a debug log line to stderr, gated by BRIEFBOT_DEBUG."""
    if os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes", "on"):
        sys.stderr.write(f"[BRIEFBOT] {message}\n")
        sys.stderr.flush()

# Ensure library modules are discoverable
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from briefbot_engine import (
    config,
    content,
    net,
    output,
    ranking,
    temporal,
    terminal,
)
from briefbot_engine.providers import (
    enrich,
    linkedin,
    reddit,
    registry,
    twitter,
    web,
    youtube,
)
from briefbot_engine.scheduling import cron, jobs, platform as sched_platform
from briefbot_engine.delivery import email, telegram


def load_fixture(name: str) -> dict:
    """Load fixture payload from repository fixtures dir."""
    path = ROOT.parent / "fixtures" / name

    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _query_reddit(
    topic: str,
    cfg: dict,
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
        response = load_fixture("provider_reddit_response.json")
    else:
        try:
            response = reddit.search(
                cfg["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                depth=depth,
            )
        except net.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"API error: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"{type(generic_err).__name__}: {generic_err}"

    items = reddit.parse_reddit_response(response or {})

    has_few_results = len(items) < 4
    should_retry = has_few_results and not mock and error is None

    if should_retry:
        simplified_topic = reddit.compress_topic(topic)
        topics_differ = simplified_topic.strip().lower() != topic.strip().lower()

        if topics_differ:
            try:
                supplemental_response = reddit.search(
                    cfg["OPENAI_API_KEY"],
                    models_picked["openai"],
                    simplified_topic,
                    start_date,
                    end_date,
                    depth=depth,
                )
                supplemental_items = reddit.parse_reddit_response(
                    supplemental_response
                )

                by_url = {}
                for base_item in items:
                    item_url = str(base_item.get("url", "")).strip()
                    if item_url:
                        by_url[item_url] = base_item
                for extra_item in supplemental_items:
                    item_url = str(extra_item.get("url", "")).strip()
                    if item_url and item_url not in by_url:
                        by_url[item_url] = extra_item
                if by_url:
                    items = list(by_url.values())
            except Exception:
                pass

    return items, response, error


def _query_x(
    topic: str,
    cfg: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    depth: str,
    mock: bool,
) -> tuple:
    """Query X/Twitter via xAI API. Returns (items, response, error)."""
    response = None
    error = None

    _log("=== _query_x START ===")
    _log(f"  Subject: '{topic}'")
    _log(f"  Date range: {start_date} to {end_date}")
    _log(f"  Depth: {depth}")
    _log(f"  Mock data: {mock}")

    if mock:
        _log("  Using MOCK data for X search")
        response = load_fixture("provider_x_response.json")
        items = twitter.parse_x_response(response or {})
        _log(f"  Mock returned {len(items)} items")
        return items, response, error

    has_xai = bool(cfg.get("XAI_API_KEY"))
    xai_key_preview = ""
    if has_xai:
        xai_key = cfg["XAI_API_KEY"]
        xai_key_preview = f"{xai_key[:8]}...{xai_key[-4:]} ({len(xai_key)} chars)"

    _log(f"  xAI key present: {has_xai} {xai_key_preview if has_xai else ''}")
    _log(f"  xAI model: {models_picked.get('xai')}")

    if has_xai:
        _log("  PATH: xAI API (paid, direct)")
        _log(f"  Calling twitter.search(key={xai_key_preview}, model={models_picked.get('xai')}, topic='{topic[:50]}', dates={start_date}->{end_date}, depth={depth})")
        try:
            response = twitter.search(
                cfg["XAI_API_KEY"],
                models_picked["xai"],
                topic,
                start_date,
                end_date,
                depth=depth,
            )
            _log(f"  xAI API call succeeded, response keys: {list(response.keys()) if isinstance(response, dict) else type(response).__name__}")
        except net.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"API error: {network_err}"
            _log(f"  xAI API HTTP ERROR: {network_err} (status={getattr(network_err, 'status_code', '?')}, body={(getattr(network_err, 'body', '') or '')[:300]})")
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"{type(generic_err).__name__}: {generic_err}"
            _log(f"  xAI API EXCEPTION: {error}")

        items = twitter.parse_x_response(response or {})
        _log(f"  xAI parsed {len(items)} items")
    else:
        _log("  PATH: NO X BACKEND AVAILABLE (no xAI key)")
        response = {
            "error": "No X search backend available (no xAI key configured)"
        }
        error = "No X search backend available"
        items = []

    _log(f"=== _query_x END: {len(items)} items, error={error} ===")
    return items, response, error


def _query_youtube(
    topic: str,
    cfg: dict,
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
            response = youtube.search(
                cfg["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                depth=depth,
            )
        except net.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"API error: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"{type(generic_err).__name__}: {generic_err}"

    items = youtube.parse_youtube_response(response or {})

    return items, response, error


def _query_linkedin(
    topic: str,
    cfg: dict,
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
            response = linkedin.search(
                cfg["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                depth=depth,
            )
        except net.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"API error: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"{type(generic_err).__name__}: {generic_err}"

    items = linkedin.parse_linkedin_response(response or {})

    return items, response, error


def run_research(
    topic: str,
    platform: str,
    cfg: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    depth: str = "default",
    mock: bool = False,
    progress: terminal.Progress = None,
) -> tuple:
    """Orchestrate the full research pipeline across all platforms. Returns a 14-element tuple."""
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

    web_search_modes = ("all", "web", "reddit-web", "x-web")
    requires_web_search = platform in web_search_modes

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

    openai_available = bool(cfg.get("OPENAI_API_KEY"))
    xai_available = bool(cfg.get("XAI_API_KEY"))
    x_available = xai_available

    _log("=== run_research ===")
    _log(f"  Platform: '{platform}'")
    _log(f"  OpenAI available: {openai_available}")
    _log(f"  xAI available: {xai_available}")
    _log(f"  X available (xAI): {x_available}")
    _log(f"  Depth: {depth}")
    _log(f"  Models picked: {models_picked}")

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

    _log(f"  should_query_reddit: {should_query_reddit}")
    _log(f"  should_query_x: {should_query_x}")
    _log(f"  should_query_youtube: {should_query_youtube}")
    _log(f"  should_query_linkedin: {should_query_linkedin}")

    with ThreadPoolExecutor(max_workers=5) as thread_pool:
        futures = {}
        if should_query_reddit:
            if progress is not None:
                progress.start_reddit()

            future = thread_pool.submit(
                _query_reddit,
                topic,
                cfg,
                models_picked,
                start_date,
                end_date,
                depth,
                mock,
            )
            futures[future] = "reddit"

        if should_query_x:
            if progress is not None:
                progress.start_x()

            future = thread_pool.submit(
                _query_x,
                topic,
                cfg,
                models_picked,
                start_date,
                end_date,
                depth,
                mock,
            )
            futures[future] = "x"

        if should_query_youtube:
            future = thread_pool.submit(
                _query_youtube,
                topic,
                cfg,
                models_picked,
                start_date,
                end_date,
                depth,
                mock,
            )
            futures[future] = "youtube"

        if should_query_linkedin:
            future = thread_pool.submit(
                _query_linkedin,
                topic,
                cfg,
                models_picked,
                start_date,
                end_date,
                depth,
                mock,
            )
            futures[future] = "linkedin"

        for future in as_completed(futures):
            source = futures[future]
            try:
                items, raw_response, source_error = future.result()
            except Exception as exc:
                items = []
                raw_response = None
                source_error = f"{type(exc).__name__}: {exc}"

            if source == "reddit":
                reddit_items = items
                raw_openai = raw_response
                reddit_error = source_error
                if progress is not None:
                    if reddit_error:
                        progress.show_error(f"Reddit error: {reddit_error}")
                    progress.end_reddit(len(reddit_items))
            elif source == "x":
                x_items = items
                raw_xai = raw_response
                x_error = source_error
                if progress is not None:
                    if x_error:
                        progress.show_error(f"X error: {x_error}")
                    progress.end_x(len(x_items))
            elif source == "youtube":
                youtube_items = items
                raw_youtube = raw_response
                youtube_error = source_error
                if progress is not None and youtube_error:
                    progress.show_error(f"YouTube error: {youtube_error}")
            elif source == "linkedin":
                linkedin_items = items
                raw_linkedin = raw_response
                linkedin_error = source_error
                if progress is not None and linkedin_error:
                    progress.show_error(f"LinkedIn error: {linkedin_error}")

    _log("=== Query results summary ===")
    _log(f"  Reddit: {len(reddit_items)} items, error={reddit_error}")
    _log(f"  X:      {len(x_items)} items, error={x_error}")
    _log(f"  YouTube: {len(youtube_items)} items, error={youtube_error}")
    _log(f"  LinkedIn: {len(linkedin_items)} items, error={linkedin_error}")

    if len(reddit_items) > 0:
        if progress is not None:
            progress.start_reddit_enrich(1, len(reddit_items))

        for i, item in enumerate(reddit_items):
            if progress is not None and i > 0:
                progress.update_reddit_enrich(i + 1, len(reddit_items))

            try:
                if mock:
                    thread_data = load_fixture("provider_reddit_thread.json")
                    reddit_items[i] = enrich.enrich(item, thread_data)
                else:
                    reddit_items[i] = enrich.enrich(item)
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
        "--format",
        dest="emit",
        choices=["compact", "json", "md", "context", "path"],
        default="compact",
        help="Output mode",
    )
    parser.add_argument(
        "--emit",
        dest="emit",
        choices=["compact", "json", "md", "context", "path"],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--channels",
        dest="sources",
        choices=["auto", "reddit", "x", "youtube", "linkedin", "both", "all"],
        default="auto",
        help="Source selection (auto, reddit, x, youtube, linkedin, both=reddit+x, all=all sources)",
    )
    parser.add_argument(
        "--sources",
        dest="sources",
        choices=["auto", "reddit", "x", "youtube", "linkedin", "both", "all"],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--depth",
        choices=["quick", "default", "deep"],
        help="Sampling depth (quick/default/deep)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use a light pass with smaller sample sizes",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Use exhaustive sampling for denser coverage",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--window",
        dest="days",
        type=int,
        default=30,
        help="Number of days to search back (default: 30, e.g., 7 for a week, 1 for today)",
    )
    parser.add_argument(
        "--days",
        dest="days",
        type=int,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--augment-web",
        dest="include_web",
        action="store_true",
        help="Include general web search alongside Reddit/X (lower weighted)",
    )
    parser.add_argument(
        "--include-web",
        dest="include_web",
        action="store_true",
        help=argparse.SUPPRESS,
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

    if args.setup:
        from setup import run_setup

        run_setup()
        return

    if args.list_jobs:
        _list_jobs()
        return

    if args.delete_job:
        _delete_job(args.delete_job)
        return

    if args.schedule:
        _create_schedule(args)
        return

    if args.debug:
        os.environ["BRIEFBOT_DEBUG"] = "1"
        net.DEBUG = True

    if args.quick and args.deep:
        print("Error: Cannot use both --quick and --deep", file=sys.stderr)
        sys.exit(1)

    depth = "default"
    if args.depth:
        depth = args.depth
    elif args.quick:
        depth = "quick"
    elif args.deep:
        depth = "deep"

    if args.topic is None:
        print("Error: Please provide a topic to research.", file=sys.stderr)
        print("Usage: python3 briefbot.py <topic> [options]", file=sys.stderr)
        sys.exit(1)

    _log("=== main: Loading configuration ===")
    cfg = config.load_config()

    platforms = config.determine_available_platforms(cfg)
    _log(f"Available platforms: '{platforms}'")

    if args.mock:
        platform = "both" if args.sources == "auto" else args.sources
    else:
        platform, src_err = config.validate_sources(
            args.sources, platforms, args.include_web
        )

        _log(f"Source validation: platform='{platform}', error={src_err}")

        if src_err is not None:
            if "WebSearch fallback" in src_err:
                print(f"Note: {src_err}", file=sys.stderr)
            else:
                print(f"Error: {src_err}", file=sys.stderr)
                sys.exit(1)

    days = args.days
    start_date, end_date = temporal.window(days)

    missing_keys = config.identify_missing_credentials(cfg)

    progress = terminal.Progress(args.topic, display_header=True)

    if missing_keys != "none":
        progress.show_promo(missing_keys)

    if args.mock:
        mock_openai_models = load_fixture("api_openai_models.json").get(
            "data", []
        )
        mock_xai_models = load_fixture("api_xai_models.json").get(
            "data", []
        )

        models_picked = registry.get_models(
            {
                "OPENAI_API_KEY": "mock",
                "XAI_API_KEY": "mock",
                **cfg,
            },
            mock_openai_models,
            mock_xai_models,
        )
    else:
        models_picked = registry.get_models(cfg)

    _log(f"Models picked: openai={models_picked.get('openai')}, xai={models_picked.get('xai')}")

    mode_aliases = [
        ("both", "both"),
        ("all", "all"),
        ("reddit", "reddit-only"),
        ("x", "x-only"),
        ("reddit-web", "reddit-web"),
        ("x-web", "x-web"),
        ("web", "web-only"),
        ("youtube", "youtube-only"),
        ("linkedin", "linkedin-only"),
    ]
    display_mode = platform
    for raw_mode, friendly in mode_aliases:
        if platform == raw_mode:
            display_mode = friendly
            break

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
        cfg,
        models_picked,
        start_date,
        end_date,
        depth,
        args.mock,
        progress,
    )

    # Begin post-processing phase
    progress.start_processing()

    # Convert raw dicts to unified ContentItems
    from briefbot_engine.content import Source, items_from_raw, filter_by_date

    normalized_reddit = items_from_raw(reddit_items, Source.REDDIT, start_date, end_date)
    normalized_x = items_from_raw(x_items, Source.X, start_date, end_date)
    normalized_youtube = items_from_raw(youtube_items, Source.YOUTUBE, start_date, end_date)
    normalized_linkedin = items_from_raw(linkedin_items, Source.LINKEDIN, start_date, end_date)

    # Apply strict date filtering
    filtered_reddit = filter_by_date(normalized_reddit, start_date, end_date)
    filtered_x = filter_by_date(normalized_x, start_date, end_date)
    filtered_youtube = filter_by_date(normalized_youtube, start_date, end_date)
    filtered_linkedin = filter_by_date(normalized_linkedin, start_date, end_date)

    # Combine all items then score -> dedupe -> rescore for final ranking
    all_items = filtered_reddit + filtered_x + filtered_youtube + filtered_linkedin
    initial_ranked = ranking.rank_items(all_items)
    deduped_items = ranking.deduplicate(initial_ranked)
    scored_items = ranking.rank_items(deduped_items)

    progress.end_processing()

    # Assemble the final report
    report = content.build_report(
        args.topic,
        start_date,
        end_date,
        display_mode,
        models_picked.get("openai"),
        models_picked.get("xai"),
    )
    report.items = deduped_items
    report.reddit_error = reddit_error
    report.x_error = x_error
    report.youtube_error = youtube_error
    report.linkedin_error = linkedin_error

    report.context_snippet_md = output.context_fragment(report)

    output.save_artifacts(
        report, raw_openai, raw_xai, raw_reddit_enriched, raw_youtube, raw_linkedin
    )

    if platform == "web":
        progress.show_web_only_complete()
    else:
        progress.show_complete(
            len(report.reddit),
            len(report.x),
            len(report.youtube),
            len(report.linkedin),
        )

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
            parsed = cron.parse_cron_expression(job["schedule"])
            schedule_desc = cron.describe_schedule(parsed)
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

    try:
        scheduler_msg = sched_platform.unregister_job(job)
        print(scheduler_msg)
    except RuntimeError as err:
        print(
            f"Warning: Could not remove from OS scheduler: {err}",
            file=sys.stderr,
        )

    deleted = jobs.delete_job(job_id)
    if deleted:
        print(f"Job {job_id} deleted from registry.")
    else:
        print(f"Warning: Job {job_id} was not in registry.", file=sys.stderr)


def _create_schedule(args):
    """Create a new scheduled job from CLI arguments."""
    if not args.topic:
        print("Error: Topic is required when creating a schedule.", file=sys.stderr)
        print(
            'Usage: python briefbot.py "topic" --schedule "0 6 * * *" --email you@example.com',
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        parsed = cron.parse_cron_expression(args.schedule)
        schedule_desc = cron.describe_schedule(parsed)
    except ValueError as err:
        print(f"Error: Invalid schedule: {err}", file=sys.stderr)
        sys.exit(1)

    if args.email:
        cfg = config.load_config()
        smtp_error = email.validate_smtp_config(cfg)
        if smtp_error:
            print(f"Error: {smtp_error}", file=sys.stderr)
            sys.exit(1)

    if not args.email and not args.audio and not args.telegram:
        print(
            "Warning: No --email, --audio, or --telegram specified. The job will run research but produce no output.",
            file=sys.stderr,
        )
        print("Consider adding --audio, --email, and/or --telegram.", file=sys.stderr)

    args_dict = {
        "quick": args.quick,
        "deep": args.deep,
        "audio": args.audio,
        "days": args.days,
        "sources": args.sources,
        "include_web": args.include_web,
        "telegram": args.telegram,
    }

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

    runner_path = ROOT / "run_job.py"
    try:
        scheduler_msg = sched_platform.register_job(job, runner_path)
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

    try:
        next_fire = cron.next_occurrence(parsed)
        print(f"\n  Next run: {next_fire.strftime('%Y-%m-%d %H:%M')}")
    except ValueError:
        pass


def output_report(
    report,
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
        "compact": lambda: print(output.compact(report, missing_keys=missing_keys)),
        "json": lambda: print(json.dumps(report.to_dict(), indent=2)),
        "md": lambda: print(output.full_report(report)),
        "context": lambda: print(report.context_snippet_md),
        "path": lambda: print(output.context_path()),
    }

    handler = format_handlers.get(output_format)
    if handler is not None:
        handler()

    if requires_web_search:
        separator_line = "=" * 64

        print()
        print(separator_line)
        print("### WEB AUGMENTATION REQUIRED ###")
        print(separator_line)
        print(f"Topic: {topic}")
        print(f"Date range: {start_date} to {end_date}")
        print()
        print("Run WebSearch and gather 8-15 non-social sources.")
        print("Exclude reddit.com, x.com, and twitter.com (already covered above).")
        print(f"Prioritize docs, blogs, changelogs, and news from the last {days} days.")
        print()
        print("Merge web findings with platform findings into a single synthesis.")
        print("When confidence is close, prefer Reddit/X evidence above plain web links")
        print("because social items include richer engagement signals.")
        print(separator_line)


if __name__ == "__main__":
    main()
