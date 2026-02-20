"""HTTP client with retry logic using only stdlib."""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
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
        sys.stderr.write(f"[NET] {msg}\n")
        sys.stderr.flush()


class NetworkFailure(Exception):
    """Network request failure with optional status code and raw body."""

    def __init__(
        self,
        description: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(description)
        self.status_code = status_code
        self.body = response_body


# Backward-compatible alias used across the codebase and tests.
HTTPError = NetworkFailure


def _retry_delay(attempt_index: int) -> float:
    return BACKOFF * (1.6 ** attempt_index) + (attempt_index * 0.09)


def _can_retry_status(status_code: int) -> bool:
    if status_code in (429, 503, 504):
        return True
    return status_code >= 500


def _prepare_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]],
    json_body: Optional[Dict[str, Any]],
) -> urllib.request.Request:
    outgoing_headers = dict(headers or {})
    outgoing_headers.setdefault("User-Agent", USER_AGENT)
    payload = None
    if json_body is not None:
        outgoing_headers.setdefault("Content-Type", "application/json")
        payload = json.dumps(json_body).encode("utf-8")
    return urllib.request.Request(url, data=payload, headers=outgoing_headers, method=method.upper())


def _decode_json_or_raise(body_text: str) -> Dict[str, Any]:
    if not body_text:
        return {}
    try:
        return json.loads(body_text)
    except json.JSONDecodeError as exc:
        _debug(f"JSON decode error: {exc}")
        raise NetworkFailure(f"Invalid JSON response: {exc}") from exc


def request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = TIMEOUT,
    retries: int = MAX_RETRIES,
) -> Dict[str, Any]:
    """Execute an HTTP request with automatic retry and return parsed JSON."""
    _debug(f"{method.upper()} {url}")
    if isinstance(json_body, dict):
        _debug(f"Payload keys: {sorted(json_body.keys())}")

    last_error: Optional[NetworkFailure] = None
    for attempt in range(max(1, retries)):
        req = _prepare_request(method, url, headers, json_body)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                _debug(f"Response: {resp.status} ({len(body)} bytes)")
                return _decode_json_or_raise(body)
        except urllib.error.HTTPError as exc:
            raw_body = None
            try:
                raw_body = exc.read().decode("utf-8")
            except Exception:
                raw_body = None
            _debug(f"HTTP Error {exc.code}: {exc.reason}")
            if raw_body:
                _debug(f"Error body: {raw_body[:500]}")
            last_error = NetworkFailure(
                f"HTTP {exc.code}: {exc.reason}", exc.code, raw_body
            )
            if not _can_retry_status(exc.code):
                raise last_error
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            _debug(f"URL Error: {reason}")
            last_error = NetworkFailure(f"URL Error: {reason}")
        except (OSError, TimeoutError, ConnectionResetError) as exc:
            label = type(exc).__name__
            _debug(f"Connection error: {label}: {exc}")
            last_error = NetworkFailure(f"Connection error: {label}: {exc}")

        if attempt < retries - 1:
            time.sleep(_retry_delay(attempt))

    if last_error is not None:
        raise last_error
    raise NetworkFailure("All retry attempts exhausted without a response")


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


def _normalize_reddit_endpoint(path: str) -> str:
    candidate = (path or "").strip().rstrip("/")
    if not candidate:
        candidate = "/"
    if not candidate.startswith("/"):
        candidate = f"/{candidate}"
    if not candidate.endswith(".json"):
        candidate = f"{candidate}.json"
    return candidate


def reddit_json(path: str) -> Dict[str, Any]:
    """Fetch Reddit JSON payload for a thread-like URL path."""
    endpoint = _normalize_reddit_endpoint(path)
    query = urllib.parse.urlencode({"raw_json": "1"})
    target = f"https://www.reddit.com{endpoint}?{query}"
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    return get(target, headers=request_headers)
