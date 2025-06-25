"""Tests for Azure OpenAI provider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from providers.azure_openai import AzureOpenAIModelProvider
from providers.base import ProviderType


class TestAzureOpenAIProvider:
    """Test Azure OpenAI provider functionality."""

    def test_initialization(self):
        """Test provider initialization with resource name and API key."""
        provider = AzureOpenAIModelProvider(
            resource_name="test-resource", api_key="test-key", api_version="2025-01-01-preview"
        )
        assert provider.resource_name == "test-resource"
        assert provider.api_key == "test-key"
        assert provider.api_version == "2025-01-01-preview"
        assert provider.base_url == "https://test-resource.openai.azure.com"

    def test_initialization_with_endpoint(self):
        """Test provider initialization with direct endpoint."""
        provider = AzureOpenAIModelProvider(
            endpoint="https://custom-endpoint.openai.azure.com/", api_key="test-key", api_version="2025-01-01-preview"
        )
        assert provider.resource_name == "custom-endpoint"
        assert provider.api_key == "test-key"
        assert provider.api_version == "2025-01-01-preview"
        assert provider.base_url == "https://custom-endpoint.openai.azure.com"

    def test_supported_models(self):
        """Test that only O3 and O4-mini models are supported."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")
        assert "o3" in provider.SUPPORTED_MODELS
        assert "o4-mini" in provider.SUPPORTED_MODELS
        assert len(provider.SUPPORTED_MODELS) == 2

    def test_provider_type(self):
        """Test provider type is AZURE_OPENAI."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")
        assert provider.get_provider_type() == ProviderType.AZURE_OPENAI

    def test_model_validation(self):
        """Test model name validation."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        # Valid models
        assert provider.validate_model_name("o3")
        assert provider.validate_model_name("o4-mini")
        assert provider.validate_model_name("mini")  # alias for o4-mini

        # Invalid models
        assert not provider.validate_model_name("gpt-4")
        assert not provider.validate_model_name("o3-mini")
        assert not provider.validate_model_name("invalid-model")

    def test_model_capabilities(self):
        """Test model capabilities for Azure models."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        # Test O3 capabilities
        o3_caps = provider.get_capabilities("o3")
        assert o3_caps.model_name == "o3"
        assert o3_caps.context_window == 200_000
        assert o3_caps.max_output_tokens == 65536
        assert not o3_caps.supports_temperature
        assert o3_caps.supports_images
        assert o3_caps.provider == ProviderType.AZURE_OPENAI

        # Test O4-mini capabilities
        o4_caps = provider.get_capabilities("o4-mini")
        assert o4_caps.model_name == "o4-mini"
        assert o4_caps.context_window == 200_000
        assert o4_caps.max_output_tokens == 65536
        assert not o4_caps.supports_temperature
        assert o4_caps.supports_images
        assert o4_caps.provider == ProviderType.AZURE_OPENAI

    def test_model_alias_resolution(self):
        """Test model alias resolution."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        # Test aliases
        assert provider._resolve_model_name("mini") == "o4-mini"
        assert provider._resolve_model_name("o4mini") == "o4-mini"
        assert provider._resolve_model_name("O4-MINI") == "o4-mini"  # case insensitive
        assert provider._resolve_model_name("o3") == "o3"
        assert provider._resolve_model_name("O3") == "o3"  # case insensitive

    def test_list_models(self):
        """Test listing available models."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        models = provider.list_models(respect_restrictions=False)
        assert set(models) == {"o3", "o4-mini"}

    @patch.dict(os.environ, {"AZURE_OPENAI_O3_DEPLOYMENT": "custom-o3-deployment"})
    def test_custom_deployment_name(self):
        """Test custom deployment name from environment variable."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        # Mock the parent generate_content to capture the deployment name
        with patch.object(provider, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30

            mock_client.chat.completions.create.return_value = mock_response

            # Generate content should use custom deployment name
            result = provider.generate_content(
                prompt="Test prompt", model_name="o3", system_prompt="Test system", temperature=1.0
            )

            # Check that custom deployment name was used
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == "custom-o3-deployment"

    def test_no_thinking_mode_support(self):
        """Test that Azure models don't support thinking mode."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        assert not provider.supports_thinking_mode("o3")
        assert not provider.supports_thinking_mode("o4-mini")

    def test_temperature_constraints(self):
        """Test that Azure O3/O4 models have fixed temperature."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        # O3 temperature constraint
        o3_caps = provider.get_capabilities("o3")
        assert not o3_caps.supports_temperature
        assert o3_caps.temperature_constraint.get_default() == 1.0
        assert o3_caps.temperature_constraint.validate(1.0)
        assert not o3_caps.temperature_constraint.validate(0.7)

        # O4-mini temperature constraint
        o4_caps = provider.get_capabilities("o4-mini")
        assert not o4_caps.supports_temperature
        assert o4_caps.temperature_constraint.get_default() == 1.0
        assert o4_caps.temperature_constraint.validate(1.0)
        assert not o4_caps.temperature_constraint.validate(0.5)

    def test_azure_client_creation(self):
        """Test that Azure-specific client is created."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        with patch("providers.azure_openai.AzureOpenAI") as mock_azure_client:
            # Access client property to trigger creation
            _ = provider.client

            # Verify AzureOpenAI was called with correct parameters
            mock_azure_client.assert_called_once_with(
                azure_endpoint="https://test-resource.openai.azure.com",
                api_key="test-key",
                api_version="2025-01-01-preview",
            )

    def test_reasoning_effort_configuration(self):
        """Test reasoning effort configuration for O3/O4 models."""
        provider = AzureOpenAIModelProvider(resource_name="test-resource", api_key="test-key")

        # Mock the client to test reasoning effort parameter
        with patch.object(provider, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.usage = MagicMock()
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30
            mock_response.choices[0].finish_reason = "stop"
            mock_response.model = "o3"
            mock_response.id = "test-id"
            mock_response.created = 1234567890

            mock_client.chat.completions.create.return_value = mock_response

            # Test with explicit reasoning effort
            result = provider.generate_content(prompt="Test prompt", model_name="o3", reasoning_effort="high")

            # Check that reasoning effort was passed
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["reasoning_effort"] == "high"

            # Test with environment variable
            with patch.dict(os.environ, {"AZURE_OPENAI_REASONING_EFFORT": "low"}):
                result = provider.generate_content(prompt="Test prompt", model_name="o4-mini")

                # Check that env var reasoning effort was used
                call_args = mock_client.chat.completions.create.call_args
                assert call_args.kwargs["reasoning_effort"] == "low"
