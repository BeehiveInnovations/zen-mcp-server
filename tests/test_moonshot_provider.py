"""Tests for Moonshot provider implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from providers.base import ProviderType
from providers.moonshot import MoonshotProvider


class TestMoonshotProvider:
    """Test Moonshot provider functionality."""

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

    @patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-key"})
    def test_initialization(self):
        """Test provider initialization."""
        provider = MoonshotProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.get_provider_type() == ProviderType.MOONSHOT
        assert provider.base_url == "https://api.moonshot.ai/v1"

    def test_initialization_with_custom_url(self):
        """Test provider initialization with custom base URL."""
        provider = MoonshotProvider("test-key", base_url="https://custom.moonshot.ai/v1")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://custom.moonshot.ai/v1"

    def test_model_validation(self):
        """Test model name validation."""
        provider = MoonshotProvider("test-key")

        # Test valid models
        assert provider.validate_model_name("kimi-latest") is True
        assert provider.validate_model_name("kimi-thinking-preview") is True
        assert provider.validate_model_name("kimi-thinking") is True
        assert provider.validate_model_name("moonshot-latest") is True
        assert provider.validate_model_name("moonshot-thinking") is True

        # Test invalid model
        assert provider.validate_model_name("invalid-model") is False
        assert provider.validate_model_name("gpt-4") is False
        assert provider.validate_model_name("gemini-pro") is False

    def test_resolve_model_name(self):
        """Test model name resolution."""
        provider = MoonshotProvider("test-key")

        # Test shorthand resolution
        assert provider._resolve_model_name("kimi-thinking") == "kimi-thinking-preview"
        assert provider._resolve_model_name("moonshot-latest") == "kimi-latest"
        assert provider._resolve_model_name("moonshot-thinking") == "kimi-thinking-preview"

        # Test full name passthrough
        assert provider._resolve_model_name("kimi-latest") == "kimi-latest"
        assert provider._resolve_model_name("kimi-thinking-preview") == "kimi-thinking-preview"

    def test_get_capabilities_kimi_latest(self):
        """Test getting model capabilities for kimi-latest."""
        provider = MoonshotProvider("test-key")

        capabilities = provider.get_capabilities("kimi-latest")
        assert capabilities.model_name == "kimi-latest"
        assert capabilities.friendly_name == "Moonshot (Kimi Latest)"
        assert capabilities.context_window == 200_000
        assert capabilities.provider == ProviderType.MOONSHOT
        assert capabilities.supports_extended_thinking is True
        assert capabilities.supports_system_prompts is True
        assert capabilities.supports_streaming is True
        assert capabilities.supports_function_calling is True

        # Test temperature range
        assert capabilities.temperature_constraint.min_temp == 0.0
        assert capabilities.temperature_constraint.max_temp == 1.0
        assert capabilities.temperature_constraint.default_temp == 0.3

    def test_get_capabilities_kimi_thinking(self):
        """Test getting model capabilities for kimi-thinking-preview."""
        provider = MoonshotProvider("test-key")

        capabilities = provider.get_capabilities("kimi-thinking-preview")
        assert capabilities.model_name == "kimi-thinking-preview"
        assert capabilities.friendly_name == "Moonshot (Kimi Thinking)"
        assert capabilities.context_window == 200_000
        assert capabilities.provider == ProviderType.MOONSHOT
        assert capabilities.supports_extended_thinking is True

    def test_get_capabilities_with_shorthand(self):
        """Test getting model capabilities with shorthand."""
        provider = MoonshotProvider("test-key")

        capabilities = provider.get_capabilities("moonshot-latest")
        assert capabilities.model_name == "kimi-latest"  # Should resolve to full name
        assert capabilities.context_window == 200_000

        capabilities_thinking = provider.get_capabilities("kimi-thinking")
        assert capabilities_thinking.model_name == "kimi-thinking-preview"  # Should resolve to full name

    def test_unsupported_model_capabilities(self):
        """Test error handling for unsupported models."""
        provider = MoonshotProvider("test-key")

        with pytest.raises(ValueError, match="Unsupported Moonshot model"):
            provider.get_capabilities("invalid-model")

    def test_thinking_mode_support(self):
        """Test that Moonshot models support thinking mode."""
        provider = MoonshotProvider("test-key")

        assert provider.supports_thinking_mode("kimi-latest")
        assert provider.supports_thinking_mode("kimi-thinking-preview")
        assert provider.supports_thinking_mode("kimi-thinking")
        assert provider.supports_thinking_mode("moonshot-latest")

    def test_provider_type(self):
        """Test provider type identification."""
        provider = MoonshotProvider("test-key")
        assert provider.get_provider_type() == ProviderType.MOONSHOT

    @patch.dict(os.environ, {"MOONSHOT_ALLOWED_MODELS": "kimi-latest"})
    def test_model_restrictions(self):
        """Test model restrictions functionality."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = MoonshotProvider("test-key")

        # kimi-latest should be allowed
        assert provider.validate_model_name("kimi-latest") is True
        assert provider.validate_model_name("moonshot-latest") is True  # Shorthand for kimi-latest

        # kimi-thinking-preview should be blocked by restrictions
        assert provider.validate_model_name("kimi-thinking-preview") is False
        assert provider.validate_model_name("kimi-thinking") is False

    @patch.dict(os.environ, {"MOONSHOT_ALLOWED_MODELS": "kimi-latest,moonshot-thinking"})
    def test_multiple_model_restrictions(self):
        """Test multiple models in restrictions."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = MoonshotProvider("test-key")

        # Models explicitly listed should be allowed
        assert provider.validate_model_name("kimi-latest") is True
        assert provider.validate_model_name("moonshot-thinking") is True

        # Aliases for listed models should be allowed
        assert provider.validate_model_name("moonshot-latest") is True  # Alias for kimi-latest

        # Models not explicitly listed (even if aliases exist) should not be allowed
        assert (
            provider.validate_model_name("kimi-thinking") is False
        )  # Not listed (moonshot-thinking is listed instead)

    @patch.dict(os.environ, {"MOONSHOT_ALLOWED_MODELS": ""})
    def test_empty_restrictions_allows_all(self):
        """Test that empty restrictions allow all models."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = MoonshotProvider("test-key")

        assert provider.validate_model_name("kimi-latest") is True
        assert provider.validate_model_name("kimi-thinking-preview") is True
        assert provider.validate_model_name("moonshot-latest") is True
        assert provider.validate_model_name("moonshot-thinking") is True

    def test_friendly_name(self):
        """Test friendly name constant."""
        provider = MoonshotProvider("test-key")
        assert provider.FRIENDLY_NAME == "Moonshot"

        capabilities = provider.get_capabilities("kimi-latest")
        assert capabilities.friendly_name == "Moonshot (Kimi Latest)"

    def test_supported_models_structure(self):
        """Test that SUPPORTED_MODELS has the correct structure."""
        provider = MoonshotProvider("test-key")

        # Check that all expected base models are present
        assert "kimi-latest" in provider.SUPPORTED_MODELS
        assert "kimi-thinking-preview" in provider.SUPPORTED_MODELS

        # Check model configs have required fields
        from providers.base import ModelCapabilities

        kimi_latest_config = provider.SUPPORTED_MODELS["kimi-latest"]
        assert isinstance(kimi_latest_config, ModelCapabilities)
        assert hasattr(kimi_latest_config, "context_window")
        assert hasattr(kimi_latest_config, "supports_extended_thinking")
        assert hasattr(kimi_latest_config, "aliases")
        assert kimi_latest_config.context_window == 200_000
        assert kimi_latest_config.supports_extended_thinking is True

        # Check aliases are correctly structured
        assert "kimi-latest" in kimi_latest_config.aliases
        assert "moonshot-latest" in kimi_latest_config.aliases

        kimi_thinking_config = provider.SUPPORTED_MODELS["kimi-thinking-preview"]
        assert "kimi-thinking" in kimi_thinking_config.aliases
        assert "moonshot-thinking" in kimi_thinking_config.aliases

    @patch("providers.openai_compatible.OpenAI")
    def test_generate_content_resolves_alias_before_api_call(self, mock_openai_class):
        """Test that generate_content resolves aliases before making API calls."""
        # Set up mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "kimi-latest"  # API returns the resolved model name
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        provider = MoonshotProvider("test-key")

        # Call generate_content with alias 'moonshot-latest'
        result = provider.generate_content(
            prompt="Test prompt",
            model_name="moonshot-latest",
            temperature=0.7,  # This should be resolved to "kimi-latest"
        )

        # Verify the API was called with the RESOLVED model name
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]

        # CRITICAL ASSERTION: The API should receive "kimi-latest", not "moonshot-latest"
        assert (
            call_kwargs["model"] == "kimi-latest"
        ), f"Expected 'kimi-latest' but API received '{call_kwargs['model']}'"

        # Verify other parameters
        assert call_kwargs["temperature"] == 0.7
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        assert call_kwargs["messages"][0]["content"] == "Test prompt"

        # Verify response
        assert result.content == "Test response"
        assert result.model_name == "kimi-latest"  # Should be the resolved name

    @patch("providers.openai_compatible.OpenAI")
    def test_generate_content_other_aliases(self, mock_openai_class):
        """Test other alias resolutions in generate_content."""
        from unittest.mock import MagicMock

        # Set up mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        provider = MoonshotProvider("test-key")

        # Test kimi-thinking -> kimi-thinking-preview
        mock_response.model = "kimi-thinking-preview"
        provider.generate_content(prompt="Test", model_name="kimi-thinking", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "kimi-thinking-preview"

        # Test moonshot-thinking -> kimi-thinking-preview
        provider.generate_content(prompt="Test", model_name="moonshot-thinking", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "kimi-thinking-preview"
