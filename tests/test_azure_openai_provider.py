"""Tests for Azure OpenAI provider implementation"""

import os
from unittest.mock import Mock, patch

import pytest

from providers.azure_openai import AzureOpenAIProvider
from providers.base import ModelCapabilities, ProviderType


class TestAzureOpenAIProvider:
    """Test Azure OpenAI model provider"""

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_provider_initialization(self):
        """Test provider initialization with required parameters"""
        provider = AzureOpenAIProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.azure_endpoint == "https://test-resource.openai.azure.com/"
        assert provider.api_version == "2024-02-01"
        assert provider.get_provider_type() == ProviderType.AZURE_OPENAI

    @patch.dict(os.environ, {}, clear=True)
    def test_provider_initialization_missing_endpoint(self):
        """Test that initialization fails without endpoint"""
        with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT environment variable is required"):
            AzureOpenAIProvider(api_key="test-key")

    @patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "http://test-resource.openai.azure.com/"})
    def test_provider_initialization_invalid_endpoint_protocol(self):
        """Test that initialization fails with non-HTTPS endpoint"""
        with pytest.raises(ValueError, match="Azure OpenAI endpoint must use HTTPS"):
            AzureOpenAIProvider(api_key="test-key")

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_get_capabilities_o3(self):
        """Test getting model capabilities for O3 model"""
        provider = AzureOpenAIProvider(api_key="test-key")

        capabilities = provider.get_capabilities("o3")

        assert isinstance(capabilities, ModelCapabilities)
        assert capabilities.provider == ProviderType.AZURE_OPENAI
        assert capabilities.model_name == "o3"
        assert capabilities.friendly_name == "Azure OpenAI"
        assert capabilities.context_window == 200_000
        assert not capabilities.supports_extended_thinking
        assert capabilities.supports_system_prompts
        assert capabilities.supports_streaming
        assert capabilities.supports_function_calling

        # O3 models have fixed temperature constraint
        temp_constraint = capabilities.temperature_constraint
        assert temp_constraint.validate(1.0)
        assert not temp_constraint.validate(0.5)

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_get_capabilities_gpt4o(self):
        """Test getting model capabilities for GPT-4o model"""
        provider = AzureOpenAIProvider(api_key="test-key")

        capabilities = provider.get_capabilities("gpt-4o")

        assert isinstance(capabilities, ModelCapabilities)
        assert capabilities.provider == ProviderType.AZURE_OPENAI
        assert capabilities.model_name == "gpt-4o"
        assert capabilities.context_window == 128_000

        # GPT-4o models support range temperature constraint
        temp_constraint = capabilities.temperature_constraint
        assert temp_constraint.validate(0.5)
        assert temp_constraint.validate(1.0)
        assert temp_constraint.validate(1.5)

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_get_capabilities_unsupported_model(self):
        """Test that unsupported model raises error"""
        provider = AzureOpenAIProvider(api_key="test-key")

        with pytest.raises(ValueError, match="Unsupported Azure OpenAI model"):
            provider.get_capabilities("unsupported-model")

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_validate_model_name_supported(self):
        """Test model validation for supported models"""
        provider = AzureOpenAIProvider(api_key="test-key")

        assert provider.validate_model_name("o3")
        assert provider.validate_model_name("o4-mini")
        assert provider.validate_model_name("gpt-4o")
        assert provider.validate_model_name("mini")  # shorthand

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_validate_model_name_unsupported(self):
        """Test model validation for unsupported models"""
        provider = AzureOpenAIProvider(api_key="test-key")

        assert not provider.validate_model_name("unsupported-model")
        assert not provider.validate_model_name("gpt-3.5-turbo")

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_resolve_model_name_shorthand(self):
        """Test resolving model shorthand names"""
        provider = AzureOpenAIProvider(api_key="test-key")

        assert provider._resolve_model_name("mini") == "o4-mini"
        assert provider._resolve_model_name("o3mini") == "o3-mini"
        assert provider._resolve_model_name("o4minihigh") == "o4-mini-high"
        assert provider._resolve_model_name("o3") == "o3"  # No shorthand

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_supports_thinking_mode(self):
        """Test that Azure OpenAI models don't support thinking mode"""
        provider = AzureOpenAIProvider(api_key="test-key")

        assert not provider.supports_thinking_mode("o3")
        assert not provider.supports_thinking_mode("gpt-4o")

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_count_tokens_approximation(self):
        """Test token counting approximation"""
        provider = AzureOpenAIProvider(api_key="test-key")

        # Test approximation (1 token ≈ 4 characters)
        text = "This is a test string"  # 21 characters
        token_count = provider.count_tokens(text, "o3")
        assert token_count == 21 // 4  # Should be 5

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_success(self, mock_azure_openai):
        """Test successful content generation"""
        # Mock the Azure OpenAI client and response
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.id = "test-response-id"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        provider = AzureOpenAIProvider(api_key="test-key")

        response = provider.generate_content(
            prompt="Test prompt", model_name="o4-mini", system_prompt="Test system prompt", temperature=0.7
        )

        assert response.content == "Test response"
        assert response.model_name == "o4-mini"  # Should use deployment name
        assert response.friendly_name == "Azure OpenAI"
        assert response.provider == ProviderType.AZURE_OPENAI
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 5
        assert response.usage["total_tokens"] == 15
        assert response.metadata["azure_endpoint"] == "https://test-resource.openai.azure.com/"
        assert response.metadata["api_version"] == "2024-02-01"
        assert response.metadata["deployment_name"] == "o4-mini"
        assert response.metadata["original_model_name"] == "o4-mini"

        # Verify the API call was made correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "o4-mini"  # Should use deployment name
        assert call_args["temperature"] == 0.7
        assert len(call_args["messages"]) == 2  # System + user message
        assert call_args["messages"][0]["role"] == "system"
        assert call_args["messages"][0]["content"] == "Test system prompt"
        assert call_args["messages"][1]["role"] == "user"
        assert call_args["messages"][1]["content"] == "Test prompt"

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_with_deployment_name(self, mock_azure_openai):
        """Test content generation with custom deployment name"""
        # Mock the Azure OpenAI client and response
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.id = "test-response-id"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        provider = AzureOpenAIProvider(api_key="test-key")

        response = provider.generate_content(
            prompt="Test prompt", model_name="o4-mini", deployment_name="custom-deployment", temperature=0.7
        )

        # Verify the API call used the custom deployment name
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "custom-deployment"

        # Response should reflect the deployment name used
        assert response.model_name == "custom-deployment"
        assert response.metadata["deployment_name"] == "custom-deployment"
        assert response.metadata["original_model_name"] == "o4-mini"

    @patch.dict(
        os.environ,
        {"AZURE_OPENAI_ENDPOINT": "https://test-resource.openai.azure.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"},
    )
    def test_is_localhost_url(self):
        """Test that Azure OpenAI endpoints are never considered localhost"""
        provider = AzureOpenAIProvider(api_key="test-key")

        assert not provider._is_localhost_url()

    @patch.dict(
        os.environ, {"AZURE_OPENAI_ENDPOINT": "https://custom.example.com/", "AZURE_OPENAI_API_VERSION": "2024-02-01"}
    )
    def test_validate_base_url_warning(self):
        """Test validation warning for non-standard Azure endpoints"""
        with patch("providers.azure_openai.logger") as mock_logger:
            provider = AzureOpenAIProvider(api_key="test-key")

            provider._validate_base_url()

            # Should log a warning for non-standard endpoint format
            # Note: It may be called multiple times during initialization
            assert mock_logger.warning.called
            warning_calls = [
                call for call in mock_logger.warning.call_args_list if "doesn't follow expected format" in str(call)
            ]
            assert len(warning_calls) > 0
