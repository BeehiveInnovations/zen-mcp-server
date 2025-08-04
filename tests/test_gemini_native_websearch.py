"""Tests for Gemini provider websearch functionality."""

from unittest.mock import MagicMock, patch

import pytest

from providers.base import ProviderType
from providers.gemini import GeminiModelProvider


class TestGeminiWebsearch:
    """Test Gemini provider websearch functionality."""

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

    def test_gemini_models_websearch_support(self):
        """Test that Gemini models have correct websearch support configuration."""
        with patch("google.genai.Client"):
            provider = GeminiModelProvider("test-key")

            # Models that should support websearch
            supporting_models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
            for model_name in supporting_models:
                capabilities = provider.get_capabilities(model_name)
                assert capabilities.supports_native_websearch is True, f"Model {model_name} should support websearch"

            # Models that should NOT support websearch
            non_supporting_models = ["gemini-2.0-flash-lite"]
            for model_name in non_supporting_models:
                capabilities = provider.get_capabilities(model_name)
                assert (
                    capabilities.supports_native_websearch is False
                ), f"Model {model_name} should NOT support websearch"

    @patch("google.genai.Client")
    def test_gemini_adds_grounding_tool_when_websearch_enabled(self, mock_client_class):
        """Test that Gemini provider adds GoogleSearch grounding tool when use_websearch=True."""
        # Set up mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "Search results: Latest AI developments include..."
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 30
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = "STOP"

        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiModelProvider("test-key")

        # Call generate_content with use_websearch=True
        result = provider.generate_content(
            prompt="What are the latest developments in AI?",
            model_name="gemini-2.5-flash",
            use_websearch=True,
            temperature=0.7,
        )

        # Verify that generate_content was called
        mock_client.models.generate_content.assert_called_once()

        # Extract the call arguments to verify grounding tool was added
        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]

        # Check that tools were added to the generation config
        assert hasattr(config, "tools"), "Grounding tools should be added to generation config"
        assert config.tools is not None, "Tools list should not be None"
        assert len(config.tools) == 1, "Should have exactly one tool (GoogleSearch)"

        # Verify the tool is GoogleSearch
        tool = config.tools[0]
        assert hasattr(tool, "google_search"), "Tool should have google_search attribute"

        # Verify the response
        assert result.content == "Search results: Latest AI developments include..."
        assert result.model_name == "gemini-2.5-flash"

    @patch("google.genai.Client")
    def test_gemini_no_grounding_tool_when_websearch_disabled(self, mock_client_class):
        """Test that Gemini provider does NOT add grounding tool when use_websearch=False."""
        # Set up mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "Regular response without search"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 15
        mock_response.usage_metadata.candidates_token_count = 20
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = "STOP"

        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiModelProvider("test-key")

        # Call generate_content with use_websearch=False
        result = provider.generate_content(
            prompt="What is 2+2?", model_name="gemini-2.5-flash", use_websearch=False, temperature=0.7
        )

        # Verify that generate_content was called
        mock_client.models.generate_content.assert_called_once()

        # Extract the call arguments
        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]

        # Check that NO tools were added
        assert not hasattr(config, "tools") or config.tools is None, "No tools should be added when use_websearch=False"

        # Verify the response
        assert result.content == "Regular response without search"
        assert result.model_name == "gemini-2.5-flash"

    @patch("google.genai.Client")
    def test_gemini_lite_model_no_grounding_tool_even_when_requested(self, mock_client_class):
        """Test that Gemini Lite model does NOT add grounding tool even when use_websearch=True."""
        # Set up mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "Lite model response without search capability"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 15
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = "STOP"

        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiModelProvider("test-key")

        # Call generate_content with use_websearch=True on lite model
        result = provider.generate_content(
            prompt="What are the latest AI developments?",
            model_name="gemini-2.0-flash-lite",
            use_websearch=True,  # Requested but should be ignored
            temperature=0.7,
        )

        # Verify that generate_content was called
        mock_client.models.generate_content.assert_called_once()

        # Extract the call arguments
        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]

        # Check that NO tools were added (lite model doesn't support grounding)
        assert (
            not hasattr(config, "tools") or config.tools is None
        ), "Lite model should not add grounding tools even when use_websearch=True"

        # Verify the response
        assert result.content == "Lite model response without search capability"
        assert result.model_name == "gemini-2.0-flash-lite"

    @patch("google.genai.Client")
    def test_gemini_pro_model_with_websearch(self, mock_client_class):
        """Test that Gemini Pro model correctly adds grounding tool when use_websearch=True."""
        # Set up mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "Pro model search results with comprehensive analysis..."
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 25
        mock_response.usage_metadata.candidates_token_count = 40
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = "STOP"

        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiModelProvider("test-key")

        # Call generate_content with use_websearch=True on pro model
        result = provider.generate_content(
            prompt="Provide a comprehensive analysis of quantum computing breakthroughs",
            model_name="gemini-2.5-pro",
            use_websearch=True,
            temperature=0.7,
        )

        # Verify that generate_content was called
        mock_client.models.generate_content.assert_called_once()

        # Extract the call arguments to verify grounding tool was added
        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]

        # Check that tools were added
        assert hasattr(config, "tools"), "Pro model should add grounding tools when use_websearch=True"
        assert config.tools is not None, "Tools list should not be None"
        assert len(config.tools) == 1, "Should have exactly one tool (GoogleSearch)"

        # Verify the tool is GoogleSearch
        tool = config.tools[0]
        assert hasattr(tool, "google_search"), "Tool should have google_search attribute"

        # Verify the response
        assert result.content == "Pro model search results with comprehensive analysis..."
        assert result.model_name == "gemini-2.5-pro"

    @patch("google.genai.Client")
    def test_gemini_websearch_with_other_parameters(self, mock_client_class):
        """Test that websearch works correctly with other parameters like thinking_mode."""
        # Set up mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock the response
        mock_response = MagicMock()
        mock_response.text = "Thoughtful search-enhanced response"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 30
        mock_response.usage_metadata.candidates_token_count = 50
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason = "STOP"

        mock_client.models.generate_content.return_value = mock_response

        provider = GeminiModelProvider("test-key")

        # Call generate_content with both use_websearch and thinking_mode
        result = provider.generate_content(
            prompt="Analyze the implications of recent AI policy changes",
            model_name="gemini-2.5-pro",
            use_websearch=True,
            thinking_mode="high",
            temperature=0.8,
        )

        # Verify that generate_content was called
        mock_client.models.generate_content.assert_called_once()

        # Extract the call arguments
        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]

        # Check that both grounding tools AND thinking config were added
        assert hasattr(config, "tools"), "Should have grounding tools"
        assert config.tools is not None, "Tools should not be None"
        assert hasattr(config, "thinking_config"), "Should have thinking config"
        assert config.thinking_config is not None, "Thinking config should not be None"

        # Verify temperature was set
        assert config.temperature == 0.8, "Temperature should be preserved"

        # Verify the response
        assert result.content == "Thoughtful search-enhanced response"
        assert result.model_name == "gemini-2.5-pro"

    def test_gemini_model_capabilities_consistency(self):
        """Test that Gemini model capabilities are consistent with implementation."""
        with patch("google.genai.Client"):
            provider = GeminiModelProvider("test-key")

            # Test all supported models
            model_configs = [
                ("gemini-2.0-flash", True),
                ("gemini-2.0-flash-lite", False),
                ("gemini-2.5-flash", True),
                ("gemini-2.5-pro", True),
            ]

            for model_name, should_support_websearch in model_configs:
                capabilities = provider.get_capabilities(model_name)

                # Check websearch support matches expectation
                assert (
                    capabilities.supports_native_websearch == should_support_websearch
                ), f"Model {model_name} websearch support should be {should_support_websearch}"

                # All Gemini models should support grounding-compatible features
                assert capabilities.provider == ProviderType.GOOGLE
                assert capabilities.supports_system_prompts is True
                assert capabilities.supports_function_calling is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
