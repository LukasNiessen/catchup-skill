"""X/Twitter discovery via the xAI API with live search."""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from .. import net
from . import registry


def _err(msg: str):
    """Log an error to stderr."""
    sys.stderr.write(f"[X ERROR] {msg}\n")
    sys.stderr.flush()


def _log(message: str):
    """Emit a debug line to stderr when BRIEFBOT_DEBUG is set."""
    if os.environ.get("BRIEFBOT_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write(f"[XAI_X] {message}\n")
        sys.stderr.flush()


API_URL = "https://api.x.ai/v1/responses"

# How many results to request per depth level
DEPTH_TARGETS = {
    "quick": {"min": 9, "max": 14},
    "default": {"min": 18, "max": 30},
    "deep": {"min": 34, "max": 58},
}

X_DISCOVERY_PROMPT = """Search X (formerly Twitter) for real-time discussion about: {topic}

Window: {from_date} to {to_date}. Target {min_items}-{max_items} substantive posts.

Respond with raw JSON only, no markdown fencing or explanation:
{{
  "items": [
    {{
      "text": "Abbreviated post content",
      "url": "https://x.com/user/status/1234567890",
      "author_handle": "example_user",
      "date": "2026-01-20",
      "engagement": {{
        "likes": 250,
        "reposts": 40,
        "replies": 30,
        "quotes": 8
      }},
      "why_relevant": "Provides firsthand perspective on the topic",
      "relevance": 0.92
    }}
  ]
}}

Constraints:
- relevance ranges from 0.0 (off-topic) to 1.0 (directly on-topic)
- dates in YYYY-MM-DD format; use null when uncertain
- engagement fields accept null when metrics are unavailable
- prioritize original analysis and commentary over retweets or link-drops
- surface a range of viewpoints when the topic is debated"""


def _make_request(
    key: str,
    model: str,
    prompt_content: str,
    headers: Dict[str, str],
    timeout: int,
) -> Dict[str, Any]:
    """Send a single xAI API request and return the response dict."""
    payload = {
        "model": model,
        "tools": [
            {"type": "x_search"},
        ],
        "input": [
            {
                "role": "user",
                "content": prompt_content,
            }
        ],
    }

    _log(f"  Endpoint: {API_URL}")
    _log(f"  Payload model: {payload['model']}, tools: {[t['type'] for t in payload['tools']]}, input_length: {len(payload['input'][0]['content'])} chars")
    _log("  Sending POST request...")

    response = net.post(API_URL, payload, headers=headers, timeout=timeout)

    _log(f"  Response received, type: {type(response).__name__}, keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
    if isinstance(response, dict):
        if "error" in response:
            _log(f"  Response contains ERROR: {str(response['error'])[:300]}")
        if "output" in response:
            output = response["output"]
            if isinstance(output, list):
                _log(f"  Response output: list with {len(output)} elements")
                for i, elem in enumerate(output):
                    if isinstance(elem, dict):
                        _log(f"    output[{i}]: type='{elem.get('type', '?')}', keys={list(elem.keys())}")
            elif isinstance(output, str):
                _log(f"  Response output: string ({len(output)} chars)")
        if "id" in response:
            _log(f"  Response id: {response['id']}")
        if "model" in response:
            _log(f"  Response model: {response['model']}")

    return response


# Fallback models to try when the primary model returns 403 (permission denied).
# Ordered by preference: reasoning models first, then non-reasoning variants.
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
    """Return True when an HTTP failure likely means model permission/access issues."""
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
    return any(
        marker in body_lower
        for marker in markers
    )


def _extract_items_blob(output_text: str) -> List[Dict[str, Any]]:
    """Decode the first JSON object containing an `items` list from model output text."""
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
        if isinstance(candidate, dict) and isinstance(candidate.get("items"), list):
            return candidate["items"]
        cursor = start + max(consumed, 1)


def _pick_text_payload(api_response: Dict[str, Any]) -> str:
    """Extract first meaningful text payload from xAI response layouts."""
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


def _normalize_engagement(raw_eng: Any) -> Optional[Dict[str, Optional[int]]]:
    if not isinstance(raw_eng, dict):
        return None
    normalized: Dict[str, Optional[int]] = {}
    for key in ("likes", "reposts", "replies", "quotes"):
        value = raw_eng.get(key)
        if value in (None, ""):
            normalized[key] = None
            continue
        try:
            normalized[key] = int(value)
        except (ValueError, TypeError):
            normalized[key] = None
    return normalized if any(v is not None for v in normalized.values()) else None


def _safe_relevance(raw: Any) -> float:
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
    """Query X posts via xAI's Agent Tools API with live search.

    If the primary model returns a model-access error, automatically
    retries with fallback models until one succeeds or all are exhausted.
    """
    _log("=== search START ===")
    _log(f"  API credential: {key[:8]}...{key[-4:]} ({len(key)} chars)")
    _log(f"  Model: {model}")
    _log(f"  Subject: '{topic}'")
    _log(f"  Date range: {start} to {end}")
    _log(f"  Depth: {depth}")

    if mock_response is not None:
        _log("  Using MOCK response")
        return mock_response

    depth_bucket = DEPTH_TARGETS.get(depth, DEPTH_TARGETS["default"])
    min_items = depth_bucket["min"]
    max_items = depth_bucket["max"]
    _log(f"  Requesting {min_items}-{max_items} results")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    timeout_map = {"quick": 80, "default": 110, "deep": 150}
    timeout = timeout_map.get(depth, 110)
    _log(f"  Timeout: {timeout}s")

    prompt_content = X_DISCOVERY_PROMPT.format(
        topic=topic,
        from_date=start,
        to_date=end,
        min_items=min_items,
        max_items=max_items,
    )

    # Try the primary model first
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
        _log(
            f"  Primary model '{model}' failed with access-style error "
            f"(status {e.status_code}), entering fallback loop"
        )
        # Invalidate the cached model so next run picks a working one
        registry.set_cached_model("xai", "")
        last_err = e

    # Phase 1: Try hardcoded fallback list
    fallbacks = [m for m in MODEL_FALLBACKS if m not in tried]
    for fallback_model in fallbacks:
        tried.add(fallback_model)
        _log(f"  Trying fallback model: {fallback_model}")
        try:
            response = _make_request(key, fallback_model, prompt_content, headers, timeout)
            _err(f"Fallback succeeded with model '{fallback_model}'")
            _log(f"  Fallback model '{fallback_model}' succeeded!")
            registry.set_cached_model("xai", fallback_model)
            _log("=== search END (via fallback) ===")
            return response
        except net.HTTPError as e:
            if _is_model_access_error(e):
                _log(
                    f"  Fallback model '{fallback_model}' failed with access-style error "
                    f"(status {e.status_code}), skipping"
                )
                last_err = e
                continue
            raise

    # Phase 2: Dynamic discovery — ask the API what models the key actually has
    _log("  Hardcoded fallbacks exhausted, attempting dynamic model discovery...")
    discovered = registry.discover_xai_models(key)
    dynamic_candidates = [
        m for m in discovered
        if m.startswith("grok-") and m not in tried
    ]
    _log(f"  Discovered {len(dynamic_candidates)} untried models: {dynamic_candidates}")

    for fallback_model in dynamic_candidates:
        tried.add(fallback_model)
        _log(f"  Trying discovered model: {fallback_model}")
        try:
            response = _make_request(key, fallback_model, prompt_content, headers, timeout)
            _err(f"Dynamic fallback succeeded with model '{fallback_model}'")
            _log(f"  Discovered model '{fallback_model}' succeeded!")
            registry.set_cached_model("xai", fallback_model)
            _log("=== search END (via dynamic discovery) ===")
            return response
        except net.HTTPError as e:
            if _is_model_access_error(e):
                _log(
                    f"  Discovered model '{fallback_model}' failed with access-style error "
                    f"(status {e.status_code}), skipping"
                )
                last_err = e
                continue
            raise

    # All options exhausted
    total = len(tried)
    _err(f"All {total} candidate models were rejected by access constraints")
    _log(f"  Tried models: {sorted(tried)}")
    _log("=== search END (all fallbacks exhausted) ===")
    if last_err:
        raise last_err
    raise net.HTTPError("All models were rejected by access constraints", 403)


def parse_x_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse X post items from an xAI API response."""
    _log("=== parse_x_response START ===")
    parsed_items: List[Dict[str, Any]] = []

    api_error = api_response.get("error")
    if api_error:
        message = api_error.get("message") if isinstance(api_error, dict) else str(api_error)
        _err(f"xAI API error: {message}")
        if net.DEBUG:
            _err(f"Full error response: {json.dumps(api_response, indent=2)[:1000]}")
        _log("=== parse_x_response END (api error) ===")
        return parsed_items

    payload_text = _pick_text_payload(api_response)
    if not payload_text:
        _log("No text payload found in xAI response")
        _log("=== parse_x_response END (empty payload) ===")
        return parsed_items

    candidates = _extract_items_blob(payload_text)
    _log(f"Candidate items extracted: {len(candidates)}")

    for row in candidates:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url", "")).strip()
        if not url:
            continue

        date_value = row.get("date")
        if date_value and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_value)):
            date_value = None

        parsed_items.append(
            {
                "id": f"X{len(parsed_items) + 1}",
                "text": str(row.get("text", "")).strip()[:500],
                "url": url,
                "author_handle": str(row.get("author_handle", "")).strip().lstrip("@"),
                "date": date_value,
                "engagement": _normalize_engagement(row.get("engagement")),
                "why_relevant": str(row.get("why_relevant", "")).strip(),
                "relevance": _safe_relevance(row.get("relevance")),
            }
        )

    _log(f"=== parse_x_response END ({len(parsed_items)} items) ===")
    return parsed_items
