"""Reddit discovery via OpenAI Responses web tool."""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

from .. import net

FALLBACK_MODELS = ["gpt-4o-mini", "gpt-4o"]


def _err(msg: str) -> None:
    sys.stderr.write(f"[REDDIT ERROR] {msg}\n")
    sys.stderr.flush()


def _info(msg: str) -> None:
    sys.stderr.write(f"[REDDIT] {msg}\n")
    sys.stderr.flush()


def _is_access_err(err: net.HTTPError) -> bool:
    if err.status_code not in (400, 403) or not err.body:
        return False
    text = err.body.lower()
    tokens = (
        "organization must be verified",
        "does not have access",
        "model not found",
        "not available for your account",
        "access denied",
    )
    return any(token in text for token in tokens)


API_URL = "https://api.openai.com/v1/responses"

DEPTH_SPECS = {
    "quick": {"min": 9, "max": 16},
    "default": {"min": 20, "max": 36},
    "deep": {"min": 42, "max": 74},
}

REDDIT_DISCOVERY_PROMPT = """You are scouting Reddit threads for research.

Topic: {topic}
Window: {from_date} through {to_date}
Goal: collect {min_items}-{max_items} substantive threads.

Guidelines:
- First distill the topic into a 2-3 word search phrase.
- Run broad `site:reddit.com` searches and over-collect if needed.
- Prefer community discussions with details or lessons learned.
- Ignore developer/business subdomains.

Return JSON only in this structure:
{{
  "threads": [
    {{
      "headline": "Thread title",
      "link": "https://www.reddit.com/r/example/comments/abc123/example_thread/",
      "community": "example",
      "posted": "2026-01-15",
      "signal": 0.9,
      "reason": "Explains why the thread matters for the topic"
    }}
  ]
}}
"""

_FILLERS = (
    r"\bhow\s+to\b",
    r"\btips?\s+for\b",
    r"\bbest\b",
    r"\btop\b",
    r"\bultimate\b",
    r"\bcomplete\b",
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


def compress_topic(verbose_query: str) -> str:
    """Reduce verbose queries to a compact search phrase."""
    lowered = verbose_query.lower()
    for pattern in _FILLERS:
        lowered = re.sub(pattern, " ", lowered)
    tokens = [tok for tok in re.findall(r"[a-z0-9][a-z0-9.+_-]*", lowered) if tok not in _STOPWORDS]
    if len(tokens) <= 3:
        return " ".join(tokens) or verbose_query
    return " ".join(tokens[:3])


def _iter_text_chunks(output: Any) -> Iterable[str]:
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


def _extract_threads_blob(payload_text: str) -> List[Dict[str, Any]]:
    if not payload_text:
        return []
    decoder = json.JSONDecoder()
    cursor = 0
    while True:
        brace = payload_text.find("{", cursor)
        if brace < 0:
            return []
        try:
            obj, end = decoder.raw_decode(payload_text[brace:])
        except json.JSONDecodeError:
            cursor = brace + 1
            continue
        if isinstance(obj, dict) and isinstance(obj.get("threads"), list):
            return obj["threads"]
        cursor = brace + max(end, 1)


def _to_signal(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _normalize_item(raw: Dict[str, Any], ordinal: int) -> Optional[Dict[str, Any]]:
    link = str(raw.get("link", "")).strip()
    if "reddit.com" not in link:
        return None
    date_value = raw.get("posted")
    if date_value is not None and not _ID_DATE.match(str(date_value)):
        date_value = None
    community = str(raw.get("community", "")).strip()
    if community.lower().startswith("r/"):
        community = community[2:]
    return {
        "uid": f"R{ordinal}",
        "title": str(raw.get("headline", "")).strip(),
        "link": link,
        "community": community,
        "posted": date_value,
        "reason": str(raw.get("reason", "")).strip(),
        "signal": _to_signal(raw.get("signal")),
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
    if mock_response is not None:
        return mock_response

    depth_spec = DEPTH_SPECS.get(depth, DEPTH_SPECS["default"])
    min_items = depth_spec["min"]
    max_items = depth_spec["max"]
    headers = {"Authorization": f"Bearer {key}"}
    timeout = {"quick": 65, "default": 95, "deep": 150}.get(depth, 95)
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
            "input": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
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

    raw_items = _extract_threads_blob(raw_text)
    parsed: List[Dict[str, Any]] = []
    for index, row in enumerate(raw_items, start=1):
        if not isinstance(row, dict):
            continue
        normalized = _normalize_item(row, index)
        if normalized is not None:
            parsed.append(normalized)
    return parsed
