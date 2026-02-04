#
# Reddit Discovery Client: OpenAI Responses API integration for Reddit content
# Searches for discussion threads using web search capabilities
#

import json
import re
import sys
from typing import Any, Dict, List, Optional

from . import http

# Alternative models when primary selection is unavailable
FALLBACK_MODEL_SEQUENCE = ["gpt-4o", "gpt-4o-mini"]


def _emit_error_log(message_content: str):
    """Writes error diagnostic to stderr."""
    sys.stderr.write("[REDDIT ERROR] {}\n".format(message_content))
    sys.stderr.flush()


def _emit_info_log(message_content: str):
    """Writes informational diagnostic to stderr."""
    sys.stderr.write("[REDDIT] {}\n".format(message_content))
    sys.stderr.flush()


def _is_model_access_error(error_instance: http.HTTPError) -> bool:
    """
    Determines if the error indicates model access or verification issues.

    These errors warrant trying fallback models rather than failing entirely.
    """
    if error_instance.status_code != 400:
        return False

    if not error_instance.body:
        return False

    body_content = error_instance.body.lower()
    access_indicators = [
        "verified",
        "organization must be",
        "does not have access",
        "not available",
        "not found",
    ]

    for indicator in access_indicators:
        if indicator in body_content:
            return True

    return False


# API endpoint for OpenAI Responses
OPENAI_API_ENDPOINT = "https://api.openai.com/v1/responses"

# Result quantity settings by research depth
# Request more than needed since date filtering removes many
QUANTITY_SETTINGS = {
    "quick": (15, 25),
    "default": (30, 50),
    "deep": (70, 100),
}

REDDIT_DISCOVERY_PROMPT = """Find Reddit discussion threads about: {topic}

STEP 1: EXTRACT THE CORE SUBJECT
Get the MAIN NOUN/PRODUCT/TOPIC:
- "best nano banana prompting practices" → "nano banana"
- "killer features of clawdbot" → "clawdbot"
- "top Claude Code skills" → "Claude Code"
DO NOT include "best", "top", "tips", "practices", "features" in your search.

STEP 2: SEARCH BROADLY
Search for the core subject:
1. "[core subject] site:reddit.com"
2. "reddit [core subject]"
3. "[core subject] reddit"

Return as many relevant threads as you find. We filter by date server-side.

STEP 3: INCLUDE ALL MATCHES
- Include ALL threads about the core subject
- Set date to "YYYY-MM-DD" if you can determine it, otherwise null
- We verify dates and filter old content server-side
- DO NOT pre-filter aggressively - include anything relevant

REQUIRED: URLs must contain "/r/" AND "/comments/"
REJECT: developers.reddit.com, business.reddit.com

Find {min_items}-{max_items} threads. Return MORE rather than fewer.

Return JSON:
{{
  "items": [
    {{
      "title": "Thread title",
      "url": "https://www.reddit.com/r/sub/comments/xyz/title/",
      "subreddit": "subreddit_name",
      "date": "YYYY-MM-DD or null",
      "why_relevant": "Why relevant",
      "relevance": 0.85
    }}
  ]
}}"""


def _extract_core_subject(verbose_query: str) -> str:
    """
    Distills a verbose search query down to its essential subject.

    Removes common filler words to improve search effectiveness.
    """
    filler_words = [
        'best', 'top', 'how to', 'tips for', 'practices', 'features',
        'killer', 'guide', 'tutorial', 'recommendations', 'advice',
        'prompting', 'using', 'for', 'with', 'the', 'of', 'in', 'on'
    ]
    query_tokens = verbose_query.lower().split()
    essential_tokens = [token for token in query_tokens if token not in filler_words]
    return ' '.join(essential_tokens[:3]) or verbose_query


def search_reddit(
    api_credential: str,
    model_identifier: str,
    search_subject: str,
    range_start: str,
    range_end: str,
    thoroughness: str = "default",
    mock_api_response: Optional[Dict] = None,
    _is_retry: bool = False,
) -> Dict[str, Any]:
    """
    Searches Reddit for relevant threads using OpenAI's Responses API.

    Args:
        api_credential: OpenAI API key
        model_identifier: Model to use for search
        search_subject: Topic to search for
        range_start: Start date (YYYY-MM-DD) - threads after this
        range_end: End date (YYYY-MM-DD) - threads before this
        thoroughness: Research depth - "quick", "default", or "deep"
        mock_api_response: Mock response for testing

    Returns:
        Raw API response dictionary
    """
    if mock_api_response is not None:
        return mock_api_response

    min_results, max_results = QUANTITY_SETTINGS.get(thoroughness, QUANTITY_SETTINGS["default"])

    request_headers = {
        "Authorization": "Bearer {}".format(api_credential),
        "Content-Type": "application/json",
    }

    # Adjust timeout based on search depth (generous for web_search latency)
    timeout_mapping = {"quick": 90, "default": 120, "deep": 180}
    request_timeout = timeout_mapping.get(thoroughness, 120)

    # Build model fallback chain
    models_to_attempt = [model_identifier] + [m for m in FALLBACK_MODEL_SEQUENCE if m != model_identifier]

    # Note: allowed_domains accepts base domain, not subdomains
    # Prompt-based filtering handles developers.reddit.com etc.
    search_instruction = REDDIT_DISCOVERY_PROMPT.format(
        topic=search_subject,
        from_date=range_start,
        to_date=range_end,
        min_items=min_results,
        max_items=max_results,
    )

    most_recent_error = None

    for current_model in models_to_attempt:
        request_payload = {
            "model": current_model,
            "tools": [
                {
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": ["reddit.com"]
                    }
                }
            ],
            "include": ["web_search_call.action.sources"],
            "input": search_instruction,
        }

        try:
            return http.post(OPENAI_API_ENDPOINT, request_payload, request_headers=request_headers, timeout_seconds=request_timeout)
        except http.HTTPError as api_error:
            most_recent_error = api_error
            if _is_model_access_error(api_error):
                _emit_info_log("Model {} not accessible, trying fallback...".format(current_model))
                continue
            raise

    if most_recent_error:
        _emit_error_log("All models failed. Last error: {}".format(most_recent_error))
        raise most_recent_error

    raise http.HTTPError("No models available")


def parse_reddit_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts Reddit item data from the OpenAI API response.

    Handles various response formats and performs data validation.
    """
    extracted_items = []

    # Check for API-level errors
    if "error" in api_response and api_response["error"]:
        error_data = api_response["error"]
        error_message = error_data.get("message", str(error_data)) if isinstance(error_data, dict) else str(error_data)
        _emit_error_log("OpenAI API error: {}".format(error_message))
        if http.DEBUG:
            _emit_error_log("Full error response: {}".format(json.dumps(api_response, indent=2)[:1000]))
        return extracted_items

    # Locate the output text within the response structure
    output_content = ""

    if "output" in api_response:
        output_data = api_response["output"]

        if isinstance(output_data, str):
            output_content = output_data
        elif isinstance(output_data, list):
            for output_element in output_data:
                if isinstance(output_element, dict):
                    if output_element.get("type") == "message":
                        message_content = output_element.get("content", [])
                        for content_block in message_content:
                            if isinstance(content_block, dict) and content_block.get("type") == "output_text":
                                output_content = content_block.get("text", "")
                                break
                    elif "text" in output_element:
                        output_content = output_element["text"]
                elif isinstance(output_element, str):
                    output_content = output_element

                if output_content:
                    break

    # Check legacy response format
    if not output_content and "choices" in api_response:
        for choice in api_response["choices"]:
            if "message" in choice:
                output_content = choice["message"].get("content", "")
                break

    if not output_content:
        print("[REDDIT WARNING] No output text found in OpenAI response. Keys present: {}".format(list(api_response.keys())), flush=True)
        return extracted_items

    # Extract JSON from the text response
    json_pattern = re.search(r'\{[\s\S]*"items"[\s\S]*\}', output_content)

    if json_pattern:
        try:
            parsed_data = json.loads(json_pattern.group())
            extracted_items = parsed_data.get("items", [])
        except json.JSONDecodeError:
            pass

    # Validate and clean extracted items
    validated_items = []
    item_counter = 0

    while item_counter < len(extracted_items):
        raw_item = extracted_items[item_counter]

        if not isinstance(raw_item, dict):
            item_counter += 1
            continue

        item_url = raw_item.get("url", "")

        if not item_url or "reddit.com" not in item_url:
            item_counter += 1
            continue

        cleaned_item = {
            "id": "R{}".format(item_counter + 1),
            "title": str(raw_item.get("title", "")).strip(),
            "url": item_url,
            "subreddit": str(raw_item.get("subreddit", "")).strip().lstrip("r/"),
            "date": raw_item.get("date"),
            "why_relevant": str(raw_item.get("why_relevant", "")).strip(),
            "relevance": min(1.0, max(0.0, float(raw_item.get("relevance", 0.5)))),
        }

        # Validate date format
        if cleaned_item["date"]:
            date_pattern = re.match(r'^\d{4}-\d{2}-\d{2}$', str(cleaned_item["date"]))
            if not date_pattern:
                cleaned_item["date"] = None

        validated_items.append(cleaned_item)
        item_counter += 1

    return validated_items
