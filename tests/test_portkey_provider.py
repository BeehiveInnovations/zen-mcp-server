"""Tests for Portkey provider implementation."""

import os
from unittest.mock import patch

from providers.base import ProviderType
from providers.portkey import PortkeyProvider


class TestPortkeyProvider:
    """Test Portkey provider functionality."""

    def setup_method(self):
        """Set up clean state before each test."""
        # Clear restriction service cache before each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None
        # Reset class-level registry
        PortkeyProvider._registry = None

    def teardown_method(self):
        """Clean up after each test to avoid singleton issues."""
        # Clear restriction service cache after each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None
        # Reset class-level registry
        PortkeyProvider._registry = None

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_initialization(self):
        """Test provider initialization."""
        provider = PortkeyProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.get_provider_type() == ProviderType.PORTKEY
        assert provider.base_url == "https://api.portkey.ai/v1"

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_initialization_with_virtual_key(self):
        """Test provider initialization with virtual key."""
        provider = PortkeyProvider("test-key", virtual_key="vk-123")
        assert provider.api_key == "test-key"
        assert provider.virtual_key == "vk-123"

    def test_get_clean_headers(self):
        """Test headers cleaning functionality."""
        # Since DEFAULT_HEADERS uses os.getenv at import time, we need to test
        # the filtering logic rather than dynamic environment changes

        # Mock the class variable to test the filtering
        original_headers = PortkeyProvider.DEFAULT_HEADERS.copy()

        try:
            # Test with headers containing None values
            PortkeyProvider.DEFAULT_HEADERS = {
                "x-portkey-api-key": "test-key",
                "x-test-header": None,
                "x-valid-header": "value",
            }
            headers = PortkeyProvider._get_clean_headers()
            assert headers == {"x-portkey-api-key": "test-key", "x-valid-header": "value"}

            # Test with all None values
            PortkeyProvider.DEFAULT_HEADERS = {"x-portkey-api-key": None, "x-test-header": None}
            headers = PortkeyProvider._get_clean_headers()
            assert headers == {}

        finally:
            # Restore original headers
            PortkeyProvider.DEFAULT_HEADERS = original_headers

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_model_validation(self):
        """Test model name validation."""
        provider = PortkeyProvider("test-key")

        # Test valid models from registry
        assert provider.validate_model_name("gpt-4") is True
        assert provider.validate_model_name("claude-3-5-sonnet-20241022") is True
        assert provider.validate_model_name("gemini-1.5-pro") is True
        assert provider.validate_model_name("o1-preview") is True

        # Test model aliases
        assert provider.validate_model_name("gpt4") is True
        assert provider.validate_model_name("claude") is True
        assert provider.validate_model_name("flash") is True

        # Portkey as a gateway provider accepts any model name unless restricted
        # So even "invalid-model" returns True unless there are restrictions configured
        assert provider.validate_model_name("invalid-model") is True

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_list_models(self):
        """Test listing available models."""
        provider = PortkeyProvider("test-key")
        models = provider.list_models()

        # Should include standard models
        assert "gpt-4" in models
        assert "claude-3-5-sonnet-20241022" in models
        assert "gemini-1.5-pro" in models
        assert "o1-preview" in models

        # Should be non-empty
        assert len(models) > 0

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_model_config_loading_with_env_vars(self):
        """Test loading model configs from environment variables."""
        with patch.dict(os.environ, {"PORTKEY_CONFIG_GPT4": "pc-gpt4-123", "PORTKEY_CONFIG_CLAUDE": "pc-claude-456"}):
            provider = PortkeyProvider("test-key")
            configs = provider._load_model_configs()

            assert configs["gpt4"] == "pc-gpt4-123"
            assert configs["claude"] == "pc-claude-456"

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_model_config_loading_empty(self):
        """Test loading model configs with no environment variables."""
        provider = PortkeyProvider("test-key")
        configs = provider._load_model_configs()
        assert configs == {}

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_get_config_for_model(self):
        """Test getting config for specific models."""
        with patch.dict(os.environ, {"PORTKEY_CONFIG_GPT": "pc-gpt-123", "PORTKEY_CONFIG_CLAUDE": "pc-claude-456"}):
            provider = PortkeyProvider("test-key")

            # Test exact matches
            assert provider._get_config_for_model("gpt-4") == "pc-gpt-123"

            # Test provider-based matching
            assert provider._get_config_for_model("gpt-3.5-turbo") == "pc-gpt-123"
            assert provider._get_config_for_model("claude-3-haiku") == "pc-claude-456"

            # Test no match
            assert provider._get_config_for_model("unknown-model") is None

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_get_provider_for_model(self):
        """Test getting provider name for models."""
        provider = PortkeyProvider("test-key")

        # Test OpenAI models
        assert provider._get_provider_for_model("gpt-4") == "openai"
        assert provider._get_provider_for_model("gpt-3.5-turbo") == "openai"

        # Test Anthropic models
        assert provider._get_provider_for_model("claude-3-5-sonnet") == "anthropic"
        assert provider._get_provider_for_model("claude-haiku") == "anthropic"

        # Test Google models
        assert provider._get_provider_for_model("gemini-1.5-pro") == "google"
        assert provider._get_provider_for_model("gemini-flash") == "google"

        # Test Meta models
        assert provider._get_provider_for_model("llama-3.1-405b") == "meta-llama"

        # Test Mistral models
        assert provider._get_provider_for_model("mistral-large") == "mistralai"

        # Test unknown model
        assert provider._get_provider_for_model("unknown-model") is None

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_registry_singleton(self):
        """Test that registry is shared across instances."""
        provider1 = PortkeyProvider("test-key-1")
        provider2 = PortkeyProvider("test-key-2")

        # Both should use the same registry instance
        assert provider1._registry is provider2._registry

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_model_capabilities(self):
        """Test model capabilities are properly configured."""
        provider = PortkeyProvider("test-key")

        # Test a few key models have capabilities
        gpt4_caps = provider.get_capabilities("gpt-4")
        assert gpt4_caps.context_window == 128000
        assert gpt4_caps.temperature_constraint is not None

        claude_caps = provider.get_capabilities("claude-3-5-sonnet-20241022")
        assert claude_caps.context_window == 200000

        o1_caps = provider.get_capabilities("o1-preview")
        assert o1_caps.context_window == 128000

    @patch.dict(os.environ, {"PORTKEY_API_KEY": "test-key"})
    def test_friendly_name(self):
        """Test provider friendly name."""
        provider = PortkeyProvider("test-key")
        assert provider.FRIENDLY_NAME == "Portkey"
