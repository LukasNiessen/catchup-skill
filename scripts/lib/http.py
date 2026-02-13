#
# Network Layer: HTTP client implementation for the BriefBot skill
# Uses only standard library modules for maximum compatibility
#

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import urlencode

# Request configuration constants
REQUEST_TIMEOUT_SECONDS = 30
MAXIMUM_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.0
CLIENT_IDENTIFIER = "last30days-skill/1.0 (Claude Code Skill)"

# Debug mode flag (controlled by environment variable)
DEBUG = os.environ.get("LAST30DAYS_DEBUG", "").lower() in ("1", "true", "yes")


def emit_debug_message(message_text: str):
    """
    Writes a diagnostic message to stderr when debug mode is enabled.

    Debug output is prefixed with [DEBUG] for easy identification.
    """
    if DEBUG:
        sys.stderr.write("[DEBUG] {}\n".format(message_text))
        sys.stderr.flush()


# Preserve the original function name for API compatibility
log = emit_debug_message


class HTTPError(Exception):
    """
    Custom exception for HTTP request failures.

    Captures the HTTP status code and response body when available,
    enabling more informative error handling upstream.
    """

    def __init__(
        self,
        description: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None
    ):
        super().__init__(description)
        self.status_code = status_code
        self.body = response_body


def execute_http_request(
    http_method: str,
    target_url: str,
    request_headers: Optional[Dict[str, str]] = None,
    json_payload: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
    retry_limit: int = MAXIMUM_RETRY_ATTEMPTS,
) -> Dict[str, Any]:
    """
    Executes an HTTP request and returns the parsed JSON response.

    Features:
    - Automatic retry with exponential backoff
    - JSON request/response handling
    - Comprehensive error capture

    Args:
        http_method: HTTP verb (GET, POST, etc.)
        target_url: Full request URL
        request_headers: Optional header dictionary
        json_payload: Optional JSON body for POST requests
        timeout_seconds: Request timeout
        retry_limit: Maximum retry attempts

    Returns:
        Parsed JSON response as dictionary

    Raises:
        HTTPError: On request failure after all retries
    """
    request_headers = request_headers or {}
    request_headers.setdefault("User-Agent", CLIENT_IDENTIFIER)

    encoded_body = None
    if json_payload is not None:
        encoded_body = json.dumps(json_payload).encode('utf-8')
        request_headers.setdefault("Content-Type", "application/json")

    http_request = urllib.request.Request(
        target_url,
        data=encoded_body,
        headers=request_headers,
        method=http_method
    )

    emit_debug_message("{} {}".format(http_method, target_url))
    if json_payload:
        emit_debug_message("Payload keys: {}".format(list(json_payload.keys())))

    most_recent_error = None
    attempt_number = 0

    while attempt_number < retry_limit:
        try:
            with urllib.request.urlopen(http_request, timeout=timeout_seconds) as http_response:
                response_content = http_response.read().decode('utf-8')
                emit_debug_message("Response: {} ({} bytes)".format(
                    http_response.status, len(response_content)
                ))
                return json.loads(response_content) if response_content else {}

        except urllib.error.HTTPError as http_err:
            error_body = None
            try:
                error_body = http_err.read().decode('utf-8')
            except:
                pass

            emit_debug_message("HTTP Error {}: {}".format(http_err.code, http_err.reason))
            if error_body:
                emit_debug_message("Error body: {}".format(error_body[:500]))

            most_recent_error = HTTPError(
                "HTTP {}: {}".format(http_err.code, http_err.reason),
                http_err.code,
                error_body
            )

            # Don't retry client errors (4xx) except rate limits
            is_client_error = 400 <= http_err.code < 500
            is_rate_limit = http_err.code == 429
            if is_client_error and not is_rate_limit:
                raise most_recent_error

            # Apply backoff before retry
            if attempt_number < retry_limit - 1:
                backoff_duration = RETRY_BACKOFF_SECONDS * (attempt_number + 1)
                time.sleep(backoff_duration)

        except urllib.error.URLError as url_err:
            emit_debug_message("URL Error: {}".format(url_err.reason))
            most_recent_error = HTTPError("URL Error: {}".format(url_err.reason))

            if attempt_number < retry_limit - 1:
                backoff_duration = RETRY_BACKOFF_SECONDS * (attempt_number + 1)
                time.sleep(backoff_duration)

        except json.JSONDecodeError as parse_err:
            emit_debug_message("JSON decode error: {}".format(parse_err))
            most_recent_error = HTTPError("Invalid JSON response: {}".format(parse_err))
            raise most_recent_error

        except (OSError, TimeoutError, ConnectionResetError) as connection_err:
            error_type = type(connection_err).__name__
            emit_debug_message("Connection error: {}: {}".format(error_type, connection_err))
            most_recent_error = HTTPError(
                "Connection error: {}: {}".format(error_type, connection_err)
            )

            if attempt_number < retry_limit - 1:
                backoff_duration = RETRY_BACKOFF_SECONDS * (attempt_number + 1)
                time.sleep(backoff_duration)

        attempt_number += 1

    if most_recent_error:
        raise most_recent_error

    raise HTTPError("Request failed with no error details")


# Preserve the original function name for API compatibility
request = execute_http_request


def perform_get_request(
    target_url: str,
    request_headers: Optional[Dict[str, str]] = None,
    **additional_options
) -> Dict[str, Any]:
    """Convenience wrapper for GET requests."""
    return execute_http_request("GET", target_url, request_headers=request_headers, **additional_options)


# Preserve the original function name for API compatibility
get = perform_get_request


def perform_post_request(
    target_url: str,
    json_payload: Dict[str, Any],
    request_headers: Optional[Dict[str, str]] = None,
    **additional_options
) -> Dict[str, Any]:
    """Convenience wrapper for POST requests with JSON body."""
    return execute_http_request(
        "POST", target_url,
        request_headers=request_headers,
        json_payload=json_payload,
        **additional_options
    )


# Preserve the original function name for API compatibility
post = perform_post_request


def fetch_reddit_thread_data(thread_path: str) -> Dict[str, Any]:
    """
    Retrieves JSON data for a Reddit thread.

    Args:
        thread_path: Reddit path (e.g., /r/subreddit/comments/id/title)

    Returns:
        Parsed thread data
    """
    # Ensure path has leading slash
    if not thread_path.startswith('/'):
        thread_path = '/' + thread_path

    # Remove trailing slash and append .json extension
    thread_path = thread_path.rstrip('/')
    if not thread_path.endswith('.json'):
        thread_path = thread_path + '.json'

    full_url = "https://www.reddit.com{}?raw_json=1".format(thread_path)

    custom_headers = {
        "User-Agent": CLIENT_IDENTIFIER,
        "Accept": "application/json",
    }

    return perform_get_request(full_url, request_headers=custom_headers)


# Preserve the original function name for API compatibility
get_reddit_json = fetch_reddit_thread_data
