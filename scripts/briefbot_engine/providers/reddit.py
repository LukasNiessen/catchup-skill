"""Reddit discovery via OpenAI Responses API with web search."""

import json
import re
import sys
from typing import Any, Dict, List, Optional

from .. import net

# Fallback chain when the primary model is inaccessible
FALLBACK_MODELS = ["gpt-4o-mini", "gpt-4o"]


def _err(msg: str):
    """Log an error to stderr."""
    sys.stderr.write(f"[REDDIT ERROR] {msg}\n")
    sys.stderr.flush()


def _info(msg: str):
    """Log informational output to stderr."""
    sys.stderr.write(f"[REDDIT] {msg}\n")
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

# How many results to request per depth level (over-fetch for date filtering)
DEPTH_SIZES = {
    "quick": (12, 20),
    "default": (25, 45),
    "deep": (55, 85),
}

REDDIT_DISCOVERY_PROMPT = """Investigate Reddit community discussions related to: {topic}

First, distill the essential query. Simplify compound queries to their root subject
(e.g., "best wireless headphones 2026" becomes "wireless headphones",
"killer features of clawdbot" becomes "clawdbot").

Execute broad searches using site:reddit.com combined with the distilled subject.
Over-fetch rather than under-fetch -- server-side filters will handle precision.

Content window: {from_date} through {to_date}

For every matching thread, record:
- Thread title
- Full reddit.com URL -- URLs must include both /r/ and /comments/ path segments.
  Discard developers.reddit.com and business.reddit.com domains.
- Publication date in YYYY-MM-DD format, or null if not visible
- A relevance score between 0.0 and 1.0
- Brief explanation of why the thread is relevant

Aim for {min_items} to {max_items} threads. More is better than fewer.

Output strictly as JSON:
{{
  "items": [
    {{
      "title": "Example discussion title",
      "url": "https://www.reddit.com/r/example/comments/abc123/example_thread/",
      "subreddit": "example",
      "date": "2026-01-15",
      "why_relevant": "Directly discusses the topic with community input",
      "relevance": 0.9
    }}
  ]
}}"""


def _core_subject(verbose_query: str) -> str:
    """Strip filler words from a query, returning the essential subject."""
    filler = {
        "best",
        "top",
        "how to",
        "tips for",
        "review",
        "features",
        "killer",
        "comparison",
        "overview",
        "recommendations",
        "advice",
        "tutorial",
        "prompting",
        "using",
        "for",
        "with",
        "the",
        "of",
        "in",
        "on",
    }
    tokens = verbose_query.lower().split()
    kept = [t for t in tokens if t not in filler]
    return " ".join(kept[:3]) or verbose_query


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
    """Query Reddit threads via OpenAI Responses API web search."""
    if mock_response is not None:
        return mock_response

    min_items, max_items = DEPTH_SIZES.get(depth, DEPTH_SIZES["default"])

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    timeout_map = {"quick": 75, "default": 105, "deep": 160}
    timeout = timeout_map.get(depth, 105)

    models_chain = [model] + [m for m in FALLBACK_MODELS if m != model]

    prompt = REDDIT_DISCOVERY_PROMPT.format(
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
                        "allowed_domains": ["reddit.com"],
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


def parse_reddit_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Reddit items from an OpenAI API response."""
    extracted = []

    # API-level error check
    if api_response.get("error"):
        err_data = api_response["error"]
        err_msg = (
            err_data.get("message", str(err_data))
            if isinstance(err_data, dict)
            else str(err_data)
        )
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

    # Legacy format fallback
    if not output_text and "choices" in api_response:
        for choice in api_response["choices"]:
            if "message" in choice:
                output_text = choice["message"].get("content", "")
                break

    if not output_text:
        print(
            f"[WARNING REDDIT] No output text found in the response from OpenAI. Keys present: {list(api_response.keys())}",
            flush=True,
        )
        return extracted

    # Pull JSON from the text
    match = re.search(r'\{[^{}]*"items"\s*:\s*\[[\s\S]*?\]\s*\}', output_text)

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
        if not url or "reddit.com" not in url:
            continue

        item = {
            "id": f"R{idx + 1}",
            "title": str(raw.get("title", "")).strip(),
            "url": url,
            "subreddit": str(raw.get("subreddit", "")).strip().lstrip("r/"),
            "date": raw.get("date"),
            "why_relevant": str(raw.get("why_relevant", "")).strip(),
            "relevance": min(1.0, max(0.0, float(raw.get("relevance", 0.5)))),
        }

        if item["date"]:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(item["date"])):
                item["date"] = None

        validated.append(item)

    return validated
