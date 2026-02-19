"""HTTP client with retry logic using only stdlib."""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

TIMEOUT = 25
MAX_RETRIES = 4
BACKOFF = 0.75
USER_AGENT = "briefbot-skill/1.0 (Claude Code Skill)"

DEBUG = os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str):
    """Write a debug message to stderr if debug mode is on."""
    if DEBUG:
        sys.stderr.write(f"[HTTP] {msg}\n")
        sys.stderr.flush()


class HTTPError(Exception):
    """HTTP request failure with optional status code and response body."""

    def __init__(
        self,
        description: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(description)
        self.status_code = status_code
        self.body = response_body


def request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = TIMEOUT,
    retries: int = MAX_RETRIES,
) -> Dict[str, Any]:
    """Execute an HTTP request with automatic retry and return parsed JSON."""
    headers = headers or {}
    headers.setdefault("User-Agent", USER_AGENT)

    encoded = None
    if json_body is not None:
        encoded = json.dumps(json_body).encode('utf-8')
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=encoded, headers=headers, method=method)

    _debug(f"{method} {url}")
    if json_body:
        _debug(f"Payload keys: {list(json_body.keys())}")

    last_err = None

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode('utf-8')
                _debug(f"Response: {resp.status} ({len(body)} bytes)")
                return json.loads(body) if body else {}

        except json.JSONDecodeError as e:
            _debug(f"JSON decode error: {e}")
            last_err = HTTPError(f"Invalid JSON response: {e}")
            raise last_err

        except urllib.error.HTTPError as e:
            err_body = None
            try:
                err_body = e.read().decode('utf-8')
            except Exception:
                pass

            _debug(f"HTTP Error {e.code}: {e.reason}")
            if err_body:
                _debug(f"Error body: {err_body[:500]}")

            last_err = HTTPError(f"HTTP {e.code}: {e.reason}", e.code, err_body)

            # Don't retry client errors (4xx) except rate limits (429) and 503
            if 400 <= e.code < 500 and e.code not in (429, 503):
                raise last_err

            if attempt < retries - 1:
                delay = BACKOFF * (2 ** attempt) + (attempt * 0.1)
                time.sleep(delay)

        except (OSError, TimeoutError, ConnectionResetError) as e:
            etype = type(e).__name__
            _debug(f"Connection error: {etype}: {e}")
            last_err = HTTPError(f"Connection error: {etype}: {e}")

            if attempt < retries - 1:
                delay = BACKOFF * (2 ** attempt) + (attempt * 0.1)
                time.sleep(delay)

        except urllib.error.URLError as e:
            _debug(f"URL Error: {e.reason}")
            last_err = HTTPError(f"URL Error: {e.reason}")

            if attempt < retries - 1:
                delay = BACKOFF * (2 ** attempt) + (attempt * 0.1)
                time.sleep(delay)

    if last_err:
        raise last_err

    raise HTTPError("All retry attempts exhausted without a response")


def get(url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
    """Convenience wrapper for GET requests."""
    return request("GET", url, headers=headers, **kwargs)


def post(
    url: str,
    json_body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Convenience wrapper for POST requests with JSON body."""
    return request("POST", url, headers=headers, json_body=json_body, **kwargs)


def reddit_json(path: str) -> Dict[str, Any]:
    """Fetch JSON data for a Reddit thread path."""
    if not path.startswith('/'):
        path = f"/{path}"

    path = path.rstrip('/')
    if not path.endswith('.json'):
        path = f"{path}.json"

    url = f"https://www.reddit.com{path}"
    if "?" not in url:
        url += "?raw_json=1"
    else:
        url += "&raw_json=1"
    return get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})


# Backward compat aliases for out-of-scope callers (models.py etc.)
def perform_get_request(url, request_headers=None, **kw):
    return get(url, headers=request_headers, **kw)

def perform_post_request(url, json_payload=None, request_headers=None, **kw):
    return post(url, json_payload, headers=request_headers, **kw)

fetch_reddit_thread_data = reddit_json
