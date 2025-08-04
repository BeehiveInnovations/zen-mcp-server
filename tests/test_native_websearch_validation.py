"""
Test suite for websearch functionality validation.

This module contains tests to validate that websearch capabilities are properly
configured for different models and providers.
"""

from unittest.mock import Mock, patch

import pytest

from providers.base import ModelCapabilities, ProviderType, create_temperature_constraint
from providers.gemini import GeminiModelProvider
from providers.openai_provider import OpenAIModelProvider
from tools.shared.base_models import ToolRequest


class TestNativeWebsearchModelCapabilities:
    """Test native websearch model capability detection."""

    def setup_method(self):
        """Set up clean state before each test."""
        # Clear restriction service cache before each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    def teardown_method(self):
        """Clean up after each test to avoid singleton issues."""
        # Clear restriction service cache after each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    @patch.dict("os.environ", {"OPENAI_ALLOWED_MODELS": "o3,o3-mini,o3-pro-2025-06-10,o4-mini,gpt-4.1-2025-04-14"})
    def test_openai_models_support_native_websearch(self):
        """Test that OpenAI models are configured with native websearch support."""
        provider = OpenAIModelProvider("test-key")

        # All OpenAI models should support native websearch
        for model_name in ["o3", "o3-mini", "o3-pro-2025-06-10", "o4-mini", "gpt-4.1-2025-04-14"]:
            capabilities = provider.get_capabilities(model_name)
            assert capabilities.supports_native_websearch is True, f"Model {model_name} should support native websearch"

    def test_gemini_models_support_native_websearch(self):
        """Test that Gemini models are configured with native websearch support."""
        with patch("google.genai.Client"):
            provider = GeminiModelProvider("test-key")

            # Most Gemini models should support native websearch
            for model_name in ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]:
                capabilities = provider.get_capabilities(model_name)
                assert (
                    capabilities.supports_native_websearch is True
                ), f"Model {model_name} should support native websearch"

            # Lite model should not support native websearch
            capabilities = provider.get_capabilities("gemini-2.0-flash-lite")
            assert capabilities.supports_native_websearch is False, "Flash Lite should not support native websearch"

    def test_model_capabilities_fields(self):
        """Test that ModelCapabilities includes the supports_native_websearch field."""
        capabilities = ModelCapabilities(
            provider=ProviderType.GOOGLE,
            model_name="test-model",
            friendly_name="Test Model",
            context_window=100_000,
            max_output_tokens=4_000,
            supports_native_websearch=True,
            temperature_constraint=create_temperature_constraint("range"),
        )

        assert hasattr(capabilities, "supports_native_websearch")
        assert capabilities.supports_native_websearch is True


class TestWebsearchParameterValidation:
    """Test websearch parameter validation."""

    def test_use_websearch_true_valid(self):
        """Test that use_websearch=True is valid."""
        request = ToolRequest(use_websearch=True, model="flash")
        assert request.use_websearch is True

    def test_use_websearch_false_valid(self):
        """Test that use_websearch=False is valid."""
        request = ToolRequest(use_websearch=False, model="flash")
        assert request.use_websearch is False

    def test_default_values_valid(self):
        """Test that default values (use_websearch=True) are valid."""
        request = ToolRequest(model="flash")
        assert request.use_websearch is True


class TestProviderWebsearchRouting:
    """Test provider-specific routing logic for websearch."""

    @patch("openai.OpenAI")
    def test_openai_compatible_routes_to_responses_endpoint_when_use_websearch_true(self, mock_openai):
        """Test that OpenAI compatible provider routes to responses endpoint when use_websearch=True."""
        provider = OpenAIModelProvider("test-key")

        # Mock the responses endpoint method
        provider._generate_with_responses_endpoint = Mock(return_value=Mock())

        # Call generate_content with use_websearch=True (default)
        provider.generate_content(prompt="test prompt", model_name="o3", use_websearch=True)

        # Verify that responses endpoint was called
        provider._generate_with_responses_endpoint.assert_called_once()

    @patch("openai.OpenAI")
    def test_openai_compatible_uses_regular_endpoint_when_use_websearch_false(self, mock_openai):
        """Test that OpenAI compatible provider uses regular endpoint when use_websearch=False."""
        provider = OpenAIModelProvider("test-key")

        # Mock the client and chat completions
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "test response"
        mock_response.model = "o3"
        mock_response.id = "test-id"
        mock_response.created = 123456
        mock_response.choices[0].finish_reason = "stop"

        # Mock usage
        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30
        mock_response.usage = mock_usage

        mock_client.chat.completions.create.return_value = mock_response
        provider._client = mock_client

        # Call generate_content with use_websearch=False
        result = provider.generate_content(
            prompt="test prompt",
            model_name="gpt-4.1-2025-04-14",  # Use a model that supports temperature
            use_websearch=False,
        )

        # Verify that regular chat completions endpoint was called
        mock_client.chat.completions.create.assert_called_once()
        assert result.content == "test response"

    @patch("google.genai.Client")
    def test_gemini_adds_grounding_tool_when_use_websearch_true(self, mock_genai_client):
        """Test that Gemini provider adds grounding tool when use_websearch=True."""
        provider = GeminiModelProvider("test-key")

        # Mock the client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "test response with grounding"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].finish_reason = "STOP"

        mock_client.models.generate_content.return_value = mock_response
        provider._client = mock_client

        # Call generate_content with use_websearch=True
        _ = provider.generate_content(prompt="test prompt", model_name="gemini-2.5-flash", use_websearch=True)

        # Verify that generate_content was called
        mock_client.models.generate_content.assert_called_once()

        # Extract the call arguments to verify grounding tool was added
        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]

        # Check that tools were added to the generation config
        assert hasattr(config, "tools"), "Grounding tools should be added to generation config"
        assert config.tools is not None, "Tools list should not be None"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
