"""Regression tests for X query orchestration in briefbot.py."""

import briefbot


def test_query_x_reports_error_when_bird_empty_and_xai_fallback_fails(monkeypatch):
    monkeypatch.setattr(briefbot, "DISABLE_BIRD", False)
    monkeypatch.setattr(briefbot.bird, "search_x", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(briefbot.bird, "parse_bird_response", lambda _resp: [])
    monkeypatch.setattr(briefbot.twitter, "search", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    cfg = {
        "BIRD_X_AVAILABLE": True,
        "XAI_API_KEY": "xai-test-key",
    }
    models = {"xai": "grok-4-fast"}

    items, _response, error = briefbot._query_x(
        topic="test",
        cfg=cfg,
        models_picked=models,
        start_date="2026-01-01",
        end_date="2026-01-31",
        depth="default",
        mock=False,
    )

    assert items == []
    assert error is not None
    assert "xAI fallback: RuntimeError: boom" in error
