"""Chrome cookie access for BriefBot (Windows).

Chrome 127+ uses App-Bound Encryption (v20) which prevents external processes
from decrypting cookies. Chrome 130+ additionally validates the caller's
process path, making the COM IElevator approach impossible from Python.

Solution: The BriefBot Cookie Bridge Chrome extension reads decrypted cookies
via the chrome.cookies API (which runs inside Chrome and bypasses v20) and
sends them to a native messaging host that writes AUTH_TOKEN and CT0 to
~/.config/briefbot/.env. bird_x.py reads from that file.

See lib/cookie-bridge/ for the extension, native host, and setup script.
"""

import sys
from typing import Optional, Tuple


def get_x_auth_tokens() -> Optional[Tuple[str, str]]:
    """Stub — cookie extraction now handled by cookie-bridge Chrome extension.

    Returns None. AUTH_TOKEN/CT0 are read from .env by bird_x._get_x_cookie_env().
    """
    return None
