"""Tests for xAI X provider fallback behavior."""

import pytest

from briefbot_engine.net import HTTPError
from briefbot_engine.providers import twitter


def test_is_model_access_error_detects_400_access_message():
    err = HTTPError(
        "bad request",
        status_code=400,
        response_body="This API key does not have access to model grok-4-fast.",
    )
    assert twitter._is_model_access_error(err) is True


def test_is_model_access_error_detects_422_with_model_not_found():
    err = HTTPError(
        "unprocessable",
        status_code=422,
        response_body="Model not found for this account",
    )
    assert twitter._is_model_access_error(err) is True


def test_is_model_access_error_ignores_unrelated_400():
    err = HTTPError(
        "bad request",
        status_code=400,
        response_body="Malformed request body",
    )
    assert twitter._is_model_access_error(err) is False


def test_search_retries_with_fallback_on_400_access_error(monkeypatch):
    attempts = []
    cache_updates = []

    def fake_make_request(_key, model, _prompt, _headers, _timeout):
        attempts.append(model)
        if model == "grok-4-fast":
            raise HTTPError(
                "bad request",
                status_code=400,
                response_body="The account does not have access to this model.",
            )
        return {"ok": True, "model": model, "output": []}

    monkeypatch.setattr(twitter, "_make_request", fake_make_request)
    monkeypatch.setattr(twitter, "MODEL_FALLBACKS", ["grok-4-1-fast-non-reasoning"])
    monkeypatch.setattr(twitter.registry, "set_cached_model", lambda provider, model: cache_updates.append((provider, model)))
    monkeypatch.setattr(twitter.registry, "discover_xai_models", lambda _key: [])

    response = twitter.search(
        key="xai-test-key",
        model="grok-4-fast",
        topic="test",
        start="2026-01-01",
        end="2026-01-31",
    )

    assert response["model"] == "grok-4-1-fast-non-reasoning"
    assert attempts == ["grok-4-fast", "grok-4-1-fast-non-reasoning"]
    assert ("xai", "") in cache_updates
    assert ("xai", "grok-4-1-fast-non-reasoning") in cache_updates


def test_search_does_not_fallback_for_unrelated_400(monkeypatch):
    def fake_make_request(_key, _model, _prompt, _headers, _timeout):
        raise HTTPError(
            "bad request",
            status_code=400,
            response_body="Malformed request body",
        )

    monkeypatch.setattr(twitter, "_make_request", fake_make_request)
    monkeypatch.setattr(twitter.registry, "discover_xai_models", lambda _key: [])

    with pytest.raises(HTTPError) as exc:
        twitter.search(
            key="xai-test-key",
            model="grok-4-fast",
            topic="test",
            start="2026-01-01",
            end="2026-01-31",
        )
    assert exc.value.status_code == 400


def test_search_uses_discovered_models_after_hardcoded_failures(monkeypatch):
    attempts = []

    def fake_make_request(_key, model, _prompt, _headers, _timeout):
        attempts.append(model)
        raise HTTPError(
            "forbidden",
            status_code=403,
            response_body="access denied",
        )

    monkeypatch.setattr(twitter, "_make_request", fake_make_request)
    monkeypatch.setattr(twitter, "MODEL_FALLBACKS", ["grok-hardcoded-a"])
    monkeypatch.setattr(twitter.registry, "set_cached_model", lambda *_args: None)
    monkeypatch.setattr(twitter.registry, "discover_xai_models", lambda _key: ["grok-discovered-b"])

    with pytest.raises(HTTPError) as exc:
        twitter.search(
            key="xai-test-key",
            model="grok-primary",
            topic="test",
            start="2026-01-01",
            end="2026-01-31",
        )

    assert exc.value.status_code == 403
    assert attempts == ["grok-primary", "grok-hardcoded-a", "grok-discovered-b"]


def test_parse_x_response_handles_json_with_metadata_before_items():
    response = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": """
Here is the data:
{
  "meta": {"model": "grok-4-1-fast"},
  "posts": [
    {
      "excerpt": "hello world",
      "link": "https://x.com/u/status/1",
      "handle": "u",
      "posted": "2026-02-20",
      "metrics": {"likes": 1, "reposts": 2, "replies": 3, "quotes": 4},
      "reason": "test",
      "signal": 0.9
    }
  ]
}
""",
                    }
                ],
            }
        ]
    }
    items = twitter.parse_x_response(response)
    assert len(items) == 1
    assert items[0]["uid"] == "X1"
    assert items[0]["handle"] == "u"
