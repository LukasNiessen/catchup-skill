#
# X Discovery Client: xAI API integration for X/Twitter content
# Searches for posts using xAI's live X search capabilities
#

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from . import http


def _emit_error_log(message_content: str):
    """Writes error diagnostic to stderr."""
    sys.stderr.write("[X ERROR] {}\n".format(message_content))
    sys.stderr.flush()


def _log(message: str):
    """Emit a debug log line to stderr, gated by LAST30DAYS_DEBUG."""
    if os.environ.get("LAST30DAYS_DEBUG", "").lower() in ("1", "true", "yes"):
        sys.stderr.write("[XAI_X] {}\n".format(message))
        sys.stderr.flush()


# xAI uses the responses endpoint with Agent Tools API
XAI_API_ENDPOINT = "https://api.x.ai/v1/responses"

# Result quantity settings by research depth
QUANTITY_SETTINGS = {
    "quick": (8, 12),
    "default": (20, 30),
    "deep": (40, 60),
}

X_DISCOVERY_PROMPT = """You have access to real-time X (Twitter) data. Search for posts about: {topic}

Focus on posts from {from_date} to {to_date}. Find {min_items}-{max_items} high-quality, relevant posts.

IMPORTANT: Return ONLY valid JSON in this exact format, no other text:
{{
  "items": [
    {{
      "text": "Post text content (truncated if long)",
      "url": "https://x.com/user/status/...",
      "author_handle": "username",
      "date": "YYYY-MM-DD or null if unknown",
      "engagement": {{
        "likes": 100,
        "reposts": 25,
        "replies": 15,
        "quotes": 5
      }},
      "why_relevant": "Brief explanation of relevance",
      "relevance": 0.85
    }}
  ]
}}

Rules:
- relevance is 0.0 to 1.0 (1.0 = highly relevant)
- date must be YYYY-MM-DD format or null
- engagement can be null if unknown
- Include diverse voices/accounts if applicable
- Prefer posts with substantive content, not just links"""


def search_x(
    api_credential: str,
    model_identifier: str,
    search_subject: str,
    range_start: str,
    range_end: str,
    thoroughness: str = "default",
    mock_api_response: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Searches X for relevant posts using xAI's API with live search.

    Args:
        api_credential: xAI API key
        model_identifier: Model to use (must support x_search tool)
        search_subject: Topic to search for
        range_start: Start date (YYYY-MM-DD)
        range_end: End date (YYYY-MM-DD)
        thoroughness: Research depth - "quick", "default", or "deep"
        mock_api_response: Mock response for testing

    Returns:
        Raw API response dictionary
    """
    _log("=== search_x START ===")
    _log("  API credential: {}...{} ({} chars)".format(
        api_credential[:8], api_credential[-4:], len(api_credential)))
    _log("  Model: {}".format(model_identifier))
    _log("  Subject: '{}'".format(search_subject))
    _log("  Date range: {} to {}".format(range_start, range_end))
    _log("  Thoroughness: {}".format(thoroughness))

    if mock_api_response is not None:
        _log("  Using MOCK response")
        return mock_api_response

    min_results, max_results = QUANTITY_SETTINGS.get(thoroughness, QUANTITY_SETTINGS["default"])
    _log("  Requesting {}-{} results".format(min_results, max_results))

    request_headers = {
        "Authorization": "Bearer {}".format(api_credential),
        "Content-Type": "application/json",
    }

    # Adjust timeout based on search depth
    timeout_mapping = {"quick": 90, "default": 120, "deep": 180}
    request_timeout = timeout_mapping.get(thoroughness, 120)
    _log("  Timeout: {}s".format(request_timeout))

    # Construct request using Agent Tools API with x_search tool
    request_payload = {
        "model": model_identifier,
        "tools": [
            {"type": "x_search"}
        ],
        "input": [
            {
                "role": "user",
                "content": X_DISCOVERY_PROMPT.format(
                    topic=search_subject,
                    from_date=range_start,
                    to_date=range_end,
                    min_items=min_results,
                    max_items=max_results,
                ),
            }
        ],
    }

    _log("  Endpoint: {}".format(XAI_API_ENDPOINT))
    _log("  Payload model: {}, tools: {}, input_length: {} chars".format(
        request_payload["model"],
        [t["type"] for t in request_payload["tools"]],
        len(request_payload["input"][0]["content"]),
    ))
    _log("  Sending POST request...")

    response = http.post(XAI_API_ENDPOINT, request_payload, request_headers=request_headers, timeout_seconds=request_timeout)

    _log("  Response received, type: {}, keys: {}".format(
        type(response).__name__,
        list(response.keys()) if isinstance(response, dict) else "N/A"))
    if isinstance(response, dict):
        if "error" in response:
            _log("  Response contains ERROR: {}".format(
                str(response["error"])[:300]))
        if "output" in response:
            output = response["output"]
            if isinstance(output, list):
                _log("  Response output: list with {} elements".format(len(output)))
                for i, elem in enumerate(output):
                    if isinstance(elem, dict):
                        _log("    output[{}]: type='{}', keys={}".format(
                            i, elem.get("type", "?"), list(elem.keys())))
            elif isinstance(output, str):
                _log("  Response output: string ({} chars)".format(len(output)))
        if "id" in response:
            _log("  Response id: {}".format(response["id"]))
        if "model" in response:
            _log("  Response model: {}".format(response["model"]))

    _log("=== search_x END ===")
    return response


def parse_x_response(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts X post data from the xAI API response.

    Handles various response formats and performs data validation.
    """
    extracted_items = []

    _log("=== parse_x_response START ===")
    _log("  Response type: {}, keys: {}".format(
        type(api_response).__name__,
        list(api_response.keys()) if isinstance(api_response, dict) else "N/A"))

    # Check for API-level errors
    if "error" in api_response and api_response["error"]:
        error_data = api_response["error"]
        error_message = error_data.get("message", str(error_data)) if isinstance(error_data, dict) else str(error_data)
        _emit_error_log("xAI API error: {}".format(error_message))
        _log("  API ERROR detected: {}".format(error_message))
        if http.DEBUG:
            _emit_error_log("Full error response: {}".format(json.dumps(api_response, indent=2)[:1000]))
        _log("=== parse_x_response END (error, 0 items) ===")
        return extracted_items

    # Locate the output text within the response structure
    output_content = ""

    if "output" in api_response:
        output_data = api_response["output"]
        _log("  'output' key found, type: {}".format(type(output_data).__name__))

        if isinstance(output_data, str):
            output_content = output_data
            _log("  output is string, {} chars".format(len(output_content)))
        elif isinstance(output_data, list):
            _log("  output is list with {} elements".format(len(output_data)))
            for idx, output_element in enumerate(output_data):
                if isinstance(output_element, dict):
                    _log("    output[{}]: type='{}', keys={}".format(
                        idx, output_element.get("type", "?"), list(output_element.keys())))
                    if output_element.get("type") == "message":
                        message_content = output_element.get("content", [])
                        _log("    message has {} content blocks".format(len(message_content)))
                        for block_idx, content_block in enumerate(message_content):
                            if isinstance(content_block, dict):
                                _log("      content[{}]: type='{}'".format(
                                    block_idx, content_block.get("type", "?")))
                                if content_block.get("type") == "output_text":
                                    output_content = content_block.get("text", "")
                                    _log("      Found output_text: {} chars".format(len(output_content)))
                                    break
                    elif "text" in output_element:
                        output_content = output_element["text"]
                        _log("    Found text field: {} chars".format(len(output_content)))
                elif isinstance(output_element, str):
                    output_content = output_element
                    _log("    output[{}] is string: {} chars".format(idx, len(output_content)))

                if output_content:
                    break
    else:
        _log("  No 'output' key in response")

    # Check legacy response format
    if not output_content and "choices" in api_response:
        _log("  Trying legacy 'choices' format...")
        for choice in api_response["choices"]:
            if "message" in choice:
                output_content = choice["message"].get("content", "")
                _log("  Found content in choices: {} chars".format(len(output_content)))
                break

    if not output_content:
        _log("  NO output content found in response, returning 0 items")
        _log("  Full response preview: {}".format(
            json.dumps(api_response, indent=2)[:500] if isinstance(api_response, dict) else str(api_response)[:500]))
        _log("=== parse_x_response END (no content, 0 items) ===")
        return extracted_items

    _log("  Output content: {} chars, preview: '{}'".format(
        len(output_content), output_content[:200].replace('\n', '\\n')))

    # Extract JSON from the text response
    json_pattern = re.search(r'\{[\s\S]*"items"[\s\S]*\}', output_content)

    if json_pattern:
        _log("  JSON pattern found ({} chars)".format(len(json_pattern.group())))
        try:
            parsed_data = json.loads(json_pattern.group())
            extracted_items = parsed_data.get("items", [])
            _log("  Parsed {} items from JSON".format(len(extracted_items)))
        except json.JSONDecodeError as jde:
            _log("  JSON PARSE ERROR: {}".format(jde))
            _emit_error_log("JSON parse error: {}".format(jde))
    else:
        _log("  NO JSON pattern with 'items' found in output")
        _log("  Output preview for debugging: '{}'".format(output_content[:500].replace('\n', '\\n')))

    # Validate and clean extracted items
    validated_items = []
    item_counter = 0

    while item_counter < len(extracted_items):
        raw_item = extracted_items[item_counter]

        if not isinstance(raw_item, dict):
            item_counter += 1
            continue

        item_url = raw_item.get("url", "")

        if not item_url:
            item_counter += 1
            continue

        # Parse engagement metrics
        engagement_data = None
        raw_engagement = raw_item.get("engagement")

        if isinstance(raw_engagement, dict):
            engagement_data = {
                "likes": int(raw_engagement.get("likes", 0)) if raw_engagement.get("likes") else None,
                "reposts": int(raw_engagement.get("reposts", 0)) if raw_engagement.get("reposts") else None,
                "replies": int(raw_engagement.get("replies", 0)) if raw_engagement.get("replies") else None,
                "quotes": int(raw_engagement.get("quotes", 0)) if raw_engagement.get("quotes") else None,
            }

        cleaned_item = {
            "id": "X{}".format(item_counter + 1),
            "text": str(raw_item.get("text", "")).strip()[:500],
            "url": item_url,
            "author_handle": str(raw_item.get("author_handle", "")).strip().lstrip("@"),
            "date": raw_item.get("date"),
            "engagement": engagement_data,
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

    _log("  Validated {} of {} raw items".format(len(validated_items), len(extracted_items)))
    if validated_items:
        _log("  First item: author={}, url={}, date={}".format(
            validated_items[0].get("author_handle", "?"),
            validated_items[0].get("url", "?")[:60],
            validated_items[0].get("date", "?")))
    _log("=== parse_x_response END ({} items) ===".format(len(validated_items)))
    return validated_items
