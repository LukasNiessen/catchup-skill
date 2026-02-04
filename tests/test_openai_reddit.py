#
# Verification Suite: OpenAI Reddit Module Functionality
#

import sys
import unittest
from pathlib import Path

# Configure module search path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lib import http
from lib.openai_reddit import _is_model_access_error, FALLBACK_MODEL_SEQUENCE


class ModelAccessErrorDetectionVerification(unittest.TestCase):
    # Tests for _is_model_access_error function

    def test_returns_false_for_non_400_error(self):
        # Non-400 errors should not trigger fallback
        error_instance = http.HTTPError("Server error", status_code=500, response_body="Internal error")
        self.assertFalse(_is_model_access_error(error_instance))

    def test_returns_false_for_400_without_body(self):
        # 400 without body should not trigger fallback
        error_instance = http.HTTPError("Bad request", status_code=400, response_body=None)
        self.assertFalse(_is_model_access_error(error_instance))

    def test_returns_true_for_verification_error(self):
        # Verification error should trigger fallback
        error_instance = http.HTTPError(
            "Bad request",
            status_code=400,
            response_body='{"error": {"message": "Your organization must be verified to use the model \'gpt-5.2\'"}}'
        )
        self.assertTrue(_is_model_access_error(error_instance))

    def test_returns_true_for_access_error(self):
        # Access denied error should trigger fallback
        error_instance = http.HTTPError(
            "Bad request",
            status_code=400,
            response_body='{"error": {"message": "Your account does not have access to this model"}}'
        )
        self.assertTrue(_is_model_access_error(error_instance))

    def test_returns_true_for_model_not_found(self):
        # Model not found error should trigger fallback
        error_instance = http.HTTPError(
            "Bad request",
            status_code=400,
            response_body='{"error": {"message": "The model gpt-5.2 was not found"}}'
        )
        self.assertTrue(_is_model_access_error(error_instance))

    def test_returns_false_for_unrelated_400(self):
        # Unrelated 400 errors should not trigger fallback
        error_instance = http.HTTPError(
            "Bad request",
            status_code=400,
            response_body='{"error": {"message": "Invalid JSON in request body"}}'
        )
        self.assertFalse(_is_model_access_error(error_instance))


class ModelFallbackSequenceVerification(unittest.TestCase):
    # Tests for FALLBACK_MODEL_SEQUENCE constant

    def test_contains_gpt4o(self):
        # Fallback list should include gpt-4o
        self.assertIn("gpt-4o", FALLBACK_MODEL_SEQUENCE)

    def test_gpt4o_is_first(self):
        # gpt-4o should be the first fallback option
        self.assertEqual(FALLBACK_MODEL_SEQUENCE[0], "gpt-4o")


if __name__ == "__main__":
    unittest.main()
