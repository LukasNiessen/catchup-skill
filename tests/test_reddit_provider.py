"""Tests for the Reddit provider module (briefbot_engine.providers.reddit)."""

import pytest

from briefbot_engine.providers.reddit import _is_access_err, FALLBACK_MODELS
from briefbot_engine.net import HTTPError


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
        response_body="Invalid JSON in request body",
    )
    assert _is_access_err(err) is False


# ---------------------------------------------------------------------------
# FALLBACK_MODELS
# ---------------------------------------------------------------------------

def test_fallback_models_contains_gpt4o():
    assert "gpt-4o" in FALLBACK_MODELS


def test_fallback_models_first_item_is_gpt4o_mini():
    assert FALLBACK_MODELS[0] == "gpt-4o-mini"
