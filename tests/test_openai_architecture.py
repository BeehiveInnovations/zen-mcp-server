"""Tests for OpenAI architecture (Responses API vs Chat Completions API routing)."""

import unittest
from unittest.mock import MagicMock, patch

from providers.openai import OpenAIModelProvider


class TestOpenAIArchitecture(unittest.TestCase):
    """Test OpenAI provider architecture and API routing logic."""

    def test_responses_provider_initialization(self):
        """Test that OpenAIResponsesProvider is properly initialized."""
        with patch("openai.OpenAI"):
            provider = OpenAIModelProvider(api_key="test-key")
            self.assertIsNotNone(provider.responses_provider)
            self.assertEqual(provider.responses_provider.__class__.__name__, "OpenAIResponsesProvider")

    def test_routing_logic_when_use_responses_api_true(self):
        """Test routing to Responses API when use_openai_response_api=true."""
        with patch("openai.OpenAI") as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            # Mock Responses API provider
            with patch("providers.openai.OpenAIResponsesProvider") as mock_responses_class:
                mock_responses_instance = MagicMock()
                mock_responses_instance.generate_content.return_value = MagicMock(content="test response")
                mock_responses_class.return_value = mock_responses_instance

                provider = OpenAIModelProvider(api_key="test-key")

                # Mock capabilities with use_openai_response_api=TRUE
                mock_capabilities = MagicMock()
                mock_capabilities.use_openai_response_api = True

                with patch.object(provider, "get_capabilities", return_value=mock_capabilities):
                    provider.generate_content(prompt="Test prompt", model_name="test-model")

                    # EXPECT: Responses API should be called
                    mock_responses_instance.generate_content.assert_called_once()

    def test_routing_logic_when_use_responses_api_false(self):
        """Test routing to Chat API when use_openai_response_api=false."""
        with patch("openai.OpenAI"):
            provider = OpenAIModelProvider(api_key="test-key")

            # Mock the client's chat.completions.create method
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="test response"))]
            mock_response.usage = MagicMock(input_tokens=10, output_tokens=20, total_tokens=30)
            mock_response.model = "test-model"
            mock_response.id = "test-id"
            mock_response.created = 1234567890

            # Mock capabilities with use_openai_response_api=FALSE
            mock_capabilities = MagicMock()
            mock_capabilities.use_openai_response_api = False
            mock_capabilities.supports_temperature = True
            mock_capabilities.max_output_tokens = 4096

            with patch.object(provider.client.chat.completions, "create", return_value=mock_response):
                with patch.object(provider, "get_capabilities", return_value=mock_capabilities):
                    with patch.object(provider, "_resolve_model_name", return_value="test-model"):
                        result = provider.generate_content(prompt="Test prompt", model_name="test-model")

                        # EXPECT: Chat API should be called
                        provider.client.chat.completions.create.assert_called_once()
                        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
