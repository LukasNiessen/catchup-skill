"""YouTube discovery via OpenAI Responses API with web search."""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional

from .. import net

FALLBACK_MODELS = ["gpt-4o", "gpt-4o-mini"]


def _err(msg: str) -> None:
    sys.stderr.write(f"[YOUTUBE ERROR] {msg}\n")
    sys.stderr.flush()


def _info(msg: str) -> None:
    sys.stderr.write(f"[YOUTUBE] {msg}\n")
    sys.stderr.flush()


def _is_access_err(err: net.HTTPError) -> bool:
    if err.status_code not in (400, 403) or not err.body:
        return False
    lowered = err.body.lower()
    indicators = (
        "organization must be verified",
        "does not have access",
        "access denied",
        "model not found",
        "not available for your account",
    )
    return any(term in lowered for term in indicators)


API_URL = "https://api.openai.com/v1/responses"

DEPTH_SPECS = {
    "quick": {"min": 6, "max": 12},
    "default": {"min": 12, "max": 22},
    "deep": {"min": 26, "max": 48},
}

YOUTUBE_DISCOVERY_PROMPT = """Find YouTube videos about: {topic}

Distill the topic into a short search phrase, then search YouTube via site:youtube.com.
Return only actual video URLs (youtube.com/watch?v= or youtu.be).

Target {min_items}-{max_items} videos.

Return JSON only:
{{
  "videos": [
    {{
      "title": "Video title",
      "link": "https://www.youtube.com/watch?v=...",
      "channel": "Channel Name",
      "posted": "YYYY-MM-DD or null",
      "metrics": {{
        "views": 12345,
        "likes": 500
      }},
      "summary": "Short description or null",
      "signal": 0.85,
      "reason": "Why this video is relevant"
    }}
  ]
}}
"""


def _extract_items(output_text: str) -> List[Dict[str, Any]]:
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
        if isinstance(candidate, dict) and isinstance(candidate.get("videos"), list):
            return candidate["videos"]
        cursor = start + max(consumed, 1)


def search(
    key: str,
    model: str,
    topic: str,
    start: str,
    end: str,
    depth: str = "default",
    mock_response: Optional[Dict] = None,
    _is_retry: bool = False,
) -> Dict[str, Any]:
    if mock_response is not None:
        return mock_response

    depth_spec = DEPTH_SPECS.get(depth, DEPTH_SPECS["default"])
    min_items = depth_spec["min"]
    max_items = depth_spec["max"]

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    timeout_map = {"quick": 90, "default": 120, "deep": 180}
    timeout = timeout_map.get(depth, 120)

    models_chain = [model] + [m for m in FALLBACK_MODELS if m != model]

    prompt = YOUTUBE_DISCOVERY_PROMPT.format(
        topic=topic,
        from_date=start,
        to_date=end,
        min_items=min_items,
        max_items=max_items,
    )

    last_err = None

    for current_model in models_chain:
        payload = {
            "model": current_model,
            "input": [{"role": "user", "content": prompt}],
            "tools": [
                {
                    "type": "web_search",
                    "filters": {"allowed_domains": ["youtube.com", "youtu.be"]},
                }
            ],
            "include": ["web_search_call.action.sources"],
        }

        try:
            return net.post(API_URL, payload, headers=headers, timeout=timeout)
        except net.HTTPError as api_err:
            last_err = api_err
            if _is_access_err(api_err):
                _info(f"Model {current_model} not accessible, trying fallback...")
                continue
            raise

    if last_err:
        _err(f"All models failed. Last error: {last_err}")
        raise last_err

    raise net.HTTPError("No models available")


def parse_youtube_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    extracted: List[Dict[str, Any]] = []

    if api_response.get("error"):
        err_data = api_response["error"]
        err_msg = err_data.get("message", str(err_data)) if isinstance(err_data, dict) else str(err_data)
        _err(f"OpenAI API error: {err_msg}")
        if net.DEBUG:
            _err(f"Full error response: {json.dumps(api_response, indent=2)[:1000]}")
        return extracted

    output_text = ""
    output_data = api_response.get("output")
    if isinstance(output_data, str):
        output_text = output_data
    elif isinstance(output_data, list):
        for elem in output_data:
            if isinstance(elem, dict):
                if elem.get("type") == "message":
                    for block in elem.get("content", []):
                        if isinstance(block, dict) and block.get("type") == "output_text":
                            output_text = block.get("text", "")
                            break
                elif "text" in elem:
                    output_text = elem["text"]
            elif isinstance(elem, str):
                output_text = elem
            if output_text:
                break

    if not output_text and "choices" in api_response:
        for choice in api_response["choices"]:
            if "message" in choice:
                output_text = choice["message"].get("content", "")
                break

    if not output_text:
        print(f"[YOUTUBE WARNING] No output text found in response. Keys: {list(api_response.keys())}", flush=True)
        return extracted

    raw_items = _extract_items(output_text)

    validated: List[Dict[str, Any]] = []
    for idx, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue

        link = raw.get("link", "")
        if not link:
            continue
        if "youtube.com" not in link and "youtu.be" not in link:
            continue
        if "/playlist" in link or "/channel/" in link or "/@" in link:
            continue

        summary = raw.get("summary")
        if summary:
            summary = str(summary).strip()[:300]

        item = {
            "uid": f"YT{idx + 1}",
            "title": str(raw.get("title", "")).strip(),
            "link": link,
            "channel": str(raw.get("channel", "")).strip(),
            "posted": raw.get("posted"),
            "metrics": {
                "views": int(raw.get("metrics", {}).get("views", 0)) if raw.get("metrics", {}).get("views") else None,
                "likes": int(raw.get("metrics", {}).get("likes", 0)) if raw.get("metrics", {}).get("likes") else None,
            },
            "summary": summary,
            "reason": str(raw.get("reason", "")).strip(),
            "signal": min(1.0, max(0.0, float(raw.get("signal", 0.5)))),
        }

        if item["posted"]:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(item["posted"])):
                item["posted"] = None

        validated.append(item)

    return validated
