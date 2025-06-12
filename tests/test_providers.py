"""Tests for the model provider abstraction system"""

import json
import os
from unittest.mock import Mock, patch

from providers import ModelProviderRegistry, ModelResponse
from providers.base import ProviderType
from providers.gemini import GeminiModelProvider
from providers.openai import OpenAIModelProvider


class TestModelProviderRegistry:
    """Test the model provider registry"""

    def setup_method(self):
        """Clear registry before each test"""
        ModelProviderRegistry._providers.clear()
        ModelProviderRegistry._initialized_providers.clear()

    def test_register_provider(self):
        """Test registering a provider"""
        ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)

        assert ProviderType.GOOGLE in ModelProviderRegistry._providers
        assert ModelProviderRegistry._providers[ProviderType.GOOGLE] == GeminiModelProvider

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_get_provider(self):
        """Test getting a provider instance"""
        ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)

        provider = ModelProviderRegistry.get_provider(ProviderType.GOOGLE)

        assert provider is not None
        assert isinstance(provider, GeminiModelProvider)
        assert provider.api_key == "test-key"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_provider_no_api_key(self):
        """Test getting provider without API key returns None"""
        ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)

        provider = ModelProviderRegistry.get_provider(ProviderType.GOOGLE)

        assert provider is None

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_get_provider_for_model(self):
        """Test getting provider for a specific model"""
        ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)

        provider = ModelProviderRegistry.get_provider_for_model("gemini-2.5-flash-preview-05-20")

        assert provider is not None
        assert isinstance(provider, GeminiModelProvider)

    def test_get_available_providers(self):
        """Test getting list of available providers"""
        ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)
        ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)

        providers = ModelProviderRegistry.get_available_providers()

        assert len(providers) == 2
        assert ProviderType.GOOGLE in providers
        assert ProviderType.OPENAI in providers


class TestGeminiProvider:
    """Test Gemini model provider"""

    def test_provider_initialization(self):
        """Test provider initialization"""
        provider = GeminiModelProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.get_provider_type() == ProviderType.GOOGLE

    def test_get_capabilities(self):
        """Test getting model capabilities"""
        provider = GeminiModelProvider(api_key="test-key")

        capabilities = provider.get_capabilities("gemini-2.5-flash-preview-05-20")

        assert capabilities.provider == ProviderType.GOOGLE
        assert capabilities.model_name == "gemini-2.5-flash-preview-05-20"
        assert capabilities.max_tokens == 1_048_576
        assert capabilities.supports_extended_thinking

    def test_get_capabilities_pro_model(self):
        """Test getting capabilities for Pro model with thinking support"""
        provider = GeminiModelProvider(api_key="test-key")

        capabilities = provider.get_capabilities("gemini-2.5-pro-preview-06-05")

        assert capabilities.supports_extended_thinking

    def test_model_shorthand_resolution(self):
        """Test model shorthand resolution"""
        provider = GeminiModelProvider(api_key="test-key")

        assert provider.validate_model_name("flash")
        assert provider.validate_model_name("pro")

        capabilities = provider.get_capabilities("flash")
        assert capabilities.model_name == "gemini-2.5-flash-preview-05-20"

    def test_supports_thinking_mode(self):
        """Test thinking mode support detection"""
        provider = GeminiModelProvider(api_key="test-key")

        assert provider.supports_thinking_mode("gemini-2.5-flash-preview-05-20")
        assert provider.supports_thinking_mode("gemini-2.5-pro-preview-06-05")

    @patch("google.genai.Client")
    def test_generate_content(self, mock_client_class):
        """Test content generation"""
        # Mock the client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Generated content"
        # Mock candidates for finish_reason
        mock_candidate = Mock()
        mock_candidate.finish_reason = "STOP"
        mock_response.candidates = [mock_candidate]
        # Mock usage metadata
        mock_usage = Mock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 20
        mock_response.usage_metadata = mock_usage
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        provider = GeminiModelProvider(api_key="test-key")

        response = provider.generate_content(
            prompt="Test prompt", model_name="gemini-2.5-flash-preview-05-20", temperature=0.7
        )

        assert isinstance(response, ModelResponse)
        assert response.content == "Generated content"
        assert response.model_name == "gemini-2.5-flash-preview-05-20"
        assert response.provider == ProviderType.GOOGLE
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 20
        assert response.usage["total_tokens"] == 30


class TestOpenAIProvider:
    """Test OpenAI model provider"""

    def test_provider_initialization(self):
        """Test provider initialization"""
        provider = OpenAIModelProvider(api_key="test-key", organization="test-org")

        assert provider.api_key == "test-key"
        assert provider.organization == "test-org"
        assert provider.get_provider_type() == ProviderType.OPENAI

    def test_get_capabilities_o3(self):
        """Test getting O3 model capabilities"""
        provider = OpenAIModelProvider(api_key="test-key")

        capabilities = provider.get_capabilities("o3-mini")

        assert capabilities.provider == ProviderType.OPENAI
        assert capabilities.model_name == "o3-mini"
        assert capabilities.max_tokens == 200_000
        assert not capabilities.supports_extended_thinking

    def test_validate_model_names(self):
        """Test model name validation"""
        provider = OpenAIModelProvider(api_key="test-key")

        assert provider.validate_model_name("o3")
        assert provider.validate_model_name("o3-mini")
        assert not provider.validate_model_name("gpt-4o")
        assert not provider.validate_model_name("invalid-model")

    def test_no_thinking_mode_support(self):
        """Test that no OpenAI models support thinking mode"""
        provider = OpenAIModelProvider(api_key="test-key")

        assert not provider.supports_thinking_mode("o3")
        assert not provider.supports_thinking_mode("o3-mini")

    @patch("requests.post")
    def test_o3_pro_uses_responses_api(self, mock_post):
        """Test that o3-pro model uses v1/responses API endpoint"""
        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": [
                {"type": "reasoning", "id": "rs_test"},
                {"type": "message", "content": [{"type": "output_text", "text": "Generated content for o3-pro"}]},
            ],
            "model": "o3-pro",
            "id": "test-id",
            "created_at": 1234567890,
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        }
        mock_post.return_value = mock_response

        provider = OpenAIModelProvider(api_key="test-key", organization="test-org")

        response = provider.generate_content(
            prompt="Test prompt", model_name="o3-pro", system_prompt="System prompt", temperature=1.0
        )

        # Verify the correct endpoint was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "v1/responses" in call_args[0][0]

        # Verify headers include organization
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"
        assert headers["OpenAI-Organization"] == "test-org"

        # Verify the payload - it's sent as data, not json
        json_data = call_args[1]["data"]
        payload = json.loads(json_data)
        assert payload["model"] == "o3-pro"
        assert payload["input"] == "System prompt\n\nTest prompt"  # v1/responses uses "input" not "prompt"
        assert payload["temperature"] == 1.0

        # Verify the response
        assert response.content == "Generated content for o3-pro"
        assert response.metadata["api_endpoint"] == "v1/responses"

    @patch("requests.post")
    def test_o3_pro_handles_various_base_urls(self, mock_post):
        """Test that o3-pro correctly handles different base URL formats"""
        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "test"}]}],
            "model": "o3-pro",
        }
        mock_post.return_value = mock_response

        test_cases = [
            # Standard OpenAI URLs
            ("https://api.openai.com", "https://api.openai.com/v1/responses"),
            ("https://api.openai.com/", "https://api.openai.com/v1/responses"),
            ("https://api.openai.com/v1", "https://api.openai.com/v1/responses"),
            ("https://api.openai.com/v1/", "https://api.openai.com/v1/responses"),
            # Custom endpoints with /v1 in middle of path
            ("https://custom.com/api/v1", "https://custom.com/api/v1/responses"),
            ("https://custom.com/v1/api", "https://custom.com/v1/api/v1/responses"),
            # Edge cases
            ("https://example.com///", "https://example.com/v1/responses"),
            ("https://example.com/v1///", "https://example.com/v1/responses"),
        ]

        for base_url, expected_endpoint in test_cases:
            mock_post.reset_mock()

            provider = OpenAIModelProvider(api_key="test-key", base_url=base_url)
            provider.generate_content(prompt="Test", model_name="o3-pro", temperature=1.0)

            # Verify the correct endpoint was called
            mock_post.assert_called_once()
            actual_endpoint = mock_post.call_args[0][0]
            assert actual_endpoint == expected_endpoint, (
                f"For base_url={base_url}, expected {expected_endpoint} but got {actual_endpoint}"
            )

    @patch("requests.post")
    def test_o3_pro_filters_empty_kwargs(self, mock_post):
        """Test that o3-pro filters out empty keys and unknown parameters from kwargs"""
        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "Generated content"}]}],
            "model": "o3-pro",
            "id": "test-id",
            "created_at": 1234567890,
        }
        mock_post.return_value = mock_response

        provider = OpenAIModelProvider(api_key="test-key")

        # Call with various problematic kwargs
        response = provider.generate_content(
            prompt="Test prompt",
            model_name="o3-pro",
            temperature=1.0,  # o3-pro only supports temperature=1.0
            # These should be filtered out
            thinking_mode="high",  # Not supported by OpenAI
            **{"": "empty_key_value"},  # Empty string key
            some_unknown_param="should_be_ignored",
        )

        # Verify the API was called
        mock_post.assert_called_once()
        json_data = mock_post.call_args[1]["data"]
        payload = json.loads(json_data)

        # Verify only valid parameters are in payload
        assert "model" in payload
        assert "input" in payload  # v1/responses uses "input" not "prompt"
        assert "temperature" in payload
        assert payload["temperature"] == 1.0

        # Verify problematic parameters were filtered out
        assert "" not in payload  # Empty key should be filtered
        assert "thinking_mode" not in payload  # Unknown parameter
        assert "some_unknown_param" not in payload  # Unknown parameter

        # Verify response is correct
        assert response.content == "Generated content"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("requests.post")
    def test_o3_pro_direct_api_call(self, mock_post):
        """Test that o3-pro uses direct HTTP requests instead of OpenAI client"""
        # Mock the HTTP response
        mock_http_response = Mock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = {
            "output": [
                {"type": "reasoning", "id": "rs_test"},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Test response from o3-pro"}],
                },
            ],
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            "model": "o3-pro",
            "id": "resp_test",
            "created_at": 1234567890,
        }
        mock_post.return_value = mock_http_response

        # Create provider
        provider = OpenAIModelProvider(api_key="test-key")

        # Test generate_content
        response = provider.generate_content(
            prompt="Test prompt",
            model_name="o3-pro",
            system_prompt="System prompt",
            temperature=1.0,
            max_output_tokens=100,
        )

        # Verify HTTP request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "v1/responses" in call_args[0][0]

        # Verify request payload
        json_data = call_args[1]["data"]
        payload = json.loads(json_data)
        assert payload["model"] == "o3-pro"
        assert payload["input"] == "System prompt\n\nTest prompt"
        assert payload["temperature"] == 1.0
        assert payload["max_output_tokens"] == 100

        # Verify response content
        assert response.content == "Test response from o3-pro"
        assert response.model_name == "o3-pro"
        assert response.provider == ProviderType.OPENAI
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 20

    @patch("requests.post")
    def test_o3_pro_error_scenarios(self, mock_post):
        """Test o3-pro error handling for various scenarios"""
        provider = OpenAIModelProvider(api_key="test-key")

        # Test 1: Empty parameter should be filtered (the original issue fix)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "Success"}]}],
            "model": "o3-pro",
        }
        mock_post.return_value = mock_response

        # This should work because empty keys are filtered
        response = provider.generate_content(
            prompt="Test",
            model_name="o3-pro",
            temperature=1.0,
            **{"": "value"},  # Empty key that should be filtered
        )

        # Verify the request was made successfully
        assert response.content == "Success"

        # Verify the empty key was not sent
        call_args = mock_post.call_args
        json_data = call_args[1]["data"]
        payload = json.loads(json_data)
        assert "" not in payload

        # Test 2: Invalid parameter error
        mock_response.json.return_value = {
            "error": {
                "message": "Unknown parameter: 'invalid_param'.",
                "type": "invalid_request_error",
                "param": "invalid_param",
                "code": "unknown_parameter",
            }
        }

        # This should not raise an error because we filter unknown parameters
        mock_post.reset_mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "Success"}]}],
            "model": "o3-pro",
        }

        response = provider.generate_content(
            prompt="Test",
            model_name="o3-pro",
            temperature=1.0,
            invalid_param="should_be_filtered",
        )

        # Verify the invalid parameter was not sent
        call_args = mock_post.call_args
        json_data = call_args[1]["data"]
        payload = json.loads(json_data)
        assert "invalid_param" not in payload
        assert response.content == "Success"
