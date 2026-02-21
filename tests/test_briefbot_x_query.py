"""Regression tests for X query orchestration in briefbot.py."""

import briefbot


def test_query_x_reports_error_when_xai_fails(monkeypatch):
    monkeypatch.setattr(
        briefbot.x_posts,
        "search",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    cfg = {
        "XAI_API_KEY": "xai-test-key",
    }
    models = {"xai": "grok-4-fast"}

    items, _response, error = briefbot._query_x(
        topic="test",
        cfg=cfg,
        models_picked=models,
        start_date="2026-01-01",
        end_date="2026-01-31",
        sampling="standard",
        mock=False,
    )

    assert items == []
    assert error is not None
    assert "Unhandled exception (RuntimeError) - boom" in error
