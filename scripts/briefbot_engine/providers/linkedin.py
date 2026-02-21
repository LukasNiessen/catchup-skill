"""LinkedIn discovery via OpenAI Responses API with web search."""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional

from .. import net

FALLBACK_MODELS = ["gpt-4o-mini", "gpt-4o"]


def _err(msg: str) -> None:
    sys.stderr.write(f"[LINKEDIN ERROR] {msg}\n")
    sys.stderr.flush()


def _info(msg: str) -> None:
    sys.stderr.write(f"[LINKEDIN] {msg}\n")
    sys.stderr.flush()


def _is_access_err(err: net.HTTPError) -> bool:
    if err.status_code not in (400, 403) or not err.body:
        return False
    text = err.body.lower()
    indicators = (
        "organization must be verified",
        "does not have access",
        "access denied",
        "model not found",
        "not available for your account",
    )
    return any(token in text for token in indicators)


API_URL = "https://api.openai.com/v1/responses"

DEPTH_SPECS = {
    "quick": {"min": 6, "max": 12},
    "default": {"min": 12, "max": 22},
    "deep": {"min": 26, "max": 46},
}

LINKEDIN_DISCOVERY_PROMPT = """Find LinkedIn posts related to: {topic}

Use site:linkedin.com queries and focus on posts with useful context.
Return only post URLs, not profiles or company pages.

Target {min_items}-{max_items} posts.

Return JSON only:
{{
  "posts": [
    {{
      "excerpt": "Short post text",
      "link": "https://www.linkedin.com/posts/...",
      "author": "Name",
      "role": "Title at Company",
      "posted": "2026-01-15",
      "metrics": {{
        "reactions": 120,
        "comments": 18
      }},
      "signal": 0.85,
      "reason": "Why this is relevant"
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
        if isinstance(candidate, dict) and isinstance(candidate.get("posts"), list):
            return candidate["posts"]
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

    prompt = LINKEDIN_DISCOVERY_PROMPT.format(
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
                    "filters": {"allowed_domains": ["linkedin.com"]},
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


def parse_linkedin_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    extracted: List[Dict[str, Any]] = []

    if api_response.get("error"):
        err_data = api_response["error"]
        err_msg = (
            err_data.get("message", str(err_data))
            if isinstance(err_data, dict)
            else str(err_data)
        )
        _err(f"OpenAI API error: {err_msg}")
        if net.DEBUG:
            _err(f"Full error response: {json.dumps(api_response, indent=2)[:700]}")
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
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "output_text"
                        ):
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
        print(
            f"[LINKEDIN WARNING] No output text found in response. Keys: {list(api_response.keys())}",
            flush=True,
        )
        return extracted

    raw_items = _extract_items(output_text)

    validated: List[Dict[str, Any]] = []
    for idx, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue

        link = raw.get("link", "")
        if not link or "linkedin.com" not in link:
            continue

        item = {
            "uid": f"LI{idx + 1}",
            "excerpt": str(raw.get("excerpt", "")).strip(),
            "link": link,
            "author": str(raw.get("author", "")).strip(),
            "role": str(raw.get("role", "")).strip(),
            "posted": raw.get("posted"),
            "metrics": {
                "reactions": (
                    int(raw.get("metrics", {}).get("reactions", 0))
                    if raw.get("metrics", {}).get("reactions")
                    else None
                ),
                "comments": (
                    int(raw.get("metrics", {}).get("comments", 0))
                    if raw.get("metrics", {}).get("comments")
                    else None
                ),
            },
            "reason": str(raw.get("reason", "")).strip(),
            "signal": min(1.0, max(0.0, float(raw.get("signal", 0.5)))),
        }

        if item["posted"]:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(item["posted"])):
                item["posted"] = None

        validated.append(item)

    return validated
