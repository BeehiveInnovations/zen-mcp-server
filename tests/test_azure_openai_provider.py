"""Tests for Azure OpenAI provider implementation using Responses API."""

from unittest.mock import MagicMock, patch

import pytest

from providers.azure_openai import AzureOpenAIProvider
from providers.shared import ProviderType


class TestAzureOpenAIProvider:
    """Test Azure OpenAI provider functionality."""

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

    def test_initialization_success(self):
        """Test successful provider initialization with all required parameters."""
        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        assert provider.api_key == "test-key"
        assert provider.azure_endpoint == "https://test.openai.azure.com"
        assert provider.api_version == "2025-03-01-preview"
        assert provider.deployment_name == "gpt-5"
        assert provider.get_provider_type() == ProviderType.AZURE

    def test_initialization_missing_azure_endpoint(self):
        """Test initialization fails without azure_endpoint."""
        with pytest.raises(ValueError, match="azure_endpoint is required"):
            AzureOpenAIProvider(
                api_key="test-key",
                api_version="2025-03-01-preview",
                deployment_name="gpt-5",
            )

    def test_initialization_missing_api_version(self):
        """Test initialization fails without api_version."""
        with pytest.raises(ValueError, match="api_version is required"):
            AzureOpenAIProvider(
                api_key="test-key",
                azure_endpoint="https://test.openai.azure.com",
                deployment_name="gpt-5",
            )

    def test_initialization_missing_deployment_name(self):
        """Test initialization fails without deployment_name."""
        with pytest.raises(ValueError, match="deployment_name is required"):
            AzureOpenAIProvider(
                api_key="test-key",
                azure_endpoint="https://test.openai.azure.com",
                api_version="2025-03-01-preview",
            )

    def test_initialization_old_api_version_warning(self):
        """Test warning is logged for API versions older than 2025-03-01-preview."""
        with patch("providers.azure_openai.logger") as mock_logger:
            provider = AzureOpenAIProvider(
                api_key="test-key",
                azure_endpoint="https://test.openai.azure.com",
                api_version="2024-06-01",
                deployment_name="gpt-5",
            )

            # Verify provider was created and warning was logged
            assert provider is not None
            mock_logger.warning.assert_called_once()
            warning_message = mock_logger.warning.call_args[0][0]
            assert "may not support Responses API" in warning_message

    def test_model_validation_gpt5(self):
        """Test model name validation for GPT-5."""
        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        # Test valid models
        assert provider.validate_model_name("gpt-5") is True
        assert provider.validate_model_name("gpt-5-codex") is True

        # Test valid aliases
        assert provider.validate_model_name("gpt5") is True
        assert provider.validate_model_name("azure-gpt5") is True
        assert provider.validate_model_name("azure-gpt-5") is True
        assert provider.validate_model_name("codex") is True
        assert provider.validate_model_name("gpt5-codex") is True
        assert provider.validate_model_name("gpt5codex") is True
        assert provider.validate_model_name("azure-codex") is True
        assert provider.validate_model_name("azure-gpt5-codex") is True

        # Test invalid models
        assert provider.validate_model_name("gpt-4") is False
        assert provider.validate_model_name("o3") is False
        assert provider.validate_model_name("invalid-model") is False

    def test_resolve_model_name(self):
        """Test model name resolution for aliases."""
        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        # Test GPT-5 aliases
        assert provider._resolve_model_name("gpt5") == "gpt-5"
        assert provider._resolve_model_name("azure-gpt5") == "gpt-5"
        assert provider._resolve_model_name("azure-gpt-5") == "gpt-5"

        # Test GPT-5 Codex aliases
        assert provider._resolve_model_name("gpt5-codex") == "gpt-5-codex"
        assert provider._resolve_model_name("gpt5codex") == "gpt-5-codex"
        assert provider._resolve_model_name("codex") == "gpt-5-codex"
        assert provider._resolve_model_name("azure-codex") == "gpt-5-codex"
        assert provider._resolve_model_name("azure-gpt5-codex") == "gpt-5-codex"

        # Test full names pass through unchanged
        assert provider._resolve_model_name("gpt-5") == "gpt-5"
        assert provider._resolve_model_name("gpt-5-codex") == "gpt-5-codex"

    def test_get_capabilities_gpt5(self):
        """Test getting model capabilities for GPT-5."""
        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        capabilities = provider.get_capabilities("gpt-5")

        assert capabilities.model_name == "gpt-5"
        assert capabilities.friendly_name == "Azure OpenAI (GPT-5)"
        assert capabilities.provider == ProviderType.AZURE
        assert capabilities.intelligence_score == 16
        assert capabilities.context_window == 400_000
        assert capabilities.max_output_tokens == 128_000
        assert capabilities.supports_extended_thinking is True
        assert capabilities.supports_system_prompts is True
        assert capabilities.supports_streaming is True
        assert capabilities.supports_function_calling is True
        assert capabilities.supports_json_mode is True
        assert capabilities.supports_images is True
        assert capabilities.max_image_size_mb == 20.0
        # Azure Responses API enforces fixed temperature behavior for reasoning
        # models in this provider. Temperature is not user-tunable.
        assert capabilities.supports_temperature is False
        assert getattr(capabilities.temperature_constraint, "value", None) == 1.0

    def test_get_capabilities_gpt5_codex(self):
        """Test getting model capabilities for GPT-5 Codex."""
        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5-codex",
        )

        capabilities = provider.get_capabilities("gpt-5-codex")

        assert capabilities.model_name == "gpt-5-codex"
        assert capabilities.friendly_name == "Azure OpenAI (GPT-5 Codex)"
        assert capabilities.provider == ProviderType.AZURE
        assert capabilities.intelligence_score == 17
        assert capabilities.context_window == 400_000
        assert capabilities.max_output_tokens == 128_000
        assert capabilities.supports_extended_thinking is True
        assert capabilities.supports_system_prompts is True
        assert capabilities.supports_streaming is True
        assert capabilities.supports_function_calling is True
        assert capabilities.supports_json_mode is True
        assert capabilities.supports_images is False
        assert capabilities.max_image_size_mb == 0.0
        # GPT-5-Codex requires fixed temperature=1.0
        assert capabilities.supports_temperature is False
        assert capabilities.temperature_constraint.value == 1.0

    def test_get_capabilities_with_alias(self):
        """Test getting model capabilities with alias resolves correctly."""
        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        capabilities = provider.get_capabilities("gpt5")
        assert capabilities.model_name == "gpt-5"
        assert capabilities.friendly_name == "Azure OpenAI (GPT-5)"

        capabilities = provider.get_capabilities("codex")
        assert capabilities.model_name == "gpt-5-codex"
        assert capabilities.friendly_name == "Azure OpenAI (GPT-5 Codex)"

    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_basic(self, mock_azure_class):
        """Test basic content generation using Responses API."""
        # Set up mock Azure client
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        # Mock the response object
        mock_response = MagicMock()
        mock_response.output_text = "This is the response content"
        mock_response.id = "test-response-id"
        mock_response.status = "completed"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.usage.total_tokens = 150

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        # Generate content
        result = provider.generate_content(
            prompt="Test prompt",
            model_name="gpt-5",
            temperature=1.0,
        )

        # Verify API was called correctly
        mock_client.responses.create.assert_called_once()
        call_kwargs = mock_client.responses.create.call_args[1]

        assert call_kwargs["model"] == "gpt-5"
        # For codex/reasoning models, temperature is omitted (fixed internally)
        assert "temperature" not in call_kwargs
        assert len(call_kwargs["input"]) == 1
        assert call_kwargs["input"][0]["role"] == "user"
        assert call_kwargs["input"][0]["content"] == "Test prompt"

        # Verify response
        assert result.content == "This is the response content"
        assert result.model_name == "gpt-5"
        assert result.friendly_name == "Azure OpenAI (GPT-5)"
        assert result.provider == ProviderType.AZURE
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50
        assert result.usage["total_tokens"] == 150

    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_with_system_prompt(self, mock_azure_class):
        """Test content generation with system prompt."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.output_text = "Response with system prompt"
        mock_response.id = "test-id"
        mock_response.status = "completed"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 150
        mock_response.usage.output_tokens = 75
        mock_response.usage.total_tokens = 225

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        result = provider.generate_content(
            prompt="User message",
            model_name="gpt-5",
            system_prompt="You are a helpful assistant",
            temperature=1.0,
        )

        # Verify messages include system prompt
        call_kwargs = mock_client.responses.create.call_args[1]
        assert len(call_kwargs["input"]) == 2
        assert call_kwargs["input"][0]["role"] == "system"
        assert call_kwargs["input"][0]["content"] == "You are a helpful assistant"
        assert call_kwargs["input"][1]["role"] == "user"
        assert call_kwargs["input"][1]["content"] == "User message"

        assert result.content == "Response with system prompt"

    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_extracts_from_output_array(self, mock_azure_class):
        """Test content extraction from output array when output_text is not available."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        # Mock response with output array (no output_text)
        mock_response = MagicMock()
        mock_response.output_text = None

        # Create mock output items
        text_item = MagicMock()
        text_item.type = "text"
        text_item.content = [MagicMock(text="Text from output array")]

        mock_response.output = [text_item]
        mock_response.id = "test-id"
        mock_response.status = "completed"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 25
        mock_response.usage.total_tokens = 75

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        result = provider.generate_content(
            prompt="Test prompt",
            model_name="gpt-5",
            temperature=1.0,
        )

        # Verify content extracted from output array
        assert result.content == "Text from output array"

    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_extracts_from_message_type(self, mock_azure_class):
        """Test content extraction from output array with message type."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        # Mock response with output array containing message type
        mock_response = MagicMock()
        mock_response.output_text = None

        message_item = MagicMock()
        message_item.type = "message"
        message_item.content = "Direct message content"

        mock_response.output = [message_item]
        mock_response.id = "test-id"
        mock_response.status = "completed"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 30
        mock_response.usage.output_tokens = 20
        mock_response.usage.total_tokens = 50

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        result = provider.generate_content(
            prompt="Test",
            model_name="gpt-5",
            temperature=1.0,
        )

        assert result.content == "Direct message content"

    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_no_content_error(self, mock_azure_class):
        """Test error when no content can be extracted from response."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        # Mock response with no content
        mock_response = MagicMock()
        mock_response.output_text = None
        mock_response.output = []
        mock_response.usage = MagicMock()

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        with pytest.raises(ValueError, match="No content available in response"):
            provider.generate_content(
                prompt="Test",
                model_name="gpt-5",
                temperature=1.0,
            )

    @patch("providers.azure_openai.AzureOpenAI")
    def test_token_usage_extraction(self, mock_azure_class):
        """Test token usage extraction from response."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.output_text = "Test response"
        mock_response.id = "test-id"
        mock_response.status = "completed"

        # Test with input_tokens and output_tokens format
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 200
        mock_response.usage.output_tokens = 100
        mock_response.usage.total_tokens = 300

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        result = provider.generate_content(
            prompt="Test", model_name="gpt-5", temperature=1.0
        )

        assert result.usage["input_tokens"] == 200
        assert result.usage["prompt_tokens"] == 200
        assert result.usage["output_tokens"] == 100
        assert result.usage["completion_tokens"] == 100
        assert result.usage["total_tokens"] == 300

    @patch("providers.azure_openai.AzureOpenAI")
    def test_token_usage_extraction_alternative_format(self, mock_azure_class):
        """Test token usage extraction with prompt_tokens and completion_tokens format."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.output_text = "Test response"
        mock_response.id = "test-id"
        mock_response.status = "completed"

        # Test with prompt_tokens and completion_tokens format
        # Create a custom mock class that only has specific attributes
        class UsageWithLegacyFields:
            prompt_tokens = 250
            completion_tokens = 125

        mock_response.usage = UsageWithLegacyFields()

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        result = provider.generate_content(
            prompt="Test", model_name="gpt-5", temperature=1.0
        )

        assert result.usage["prompt_tokens"] == 250
        assert result.usage["input_tokens"] == 250
        assert result.usage["completion_tokens"] == 125
        assert result.usage["output_tokens"] == 125
        assert result.usage["total_tokens"] == 375  # Calculated

    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_with_max_output_tokens(self, mock_azure_class):
        """Test content generation with explicit max_output_tokens."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.output_text = "Response"
        mock_response.id = "test-id"
        mock_response.status = "completed"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 25
        mock_response.usage.total_tokens = 75

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        result = provider.generate_content(
            prompt="Test",
            model_name="gpt-5",
            max_output_tokens=4000,
            temperature=1.0,
        )

        # Verify max_output_tokens was passed and result is not None
        assert result is not None
        call_kwargs = mock_client.responses.create.call_args[1]
        assert call_kwargs["max_output_tokens"] == 4000

    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_api_error(self, mock_azure_class):
        """Test error handling when API call fails."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        # Simulate API error
        mock_client.responses.create.side_effect = Exception("API Error")

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        with pytest.raises(Exception, match="API Error"):
            provider.generate_content(
                prompt="Test",
                model_name="gpt-5",
                temperature=1.0,
            )

    def test_provider_type(self):
        """Test get_provider_type returns ProviderType.AZURE."""
        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        assert provider.get_provider_type() == ProviderType.AZURE

    def test_get_preferred_model_extended_reasoning(self):
        """Test get_preferred_model for extended reasoning category."""
        from tools.models import ToolModelCategory

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        # Test with both models available
        allowed = ["gpt-5", "gpt-5-codex"]
        preferred = provider.get_preferred_model(ToolModelCategory.EXTENDED_REASONING, allowed)
        assert preferred == "gpt-5-codex"  # Codex preferred for extended reasoning

        # Test with only gpt-5 available
        allowed = ["gpt-5"]
        preferred = provider.get_preferred_model(ToolModelCategory.EXTENDED_REASONING, allowed)
        assert preferred == "gpt-5"

        # Test with empty list
        preferred = provider.get_preferred_model(ToolModelCategory.EXTENDED_REASONING, [])
        assert preferred is None

    def test_get_preferred_model_fast_response(self):
        """Test get_preferred_model for fast response category."""
        from tools.models import ToolModelCategory

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        # Test with both models available
        allowed = ["gpt-5", "gpt-5-codex"]
        preferred = provider.get_preferred_model(ToolModelCategory.FAST_RESPONSE, allowed)
        assert preferred == "gpt-5"  # gpt-5 preferred for fast response

        # Test with only codex available
        allowed = ["gpt-5-codex"]
        preferred = provider.get_preferred_model(ToolModelCategory.FAST_RESPONSE, allowed)
        assert preferred == "gpt-5-codex"

    def test_get_preferred_model_balanced(self):
        """Test get_preferred_model for balanced category."""
        from tools.models import ToolModelCategory

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        # Test with both models available
        allowed = ["gpt-5", "gpt-5-codex"]
        preferred = provider.get_preferred_model(ToolModelCategory.BALANCED, allowed)
        assert preferred == "gpt-5-codex"  # Codex preferred for code tasks

        # Test with only gpt-5 available
        allowed = ["gpt-5"]
        preferred = provider.get_preferred_model(ToolModelCategory.BALANCED, allowed)
        assert preferred == "gpt-5"

    @patch("providers.azure_openai.AzureOpenAI")
    def test_close_cleanup(self, mock_azure_class):
        """Test close method properly cleans up resources."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        # Initialize client by calling _get_client
        provider._get_client()
        assert provider._client is not None

        # Close should set client to None
        provider.close()
        assert provider._client is None

    @patch("providers.azure_openai.AzureOpenAI")
    def test_lazy_client_initialization(self, mock_azure_class):
        """Test that Azure client is lazily initialized on first use."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5",
        )

        # Client should not be initialized yet
        assert provider._client is None
        mock_azure_class.assert_not_called()

        # Get client should initialize it
        client = provider._get_client()
        assert client is not None
        assert provider._client is not None
        mock_azure_class.assert_called_once_with(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
        )

        # Second call should return same client
        client2 = provider._get_client()
        assert client2 is client
        mock_azure_class.assert_called_once()  # Still only called once

    @patch("providers.azure_openai.AzureOpenAI")
    def test_metadata_in_response(self, mock_azure_class):
        """Test that response metadata includes deployment and status info."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.output_text = "Test content"
        mock_response.id = "response-123"
        mock_response.status = "completed"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 25
        mock_response.usage.total_tokens = 75

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="my-gpt5-deployment",
        )

        result = provider.generate_content(
            prompt="Test", model_name="gpt-5", temperature=1.0
        )

        # Verify metadata
        assert result.metadata["response_id"] == "response-123"
        assert result.metadata["status"] == "completed"
        assert result.metadata["deployment_name"] == "my-gpt5-deployment"

    @patch("providers.azure_openai.AzureOpenAI")
    def test_generate_content_resolves_alias(self, mock_azure_class):
        """Test that generate_content resolves aliases before making API call."""
        mock_client = MagicMock()
        mock_azure_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.output_text = "Test response"
        mock_response.id = "test-id"
        mock_response.status = "completed"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 25
        mock_response.usage.total_tokens = 75

        mock_client.responses.create.return_value = mock_response

        provider = AzureOpenAIProvider(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2025-03-01-preview",
            deployment_name="gpt-5-codex",
        )

        # Use alias "codex"
        result = provider.generate_content(
            prompt="Test prompt",
            model_name="codex",
            temperature=1.0,
        )

        # Verify API was called with deployment name (not the alias)
        call_kwargs = mock_client.responses.create.call_args[1]
        assert call_kwargs["model"] == "gpt-5-codex"  # Uses deployment name

        # Verify result uses resolved model name
        assert result.model_name == "gpt-5-codex"
