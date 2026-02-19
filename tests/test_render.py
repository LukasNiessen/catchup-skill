import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import render, schema


class TestCompactOutput(unittest.TestCase):
    def test_renders_basic_report(self):
        test_report = schema.Report(
            topic="test topic",
            range_from="2026-01-01",
            range_to="2026-01-31",
            generated_at="2026-01-31T12:00:00Z",
            mode="both",
            openai_model_used="gpt-5.2",
            xai_model_used="grok-4-latest",
        )

        out = render.compact(test_report)

        self.assertIn("test topic", out)
        self.assertIn("2026-01-01", out)
        self.assertIn("both", out)
        self.assertIn("gpt-5.2", out)

    def test_renders_reddit_items(self):
        test_report = schema.Report(
            topic="test",
            range_from="2026-01-01",
            range_to="2026-01-31",
            generated_at="2026-01-31T12:00:00Z",
            mode="reddit-only",
            reddit=[
                schema.RedditItem(
                    id="R1",
                    title="Test Thread",
                    url="https://reddit.com/r/test/1",
                    subreddit="test",
                    date="2026-01-15",
                    date_confidence="high",
                    score=85,
                    why_relevant="Very relevant",
                )
            ],
        )

        out = render.compact(test_report)

        self.assertIn("R1", out)
        self.assertIn("Test Thread", out)
        self.assertIn("r/test", out)

    def test_shows_limited_data_warning_for_reddit_only(self):
        test_report = schema.Report(
            topic="test",
            range_from="2026-01-01",
            range_to="2026-01-31",
            generated_at="2026-01-31T12:00:00Z",
            mode="reddit-only",
        )

        out = render.compact(test_report)

        self.assertIn("reddit-only", out)


class TestContextFragment(unittest.TestCase):
    def test_renders_snippet(self):
        test_report = schema.Report(
            topic="Claude Code Skills",
            range_from="2026-01-01",
            range_to="2026-01-31",
            generated_at="2026-01-31T12:00:00Z",
            mode="both",
        )

        out = render.context_fragment(test_report)

        self.assertIn("Claude Code Skills", out)
        self.assertIn("Last 30 Days", out)


class TestFullReport(unittest.TestCase):
    def test_renders_full_report(self):
        test_report = schema.Report(
            topic="test topic",
            range_from="2026-01-01",
            range_to="2026-01-31",
            generated_at="2026-01-31T12:00:00Z",
            mode="both",
            openai_model_used="gpt-5.2",
            xai_model_used="grok-4-latest",
        )

        out = render.full_report(test_report)

        self.assertIn("# test topic", out)
        self.assertIn("## Models Used", out)
        self.assertIn("gpt-5.2", out)


class TestContextPath(unittest.TestCase):
    def test_returns_path_string(self):
        out = render.context_path()
        self.assertIsInstance(out, str)
        self.assertIn("briefbot.context.md", out)


if __name__ == "__main__":
    unittest.main()
