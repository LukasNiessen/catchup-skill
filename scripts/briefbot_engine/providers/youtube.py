"""YouTube discovery via OpenAI Responses API with web search."""

import json
import re
import sys
from typing import Any, Dict, List, Optional

from .. import net

# Fallback chain when the primary model is inaccessible
FALLBACK_MODELS = ["gpt-4o", "gpt-4o-mini"]


def _err(msg: str):
    """Log an error to stderr."""
    sys.stderr.write(f"[YOUTUBE ERROR] {msg}\n")
    sys.stderr.flush()


def _info(msg: str):
    """Log informational output to stderr."""
    sys.stderr.write(f"[YOUTUBE] {msg}\n")
    sys.stderr.flush()


def _is_access_err(err: net.HTTPError) -> bool:
    """Check whether the error signals a model-access or verification problem."""
    if err.status_code != 400 or not err.body:
        return False

    lowered = err.body.lower()
    indicators = [
        "verified",
        "organization must be",
        "does not have access",
        "not available",
        "not found",
    ]
    return any(term in lowered for term in indicators)


API_URL = "https://api.openai.com/v1/responses"

# How many results to request per depth level
DEPTH_SIZES = {
    "quick": (8, 12),
    "default": (15, 25),
    "deep": (30, 50),
}

YOUTUBE_DISCOVERY_PROMPT = """Locate YouTube videos related to: {topic}

Identify the main subject, ignoring filler words like "best", "top", "tutorial".
Search YouTube using the core subject via site:youtube.com queries.

We filter dates server-side, so include everything relevant you find.

Only return actual video URLs (youtube.com/watch?v= or youtu.be/).
Skip playlists, channel pages, and non-video links.

Target {min_items}-{max_items} videos. More is better.

JSON format:
{{
  "items": [
    {{
      "title": "Video title",
      "url": "https://www.youtube.com/watch?v=...",
      "channel_name": "Channel Name",
      "date": "YYYY-MM-DD or null",
      "views": 12345,
      "likes": 500,
      "description": "Short description or null",
      "why_relevant": "Relevance explanation",
      "relevance": 0.85
    }}
  ]
}}"""


def _core_subject(verbose_query: str) -> str:
    """Strip filler words from a query, returning the essential subject."""
    filler = {
        'best', 'top', 'how to', 'tips for', 'practices', 'features',
        'killer', 'guide', 'tutorial', 'recommendations', 'advice',
        'using', 'for', 'with', 'the', 'of', 'in', 'on', 'videos',
    }
    tokens = verbose_query.lower().split()
    kept = [t for t in tokens if t not in filler]
    return ' '.join(kept[:3]) or verbose_query


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
    """Query YouTube videos via OpenAI Responses API web search."""
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_SIZES.get(depth, DEPTH_SIZES["default"])

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
            "tools": [
                {
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": ["youtube.com", "youtu.be"],
                    },
                }
            ],
            "include": ["web_search_call.action.sources"],
            "input": prompt,
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
    """Parse YouTube items from an OpenAI API response."""
    extracted = []

    # API-level error check
    if api_response.get("error"):
        err_data = api_response["error"]
        err_msg = err_data.get("message", str(err_data)) if isinstance(err_data, dict) else str(err_data)
        _err(f"OpenAI API error: {err_msg}")
        if net.DEBUG:
            _err(f"Full error response: {json.dumps(api_response, indent=2)[:1000]}")
        return extracted

    # Find output text in the response
    output_text = ""

    if "output" in api_response:
        output_data = api_response["output"]

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

    # Legacy format fallback
    if not output_text and "choices" in api_response:
        for choice in api_response["choices"]:
            if "message" in choice:
                output_text = choice["message"].get("content", "")
                break

    if not output_text:
        print(f"[YOUTUBE WARNING] No output text found in response. Keys: {list(api_response.keys())}", flush=True)
        return extracted

    # Pull JSON from the text
    match = re.search(r'\{[\s\S]*"items"[\s\S]*\}', output_text)

    if match:
        try:
            parsed = json.loads(match.group())
            extracted = parsed.get("items", [])
        except json.JSONDecodeError:
            pass

    # Validate and normalise each item
    validated = []

    for idx, raw in enumerate(extracted):
        if not isinstance(raw, dict):
            continue

        url = raw.get("url", "")
        if not url:
            continue

        # Must be a YouTube video URL
        if "youtube.com" not in url and "youtu.be" not in url:
            continue

        # Reject playlists and channel pages
        if "/playlist" in url or "/channel/" in url or "/@" in url:
            continue

        desc = raw.get("description")
        if desc:
            desc = str(desc).strip()[:300]

        item = {
            "id": f"YT{idx + 1}",
            "title": str(raw.get("title", "")).strip(),
            "url": url,
            "channel_name": str(raw.get("channel_name", "")).strip(),
            "date": raw.get("date"),
            "views": int(raw.get("views", 0)) if raw.get("views") else None,
            "likes": int(raw.get("likes", 0)) if raw.get("likes") else None,
            "description": desc,
            "why_relevant": str(raw.get("why_relevant", "")).strip(),
            "relevance": min(1.0, max(0.0, float(raw.get("relevance", 0.5)))),
        }

        if item["date"]:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(item["date"])):
                item["date"] = None

        validated.append(item)

    return validated
