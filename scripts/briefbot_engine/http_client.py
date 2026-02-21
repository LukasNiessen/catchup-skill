"""HTTP utilities and lightweight retry logic."""

from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

DEFAULT_TIMEOUT_SECONDS = 26
DEFAULT_ATTEMPTS = 3
USER_AGENT = "briefbot-http/2026.2"
DEBUG = False


def _debug_enabled() -> bool:
    return DEBUG or os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes", "on")


def _debug(msg: str) -> None:
    if _debug_enabled():
        sys.stderr.write(f"[HTTP] {msg}\n")
        sys.stderr.flush()


class TransportError(Exception):
    """Raised on HTTP or transport failures."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None, url: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = response_body
        self.url = url


HTTPError = TransportError


@dataclass
class RetryPolicy:
    attempts: int = DEFAULT_ATTEMPTS
    base: float = 0.4
    cap: float = 4.0
    jitter: float = 0.25

    def delays(self):
        total = max(1, int(self.attempts))
        for attempt in range(total):
            if attempt == 0:
                yield 0.0
                continue
            backoff = min(self.cap, self.base * (2 ** (attempt - 1)))
            wiggle = random.uniform(0.0, self.jitter)
            yield backoff + wiggle


def _retryable(code: int) -> bool:
    return code in (408, 425, 429, 500, 502, 503, 504, 522, 524) or code >= 520


def _decode_json(payload: str) -> Dict[str, Any]:
    if not payload:
        return {}
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise TransportError(f"Malformed JSON payload: {exc}") from exc
    if isinstance(parsed, dict):
        return parsed
    return {"data": parsed}


def _prepare_payload(json_body: Optional[Mapping[str, Any]]) -> Optional[bytes]:
    if json_body is None:
        return None
    return json.dumps(dict(json_body), ensure_ascii=False).encode("utf-8")


def _build_request(url: str, method: str, headers: Optional[Mapping[str, str]], payload: Optional[bytes]) -> urllib.request.Request:
    combined = dict(headers or {})
    combined.setdefault("User-Agent", USER_AGENT)
    combined.setdefault("Accept", "application/json")
    if payload is not None:
        combined.setdefault("Content-Type", "application/json")
    return urllib.request.Request(url, data=payload, headers=combined, method=method.upper())


class JsonSession:
    """Minimal JSON HTTP client with retry handling."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT_SECONDS, retry_policy: Optional[RetryPolicy] = None):
        self.timeout = timeout
        self.retry = retry_policy or RetryPolicy()

    def request_json(
        self,
        method: str,
        url: str,
        headers: Optional[Mapping[str, str]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = _prepare_payload(json_body)
        last_error: Optional[TransportError] = None

        for delay in self.retry.delays():
            if delay:
                time.sleep(delay)
            req = _build_request(url, method, headers, payload)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8")
                    _debug(f"{method.upper()} {url} -> {response.status} ({len(raw)} bytes)")
                    return _decode_json(raw)
            except urllib.error.HTTPError as exc:
                body = ""
                try:
                    body = exc.read().decode("utf-8")
                except Exception:
                    body = ""
                last_error = TransportError(f"Status {exc.code} {exc.reason}", exc.code, body or None, url)
                _debug(f"{method.upper()} {url} -> HTTP {exc.code}")
                if not _retryable(exc.code):
                    raise last_error
            except urllib.error.URLError as exc:
                reason = getattr(exc, "reason", exc)
                last_error = TransportError(f"Transport error: {reason}", url=url)
                _debug(f"Transport error for {url}: {reason}")
            except (ConnectionError, TimeoutError, OSError) as exc:
                last_error = TransportError(f"{type(exc).__name__}: {exc}", url=url)
                _debug(f"Connection failure for {url}: {exc}")

        if last_error is not None:
            raise last_error
        raise TransportError("Request failed after retries", url=url)


def request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_ATTEMPTS,
) -> Dict[str, Any]:
    client = JsonSession(timeout=timeout, retry_policy=RetryPolicy(attempts=retries))
    return client.request_json(method, url, headers=headers, json_body=json_body)


def get(url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
    return request("GET", url, headers=headers, **kwargs)


def post(
    url: str,
    json_body: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    return request("POST", url, headers=headers, json_body=json_body, **kwargs)


def reddit_thread_url(path_or_url: str) -> str:
    raw = (path_or_url or "").strip()
    if not raw:
        raw = "/"
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urllib.parse.urlparse(raw)
        raw = parsed.path or "/"
    if not raw.startswith("/"):
        raw = f"/{raw}"
    if not raw.endswith(".json"):
        raw = f"{raw}.json"
    query = urllib.parse.urlencode({"raw_json": "1", "context": "0", "depth": "1", "limit": "50", "sort": "top"})
    return f"https://www.reddit.com{raw}?{query}"


def reddit_json(path_or_url: str) -> Dict[str, Any]:
    url = reddit_thread_url(path_or_url)
    return get(url, headers={"Accept": "application/json"})
