"""LinkedIn discovery via OpenAI Responses API with web search."""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional

from .. import http_client

FALLBACK_MODELS = ["gpt-4o-mini", "gpt-4o"]


def _err(msg: str) -> None:
    sys.stderr.write(f"[LinkedIn] {msg}\n")
    sys.stderr.flush()


def _info(msg: str) -> None:
    sys.stderr.write(f"[LinkedIn] {msg}\n")
    sys.stderr.flush()


_ACCESS_PATTERNS = (
    r"organization must be verified",
    r"does not have access",
    r"access denied",
    r"model .*not found",
    r"not available for your account",
)


def _is_access_err(err: http_client.HTTPError) -> bool:
    if err.status_code not in (400, 401, 403, 404, 429) or not err.body:
        return False
    text = err.body.lower()
    return any(re.search(pattern, text) for pattern in _ACCESS_PATTERNS)


API_URL = "https://api.openai.com/v1/responses"

SAMPLING_SPECS = {
    "lite": {"min": 6, "max": 12},
    "standard": {"min": 12, "max": 22},
    "dense": {"min": 26, "max": 46},
}

LINKEDIN_DISCOVERY_PROMPT = """Find LinkedIn posts related to: {topic}

Window: {from_date} to {to_date}
Query hint: {query_hint}

Focus on posts with useful context. Return only post URLs (not profiles or company pages).

Target {min_items}-{max_items} posts.

Return JSON only:
{{
  "posts": [
    {{
      "snippet": "Short post text",
      "url": "https://www.linkedin.com/posts/...",
      "author": "Name",
      "role": "Title at Company",
      "dated": "2026-01-15",
      "signals": {{
        "reactions": 120,
        "comments": 18
      }},
      "topicality": 0.85,
      "rationale": "Why this is relevant"
    }}
  ]
}}
"""


def _trim_query(topic: str) -> str:
    lowered = (topic or "").lower()
    lowered = re.sub(r"\\b(how to|best|top|guide|review|tutorial)\\b", " ", lowered)
    tokens = [tok for tok in re.findall(r"[a-z0-9]+", lowered) if len(tok) > 2]
    seen = []
    for tok in tokens:
        if tok in seen:
            continue
        seen.append(tok)
        if len(seen) >= 5:
            break
    return " ".join(seen) or topic


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
    sampling: str = "standard",
    mock_response: Optional[Dict] = None,
    _is_retry: bool = False,
) -> Dict[str, Any]:
    if mock_response is not None:
        return mock_response

    depth_spec = SAMPLING_SPECS.get(sampling, SAMPLING_SPECS["standard"])
    min_items = depth_spec["min"]
    max_items = depth_spec["max"]

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    timeout_map = {"lite": 90, "standard": 120, "dense": 180}
    timeout = timeout_map.get(sampling, 120)

    models_chain = [model]
    for candidate in FALLBACK_MODELS:
        if candidate not in models_chain:
            models_chain.append(candidate)

    query_hint = _trim_query(topic)
    prompt = LINKEDIN_DISCOVERY_PROMPT.format(
        topic=topic,
        from_date=start,
        to_date=end,
        min_items=min_items,
        max_items=max_items,
        query_hint=query_hint,
    )

    last_err = None

    for current_model in models_chain:
        payload = {
            "model": current_model,
            "input": [
                {"role": "system", "content": "You are a research scout for LinkedIn posts."},
                {"role": "user", "content": prompt},
            ],
            "tools": [
                {
                    "type": "web_search",
                    "filters": {"allowed_domains": ["linkedin.com", "www.linkedin.com"]},
                }
            ],
            "include": ["web_search_call.action.sources"],
            "metadata": {"query_hint": query_hint, "sampling": sampling},
        }

        try:
            return http_client.post(API_URL, payload, headers=headers, timeout=timeout)
        except http_client.HTTPError as api_err:
            last_err = api_err
            if _is_access_err(api_err):
                _info(f"Model {current_model} not accessible, trying fallback...")
                continue
            raise

    if last_err:
        _err(f"All models failed. Last error: {last_err}")
        raise last_err

    raise http_client.HTTPError("No models available")


def parse_linkedin_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    extracted: List[Dict[str, Any]] = []

    if api_response.get("error"):
        err_data = api_response["error"]
        err_msg = (
            err_data.get("message", str(err_data))
            if isinstance(err_data, dict)
            else str(err_data)
        )
        _err(f"OpenAI response error: {err_msg}")
        if http_client.DEBUG:
            _err(f"Response snapshot: {json.dumps(api_response, indent=2)[:600]}")
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
        print(
            f"[LinkedIn] No output text found in response. Keys: {list(api_response.keys())}",
            flush=True,
        )
        return extracted

    raw_items = _extract_items(output_text)

    validated: List[Dict[str, Any]] = []
    for idx, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue

        link = raw.get("url", raw.get("link", ""))
        if not link or "linkedin.com" not in link:
            continue

        item = {
            "key": f"LI-{idx + 1:02d}",
            "snippet": str(raw.get("snippet", raw.get("excerpt", ""))).strip(),
            "url": link,
            "author": str(raw.get("author", "")).strip(),
            "role": str(raw.get("role", "")).strip(),
            "dated": raw.get("dated", raw.get("posted")),
            "signals": {
                "reactions": (
                    int(raw.get("signals", raw.get("metrics", {})).get("reactions", 0))
                    if raw.get("signals", raw.get("metrics", {})).get("reactions")
                    else None
                ),
                "comments": (
                    int(raw.get("signals", raw.get("metrics", {})).get("comments", 0))
                    if raw.get("signals", raw.get("metrics", {})).get("comments")
                    else None
                ),
            },
            "rationale": str(raw.get("rationale", raw.get("reason", ""))).strip(),
            "topicality": min(
                1.0,
                max(0.0, float(raw.get("topicality", raw.get("signal", 0.5)))),
            ),
        }

        if item["dated"]:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(item["dated"])):
                item["dated"] = None

        validated.append(item)

    return validated
