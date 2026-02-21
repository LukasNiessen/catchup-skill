"""Intent classification, epistemic routing, and optional query decomposition."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import net


@dataclass
class IntentDiagnostics:
    complexity: str
    complexity_reason: str
    epistemic_stance: str
    epistemic_reason: str
    decomposition: List[str] = field(default_factory=list)
    decomposition_source: str = "skipped"


COMPLEX_ANALYTICAL = "COMPLEX_ANALYTICAL"
BROAD_EXPLORATORY = "BROAD_EXPLORATORY"

STANCE_BALANCED = "BALANCED"
STANCE_OPINION = "EXPERIENTIAL_OPINION"
STANCE_FACTUAL = "FACTUAL_TEMPORAL"
STANCE_TRENDING = "TRENDING_BREAKING"
STANCE_HOWTO = "HOW_TO_TUTORIAL"


STANCE_SOURCE_WEIGHTS: Dict[str, Dict[str, float]] = {
    STANCE_BALANCED: {
        "reddit": 1.00,
        "x": 1.00,
        "youtube": 1.00,
        "linkedin": 1.00,
        "web": 1.00,
    },
    STANCE_OPINION: {
        "reddit": 1.18,
        "x": 1.18,
        "youtube": 1.00,
        "linkedin": 0.95,
        "web": 0.88,
    },
    STANCE_FACTUAL: {
        "reddit": 0.92,
        "x": 0.92,
        "youtube": 0.95,
        "linkedin": 1.00,
        "web": 1.20,
    },
    STANCE_TRENDING: {
        "reddit": 1.05,
        "x": 1.26,
        "youtube": 0.92,
        "linkedin": 0.90,
        "web": 0.90,
    },
    STANCE_HOWTO: {
        "reddit": 1.00,
        "x": 0.92,
        "youtube": 1.28,
        "linkedin": 0.96,
        "web": 1.08,
    },
}


_GENERIC_TOPICS = (
    "news",
    "updates",
    "trends",
    "trend",
    "overview",
    "what's new",
)

_COMPLEXITY_TRIGGERS = (
    "why",
    "how",
    "despite",
    "because",
    "impact",
    "effect",
    "cause",
    "barrier",
    "replace",
    "replacing",
    "adoption",
    "versus",
    "vs",
    "compare",
    "difference",
    "tradeoff",
)


def classify_complexity(topic: str) -> Tuple[str, str]:
    """Return a complexity label + rationale."""
    cleaned = (topic or "").strip()
    lowered = cleaned.lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9.+_-]*", lowered)
    word_count = len(tokens)

    if word_count <= 2:
        return BROAD_EXPLORATORY, "Short topic or single entity; treat as broad."

    if any(tag in lowered for tag in _GENERIC_TOPICS):
        return BROAD_EXPLORATORY, "Generic topic request (news/updates/trends)."

    if any(trigger in lowered for trigger in _COMPLEXITY_TRIGGERS):
        return COMPLEX_ANALYTICAL, "Contains analytical cue words."

    if "?" in cleaned and re.search(r"\b(and|but|while|despite)\b", lowered):
        return COMPLEX_ANALYTICAL, "Multi-clause question detected."

    if re.search(r"\bvs\b|\bversus\b", lowered):
        return COMPLEX_ANALYTICAL, "Comparison query detected."

    return BROAD_EXPLORATORY, "Defaulted to broad exploratory."


def classify_epistemic_stance(topic: str) -> Tuple[str, str]:
    """Determine epistemic stance for routing weights."""
    lowered = (topic or "").lower()

    if re.search(r"\b(how to|tutorial|guide|steps|walkthrough|install|setup|build)\b", lowered):
        return STANCE_HOWTO, "How-to/tutorial intent."

    if re.search(r"\b(breaking|latest|today|this week|right now|news|now|live)\b", lowered):
        return STANCE_TRENDING, "Trending/breaking intent."

    if re.search(r"\b(opinion|sentiment|community|what do people think|hot take|reddit|x)\b", lowered):
        return STANCE_OPINION, "Experiential or sentiment intent."

    if re.search(r"\b(why|when|where|facts?|data|statistics|spec|documentation|technical|price|policy)\b", lowered):
        return STANCE_FACTUAL, "Factual/temporal intent."

    return STANCE_BALANCED, "Default balanced routing."


def stance_weights(stance: str) -> Dict[str, float]:
    """Return source weight multipliers for the stance."""
    return dict(STANCE_SOURCE_WEIGHTS.get(stance, STANCE_SOURCE_WEIGHTS[STANCE_BALANCED]))


def decompose_query(
    topic: str,
    api_key: Optional[str],
    model: Optional[str],
    timeout: int = 22,
) -> Tuple[List[str], str]:
    """Use an LLM to break a complex query into sub-questions."""
    if not api_key or not model:
        return [], "skipped"

    prompt = "\n".join(
        [
            "Decompose the user topic into 3-5 focused sub-questions.",
            "Aim for what/when/why/who/technical barrier coverage if relevant.",
            "Return JSON only in this format:",
            '{"subquestions": ["Q1", "Q2", "Q3"]}',
            "",
            f"Topic: {topic}",
        ]
    )

    try:
        response = net.post(
            "https://api.openai.com/v1/responses",
            json_body={
                "model": model,
                "input": [{"role": "user", "content": prompt}],
                "max_output_tokens": 300,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            retries=2,
        )
    except net.HTTPError:
        return [], "skipped"

    content = _extract_text(response)
    if not content:
        return [], "skipped"

    parsed = _parse_json_block(content)
    subqs = parsed.get("subquestions") if isinstance(parsed, dict) else None
    if isinstance(subqs, list):
        cleaned = [str(entry).strip() for entry in subqs if str(entry).strip()]
        if cleaned:
            return cleaned, "llm"

    return [], "skipped"


def _extract_text(api_response: dict) -> str:
    output = api_response.get("output")
    if isinstance(output, list):
        for entry in output:
            if isinstance(entry, dict):
                text = entry.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
                content = entry.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            block_text = block.get("text")
                            if isinstance(block_text, str) and block_text.strip():
                                return block_text.strip()
    if isinstance(api_response.get("text"), str):
        return api_response["text"].strip()
    return ""


def _parse_json_block(raw: str) -> dict:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return {}
