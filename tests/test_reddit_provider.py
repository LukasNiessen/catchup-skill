"""Tests for the Reddit provider module (briefbot_engine.sources.reddit_source)."""

import pytest

from briefbot_engine.sources.reddit_source import _is_access_err, FALLBACK_MODELS
from briefbot_engine.http_client import HTTPError


# ---------------------------------------------------------------------------
# _is_access_err()
# ---------------------------------------------------------------------------

def test_is_access_err_returns_false_for_non_400():
    err = HTTPError("Server error", status_code=500, response_body="something broke")
    assert _is_access_err(err) is False


def test_is_access_err_returns_false_for_400_without_body():
    err = HTTPError("Bad request", status_code=400, response_body=None)
    assert _is_access_err(err) is False


def test_is_access_err_returns_true_for_verified_in_body():
    err = HTTPError(
        "Bad request",
        status_code=400,
        response_body="Your organization must be verified to use this model.",
    )
    assert _is_access_err(err) is True


def test_is_access_err_returns_true_for_does_not_have_access():
    err = HTTPError(
        "Bad request",
        status_code=400,
        response_body="This account does not have access to the requested model.",
    )
    assert _is_access_err(err) is True


def test_is_access_err_returns_true_for_not_found():
    err = HTTPError(
        "Bad request",
        status_code=400,
        response_body="The model `gpt-5` was not found.",
    )
    assert _is_access_err(err) is True


def test_is_access_err_returns_false_for_unrelated_400():
    err = HTTPError(
        "Bad request",
        status_code=400,
        response_body="Malformed request payload",
    )
    assert _is_access_err(err) is False


# ---------------------------------------------------------------------------
# FALLBACK_MODELS
# ---------------------------------------------------------------------------

def test_fallback_models_contains_gpt41():
    assert "gpt-4.1" in FALLBACK_MODELS


def test_fallback_models_first_item_is_gpt41_mini():
    assert FALLBACK_MODELS[0] == "gpt-4.1-mini"
