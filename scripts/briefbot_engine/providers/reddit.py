"""Reddit discovery via OpenAI Responses API with web search."""

import json
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

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
    """Check whether the failure likely means the model cannot be used by this key."""
    if err.status_code not in (400, 403) or not err.body:
        return False
    text = err.body.lower()
    signals = (
        "organization must be verified",
        "does not have access",
        "model not found",
        "not found",
        "not available for your account",
        "access denied",
    )
    return any(token in text for token in signals)


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

_FILLER_PATTERNS = (
    r"\bhow\s+to\b",
    r"\btips?\s+for\b",
    r"\bbest\b",
    r"\btop\b",
    r"\breview(s)?\b",
    r"\bfeatures?\b",
    r"\bcomparison(s)?\b",
    r"\boverview\b",
    r"\brecommendation(s)?\b",
    r"\badvice\b",
    r"\btutorial(s)?\b",
    r"\bprompting\b",
)
_STOPWORDS = {"using", "for", "with", "the", "of", "in", "on", "a", "an"}
_ID_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _core_subject(verbose_query: str) -> str:
    """Extract a compact subject by dropping common modifier phrases and stopwords."""
    lowered = verbose_query.lower()
    for pattern in _FILLER_PATTERNS:
        lowered = re.sub(pattern, " ", lowered)
    tokens = [tok for tok in re.findall(r"[a-z0-9][a-z0-9.+_-]*", lowered) if tok not in _STOPWORDS]
    return " ".join(tokens[:4]) or verbose_query


def _iter_text_chunks(output: Any) -> Iterable[str]:
    """Yield possible text chunks from modern and legacy Responses API shapes."""
    if isinstance(output, str):
        yield output
        return
    if not isinstance(output, list):
        return
    for entry in output:
        if isinstance(entry, str):
            yield entry
            continue
        if not isinstance(entry, dict):
            continue
        text = entry.get("text")
        if isinstance(text, str):
            yield text
        content = entry.get("content", [])
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_text = block.get("text")
                if isinstance(block_text, str):
                    yield block_text


def _pick_output_text(api_response: Dict[str, Any]) -> str:
    """Pick the first non-empty text payload from known response layouts."""
    for chunk in _iter_text_chunks(api_response.get("output")):
        text = chunk.strip()
        if text:
            return text
    for choice in api_response.get("choices", []):
        if not isinstance(choice, dict):
            continue
        message = choice.get("message", {})
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def _extract_items_blob(payload_text: str) -> List[Dict[str, Any]]:
    """Decode the first JSON object containing an 'items' list from raw model text."""
    if not payload_text:
        return []
    decoder = json.JSONDecoder()
    start = 0
    while True:
        brace = payload_text.find("{", start)
        if brace < 0:
            return []
        try:
            obj, end = decoder.raw_decode(payload_text[brace:])
        except json.JSONDecodeError:
            start = brace + 1
            continue
        if isinstance(obj, dict) and isinstance(obj.get("items"), list):
            return obj["items"]
        start = brace + max(end, 1)


def _to_relevance(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _normalize_item(raw: Dict[str, Any], ordinal: int) -> Optional[Dict[str, Any]]:
    url = str(raw.get("url", "")).strip()
    if "reddit.com" not in url:
        return None
    date_value = raw.get("date")
    if date_value is not None and not _ID_DATE.match(str(date_value)):
        date_value = None
    subreddit = str(raw.get("subreddit", "")).strip()
    if subreddit.lower().startswith("r/"):
        subreddit = subreddit[2:]
    return {
        "id": f"R{ordinal}",
        "title": str(raw.get("title", "")).strip(),
        "url": url,
        "subreddit": subreddit,
        "date": date_value,
        "why_relevant": str(raw.get("why_relevant", "")).strip(),
        "relevance": _to_relevance(raw.get("relevance")),
    }


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
    headers = {"Authorization": f"Bearer {key}"}
    timeout = {"quick": 75, "default": 105, "deep": 160}.get(depth, 105)
    model_candidates = [model] + [candidate for candidate in FALLBACK_MODELS if candidate != model]
    prompt = REDDIT_DISCOVERY_PROMPT.format(
        topic=topic,
        from_date=start,
        to_date=end,
        min_items=min_items,
        max_items=max_items,
    )

    final_error = None
    for candidate in model_candidates:
        request_payload = {
            "model": candidate,
            "input": prompt,
            "tools": [{"type": "web_search", "filters": {"allowed_domains": ["reddit.com"]}}],
            "include": ["web_search_call.action.sources"],
        }
        try:
            return net.request(
                "POST",
                API_URL,
                headers=headers,
                json_body=request_payload,
                timeout=timeout,
            )
        except net.HTTPError as exc:
            final_error = exc
            if _is_access_err(exc):
                _info(f"Model {candidate} unavailable for this key, trying fallback...")
                continue
            raise

    if final_error:
        _err(f"All model attempts failed: {final_error}")
        raise final_error
    raise net.HTTPError("No compatible model could be selected")


def parse_reddit_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse Reddit items from an OpenAI API response."""
    api_error = api_response.get("error")
    if api_error:
        message = api_error.get("message") if isinstance(api_error, dict) else str(api_error)
        _err(f"OpenAI API error: {message}")
        if net.DEBUG:
            _err(f"Error payload snapshot: {json.dumps(api_response, indent=2)[:1000]}")
        return []

    raw_text = _pick_output_text(api_response)
    if not raw_text:
        _err(f"No text output returned by model. Response keys: {sorted(api_response.keys())}")
        return []

    raw_items = _extract_items_blob(raw_text)
    parsed: List[Dict[str, Any]] = []
    for index, row in enumerate(raw_items, start=1):
        if not isinstance(row, dict):
            continue
        normalized = _normalize_item(row, index)
        if normalized is not None:
            parsed.append(normalized)
    return parsed
