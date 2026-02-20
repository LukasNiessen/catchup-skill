"""LinkedIn discovery via OpenAI Responses API with web search."""

import json
import re
import sys
from typing import Any, Dict, List, Optional

from .. import net

# Fallback chain when the primary model is inaccessible
FALLBACK_MODELS = ["gpt-4o", "gpt-4o-mini"]


def _err(msg: str):
    """Log an error to stderr."""
    sys.stderr.write(f"[LINKEDIN ERROR] {msg}\n")
    sys.stderr.flush()


def _info(msg: str):
    """Log informational output to stderr."""
    sys.stderr.write(f"[LINKEDIN] {msg}\n")
    sys.stderr.flush()


def _is_access_err(err: net.HTTPError) -> bool:
    """Check whether the error signals a model-access or verification problem."""
    if err.status_code not in (400, 403) or not err.body:
        return False

    lowered = err.body.lower()
    markers = (
        "organization must be verified",
        "does not have access",
        "access denied",
        "model not found",
        "not available for your account",
    )
    return any(term in lowered for term in markers)


API_URL = "https://api.openai.com/v1/responses"

# How many results to request per depth level
DEPTH_SIZES = {
    "quick": (8, 12),
    "default": (15, 25),
    "deep": (30, 50),
}

LINKEDIN_DISCOVERY_PROMPT = """Find LinkedIn posts and articles about: {topic}

Extract the core subject, dropping generic words.
Search linkedin.com/posts and linkedin.com/pulse for relevant content.

Focus on:
- Professional posts with meaningful commentary
- Pulse articles with original analysis
- Company updates with substance

Skip job listings, profile-only pages, and "About" sections.

Date format YYYY-MM-DD if determinable, null otherwise.
We handle date verification server-side.

Target {min_items}-{max_items} posts. Over-include rather than miss relevant ones.

JSON format:
{{
  "items": [
    {{
      "text": "Post content (truncated)",
      "url": "https://www.linkedin.com/posts/...",
      "author_name": "Full Name",
      "author_title": "Title at Company",
      "date": "YYYY-MM-DD or null",
      "reactions": 150,
      "comments": 25,
      "why_relevant": "Why this is relevant",
      "relevance": 0.85
    }}
  ]
}}"""


def _core_subject(verbose_query: str) -> str:
    """Strip filler words from a query, returning the essential subject."""
    reduced = re.sub(r"\b(how\s+to|tips?\s+for|best|top|tutorials?|recommendations?)\b", " ", verbose_query.lower())
    tokens = [tok for tok in re.findall(r"[a-z0-9][a-z0-9.+_-]*", reduced) if tok not in {"for", "with", "the", "of", "in", "on", "posts"}]
    return " ".join(tokens[:4]) or verbose_query


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
    """Query LinkedIn posts via OpenAI Responses API web search."""
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
            "input": prompt,
            "tools": [
                {
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": ["linkedin.com"],
                    },
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
    """Parse LinkedIn items from an OpenAI API response."""
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
        print(f"[LINKEDIN WARNING] No output text found in response. Keys: {list(api_response.keys())}", flush=True)
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
        if not url or "linkedin.com" not in url:
            continue

        # Reject job postings
        if "/jobs/" in url or "/job/" in url:
            continue

        item = {
            "id": f"LI{idx + 1}",
            "text": str(raw.get("text", "")).strip()[:500],
            "url": url,
            "author_name": str(raw.get("author_name", "")).strip(),
            "author_title": str(raw.get("author_title", "")).strip(),
            "date": raw.get("date"),
            "reactions": int(raw.get("reactions", 0)) if raw.get("reactions") else None,
            "comments": int(raw.get("comments", 0)) if raw.get("comments") else None,
            "why_relevant": str(raw.get("why_relevant", "")).strip(),
            "relevance": min(1.0, max(0.0, float(raw.get("relevance", 0.5)))),
        }

        if item["date"]:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(item["date"])):
                item["date"] = None

        validated.append(item)

    return validated
