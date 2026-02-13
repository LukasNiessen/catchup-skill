#
# Verification Suite: Render Module Functionality
#

import sys
import unittest
from pathlib import Path

# Configure module search path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import render, schema


class CompactRenderVerification(unittest.TestCase):
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

        computed_result = render.render_compact(test_report)

        self.assertIn("test topic", computed_result)
        self.assertIn("2026-01-01", computed_result)
        self.assertIn("both", computed_result)
        self.assertIn("gpt-5.2", computed_result)

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

        computed_result = render.render_compact(test_report)

        self.assertIn("R1", computed_result)
        self.assertIn("Test Thread", computed_result)
        self.assertIn("r/test", computed_result)

    def test_shows_limited_data_warning_for_reddit_only(self):
        test_report = schema.Report(
            topic="test",
            range_from="2026-01-01",
            range_to="2026-01-31",
            generated_at="2026-01-31T12:00:00Z",
            mode="reddit-only",
        )

        computed_result = render.render_compact(test_report)

        self.assertIn("reddit-only", computed_result)


class ContextSnippetRenderVerification(unittest.TestCase):
    def test_renders_snippet(self):
        test_report = schema.Report(
            topic="Claude Code Skills",
            range_from="2026-01-01",
            range_to="2026-01-31",
            generated_at="2026-01-31T12:00:00Z",
            mode="both",
        )

        computed_result = render.render_context_snippet(test_report)

        self.assertIn("Claude Code Skills", computed_result)
        self.assertIn("Last 30 Days", computed_result)


class FullReportRenderVerification(unittest.TestCase):
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

        computed_result = render.render_full_report(test_report)

        self.assertIn("# test topic", computed_result)
        self.assertIn("## Models Used", computed_result)
        self.assertIn("gpt-5.2", computed_result)


class ContextPathRetrievalVerification(unittest.TestCase):
    def test_returns_path_string(self):
        computed_result = render.get_context_path()
        self.assertIsInstance(computed_result, str)
        self.assertIn("briefbot.context.md", computed_result)


if __name__ == "__main__":
    unittest.main()
