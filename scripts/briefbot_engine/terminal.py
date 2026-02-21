"""Terminal progress UI primitives."""

import os
import sys
import time
import threading
import random
from typing import Optional


def _enable_windows_vt_processing():
    """Activate ANSI escape support on Windows 10+."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        for handle_id in (-11, -12):
            handle = kernel32.GetStdHandle(handle_id)
            if handle == -1:
                continue
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


_enable_windows_vt_processing()

IS_TTY = bool(getattr(sys.stderr, "isatty", lambda: False)())


class Style:
    """ANSI escape codes for terminal styling."""
    MAGENTA = '\033[38;5;171m'
    AZURE = '\033[38;5;75m'
    TEAL = '\033[38;5;44m'
    LIME = '\033[38;5;40m'
    AMBER = '\033[38;5;214m'
    CRIMSON = '\033[38;5;196m'
    EMPHASIZED = '\033[1m'
    SUBDUED = '\033[2m'
    NORMAL = '\033[0m'


if "NO_COLOR" in os.environ:
    for _attr in ("MAGENTA", "AZURE", "TEAL", "LIME", "AMBER", "CRIMSON",
                   "EMPHASIZED", "SUBDUED", "NORMAL"):
        setattr(Style, _attr, "")


HEADER_ART = (
    f"{Style.MAGENTA}{Style.EMPHASIZED}\n"
    "   \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2557  \u2588\u2588\u2557\u2588\u2588\u2557   \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557\n"
    "  \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u255a\u2550\u2550\u2588\u2588\u2554\u2550\u2550\u255d\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\n"
    "  \u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\n"
    "  \u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2550\u255d\n"
    "  \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551   \u2588\u2588\u2551   \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551\n"
    "   \u255a\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u255d  \u255a\u2550\u255d   \u255a\u2550\u255d    \u255a\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d\n"
    f"{Style.NORMAL}{Style.SUBDUED}  Deep research, instant delivery.{Style.NORMAL}\n"
)

COMPACT_HEADER = f"{Style.MAGENTA}{Style.EMPHASIZED}/briefbot{Style.NORMAL} {Style.SUBDUED}\u00b7 researching...{Style.NORMAL}"

REDDIT_MSGS = [
    "Scouring subreddit discussions...",
    "Mining Reddit for relevant threads...",
    "Checking what communities are talking about...",
    "Pulling insights from Reddit...",
    "Hunting for quality discussions...",
    "Combing through the comment sections...",
    "Digging into Reddit conversations...",
]

X_MSGS = [
    "Tapping into the X firehose...",
    "Scanning posts and threads...",
    "Catching up on X discourse...",
    "Pulling real-time takes...",
    "Checking what creators are posting...",
    "Gathering posts from the timeline...",
    "Surveying X for relevant voices...",
]

ENRICH_MSGS = [
    "Pulling real engagement numbers...",
    "Grabbing upvotes and comments...",
    "Loading thread details...",
    "Collecting community reactions...",
    "Harvesting discussion metrics...",
]

PROCESS_MSGS = [
    "Running the scoring pipeline...",
    "Ranking and deduplicating...",
    "Weighing relevance signals...",
    "Sorting by quality score...",
    "Finalizing the results...",
]

WEB_MSGS = [
    "Crawling the open web...",
    "Checking blogs and documentation...",
    "Scanning news and articles...",
    "Exploring web sources...",
]

TTS_MSGS = [
    "Producing audio briefing...",
    "Rendering speech output...",
    "Building the audio file...",
    "Synthesizing narration...",
]

UPGRADE_NOTICE = f"""
{Style.AMBER}{Style.EMPHASIZED}\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{Style.NORMAL}
{Style.AMBER}\u26a1 UNLOCK THE FULL POWER OF /briefbot{Style.NORMAL}

{Style.SUBDUED}Right now you're using web search only. Add API keys to unlock:{Style.NORMAL}

  {Style.AMBER}\U0001f7e0 Reddit{Style.NORMAL} - Real upvotes, comments, and community insights
  {Style.CRIMSON}\U0001f534 YouTube{Style.NORMAL} - Video discoveries with view counts
  {Style.AZURE}\U0001f537 LinkedIn{Style.NORMAL} - Professional posts and insights
     \u2514\u2500 Add OPENAI_API_KEY (uses OpenAI's web_search)

  {Style.TEAL}\U0001f535 X (Twitter){Style.NORMAL} - Real-time posts, likes, reposts from creators
     \u2514\u2500 Add XAI_API_KEY (uses xAI's live X search)

{Style.SUBDUED}Setup:{Style.NORMAL} Edit {Style.EMPHASIZED}~/.config/briefbot/briefbot.env{Style.NORMAL} {Style.SUBDUED}(legacy .env also supported){Style.NORMAL}
{Style.AMBER}{Style.EMPHASIZED}\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{Style.NORMAL}
"""

SINGLE_KEY_HINTS = {
    "reddit": f"\n{Style.SUBDUED}\U0001f4a1 Tip: Add {Style.AMBER}OPENAI_API_KEY{Style.NORMAL}{Style.SUBDUED} to ~/.config/briefbot/briefbot.env (or legacy .env) for Reddit, YouTube & LinkedIn data!{Style.NORMAL}\n",
    "x": f"\n{Style.SUBDUED}\U0001f4a1 Tip: Add {Style.TEAL}XAI_API_KEY{Style.NORMAL}{Style.SUBDUED} to ~/.config/briefbot/briefbot.env (or legacy .env) for X/Twitter data with real likes & reposts!{Style.NORMAL}\n",
}

SPIN_CHARS = ['\u25dc', '\u25dd', '\u25de', '\u25df']


class Spinner:
    """Animated terminal spinner for long-running operations."""

    def __init__(self, status_text: str = "Working", style_code: str = Style.TEAL):
        self.status_text = status_text
        self.style_code = style_code
        self.active = False
        self.animation_thread: Optional[threading.Thread] = None
        self.frame_position = 0
        self.static_displayed = False

    def _animate(self):
        while self.active:
            frame = SPIN_CHARS[self.frame_position % len(SPIN_CHARS)]
            sys.stderr.write(f"\r{self.style_code}{frame}{Style.NORMAL} {self.status_text}  ")
            sys.stderr.flush()
            self.frame_position += 1
            time.sleep(0.1)

    def start(self):
        self.active = True
        if IS_TTY:
            self.animation_thread = threading.Thread(target=self._animate, daemon=True)
            self.animation_thread.start()
        else:
            if not self.static_displayed:
                sys.stderr.write(f"{self.style_code}\u25cf{Style.NORMAL} {self.status_text}\n")
                sys.stderr.flush()
                self.static_displayed = True

    def update(self, new_status: str):
        self.status_text = new_status
        if not IS_TTY and not self.static_displayed:
            sys.stderr.write(f"{self.style_code}\u25cf{Style.NORMAL} {new_status}\n")
            sys.stderr.flush()

    def stop(self, completion_message: str = ""):
        self.active = False
        if self.animation_thread:
            self.animation_thread.join(timeout=0.35)
        if IS_TTY:
            sys.stderr.write("\r" + (" " * 120) + "\r")
        if completion_message:
            sys.stderr.write(f"{Style.LIME}\u2713{Style.NORMAL} {completion_message}\n")
        sys.stderr.flush()


class Progress:
    """Track and display progress through research phases."""

    def __init__(self, subject_matter: str, display_header: bool = True):
        self.subject_matter = subject_matter
        self.indicator: Optional[Spinner] = None
        self.start_timestamp = time.time()

        if display_header:
            self._display_header()

    def _display_header(self):
        sys.stderr.write(f"{COMPACT_HEADER}\n")
        sys.stderr.write(f"{Style.SUBDUED}Topic: {Style.NORMAL}{Style.EMPHASIZED}{self.subject_matter}{Style.NORMAL}\n\n")
        sys.stderr.flush()

    def start_reddit(self):
        msg = random.choice(REDDIT_MSGS)
        self.indicator = Spinner(f"{Style.AMBER}Reddit{Style.NORMAL} {msg}", Style.AMBER)
        self.indicator.start()

    def end_reddit(self, item_count: int):
        if self.indicator:
            self.indicator.stop(f"{Style.AMBER}Reddit{Style.NORMAL} Found {item_count} threads")

    def start_reddit_enrich(self, current_position: int, total_count: int):
        if self.indicator:
            self.indicator.stop()
        msg = random.choice(ENRICH_MSGS)
        self.indicator = Spinner(f"{Style.AMBER}Reddit{Style.NORMAL} [{current_position}/{total_count}] {msg}", Style.AMBER)
        self.indicator.start()

    def update_reddit_enrich(self, current_position: int, total_count: int):
        if self.indicator:
            msg = random.choice(ENRICH_MSGS)
            self.indicator.update(f"{Style.AMBER}Reddit{Style.NORMAL} [{current_position}/{total_count}] {msg}")

    def end_reddit_enrich(self):
        if self.indicator:
            self.indicator.stop(f"{Style.AMBER}Reddit{Style.NORMAL} Enriched with engagement data")

    def start_x(self):
        msg = random.choice(X_MSGS)
        self.indicator = Spinner(f"{Style.AZURE}X{Style.NORMAL} {msg}", Style.AZURE)
        self.indicator.start()

    def end_x(self, item_count: int):
        if self.indicator:
            self.indicator.stop(f"{Style.AZURE}X{Style.NORMAL} Found {item_count} posts")

    def start_processing(self):
        msg = random.choice(PROCESS_MSGS)
        self.indicator = Spinner(f"{Style.MAGENTA}Processing{Style.NORMAL} {msg}", Style.MAGENTA)
        self.indicator.start()

    def end_processing(self):
        if self.indicator:
            self.indicator.stop()

    def show_complete(self, reddit_count: int, x_count: int, youtube_count: int = 0, linkedin_count: int = 0):
        elapsed = time.time() - self.start_timestamp
        sep = f"{Style.SUBDUED}{Style.EMPHASIZED}\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500{Style.NORMAL}"
        sys.stderr.write(f"\n{sep}\n")
        sys.stderr.write(f"{Style.LIME}{Style.EMPHASIZED}\u2713 Research complete{Style.NORMAL} ")
        sys.stderr.write(f"{Style.SUBDUED}({elapsed:.1f}s){Style.NORMAL}\n")
        sys.stderr.write(f"  {Style.AMBER}Reddit:{Style.NORMAL} {reddit_count} threads  ")
        sys.stderr.write(f"{Style.AZURE}X:{Style.NORMAL} {x_count} posts")
        if youtube_count > 0:
            sys.stderr.write(f"  {Style.CRIMSON}YouTube:{Style.NORMAL} {youtube_count} videos")
        if linkedin_count > 0:
            sys.stderr.write(f"  {Style.AZURE}LinkedIn:{Style.NORMAL} {linkedin_count} posts")
        sys.stderr.write(f"\n{sep}\n\n")
        sys.stderr.flush()

    def show_cached(self, cache_age_hours: float = None):
        age_display = f" ({cache_age_hours:.1f}h old)" if cache_age_hours is not None else ""
        sys.stderr.write(f"{Style.LIME}\u26a1{Style.NORMAL} {Style.SUBDUED}Using cached results{age_display} - use --refresh for fresh data{Style.NORMAL}\n\n")
        sys.stderr.flush()

    def show_error(self, error_description: str):
        sys.stderr.write(f"{Style.CRIMSON}\u2717 Error:{Style.NORMAL} {error_description}\n")
        sys.stderr.flush()

    def start_web_only(self):
        msg = random.choice(WEB_MSGS)
        self.indicator = Spinner(f"{Style.LIME}Web{Style.NORMAL} {msg}", Style.LIME)
        self.indicator.start()

    def end_web_only(self):
        if self.indicator:
            self.indicator.stop(f"{Style.LIME}Web{Style.NORMAL} Claude will search the web")

    def show_web_only_complete(self):
        elapsed = time.time() - self.start_timestamp
        sep = f"{Style.SUBDUED}{Style.EMPHASIZED}\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500{Style.NORMAL}"
        sys.stderr.write(f"\n{sep}\n")
        sys.stderr.write(f"{Style.LIME}{Style.EMPHASIZED}\u2713 Ready for web search{Style.NORMAL} ")
        sys.stderr.write(f"{Style.SUBDUED}({elapsed:.1f}s){Style.NORMAL}\n")
        sys.stderr.write(f"  {Style.LIME}Web:{Style.NORMAL} Claude will search blogs, docs & news\n")
        sys.stderr.write(f"{sep}\n\n")
        sys.stderr.flush()

    def start_tts(self):
        msg = random.choice(TTS_MSGS)
        self.indicator = Spinner(f"{Style.MAGENTA}Audio{Style.NORMAL} {msg}", Style.MAGENTA)
        self.indicator.start()

    def end_tts(self, output_file: str):
        if self.indicator:
            self.indicator.stop(f"{Style.MAGENTA}Audio{Style.NORMAL} Saved to {output_file}")

    def show_promo(self, missing_keys: str = "both"):
        if missing_keys == "both":
            sys.stderr.write(UPGRADE_NOTICE)
        elif missing_keys in SINGLE_KEY_HINTS:
            sys.stderr.write(SINGLE_KEY_HINTS[missing_keys])
        sys.stderr.flush()


def phase_status(phase_name: str, status_text: str):
    """Print a single phase-status line to stderr."""
    phase_styles = {
        "reddit": Style.AMBER,
        "x": Style.AZURE,
        "process": Style.MAGENTA,
        "done": Style.LIME,
        "error": Style.CRIMSON,
        "youtube": Style.TEAL,
        "linkedin": Style.AZURE,
    }
    color = phase_styles.get(phase_name, Style.NORMAL)
    sys.stderr.write(f"{color}\u25b8{Style.NORMAL} {status_text}\n")
    sys.stderr.flush()

