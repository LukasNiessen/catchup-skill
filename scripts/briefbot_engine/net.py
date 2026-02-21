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
USER_AGENT = "briefbot-net/2026.2"
DEBUG = False


def _debug_enabled() -> bool:
    return DEBUG or os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes", "on")


def _debug(msg: str) -> None:
    if _debug_enabled():
        sys.stderr.write(f"[NET] {msg}\n")
        sys.stderr.flush()


class ApiError(Exception):
    """Raised on HTTP or transport failures."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = response_body


HTTPError = ApiError


@dataclass
class RetryPolicy:
    attempts: int = DEFAULT_ATTEMPTS
    min_wait: float = 0.35
    max_wait: float = 4.0

    def sleep(self, attempt_index: int) -> None:
        base = self.min_wait * (2 ** attempt_index)
        jitter = random.uniform(0.0, 0.2)
        time.sleep(min(self.max_wait, base + jitter))


def _retryable(code: int) -> bool:
    return code in (408, 425, 429, 500, 502, 503, 504) or code >= 520


def _decode_json(payload: str) -> Dict[str, Any]:
    if not payload:
        return {}
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ApiError(f"Invalid JSON payload: {exc}") from exc
    if isinstance(parsed, dict):
        return parsed
    return {"data": parsed}


def _prepare_payload(json_body: Optional[Mapping[str, Any]]) -> Optional[bytes]:
    if json_body is None:
        return None
    return json.dumps(dict(json_body), ensure_ascii=False).encode("utf-8")


class HttpClient:
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
        combined = dict(headers or {})
        combined.setdefault("User-Agent", USER_AGENT)
        if json_body is not None:
            combined.setdefault("Content-Type", "application/json")

        last_error: Optional[ApiError] = None
        attempts = max(1, int(self.retry.attempts))
        for attempt in range(attempts):
            req = urllib.request.Request(
                url,
                data=payload,
                headers=combined,
                method=method.upper(),
            )
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
                last_error = ApiError(f"HTTP {exc.code}: {exc.reason}", exc.code, body or None)
                _debug(f"{method.upper()} {url} -> HTTP {exc.code}")
                if not _retryable(exc.code):
                    raise last_error
            except urllib.error.URLError as exc:
                reason = getattr(exc, "reason", exc)
                last_error = ApiError(f"Transport error: {reason}")
                _debug(f"Transport error for {url}: {reason}")
            except (ConnectionError, TimeoutError, OSError) as exc:
                last_error = ApiError(f"{type(exc).__name__}: {exc}")
                _debug(f"Connection failure for {url}: {exc}")

            if attempt + 1 < attempts:
                self.retry.sleep(attempt)

        if last_error is not None:
            raise last_error
        raise ApiError("Request failed without a captured error")


def request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_ATTEMPTS,
) -> Dict[str, Any]:
    client = HttpClient(timeout=timeout, retry_policy=RetryPolicy(attempts=retries))
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


def _reddit_endpoint(path: str) -> str:
    piece = (path or "").strip().rstrip("/")
    if not piece:
        piece = "/"
    if not piece.startswith("/"):
        piece = f"/{piece}"
    if not piece.endswith(".json"):
        piece = f"{piece}.json"
    return piece


def reddit_json(path: str) -> Dict[str, Any]:
    endpoint = _reddit_endpoint(path)
    query = urllib.parse.urlencode({"raw_json": "1"})
    url = f"https://www.reddit.com{endpoint}?{query}"
    return get(url, headers={"Accept": "application/json"})
