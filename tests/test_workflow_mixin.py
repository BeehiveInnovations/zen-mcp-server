"""
Tests for BaseWorkflowMixin model resolution functionality.

This module tests the model resolution helper method that was added to fix
the bug where fallback logic incorrectly used "unknown" instead of DEFAULT_MODEL.
"""

from unittest.mock import patch

from tools.workflow.workflow_mixin import BaseWorkflowMixin


class ConcreteWorkflowMixin(BaseWorkflowMixin):
    """Concrete implementation of BaseWorkflowMixin for testing."""

    def get_name(self) -> str:
        return "test_workflow"

    def get_workflow_request_model(self) -> type:
        return object

    def get_system_prompt(self) -> str:
        return "Test system prompt"

    def get_language_instruction(self) -> str:
        return "Test language instruction"

    def get_default_temperature(self) -> float:
        return 0.5

    def get_model_provider(self, model_name: str):
        return None

    def _resolve_model_context(self, arguments, request):
        return ("test_model", None)

    def _prepare_file_content_for_prompt(self, *args, **kwargs):
        return ("", [])

    def get_work_steps(self, request):
        return ["Step 1", "Step 2"]

    def get_required_actions(self, step_number, confidence, findings, total_steps):
        return ["Action 1", "Action 2"]

    def get_request_model_names(self):
        return None


class MockRequest:
    """Mock request object for testing."""

    def __init__(self, model=None):
        if model is not None:
            self.model = model


class TestModelResolutionHelpers:
    """Test cases for model resolution helper methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = ConcreteWorkflowMixin()

    def test_resolve_model_name_with_predefined_models(self):
        """Test that predefined models take priority."""
        request = MockRequest()
        model_names = ["flash", "pro", "o3"]

        result = self.mixin._resolve_model_name_with_fallback(request, model_names)

        assert result == "flash"  # Should return first predefined model

    def test_resolve_model_name_with_request_model(self):
        """Test that request model is used when no predefined models."""
        request = MockRequest(model="gpt-4")

        result = self.mixin._resolve_model_name_with_fallback(request, None)

        assert result == "gpt-4"

    def test_resolve_model_name_with_empty_request_model(self):
        """Test that empty request model falls back to DEFAULT_MODEL."""
        request = MockRequest(model="")

        with patch("config.DEFAULT_MODEL", "test-default"):
            result = self.mixin._resolve_model_name_with_fallback(request, None)

        assert result == "test-default"

    def test_resolve_model_name_with_none_request_model(self):
        """Test that None request model falls back to DEFAULT_MODEL."""
        request = MockRequest(model=None)

        with patch("config.DEFAULT_MODEL", "test-default"):
            result = self.mixin._resolve_model_name_with_fallback(request, None)

        assert result == "test-default"

    def test_resolve_model_name_without_model_attribute(self):
        """Test that request without model attribute falls back to DEFAULT_MODEL."""
        request = MockRequest()  # No model attribute set

        with patch("config.DEFAULT_MODEL", "test-default"):
            result = self.mixin._resolve_model_name_with_fallback(request, None)

        assert result == "test-default"

    def test_resolve_model_name_predefined_takes_priority_over_request(self):
        """Test that predefined models take priority over request model."""
        request = MockRequest(model="gpt-4")
        model_names = ["flash", "pro"]

        result = self.mixin._resolve_model_name_with_fallback(request, model_names)

        assert result == "flash"  # Should ignore request model when predefined exist

    def test_resolve_model_name_empty_predefined_list(self):
        """Test that empty predefined list falls back to request model."""
        request = MockRequest(model="gpt-4")
        model_names = []

        result = self.mixin._resolve_model_name_with_fallback(request, model_names)

        assert result == "gpt-4"

    def test_resolve_model_name_never_returns_unknown(self):
        """Test that the method never returns 'unknown' (the old bug)."""
        # This test ensures we never hit the old "unknown" fallback
        request = MockRequest()  # No model attribute

        with patch("config.DEFAULT_MODEL", "auto"):
            result = self.mixin._resolve_model_name_with_fallback(request, None)

        assert result == "auto"
        assert result != "unknown"  # Explicitly check we don't get the old buggy value

    @patch("config.DEFAULT_MODEL", "configured-default")
    def test_resolve_model_name_uses_config_default(self):
        """Test that the method correctly imports and uses DEFAULT_MODEL from config."""
        request = MockRequest()

        result = self.mixin._resolve_model_name_with_fallback(request, None)

        assert result == "configured-default"

    def test_resolve_model_name_consistent_behavior(self):
        """Test that multiple calls with same inputs return consistent results."""
        request = MockRequest(model="test-model")

        result1 = self.mixin._resolve_model_name_with_fallback(request, None)
        result2 = self.mixin._resolve_model_name_with_fallback(request, None)

        assert result1 == result2 == "test-model"


class TestModelResolutionBugFix:
    """Specific tests for the bug fix that replaced 'unknown' with DEFAULT_MODEL."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = ConcreteWorkflowMixin()

    def test_bug_fix_no_more_unknown_fallback(self):
        """
        Test that confirms the specific bug is fixed.

        Before the fix, when neither predefined models nor request.model were available,
        the code would fallback to model_name = "unknown", which would cause a ValueError
        when ModelContext("unknown") was called.

        After the fix, it should fallback to DEFAULT_MODEL instead.
        """
        # Simulate the conditions that would trigger the old bug:
        # - No predefined models
        # - Request object without model attribute
        request = object()  # Simple object without model attribute

        with patch("config.DEFAULT_MODEL", "flash"):
            result = self.mixin._resolve_model_name_with_fallback(request, None)

        # Should get DEFAULT_MODEL, not "unknown"
        assert result == "flash"
        assert result != "unknown"

    def test_bug_fix_with_different_default_models(self):
        """Test the fix works with different DEFAULT_MODEL values."""
        request = object()  # No model attribute

        test_defaults = ["auto", "gpt-4", "gemini-pro", "claude-3"]

        for default_model in test_defaults:
            with patch("config.DEFAULT_MODEL", default_model):
                result = self.mixin._resolve_model_name_with_fallback(request, None)
                assert result == default_model
                assert result != "unknown"

    def test_regression_prevention(self):
        """
        Comprehensive regression test to ensure the bug doesn't reappear.

        This tests all the edge cases that could potentially trigger the old
        "unknown" fallback behavior.
        """
        scenarios = [
            # (predefined_models, request_model_attr, expected_not_unknown)
            (None, None, True),  # No predefined, no request model
            ([], None, True),  # Empty predefined, no request model
            (None, "", True),  # No predefined, empty request model
            ([], "", True),  # Empty predefined, empty request model
            (None, False, True),  # No predefined, falsy request model
            ([], False, True),  # Empty predefined, falsy request model
        ]

        for predefined, request_model, should_not_be_unknown in scenarios:
            if request_model is None:
                request = object()  # No model attribute
            else:
                request = MockRequest(model=request_model)

            with patch("config.DEFAULT_MODEL", "test-default"):
                result = self.mixin._resolve_model_name_with_fallback(request, predefined)

                if should_not_be_unknown:
                    assert (
                        result != "unknown"
                    ), f"Got 'unknown' for scenario: predefined={predefined}, request_model={request_model}"
                    assert result == "test-default"
