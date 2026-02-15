#
# Terminal Interface Utilities: Visual feedback components for the research tool
# Provides spinners, progress indicators, and styled output for the command line
#

import os
import sys
import time
import threading
import random
from typing import Optional

# Enable ANSI color support on Windows 10+ terminals
def _enable_windows_vt_processing():
    """Activate virtual terminal processing for ANSI escape codes on Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        for handle_id in (-11, -12):  # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
            handle = kernel32.GetStdHandle(handle_id)
            if handle == -1:
                continue
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass  # Non-fatal: Claude Code renders ANSI regardless

_enable_windows_vt_processing()

# Interactive TTY detection: gates animation (\r line overwrites), NOT colors.
# Colors are always on — Claude Code, macOS Terminal, Windows Terminal, and Linux
# terminals all render ANSI. Only disabled via NO_COLOR env var convention.
TERMINAL_AVAILABLE = sys.stderr.isatty()

# ANSI escape sequences for styling
class TerminalStyles:
    MAGENTA = '\033[95m'
    AZURE = '\033[94m'
    TEAL = '\033[96m'
    LIME = '\033[92m'
    AMBER = '\033[93m'
    CRIMSON = '\033[91m'
    EMPHASIZED = '\033[1m'
    SUBDUED = '\033[2m'
    NORMAL = '\033[0m'


# Preserve the original class name for API compatibility
Colors = TerminalStyles

# Respect NO_COLOR convention (https://no-color.org/)
if "NO_COLOR" in os.environ:
    for _attr in ("MAGENTA", "AZURE", "TEAL", "LIME", "AMBER", "CRIMSON",
                   "EMPHASIZED", "SUBDUED", "NORMAL"):
        setattr(TerminalStyles, _attr, "")


HEADER_ART = """{}{}\n   \u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557 \u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2557  \u2588\u2588\u2557\u2588\u2588\u2557   \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557\n  \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u255a\u2550\u2550\u2588\u2588\u2554\u2550\u2550\u255d\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2551  \u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\n  \u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\n  \u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551   \u2588\u2588\u2551   \u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2551\u2588\u2588\u2551   \u2588\u2588\u2551\u2588\u2588\u2554\u2550\u2550\u2550\u255d\n  \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551   \u2588\u2588\u2551   \u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551\n   \u255a\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u255d  \u255a\u2550\u255d   \u255a\u2550\u255d    \u255a\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d \u255a\u2550\u255d\n{}{}  30 days of research. 30 seconds of work.{}\n""".format(TerminalStyles.MAGENTA, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL, TerminalStyles.SUBDUED, TerminalStyles.NORMAL)

COMPACT_HEADER = "{}{}/briefbot{} {}\xb7 researching...{}".format(TerminalStyles.MAGENTA, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL, TerminalStyles.SUBDUED, TerminalStyles.NORMAL)

# Preserve the original variable names for API compatibility
BANNER = HEADER_ART
MINI_BANNER = COMPACT_HEADER

# Status messages for Reddit phase
REDDIT_STATUS_VARIANTS = [
    "Diving into Reddit threads...",
    "Scanning subreddits for gold...",
    "Reading what Redditors are saying...",
    "Exploring the front page of the internet...",
    "Finding the good discussions...",
    "Upvoting mentally...",
    "Scrolling through comments...",
]

# Status messages for X phase
X_STATUS_VARIANTS = [
    "Checking what X is buzzing about...",
    "Reading the timeline...",
    "Finding the hot takes...",
    "Scanning tweets and threads...",
    "Discovering trending insights...",
    "Following the conversation...",
    "Reading between the posts...",
]

# Status messages for enrichment phase
ENRICHMENT_STATUS_VARIANTS = [
    "Getting the juicy details...",
    "Fetching engagement metrics...",
    "Reading top comments...",
    "Extracting insights...",
    "Analyzing discussions...",
]

# Status messages for processing phase
PROCESSING_STATUS_VARIANTS = [
    "Crunching the data...",
    "Scoring and ranking...",
    "Finding patterns...",
    "Removing duplicates...",
    "Organizing findings...",
]

# Status messages for web-only mode
WEB_STATUS_VARIANTS = [
    "Searching the web...",
    "Finding blogs and docs...",
    "Crawling news sites...",
    "Discovering tutorials...",
]

# Status messages for TTS phase
TTS_STATUS_VARIANTS = [
    "Generating audio...",
    "Converting to speech...",
    "Recording the briefing...",
    "Synthesizing audio...",
]

# Preserve the original variable names for API compatibility
REDDIT_MESSAGES = REDDIT_STATUS_VARIANTS
X_MESSAGES = X_STATUS_VARIANTS
ENRICHING_MESSAGES = ENRICHMENT_STATUS_VARIANTS
PROCESSING_MESSAGES = PROCESSING_STATUS_VARIANTS
WEB_ONLY_MESSAGES = WEB_STATUS_VARIANTS

# Promotional content for users without API keys
UPGRADE_NOTICE = """
{}{}\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{}
{}\u26a1 UNLOCK THE FULL POWER OF /briefbot{}

{}Right now you're using web search only. Add API keys to unlock:{}

  {}\U0001f7e0 Reddit{} - Real upvotes, comments, and community insights
  {}\U0001f534 YouTube{} - Video discoveries with view counts
  {}\U0001f537 LinkedIn{} - Professional posts and insights
     \u2514\u2500 Add OPENAI_API_KEY (uses OpenAI's web_search)

  {}\U0001f535 X (Twitter){} - Real-time posts, likes, reposts from creators
     \u2514\u2500 Add XAI_API_KEY (uses xAI's live X search)

{}Setup:{} Edit {}~/.config/briefbot/.env{}
{}{}\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501{}
""".format(TerminalStyles.AMBER, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL, TerminalStyles.AMBER, TerminalStyles.NORMAL, TerminalStyles.SUBDUED, TerminalStyles.NORMAL, TerminalStyles.AMBER, TerminalStyles.NORMAL, TerminalStyles.CRIMSON, TerminalStyles.NORMAL, TerminalStyles.AZURE, TerminalStyles.NORMAL, TerminalStyles.TEAL, TerminalStyles.NORMAL, TerminalStyles.SUBDUED, TerminalStyles.NORMAL, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL, TerminalStyles.AMBER, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL)

UPGRADE_NOTICE_PLAIN = """
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
\u26a1 UNLOCK THE FULL POWER OF /briefbot

Right now you're using web search only. Add API keys to unlock:

  \U0001f7e0 Reddit - Real upvotes, comments, and community insights
  \U0001f534 YouTube - Video discoveries with view counts
  \U0001f537 LinkedIn - Professional posts and insights
     \u2514\u2500 Add OPENAI_API_KEY (uses OpenAI's web_search)

  \U0001f535 X (Twitter) - Real-time posts, likes, reposts from creators
     \u2514\u2500 Add XAI_API_KEY (uses xAI's live X search)

Setup: Edit ~/.config/briefbot/.env
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
"""

# Preserve the original variable names for API compatibility
PROMO_MESSAGE = UPGRADE_NOTICE
PROMO_MESSAGE_PLAIN = UPGRADE_NOTICE_PLAIN

# Shorter hints for single missing key
SINGLE_KEY_HINTS = {
    "reddit": "\n{}\U0001f4a1 Tip: Add {}{}{}{} to ~/.config/briefbot/.env for Reddit, YouTube & LinkedIn data!{}\n".format(TerminalStyles.SUBDUED, TerminalStyles.AMBER, "OPENAI_API_KEY", TerminalStyles.NORMAL, TerminalStyles.SUBDUED, TerminalStyles.NORMAL),
    "x": "\n{}\U0001f4a1 Tip: Add {}{}{}{} to ~/.config/briefbot/.env for X/Twitter data with real likes & reposts!{}\n".format(TerminalStyles.SUBDUED, TerminalStyles.TEAL, "XAI_API_KEY", TerminalStyles.NORMAL, TerminalStyles.SUBDUED, TerminalStyles.NORMAL),
}

SINGLE_KEY_HINTS_PLAIN = {
    "reddit": "\n\U0001f4a1 Tip: Add OPENAI_API_KEY to ~/.config/briefbot/.env for Reddit, YouTube & LinkedIn data!\n",
    "x": "\n\U0001f4a1 Tip: Add XAI_API_KEY to ~/.config/briefbot/.env for X/Twitter data with real likes & reposts!\n",
}

# Preserve the original variable names for API compatibility
PROMO_SINGLE_KEY = SINGLE_KEY_HINTS
PROMO_SINGLE_KEY_PLAIN = SINGLE_KEY_HINTS_PLAIN

# Animation frames
ROTATION_FRAMES = ['\u280b', '\u2819', '\u2839', '\u2838', '\u283c', '\u2834', '\u2826', '\u2827', '\u2807', '\u280f']
ELLIPSIS_FRAMES = ['   ', '.  ', '.. ', '...']

# Preserve the original variable names for API compatibility
SPINNER_FRAMES = ROTATION_FRAMES
DOTS_FRAMES = ELLIPSIS_FRAMES

# Preserve the original constant for API compatibility
IS_TTY = TERMINAL_AVAILABLE


class AnimatedIndicator:
    """Provides animated feedback during long-running operations."""

    def __init__(self, status_text: str = "Working", style_code: str = TerminalStyles.TEAL):
        self.status_text = status_text
        self.style_code = style_code
        self.active = False
        self.animation_thread: Optional[threading.Thread] = None
        self.frame_position = 0
        self.static_displayed = False

    def _animate(self):
        while self.active:
            current_frame = ROTATION_FRAMES[self.frame_position % len(ROTATION_FRAMES)]
            sys.stderr.write("\r{}{}{} {}  ".format(self.style_code, current_frame, TerminalStyles.NORMAL, self.status_text))
            sys.stderr.flush()
            self.frame_position += 1
            time.sleep(0.08)

    def start(self):
        self.active = True
        if TERMINAL_AVAILABLE:
            # Real terminal - animate
            self.animation_thread = threading.Thread(target=self._animate, daemon=True)
            self.animation_thread.start()
        else:
            # Not a TTY (Claude Code) - print once with color
            if not self.static_displayed:
                sys.stderr.write("{}\u23f3{} {}\n".format(self.style_code, TerminalStyles.NORMAL, self.status_text))
                sys.stderr.flush()
                self.static_displayed = True

    def update(self, new_status: str):
        self.status_text = new_status
        if not TERMINAL_AVAILABLE and not self.static_displayed:
            sys.stderr.write("{}\u23f3{} {}\n".format(self.style_code, TerminalStyles.NORMAL, new_status))
            sys.stderr.flush()

    def stop(self, completion_message: str = ""):
        self.active = False
        if self.animation_thread:
            self.animation_thread.join(timeout=0.2)
        if TERMINAL_AVAILABLE:
            sys.stderr.write("\r" + " " * 80 + "\r")
        if completion_message:
            sys.stderr.write("{}\u2713{} {}\n".format(TerminalStyles.LIME, TerminalStyles.NORMAL, completion_message))
        sys.stderr.flush()


# Preserve the original class name for API compatibility
Spinner = AnimatedIndicator


class ResearchProgressTracker:
    """Displays progress through research phases."""

    def __init__(self, subject_matter: str, display_header: bool = True):
        self.subject_matter = subject_matter
        self.indicator: Optional[AnimatedIndicator] = None
        self.start_timestamp = time.time()

        if display_header:
            self._display_header()

    def _display_header(self):
        sys.stderr.write(COMPACT_HEADER + "\n")
        sys.stderr.write("{}Topic: {}{}{}{}\n\n".format(TerminalStyles.SUBDUED, TerminalStyles.NORMAL, TerminalStyles.EMPHASIZED, self.subject_matter, TerminalStyles.NORMAL))
        sys.stderr.flush()

    def start_reddit(self):
        status_variant = random.choice(REDDIT_STATUS_VARIANTS)
        self.indicator = AnimatedIndicator("{}Reddit{} {}".format(TerminalStyles.AMBER, TerminalStyles.NORMAL, status_variant), TerminalStyles.AMBER)
        self.indicator.start()

    def end_reddit(self, item_count: int):
        if self.indicator:
            self.indicator.stop("{}Reddit{} Found {} threads".format(TerminalStyles.AMBER, TerminalStyles.NORMAL, item_count))

    def start_reddit_enrich(self, current_position: int, total_count: int):
        if self.indicator:
            self.indicator.stop()
        status_variant = random.choice(ENRICHMENT_STATUS_VARIANTS)
        self.indicator = AnimatedIndicator("{}Reddit{} [{}/{}] {}".format(TerminalStyles.AMBER, TerminalStyles.NORMAL, current_position, total_count, status_variant), TerminalStyles.AMBER)
        self.indicator.start()

    def update_reddit_enrich(self, current_position: int, total_count: int):
        if self.indicator:
            status_variant = random.choice(ENRICHMENT_STATUS_VARIANTS)
            self.indicator.update("{}Reddit{} [{}/{}] {}".format(TerminalStyles.AMBER, TerminalStyles.NORMAL, current_position, total_count, status_variant))

    def end_reddit_enrich(self):
        if self.indicator:
            self.indicator.stop("{}Reddit{} Enriched with engagement data".format(TerminalStyles.AMBER, TerminalStyles.NORMAL))

    def start_x(self):
        status_variant = random.choice(X_STATUS_VARIANTS)
        self.indicator = AnimatedIndicator("{}X{} {}".format(TerminalStyles.TEAL, TerminalStyles.NORMAL, status_variant), TerminalStyles.TEAL)
        self.indicator.start()

    def end_x(self, item_count: int):
        if self.indicator:
            self.indicator.stop("{}X{} Found {} posts".format(TerminalStyles.TEAL, TerminalStyles.NORMAL, item_count))

    def start_processing(self):
        status_variant = random.choice(PROCESSING_STATUS_VARIANTS)
        self.indicator = AnimatedIndicator("{}Processing{} {}".format(TerminalStyles.MAGENTA, TerminalStyles.NORMAL, status_variant), TerminalStyles.MAGENTA)
        self.indicator.start()

    def end_processing(self):
        if self.indicator:
            self.indicator.stop()

    def show_complete(self, reddit_count: int, x_count: int, youtube_count: int = 0, linkedin_count: int = 0):
        elapsed_seconds = time.time() - self.start_timestamp
        separator = "{}{}\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500{}".format(TerminalStyles.SUBDUED, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL)
        sys.stderr.write("\n" + separator + "\n")
        sys.stderr.write("{}{}\u2713 Research complete{} ".format(TerminalStyles.LIME, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL))
        sys.stderr.write("{}({:.1f}s){}\n".format(TerminalStyles.SUBDUED, elapsed_seconds, TerminalStyles.NORMAL))
        sys.stderr.write("  {}Reddit:{} {} threads  ".format(TerminalStyles.AMBER, TerminalStyles.NORMAL, reddit_count))
        sys.stderr.write("{}X:{} {} posts".format(TerminalStyles.TEAL, TerminalStyles.NORMAL, x_count))
        if youtube_count > 0:
            sys.stderr.write("  {}YouTube:{} {} videos".format(TerminalStyles.CRIMSON, TerminalStyles.NORMAL, youtube_count))
        if linkedin_count > 0:
            sys.stderr.write("  {}LinkedIn:{} {} posts".format(TerminalStyles.AZURE, TerminalStyles.NORMAL, linkedin_count))
        sys.stderr.write("\n" + separator + "\n\n")
        sys.stderr.flush()

    def show_cached(self, cache_age_hours: float = None):
        if cache_age_hours is not None:
            age_display = " ({:.1f}h old)".format(cache_age_hours)
        else:
            age_display = ""
        sys.stderr.write("{}\u26a1{} {}Using cached results{} - use --refresh for fresh data{}\n\n".format(TerminalStyles.LIME, TerminalStyles.NORMAL, TerminalStyles.SUBDUED, age_display, TerminalStyles.NORMAL))
        sys.stderr.flush()

    def show_error(self, error_description: str):
        sys.stderr.write("{}\u2717 Error:{} {}\n".format(TerminalStyles.CRIMSON, TerminalStyles.NORMAL, error_description))
        sys.stderr.flush()

    def start_web_only(self):
        """Initiates web-only mode indicator."""
        status_variant = random.choice(WEB_STATUS_VARIANTS)
        self.indicator = AnimatedIndicator("{}Web{} {}".format(TerminalStyles.LIME, TerminalStyles.NORMAL, status_variant), TerminalStyles.LIME)
        self.indicator.start()

    def end_web_only(self):
        """Terminates web-only indicator."""
        if self.indicator:
            self.indicator.stop("{}Web{} Claude will search the web".format(TerminalStyles.LIME, TerminalStyles.NORMAL))

    def show_web_only_complete(self):
        """Displays completion for web-only mode."""
        elapsed_seconds = time.time() - self.start_timestamp
        separator = "{}{}\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500{}".format(TerminalStyles.SUBDUED, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL)
        sys.stderr.write("\n" + separator + "\n")
        sys.stderr.write("{}{}\u2713 Ready for web search{} ".format(TerminalStyles.LIME, TerminalStyles.EMPHASIZED, TerminalStyles.NORMAL))
        sys.stderr.write("{}({:.1f}s){}\n".format(TerminalStyles.SUBDUED, elapsed_seconds, TerminalStyles.NORMAL))
        sys.stderr.write("  {}Web:{} Claude will search blogs, docs & news\n".format(TerminalStyles.LIME, TerminalStyles.NORMAL))
        sys.stderr.write(separator + "\n\n")
        sys.stderr.flush()

    def start_tts(self):
        """Initiates TTS generation indicator."""
        status_variant = random.choice(TTS_STATUS_VARIANTS)
        self.indicator = AnimatedIndicator("{}Audio{} {}".format(TerminalStyles.MAGENTA, TerminalStyles.NORMAL, status_variant), TerminalStyles.MAGENTA)
        self.indicator.start()

    def end_tts(self, output_file: str):
        """Terminates TTS indicator with file path."""
        if self.indicator:
            self.indicator.stop("{}Audio{} Saved to {}".format(TerminalStyles.MAGENTA, TerminalStyles.NORMAL, output_file))

    def show_promo(self, missing_keys: str = "both"):
        """
        Displays promotional content for missing API keys.

        Args:
            missing_keys: Which keys are absent - 'both', 'reddit', or 'x'
        """
        if missing_keys == "both":
            sys.stderr.write(UPGRADE_NOTICE)
        elif missing_keys in SINGLE_KEY_HINTS:
            sys.stderr.write(SINGLE_KEY_HINTS[missing_keys])
        sys.stderr.flush()


# Preserve the original class name for API compatibility
ProgressDisplay = ResearchProgressTracker


def emit_phase_status(phase_name: str, status_text: str):
    """Outputs a phase status message."""
    phase_styles = {
        "reddit": TerminalStyles.AMBER,
        "x": TerminalStyles.TEAL,
        "process": TerminalStyles.MAGENTA,
        "done": TerminalStyles.LIME,
        "error": TerminalStyles.CRIMSON,
    }
    style_code = phase_styles.get(phase_name, TerminalStyles.NORMAL)
    sys.stderr.write("{}\u25b8{} {}\n".format(style_code, TerminalStyles.NORMAL, status_text))
    sys.stderr.flush()


# Preserve the original function name for API compatibility
print_phase = emit_phase_status
