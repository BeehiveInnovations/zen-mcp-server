"""Tests for Gemini provider tools functionality"""

from unittest.mock import Mock, patch

import pytest

from providers.base import ModelResponse, ProviderType
from providers.gemini import GeminiModelProvider


class TestGeminiTools:
    """Test Gemini tools functionality"""

    def setup_method(self):
        """Setup test provider"""
        self.provider = GeminiModelProvider(api_key="test-key")

    def test_tools_always_included(self):
        """Test that URL context and Google search tools are always included"""
        with patch("google.genai.Client") as mock_client_class:
            # Mock the client and response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "Response with tools"
            mock_response.candidates = [Mock(finish_reason="STOP")]
            mock_response.usage_metadata = Mock(prompt_token_count=10, candidates_token_count=15)
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Call generate_content
            self.provider.generate_content(
                prompt="Test prompt",
                model_name="gemini-2.5-flash-preview-05-20"
            )

            # Verify generate_content was called
            mock_client.models.generate_content.assert_called_once()
            call_args = mock_client.models.generate_content.call_args

            # Check that tools are included in the config
            config = call_args.kwargs["config"]
            assert hasattr(config, "tools")
            assert config.tools is not None
            assert len(config.tools) == 2

    def test_tools_types_correct(self):
        """Test that the correct tool types are instantiated"""
        with patch("google.genai.Client") as mock_client_class:
            with patch("google.genai.types.Tool") as mock_tool_class:
                with patch("google.genai.types.UrlContext") as mock_url_context:
                    with patch("google.genai.types.GoogleSearch") as mock_google_search:
                        # Mock instances
                        mock_url_instance = Mock()
                        mock_search_instance = Mock()
                        mock_url_context.return_value = mock_url_instance
                        mock_google_search.return_value = mock_search_instance

                        # Mock tool creation
                        mock_tool_instance1 = Mock()
                        mock_tool_instance2 = Mock()
                        mock_tool_class.side_effect = [mock_tool_instance1, mock_tool_instance2]

                        # Mock client
                        mock_client = Mock()
                        mock_response = Mock()
                        mock_response.text = "Response"
                        mock_response.candidates = [Mock(finish_reason="STOP")]
                        mock_response.usage_metadata = Mock(prompt_token_count=5, candidates_token_count=10)
                        mock_client.models.generate_content.return_value = mock_response
                        mock_client_class.return_value = mock_client

                        # Call generate_content
                        self.provider.generate_content(
                            prompt="Test",
                            model_name="flash"
                        )

                        # Verify tool instantiation
                        mock_url_context.assert_called_once()
                        mock_google_search.assert_called_once()

                        # Verify Tool creation with correct parameters
                        assert mock_tool_class.call_count == 2
                        mock_tool_class.assert_any_call(url_context=mock_url_instance)
                        mock_tool_class.assert_any_call(google_search=mock_search_instance)

    def test_tools_with_system_prompt(self):
        """Test that tools work correctly with system prompts"""
        with patch("google.genai.Client") as mock_client_class:
            # Mock client
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "System prompt response"
            mock_response.candidates = [Mock(finish_reason="STOP")]
            mock_response.usage_metadata = Mock(prompt_token_count=20, candidates_token_count=30)
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Call with system prompt
            self.provider.generate_content(
                prompt="User prompt",
                model_name="gemini-2.5-pro-preview-06-05",
                system_prompt="You are a helpful assistant. Use search when needed."
            )

            # Verify call was made with combined prompt and tools
            mock_client.models.generate_content.assert_called_once()
            call_args = mock_client.models.generate_content.call_args

            # Check contents include both system and user prompt
            contents = call_args.kwargs["contents"]
            assert "You are a helpful assistant. Use search when needed." in contents
            assert "User prompt" in contents

            # Check tools are still included
            config = call_args.kwargs["config"]
            assert hasattr(config, "tools")
            assert len(config.tools) == 2

    def test_tools_with_thinking_mode(self):
        """Test that tools work with thinking mode enabled"""
        with patch("google.genai.Client") as mock_client_class:
            # Mock client
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "Thinking response"
            mock_response.candidates = [Mock(finish_reason="STOP")]
            mock_response.usage_metadata = Mock(prompt_token_count=25, candidates_token_count=35)
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Call with thinking mode
            self.provider.generate_content(
                prompt="Complex question requiring search",
                model_name="gemini-2.5-pro-preview-06-05",
                thinking_mode="high"
            )

            # Verify call was made
            mock_client.models.generate_content.assert_called_once()
            call_args = mock_client.models.generate_content.call_args

            # Check tools are included
            config = call_args.kwargs["config"]
            assert hasattr(config, "tools")
            assert len(config.tools) == 2

            # Check thinking config is also included
            assert hasattr(config, "thinking_config")
            assert config.thinking_config is not None

    def test_tools_error_handling(self):
        """Test error handling when tools fail"""
        with patch("google.genai.Client") as mock_client_class:
            # Mock client to raise an exception
            mock_client = Mock()
            mock_client.models.generate_content.side_effect = Exception("Tool error")
            mock_client_class.return_value = mock_client

            # Should raise RuntimeError after retries
            with pytest.raises(RuntimeError) as exc_info:
                self.provider.generate_content(
                    prompt="Test prompt",
                    model_name="flash"
                )

            assert "Tool error" in str(exc_info.value)

    def test_tools_with_max_output_tokens(self):
        """Test that tools work with max_output_tokens parameter"""
        with patch("google.genai.Client") as mock_client_class:
            # Mock client
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "Limited response"
            mock_response.candidates = [Mock(finish_reason="LENGTH")]
            mock_response.usage_metadata = Mock(prompt_token_count=15, candidates_token_count=100)
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Call with max_output_tokens
            response = self.provider.generate_content(
                prompt="Generate long response",
                model_name="flash",
                max_output_tokens=100
            )

            # Verify call was made
            mock_client.models.generate_content.assert_called_once()
            call_args = mock_client.models.generate_content.call_args

            # Check tools are included
            config = call_args.kwargs["config"]
            assert hasattr(config, "tools")
            assert len(config.tools) == 2

            # Check max_output_tokens is set
            assert hasattr(config, "max_output_tokens")
            assert config.max_output_tokens == 100

            # Check response metadata
            assert response.metadata["finish_reason"] == "LENGTH"

    def test_shorthand_models_with_tools(self):
        """Test that shorthand model names work with tools"""
        with patch("google.genai.Client") as mock_client_class:
            # Mock client
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "Shorthand response"
            mock_response.candidates = [Mock(finish_reason="STOP")]
            mock_response.usage_metadata = Mock(prompt_token_count=12, candidates_token_count=18)
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Test both shorthand names
            for model_shorthand in ["flash", "pro"]:
                self.provider.generate_content(
                    prompt="Test shorthand",
                    model_name=model_shorthand
                )

                # Verify proper model name resolution
                call_args = mock_client.models.generate_content.call_args
                model_arg = call_args.kwargs["model"]
                assert model_arg in ["gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-06-05"]

                # Verify tools are included
                config = call_args.kwargs["config"]
                assert len(config.tools) == 2

    def test_tools_response_metadata(self):
        """Test that response metadata is properly set when using tools"""
        with patch("google.genai.Client") as mock_client_class:
            # Mock client
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "Tool-enhanced response"
            mock_response.candidates = [Mock(finish_reason="STOP")]
            mock_response.usage_metadata = Mock(prompt_token_count=30, candidates_token_count=50)
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Call generate_content
            response = self.provider.generate_content(
                prompt="Search for Python tutorials",
                model_name="gemini-2.5-flash-preview-05-20",
                thinking_mode="medium"
            )

            # Verify response structure
            assert isinstance(response, ModelResponse)
            assert response.content == "Tool-enhanced response"
            assert response.model_name == "gemini-2.5-flash-preview-05-20"
            assert response.provider == ProviderType.GOOGLE
            assert response.friendly_name == "Gemini"

            # Check usage tracking
            assert response.usage["input_tokens"] == 30
            assert response.usage["output_tokens"] == 50
            assert response.usage["total_tokens"] == 80

            # Check metadata
            assert response.metadata["thinking_mode"] == "medium"
            assert response.metadata["finish_reason"] == "STOP"

