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
DEPTH_SIZES = {
    "quick": (10, 15),
    "default": (18, 28),
    "deep": (35, 55),
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

    If the primary model returns a 403 (permission denied), automatically
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

    min_items, max_items = DEPTH_SIZES.get(depth, DEPTH_SIZES["default"])
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
        if e.status_code != 403:
            raise
        _err(f"Model '{model}' returned 403 (permission denied), trying fallbacks...")
        _log(f"  Primary model '{model}' returned 403, entering fallback loop")
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
            if e.status_code == 403:
                _log(f"  Fallback model '{fallback_model}' also returned 403, skipping")
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
            if e.status_code == 403:
                _log(f"  Discovered model '{fallback_model}' also returned 403, skipping")
                last_err = e
                continue
            raise

    # All options exhausted
    total = len(tried)
    _err(f"All {total} models returned 403 — API key lacks x_search permission")
    _log(f"  Tried models: {sorted(tried)}")
    _log("=== search END (all fallbacks exhausted) ===")
    if last_err:
        raise last_err
    raise net.HTTPError("All models returned 403 — API key lacks x_search permission", 403)


def parse_x_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse X post items from an xAI API response."""
    extracted = []

    _log("=== parse_x_response START ===")
    _log(f"  Response type: {type(api_response).__name__}, keys: {list(api_response.keys()) if isinstance(api_response, dict) else 'N/A'}")

    # API-level error check
    if api_response.get("error"):
        err_data = api_response["error"]
        err_msg = err_data.get("message", str(err_data)) if isinstance(err_data, dict) else str(err_data)
        _err(f"xAI API error: {err_msg}")
        _log(f"  API ERROR detected: {err_msg}")
        if net.DEBUG:
            _err(f"Full error response: {json.dumps(api_response, indent=2)[:1000]}")
        _log("=== parse_x_response END (error, 0 items) ===")
        return extracted

    # Find output text in the response
    output_text = ""

    if "output" in api_response:
        output_data = api_response["output"]
        _log(f"  'output' key found, type: {type(output_data).__name__}")

        if isinstance(output_data, str):
            output_text = output_data
            _log(f"  output is string, {len(output_text)} chars")
        elif isinstance(output_data, list):
            _log(f"  output is list with {len(output_data)} elements")
            for idx, elem in enumerate(output_data):
                if isinstance(elem, dict):
                    _log(f"    output[{idx}]: type='{elem.get('type', '?')}', keys={list(elem.keys())}")
                    if elem.get("type") == "message":
                        msg_content = elem.get("content", [])
                        _log(f"    message has {len(msg_content)} content blocks")
                        for block_idx, block in enumerate(msg_content):
                            if isinstance(block, dict):
                                _log(f"      content[{block_idx}]: type='{block.get('type', '?')}'")
                                if block.get("type") == "output_text":
                                    output_text = block.get("text", "")
                                    _log(f"      Found output_text: {len(output_text)} chars")
                                    break
                    elif "text" in elem:
                        output_text = elem["text"]
                        _log(f"    Found text field: {len(output_text)} chars")
                elif isinstance(elem, str):
                    output_text = elem
                    _log(f"    output[{idx}] is string: {len(output_text)} chars")

                if output_text:
                    break
    else:
        _log("  No 'output' key in response")

    # Legacy format fallback
    if not output_text and "choices" in api_response:
        _log("  Trying legacy 'choices' format...")
        for choice in api_response["choices"]:
            if "message" in choice:
                output_text = choice["message"].get("content", "")
                _log(f"  Found content in choices: {len(output_text)} chars")
                break

    if not output_text:
        _log("  NO output content found in response, returning 0 items")
        _log(f"  Full response preview: {json.dumps(api_response, indent=2)[:500] if isinstance(api_response, dict) else str(api_response)[:500]}")
        _log("=== parse_x_response END (no content, 0 items) ===")
        return extracted

    _log(f"  Output content: {len(output_text)} chars, preview: '{output_text[:200].replace(chr(10), chr(92) + 'n')}'")

    # Pull JSON from the text
    match = re.search(r'\{[^{}]*"items"\s*:\s*\[[\s\S]*?\]\s*\}', output_text)

    if match:
        _log(f"  JSON pattern found ({len(match.group())} chars)")
        try:
            parsed = json.loads(match.group())
            extracted = parsed.get("items", [])
            _log(f"  Parsed {len(extracted)} items from JSON")
        except json.JSONDecodeError as exc:
            _log(f"  JSON PARSE ERROR: {exc}")
            _err(f"JSON parse error: {exc}")
    else:
        _log("  NO JSON pattern with 'items' found in output")
        _log(f"  Output preview for debugging: '{output_text[:500].replace(chr(10), chr(92) + 'n')}'")

    # Validate and normalise each item
    validated = []

    for idx, raw in enumerate(extracted):
        if not isinstance(raw, dict):
            continue

        url = raw.get("url", "")
        if not url:
            continue

        # Parse engagement metrics
        engagement = None
        raw_eng = raw.get("engagement")
        if isinstance(raw_eng, dict):
            engagement = {
                "likes": int(raw_eng.get("likes", 0)) if raw_eng.get("likes") else None,
                "reposts": int(raw_eng.get("reposts", 0)) if raw_eng.get("reposts") else None,
                "replies": int(raw_eng.get("replies", 0)) if raw_eng.get("replies") else None,
                "quotes": int(raw_eng.get("quotes", 0)) if raw_eng.get("quotes") else None,
            }

        item = {
            "id": f"X{idx + 1}",
            "text": str(raw.get("text", "")).strip()[:500],
            "url": url,
            "author_handle": str(raw.get("author_handle", "")).strip().lstrip("@"),
            "date": raw.get("date"),
            "engagement": engagement,
            "why_relevant": str(raw.get("why_relevant", "")).strip(),
            "relevance": min(1.0, max(0.0, float(raw.get("relevance", 0.5)))),
        }

        if item["date"]:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(item["date"])):
                item["date"] = None

        validated.append(item)

    _log(f"  Validated {len(validated)} of {len(extracted)} raw items")
    if validated:
        _log(f"  First item: author={validated[0].get('author_handle', '?')}, url={validated[0].get('url', '?')[:60]}, date={validated[0].get('date', '?')}")
    _log(f"=== parse_x_response END ({len(validated)} items) ===")
    return validated
