"""X/Twitter discovery via xAI search tool."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from .. import net
from . import registry


def _err(msg: str) -> None:
    sys.stderr.write(f"[X ERROR] {msg}\n")
    sys.stderr.flush()


def _log(message: str) -> None:
    if os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write(f"[XAI_X] {message}\n")
        sys.stderr.flush()


API_URL = "https://api.x.ai/v1/responses"

DEPTH_TARGETS = {
    "quick": {"min": 7, "max": 14},
    "default": {"min": 14, "max": 30},
    "deep": {"min": 28, "max": 58},
}

X_DISCOVERY_PROMPT = """Search X (Twitter) for posts about: {topic}

Window: {from_date} to {to_date}. Target {min_items}-{max_items} meaningful posts.

Return JSON only:
{{
  "posts": [
    {{
      "excerpt": "Short post text",
      "link": "https://x.com/user/status/1234567890",
      "handle": "example_user",
      "posted": "2026-01-20",
      "metrics": {{
        "likes": 250,
        "reposts": 40,
        "replies": 30,
        "quotes": 8
      }},
      "signal": 0.92,
      "reason": "Explains why this post matters"
    }}
  ]
}}

Notes:
- signal ranges 0.0 (off-topic) to 1.0 (directly on-topic)
- dates must be YYYY-MM-DD or null if uncertain
- metrics fields can be null if unavailable
- favor original insight over retweets and link dumps
"""


def _make_request(
    key: str,
    model: str,
    prompt_content: str,
    headers: Dict[str, str],
    timeout: int,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "tools": [{"type": "x_search"}],
        "input": [{"role": "user", "content": prompt_content}],
    }

    _log(f"  Endpoint: {API_URL}")
    _log(f"  Payload model: {payload['model']}, tools: {[t['type'] for t in payload['tools']]}, input_length: {len(payload['input'][0]['content'])} chars")
    response = net.post(API_URL, payload, headers=headers, timeout=timeout)
    return response


MODEL_FALLBACKS = [
    "grok-4-1-fast",
    "grok-4-1",
    "grok-4-fast",
    "grok-4",
    "grok-4-1-fast-non-reasoning",
    "grok-4-1-non-reasoning",
    "grok-4-non-reasoning",
    "grok-3",
    "grok-3-fast",
    "grok-3-mini",
]


def _is_model_access_error(err: net.HTTPError) -> bool:
    if err.status_code is None:
        return False
    if err.status_code not in (400, 401, 403, 404, 409, 422):
        return False
    if not err.body:
        return err.status_code == 403
    body_lower = err.body.lower()
    markers = (
        "does not have access",
        "organization must be verified",
        "not available",
        "model not found",
        "access denied",
        "permission",
        "insufficient scope",
    )
    return any(marker in body_lower for marker in markers)


def _extract_posts_blob(output_text: str) -> List[Dict[str, Any]]:
    if not output_text:
        return []
    decoder = json.JSONDecoder()
    cursor = 0
    while True:
        start = output_text.find("{", cursor)
        if start < 0:
            return []
        try:
            candidate, consumed = decoder.raw_decode(output_text[start:])
        except json.JSONDecodeError:
            cursor = start + 1
            continue
        if isinstance(candidate, dict) and isinstance(candidate.get("posts"), list):
            return candidate["posts"]
        cursor = start + max(consumed, 1)


def _pick_text_payload(api_response: Dict[str, Any]) -> str:
    output = api_response.get("output")
    if isinstance(output, str) and output.strip():
        return output

    if isinstance(output, list):
        for entry in output:
            if isinstance(entry, str) and entry.strip():
                return entry
            if not isinstance(entry, dict):
                continue
            text = entry.get("text")
            if isinstance(text, str) and text.strip():
                return text
            if entry.get("type") != "message":
                continue
            for block in entry.get("content", []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "output_text":
                    block_text = block.get("text", "")
                    if isinstance(block_text, str) and block_text.strip():
                        return block_text

    for choice in api_response.get("choices", []):
        if not isinstance(choice, dict):
            continue
        message = choice.get("message", {})
        if not isinstance(message, dict):
            continue
        legacy = message.get("content")
        if isinstance(legacy, str) and legacy.strip():
            return legacy
    return ""


def _normalize_metrics(raw_metrics: Any) -> Optional[Dict[str, Optional[int]]]:
    if not isinstance(raw_metrics, dict):
        return None
    normalized: Dict[str, Optional[int]] = {}
    for metric in ("likes", "reposts", "replies", "quotes"):
        value = raw_metrics.get(metric)
        if value in (None, ""):
            normalized[metric] = None
            continue
        try:
            normalized[metric] = int(value)
        except (ValueError, TypeError):
            normalized[metric] = None
    return normalized if any(v is not None for v in normalized.values()) else None


def _safe_signal(raw: Any) -> float:
    try:
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return 0.55


def search(
    key: str,
    model: str,
    topic: str,
    start: str,
    end: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    _log("=== search START ===")

    if mock_response is not None:
        _log("  Using MOCK response")
        return mock_response

    depth_bucket = DEPTH_TARGETS.get(depth, DEPTH_TARGETS["default"])
    min_items = depth_bucket["min"]
    max_items = depth_bucket["max"]

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    timeout_map = {"quick": 70, "default": 100, "deep": 145}
    timeout = timeout_map.get(depth, 100)

    prompt_content = X_DISCOVERY_PROMPT.format(
        topic=topic,
        from_date=start,
        to_date=end,
        min_items=min_items,
        max_items=max_items,
    )

    tried = {model}
    try:
        response = _make_request(key, model, prompt_content, headers, timeout)
        _log("=== search END ===")
        return response
    except net.HTTPError as e:
        if not _is_model_access_error(e):
            raise
        _err(
            f"Model '{model}' appears unavailable for this key "
            f"(status {e.status_code}); trying fallbacks..."
        )
        registry.set_cached_model("xai", "")
        last_err = e

    fallbacks = [m for m in MODEL_FALLBACKS if m not in tried]
    for fallback_model in fallbacks:
        tried.add(fallback_model)
        try:
            response = _make_request(key, fallback_model, prompt_content, headers, timeout)
            _err(f"Fallback succeeded with model '{fallback_model}'")
            registry.set_cached_model("xai", fallback_model)
            _log("=== search END (via fallback) ===")
            return response
        except net.HTTPError as e:
            if _is_model_access_error(e):
                last_err = e
                continue
            raise

    discovered = registry.discover_xai_models(key)
    dynamic_candidates = [m for m in discovered if m.startswith("grok-") and m not in tried]

    for fallback_model in dynamic_candidates:
        tried.add(fallback_model)
        try:
            response = _make_request(key, fallback_model, prompt_content, headers, timeout)
            _err(f"Dynamic fallback succeeded with model '{fallback_model}'")
            registry.set_cached_model("xai", fallback_model)
            _log("=== search END (via dynamic discovery) ===")
            return response
        except net.HTTPError as e:
            if _is_model_access_error(e):
                last_err = e
                continue
            raise

    total = len(tried)
    _err(f"All {total} candidate models were rejected by access constraints")
    _log(f"  Tried models: {sorted(tried)}")
    _log("=== search END (all fallbacks exhausted) ===")
    if last_err:
        raise last_err
    raise net.HTTPError("All models were rejected by access constraints", 403)


def parse_x_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    _log("=== parse_x_response START ===")
    items: List[Dict[str, Any]] = []

    api_error = api_response.get("error")
    if api_error:
        message = api_error.get("message") if isinstance(api_error, dict) else str(api_error)
        _err(f"xAI API error: {message}")
        if net.DEBUG:
            _err(f"Full error response: {json.dumps(api_response, indent=2)[:1000]}")
        _log("=== parse_x_response END (api error) ===")
        return items

    payload_text = _pick_text_payload(api_response)
    if not payload_text:
        _log("No text payload found in xAI response")
        _log("=== parse_x_response END (empty payload) ===")
        return items

    candidates = _extract_posts_blob(payload_text)
    _log(f"Candidate items extracted: {len(candidates)}")

    for row in candidates:
        if not isinstance(row, dict):
            continue
        link = str(row.get("link", "")).strip()
        if not link:
            continue

        date_value = row.get("posted")
        if date_value and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_value)):
            date_value = None

        items.append(
            {
                "uid": f"X{len(items) + 1}",
                "excerpt": str(row.get("excerpt", "")).strip()[:500],
                "link": link,
                "handle": str(row.get("handle", "")).strip().lstrip("@"),
                "posted": date_value,
                "metrics": _normalize_metrics(row.get("metrics")),
                "reason": str(row.get("reason", "")).strip(),
                "signal": _safe_signal(row.get("signal")),
            }
        )

    _log(f"=== parse_x_response END ({len(items)} items) ===")
    return items
