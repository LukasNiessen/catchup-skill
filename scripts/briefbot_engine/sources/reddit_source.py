"""Reddit discovery via OpenAI Responses web tool."""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, Iterable, List, Optional

from .. import http_client

FALLBACK_MODELS = ["gpt-4.1-mini", "gpt-4.1"]


def _err(msg: str) -> None:
    sys.stderr.write(f"[Reddit] {msg}\n")
    sys.stderr.flush()


def _info(msg: str) -> None:
    sys.stderr.write(f"[Reddit] {msg}\n")
    sys.stderr.flush()


def _is_access_err(err: http_client.HTTPError) -> bool:
    if err.status_code not in (400, 401, 403) or not err.body:
        return False
    text = err.body.lower()
    tokens = (
        "organization must be verified",
        "does not have access",
        "model not found",
        "not available for your account",
        "access denied",
        "unauthorized",
    )
    return any(token in text for token in tokens)


API_URL = "https://api.openai.com/v1/responses"

SAMPLING_SPECS = {
    "lite": {"min": 7, "max": 14},
    "standard": {"min": 18, "max": 32},
    "dense": {"min": 45, "max": 72},
}

REDDIT_DISCOVERY_PROMPT = """You are assembling Reddit threads for a research brief.

Topic: {topic}
Window: {from_date} through {to_date}
Target: {min_items}-{max_items} solid threads

Process:
- Compress the topic into a tight 2-4 word query.
- Use broad searches across reddit.com and then refine if needed.
- Prefer threads with concrete details, lessons learned, or firsthand experience.
- Avoid low-effort meme posts or thin link dumps.

Return JSON only in this structure:
{{
  "threads": [
    {{
      "headline": "Thread title",
      "url": "https://www.reddit.com/r/example/comments/abc123/example_thread/",
      "forum": "example",
      "dated": "2026-01-15",
      "topicality": 0.9,
      "rationale": "Explains why the thread matters for the topic"
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
    tokens = [
        tok
        for tok in re.findall(r"[a-z0-9][a-z0-9.+_-]*", lowered)
        if tok not in _STOPWORDS
    ]
    if len(tokens) <= 4:
        return " ".join(tokens) or verbose_query
    return " ".join(tokens[:4])


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


def _to_match(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _normalize_item(raw: Dict[str, Any], ordinal: int) -> Optional[Dict[str, Any]]:
    link = str(raw.get("url", raw.get("link", ""))).strip()
    if "reddit.com" not in link:
        return None
    date_value = raw.get("dated", raw.get("date", raw.get("posted")))
    if date_value is not None and not _ID_DATE.match(str(date_value)):
        date_value = None
    community = str(raw.get("forum", raw.get("subreddit", raw.get("community", "")))).strip()
    if community.lower().startswith("r/"):
        community = community[2:]
    title = str(raw.get("headline", raw.get("title", ""))).strip()
    why = str(raw.get("rationale", raw.get("why", raw.get("reason", "")))).strip()
    return {
        "key": f"RDT-{ordinal:02d}",
        "headline": title,
        "url": link,
        "forum": community,
        "dated": date_value,
        "rationale": why,
        "topicality": _to_match(raw.get("topicality", raw.get("signal"))),
    }


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

    sampling_spec = SAMPLING_SPECS.get(sampling, SAMPLING_SPECS["standard"])
    min_items = sampling_spec["min"]
    max_items = sampling_spec["max"]
    headers = {"Authorization": f"Bearer {key}"}
    timeout = {"lite": 60, "standard": 90, "dense": 150}.get(sampling, 90)
    model_candidates = [model]
    for candidate in FALLBACK_MODELS:
        if candidate not in model_candidates:
            model_candidates.append(candidate)
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
                {"role": "system", "content": "You are a research scout for Reddit."},
                {"role": "user", "content": prompt},
            ],
            "tools": [
                {"type": "web_search", "filters": {"allowed_domains": ["reddit.com"]}}
            ],
            "temperature": 0.2,
            "max_output_tokens": 1200,
        }
        try:
            return http_client.request(
                "POST",
                API_URL,
                headers=headers,
                json_body=request_payload,
                timeout=timeout,
            )
        except http_client.HTTPError as exc:
            final_error = exc
            if _is_access_err(exc):
                _info(f"Model {candidate} unavailable for this key, trying fallback...")
                continue
            raise

    if final_error:
        _err(f"All model attempts failed: {final_error}")
        raise final_error
    raise http_client.HTTPError("No compatible model could be selected")


def parse_reddit_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    api_error = api_response.get("error")
    if api_error:
        message = (
            api_error.get("message") if isinstance(api_error, dict) else str(api_error)
        )
        _err(f"OpenAI API reported an error: {message}")
        if http_client.DEBUG:
            _err(f"Error payload snapshot: {json.dumps(api_response, indent=2)[:650]}")
        return []

    raw_text = _pick_output_text(api_response)
    if not raw_text:
        _err(
            f"No text output returned by model. Response keys: {sorted(api_response.keys())}"
        )
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
