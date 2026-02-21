#!/usr/bin/env python3
"""Multi-platform research aggregation engine."""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
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
    settings,
    records,
    analysis,
    http_client,
    presenter,
    scoring,
    timeframe,
    console,
)
from briefbot_engine.sources import (
    hydrate,
    linkedin_feed,
    reddit_source,
    catalog,
    x_posts,
    webscan,
    youtube_feed,
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


@dataclass
class ResearchBundle:
    items: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    errors: dict = field(default_factory=dict)
    needs_web: bool = False


def _query_reddit(
    topic: str,
    cfg: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    sampling: str,
    mock: bool,
) -> tuple:
    """Query Reddit via OpenAI web search API. Returns (items, response, error)."""
    response = None
    error = None

    if mock:
        response = load_fixture("provider_reddit_response.json")
    else:
        try:
            response = reddit_source.search(
                cfg["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                sampling=sampling,
            )
        except http_client.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"Request failed: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"Unhandled exception ({type(generic_err).__name__}) - {generic_err}"

    items = reddit_source.parse_reddit_response(response or {})

    has_few_results = len(items) < 4
    should_retry = has_few_results and not mock and error is None

    if should_retry:
        simplified_topic = reddit_source.trim_query(topic)
        topics_differ = simplified_topic.strip().lower() != topic.strip().lower()

        if topics_differ:
            try:
                supplemental_response = reddit_source.search(
                    cfg["OPENAI_API_KEY"],
                    models_picked["openai"],
                    simplified_topic,
                    start_date,
                    end_date,
                    sampling=sampling,
                )
                supplemental_items = reddit_source.parse_reddit_response(supplemental_response)

                by_url = {}
                for base_item in items:
                    item_url = str(
                        base_item.get("url", base_item.get("link", ""))
                    ).strip()
                    if item_url:
                        by_url[item_url] = base_item
                for extra_item in supplemental_items:
                    item_url = str(
                        extra_item.get("url", extra_item.get("link", ""))
                    ).strip()
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
    sampling: str,
    mock: bool,
) -> tuple:
    """Query X/Twitter via xAI API. Returns (items, response, error)."""
    response = None
    error = None

    _log("=== _query_x START ===")
    _log(f"  Subject: '{topic}'")
    _log(f"  Date range: {start_date} to {end_date}")
    _log(f"  Sampling: {sampling}")
    _log(f"  Mock data: {mock}")

    if mock:
        _log("  Using MOCK data for X search")
        response = load_fixture("provider_x_response.json")
        items = x_posts.parse_x_response(response or {})
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
        _log(
            f"  Calling twitter.search(key={xai_key_preview}, model={models_picked.get('xai')}, topic='{topic[:50]}', dates={start_date}->{end_date}, sampling={sampling})"
        )
        try:
            response = x_posts.search(
                cfg["XAI_API_KEY"],
                models_picked["xai"],
                topic,
                start_date,
                end_date,
                sampling=sampling,
            )
            _log(
                f"  xAI API call succeeded, response keys: {list(response.keys()) if isinstance(response, dict) else type(response).__name__}"
            )
        except http_client.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"Request failed: {network_err}"
            _log(
                f"  xAI API HTTP ERROR: {network_err} (status={getattr(network_err, 'status_code', '?')}, body={(getattr(network_err, 'body', '') or '')[:300]})"
            )
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"Unhandled exception ({type(generic_err).__name__}) - {generic_err}"
            _log(f"  xAI API EXCEPTION: {error}")

        items = x_posts.parse_x_response(response or {})
        _log(f"  xAI parsed {len(items)} items")
    else:
        _log("  PATH: NO X BACKEND AVAILABLE (no xAI key)")
        response = {"error": "No X search backend available (no xAI key configured)"}
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
    sampling: str,
    mock: bool,
) -> tuple:
    """Query YouTube via OpenAI web search API. Returns (items, response, error)."""
    response = None
    error = None

    if mock:
        response = load_fixture("youtube_sample.json")
    else:
        try:
            response = youtube_feed.search(
                cfg["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                sampling=sampling,
            )
        except http_client.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"Request failed: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"Unhandled exception ({type(generic_err).__name__}) - {generic_err}"

    items = youtube_feed.parse_youtube_response(response or {})

    return items, response, error


def _query_linkedin(
    topic: str,
    cfg: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    sampling: str,
    mock: bool,
) -> tuple:
    """Query LinkedIn via OpenAI web search API. Returns (items, response, error)."""
    response = None
    error = None

    if mock:
        response = load_fixture("linkedin_sample.json")
    else:
        try:
            response = linkedin_feed.search(
                cfg["OPENAI_API_KEY"],
                models_picked["openai"],
                topic,
                start_date,
                end_date,
                sampling=sampling,
            )
        except http_client.HTTPError as network_err:
            response = {"error": str(network_err)}
            error = f"Request failed: {network_err}"
        except Exception as generic_err:
            response = {"error": str(generic_err)}
            error = f"Unhandled exception ({type(generic_err).__name__}) - {generic_err}"

    items = linkedin_feed.parse_linkedin_response(response or {})

    return items, response, error


def run_research(
    topic: str,
    platform: str,
    cfg: dict,
    models_picked: dict,
    start_date: str,
    end_date: str,
    sampling: str = "standard",
    mock: bool = False,
    progress: console.Progress = None,
) -> ResearchBundle:
    """Orchestrate the full research pipeline across all platforms."""
    bundle = ResearchBundle(
        items={"reddit": [], "x": [], "youtube": [], "linkedin": []},
        raw={
            "openai": None,
            "xai": None,
            "youtube": None,
            "linkedin": None,
            "reddit_enriched": [],
        },
        errors={},
        needs_web=False,
    )

    web_search_modes = ("all", "web", "reddit-web", "x-web")
    bundle.needs_web = platform in web_search_modes

    if platform == "web":
        if progress is not None:
            progress.begin_web_only()
            progress.finish_web_only()
        return bundle

    openai_available = bool(cfg.get("OPENAI_API_KEY"))
    xai_available = bool(cfg.get("XAI_API_KEY"))

    _log("=== run_research ===")
    _log(f"  Platform: '{platform}'")
    _log(f"  OpenAI available: {openai_available}")
    _log(f"  xAI available: {xai_available}")
    _log(f"  Sampling: {sampling}")
    _log(f"  Models picked: {models_picked}")

    reddit_platforms = ("both", "reddit", "all", "reddit-web")
    x_platforms = ("both", "x", "all", "x-web")
    youtube_platforms = ("all", "youtube")
    linkedin_platforms = ("all", "linkedin")

    should_query_reddit = platform in reddit_platforms and openai_available
    should_query_x = platform in x_platforms and xai_available
    should_query_youtube = platform in youtube_platforms and openai_available
    should_query_linkedin = platform in linkedin_platforms and openai_available

    _log(f"  should_query_reddit: {should_query_reddit}")
    _log(f"  should_query_x: {should_query_x}")
    _log(f"  should_query_youtube: {should_query_youtube}")
    _log(f"  should_query_linkedin: {should_query_linkedin}")

    with ThreadPoolExecutor(max_workers=5) as thread_pool:
        futures = {}
        if should_query_reddit:
            if progress is not None:
                progress.begin_reddit()
            futures[thread_pool.submit(
                _query_reddit,
                topic,
                cfg,
                models_picked,
                start_date,
                end_date,
                sampling,
                mock,
            )] = "reddit"

        if should_query_x:
            if progress is not None:
                progress.begin_x()
            futures[thread_pool.submit(
                _query_x,
                topic,
                cfg,
                models_picked,
                start_date,
                end_date,
                sampling,
                mock,
            )] = "x"

        if should_query_youtube:
            futures[thread_pool.submit(
                _query_youtube,
                topic,
                cfg,
                models_picked,
                start_date,
                end_date,
                sampling,
                mock,
            )] = "youtube"

        if should_query_linkedin:
            futures[thread_pool.submit(
                _query_linkedin,
                topic,
                cfg,
                models_picked,
                start_date,
                end_date,
                sampling,
                mock,
            )] = "linkedin"

        for future in as_completed(futures):
            source = futures[future]
            try:
                items, raw_response, source_error = future.result()
            except Exception as exc:
                items = []
                raw_response = None
                source_error = f"{type(exc).__name__}: {exc}"

            if source == "reddit":
                bundle.items["reddit"] = items
                bundle.raw["openai"] = raw_response
                if source_error:
                    bundle.errors["reddit"] = source_error
                if progress is not None:
                    if source_error:
                        progress.report_error(f"Reddit error: {source_error}")
                    progress.finish_reddit(len(items))
            elif source == "x":
                bundle.items["x"] = items
                bundle.raw["xai"] = raw_response
                if source_error:
                    bundle.errors["x"] = source_error
                if progress is not None:
                    if source_error:
                        progress.report_error(f"X error: {source_error}")
                    progress.finish_x(len(items))
            elif source == "youtube":
                bundle.items["youtube"] = items
                bundle.raw["youtube"] = raw_response
                if source_error:
                    bundle.errors["youtube"] = source_error
                if progress is not None and source_error:
                    progress.report_error(f"YouTube error: {source_error}")
            elif source == "linkedin":
                bundle.items["linkedin"] = items
                bundle.raw["linkedin"] = raw_response
                if source_error:
                    bundle.errors["linkedin"] = source_error
                if progress is not None and source_error:
                    progress.report_error(f"LinkedIn error: {source_error}")

    _log("=== Query results summary ===")
    _log(f"  Reddit: {len(bundle.items['reddit'])} items, error={bundle.errors.get('reddit')}")
    _log(f"  X:      {len(bundle.items['x'])} items, error={bundle.errors.get('x')}")
    _log(f"  YouTube: {len(bundle.items['youtube'])} items, error={bundle.errors.get('youtube')}")
    _log(f"  LinkedIn: {len(bundle.items['linkedin'])} items, error={bundle.errors.get('linkedin')}")

    reddit_items = bundle.items["reddit"]
    if reddit_items:
        if progress is not None:
            progress.begin_thread_hydration(1, len(reddit_items))

        for i, item in enumerate(reddit_items):
            if progress is not None and i > 0:
                progress.update_thread_hydration(i + 1, len(reddit_items))

            try:
                if mock:
                    thread_data = load_fixture("provider_reddit_thread.json")
                    reddit_items[i] = hydrate.hydrate(item, thread_data)
                else:
                    reddit_items[i] = hydrate.hydrate(item)
            except Exception as err:
                if progress is not None:
                    url = item.get("url", "unknown")
                    progress.report_error(f"Hydration failed for {url}: {err}")

            bundle.raw["reddit_enriched"].append(reddit_items[i])

        if progress is not None:
            progress.finish_thread_hydration()

    return bundle


def main():
    """Entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Research a topic from the last N days on Reddit + X + YouTube + LinkedIn"
    )

    parser.add_argument("topic", nargs="?", help="Topic or query to research")
    parser.add_argument(
        "--fixtures",
        dest="mock",
        action="store_true",
        help="Use local fixtures instead of live APIs",
    )
    parser.add_argument(
        "--view",
        dest="emit",
        choices=["snapshot", "json", "md", "context", "path", "cards"],
        default="snapshot",
        help="Output view",
    )
    parser.add_argument(
        "--feeds",
        dest="sources",
        choices=["auto", "social", "reddit", "x", "youtube", "linkedin", "all", "web"],
        default="auto",
        help="Source selection (auto, social=reddit+x, all=all sources)",
    )
    parser.add_argument(
        "--sampling",
        choices=["lite", "standard", "dense"],
        default="standard",
        help="Sampling intensity (lite/standard/dense)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--span",
        dest="days",
        type=int,
        default=30,
        help="Number of days to search back (default: 30)",
    )
    parser.add_argument(
        "--web-plus",
        dest="include_web",
        action="store_true",
        help="Include general web search alongside social sources",
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
        http_client.DEBUG = True

    sampling = args.sampling or "standard"

    if args.topic is None:
        print("Error: Please provide a topic to research.", file=sys.stderr)
        print("Usage: python3 briefbot.py <topic> [options]", file=sys.stderr)
        sys.exit(1)

    _log("=== main: Loading configuration ===")
    cfg = settings.load_config()

    platforms = settings.determine_available_platforms(cfg)
    _log(f"Available platforms: '{platforms}'")

    if args.mock:
        raw_sources = "both" if args.sources in ("auto", "social") else args.sources
        platform = raw_sources
    else:
        requested_sources = "both" if args.sources == "social" else args.sources
        resolution = settings.resolve_sources(requested_sources, platforms, args.include_web)
        platform = resolution.mode

        _log(
            f"Source resolution: platform='{platform}', severity={resolution.severity}, message={resolution.message}"
        )

        if resolution.message:
            if resolution.severity == "warn":
                print(f"Note: {resolution.message}", file=sys.stderr)
            elif resolution.severity == "error":
                print(f"Error: {resolution.message}", file=sys.stderr)
                sys.exit(1)

    days = args.days
    start_date, end_date = timeframe.get_date_range(days)

    missing_keys = settings.identify_missing_credentials(cfg)

    progress = console.Progress(args.topic, display_header=True)

    if missing_keys != "none":
        progress.show_upgrade_notice(missing_keys)

    if args.mock:
        mock_openai_models = load_fixture("api_openai_models.json").get("data", [])
        mock_xai_models = load_fixture("api_xai_models.json").get("data", [])

        config_copy = dict(cfg)
        config_copy.update({"OPENAI_API_KEY": "mock", "XAI_API_KEY": "mock"})
        models_picked = catalog.get_models(
            config_copy,
            mock_openai_models,
            mock_xai_models,
        )
    else:
        models_picked = catalog.get_models(cfg)

    _log(
        f"Models picked: openai={models_picked.get('openai')}, xai={models_picked.get('xai')}"
    )

    complexity_class, complexity_reason = analysis.classify_complexity(args.topic)
    epistemic_stance, epistemic_reason = analysis.classify_epistemic_stance(args.topic)
    decomposition = []
    decomposition_source = "skipped"
    if complexity_class == analysis.COMPLEX_ANALYTICAL:
        decomposition, decomposition_source = analysis.decompose_query(
            args.topic,
            cfg.get("OPENAI_API_KEY"),
            models_picked.get("openai"),
        )

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

    bundle = run_research(
        args.topic,
        platform,
        cfg,
        models_picked,
        start_date,
        end_date,
        sampling,
        args.mock,
        progress,
    )

    # Begin post-processing phase
    progress.begin_scoring()

    # Convert raw dicts to unified Signals
    from briefbot_engine.records import Channel, items_from_raw, filter_by_date

    normalized_reddit = items_from_raw(
        bundle.items["reddit"], Channel.REDDIT, start_date, end_date
    )
    normalized_x = items_from_raw(bundle.items["x"], Channel.X, start_date, end_date)
    normalized_youtube = items_from_raw(
        bundle.items["youtube"], Channel.YOUTUBE, start_date, end_date
    )
    normalized_linkedin = items_from_raw(
        bundle.items["linkedin"], Channel.LINKEDIN, start_date, end_date
    )

    # Combine all items then score -> dedupe -> filter -> rescore for final ranking
    all_items = normalized_reddit + normalized_x + normalized_youtube + normalized_linkedin
    source_weights = analysis.stance_weights(epistemic_stance)
    initial_ranked = scoring.rank_items(all_items, source_weights=source_weights)
    deduped_items = scoring.deduplicate(initial_ranked)
    filtered_items = filter_by_date(deduped_items, start_date, end_date)
    scored_items = scoring.rank_items(filtered_items, source_weights=source_weights)

    progress.finish_scoring()

    # Assemble the final report
    report = records.build_brief(
        args.topic,
        start_date,
        end_date,
        display_mode,
        models_picked.get("openai"),
        models_picked.get("xai"),
        complexity_class=complexity_class,
        complexity_reason=complexity_reason,
        epistemic_stance=epistemic_stance,
        epistemic_reason=epistemic_reason,
        decomposition=decomposition,
        decomposition_source=decomposition_source,
    )
    report.items = scored_items
    report.reddit_error = bundle.errors.get("reddit")
    report.x_error = bundle.errors.get("x")
    report.youtube_error = bundle.errors.get("youtube")
    report.linkedin_error = bundle.errors.get("linkedin")
    report.metrics.item_count = len(report.items)

    report.context_snippet_md = presenter.context_fragment(report)

    presenter.save_artifacts(
        report,
        bundle.raw.get("openai"),
        bundle.raw.get("xai"),
        bundle.raw.get("reddit_enriched"),
        bundle.raw.get("youtube"),
        bundle.raw.get("linkedin"),
    )

    if platform == "web":
        progress.show_web_only_summary()
    else:
        progress.show_summary(
            len(report.reddit),
            len(report.x),
            len(report.youtube),
            len(report.linkedin),
        )

    output_report(
        report,
        args.emit,
        bundle.needs_web,
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
            print(
                f"    Last run: {job['last_run']} ({job.get('last_status', 'unknown')})"
            )
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
        cfg = settings.load_config()
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
        "sampling": args.sampling or "standard",
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
        "snapshot": lambda: print(presenter.compact(report, missing_keys=missing_keys)),
        "json": lambda: print(json.dumps(report.to_dict(), indent=2)),
        "md": lambda: print(presenter.full_report(report)),
        "context": lambda: print(report.context_snippet_md),
        "path": lambda: print(presenter.context_path()),
        "cards": lambda: print(presenter.signal_cards(report)),
    }

    handler = format_handlers.get(output_format)
    if handler is not None:
        handler()

    if requires_web_search:
        separator_line = "=" * 64

        print()
        print(separator_line)
        print("### WEB SWEEP RECOMMENDED ###")
        print(separator_line)
        print(f"Topic: {topic}")
        print(f"Date range: {start_date} to {end_date}")
        print()
        print("Run WebSearch and gather 8-15 non-social sources.")
        print("Skip reddit.com and X/Twitter domains (already covered above).")
        print(
            f"Prioritize docs, blogs, changelogs, and news from the last {days} days."
        )
        print()
        print("Merge web findings with platform findings into a single synthesis.")
        stance = (report.epistemic_stance or "").upper()
        if stance == "FACTUAL_TEMPORAL":
            print("When confidence is close, prefer authoritative web sources for factual claims.")
        elif stance == "TRENDING_BREAKING":
            print("When confidence is close, prefer X for real-time momentum signals.")
        elif stance == "HOW_TO_TUTORIAL":
            print("When confidence is close, prefer YouTube + docs for procedural guidance.")
        elif stance == "EXPERIENTIAL_OPINION":
            print("When confidence is close, prefer Reddit/X for lived experience and sentiment.")
        else:
            print(
                "When confidence is close, prefer sources with the strongest engagement signals."
            )
        print(separator_line)


if __name__ == "__main__":
    main()
