"""Tests for OpenRouter provider."""

import os
from unittest.mock import patch

from providers.base import ProviderType
from providers.openrouter import OpenRouterProvider
from providers.registry import ModelProviderRegistry


class TestOpenRouterProvider:
    """Test cases for OpenRouter provider."""

    def test_provider_initialization(self):
        """Test OpenRouter provider initialization."""
        provider = OpenRouterProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://openrouter.ai/api/v1"
        assert provider.FRIENDLY_NAME == "OpenRouter"

    def test_custom_headers(self):
        """Test OpenRouter custom headers."""
        # Test default headers
        assert "HTTP-Referer" in OpenRouterProvider.DEFAULT_HEADERS
        assert "X-Title" in OpenRouterProvider.DEFAULT_HEADERS

        # Test with environment variables
        with patch.dict(os.environ, {"OPENROUTER_REFERER": "https://myapp.com", "OPENROUTER_TITLE": "My App"}):
            from importlib import reload

            import providers.openrouter

            reload(providers.openrouter)

            provider = providers.openrouter.OpenRouterProvider(api_key="test-key")
            assert provider.DEFAULT_HEADERS["HTTP-Referer"] == "https://myapp.com"
            assert provider.DEFAULT_HEADERS["X-Title"] == "My App"

    def test_model_validation(self):
        """Test model validation."""
        provider = OpenRouterProvider(api_key="test-key")

        # Should accept any model - OpenRouter handles validation
        assert provider.validate_model_name("gpt-4") is True
        assert provider.validate_model_name("claude-3-opus") is True
        assert provider.validate_model_name("any-model-name") is True
        assert provider.validate_model_name("GPT-4") is True
        assert provider.validate_model_name("unknown-model") is True

    def test_get_capabilities(self):
        """Test capability generation."""
        provider = OpenRouterProvider(api_key="test-key")

        # Test with a model in the registry (using alias)
        caps = provider.get_capabilities("gpt4o")
        assert caps.provider == ProviderType.OPENROUTER
        assert caps.model_name == "openai/gpt-4o"  # Resolved name
        assert caps.friendly_name == "OpenRouter"

        # Test with a model not in registry - should get generic capabilities
        caps = provider.get_capabilities("unknown-model")
        assert caps.provider == ProviderType.OPENROUTER
        assert caps.model_name == "unknown-model"
        assert caps.context_window == 32_768  # Safe default
        assert hasattr(caps, "_is_generic") and caps._is_generic is True

    def test_model_alias_resolution(self):
        """Test model alias resolution."""
        provider = OpenRouterProvider(api_key="test-key")

        # Test alias resolution
        assert provider._resolve_model_name("opus") == "anthropic/claude-3-opus"
        assert provider._resolve_model_name("sonnet") == "anthropic/claude-3-sonnet"
        assert provider._resolve_model_name("gpt4o") == "openai/gpt-4o"
        assert provider._resolve_model_name("4o") == "openai/gpt-4o"
        assert provider._resolve_model_name("claude") == "anthropic/claude-3-sonnet"
        assert provider._resolve_model_name("mistral") == "mistral/mistral-large"
        assert provider._resolve_model_name("deepseek") == "deepseek/deepseek-coder"
        assert provider._resolve_model_name("coder") == "deepseek/deepseek-coder"

        # Test case-insensitive
        assert provider._resolve_model_name("OPUS") == "anthropic/claude-3-opus"
        assert provider._resolve_model_name("GPT4O") == "openai/gpt-4o"
        assert provider._resolve_model_name("Mistral") == "mistral/mistral-large"
        assert provider._resolve_model_name("CLAUDE") == "anthropic/claude-3-sonnet"

        # Test direct model names (should pass through unchanged)
        assert provider._resolve_model_name("anthropic/claude-3-opus") == "anthropic/claude-3-opus"
        assert provider._resolve_model_name("openai/gpt-4o") == "openai/gpt-4o"

        # Test unknown models pass through
        assert provider._resolve_model_name("unknown-model") == "unknown-model"
        assert provider._resolve_model_name("custom/model-v2") == "custom/model-v2"

    def test_openrouter_registration(self):
        """Test OpenRouter can be registered and retrieved."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            # Clean up any existing registration
            ModelProviderRegistry.unregister_provider(ProviderType.OPENROUTER)

            # Register the provider
            ModelProviderRegistry.register_provider(ProviderType.OPENROUTER, OpenRouterProvider)

            # Retrieve and verify
            provider = ModelProviderRegistry.get_provider(ProviderType.OPENROUTER)
            assert provider is not None
            assert isinstance(provider, OpenRouterProvider)


class TestOpenRouterRegistry:
    """Test cases for OpenRouter model registry."""

    def test_registry_loading(self):
        """Test registry loads models from config."""
        from providers.openrouter_registry import OpenRouterModelRegistry

        registry = OpenRouterModelRegistry()

        # Should have loaded models
        models = registry.list_models()
        assert len(models) > 0
        assert "anthropic/claude-3-opus" in models
        assert "openai/gpt-4o" in models

        # Should have loaded aliases
        aliases = registry.list_aliases()
        assert len(aliases) > 0
        assert "opus" in aliases
        assert "gpt4o" in aliases
        assert "claude" in aliases

    def test_registry_capabilities(self):
        """Test registry provides correct capabilities."""
        from providers.openrouter_registry import OpenRouterModelRegistry

        registry = OpenRouterModelRegistry()

        # Test known model
        caps = registry.get_capabilities("opus")
        assert caps is not None
        assert caps.model_name == "anthropic/claude-3-opus"
        assert caps.context_window == 200000  # Claude's context window

        # Test using full model name
        caps = registry.get_capabilities("anthropic/claude-3-opus")
        assert caps is not None
        assert caps.model_name == "anthropic/claude-3-opus"

        # Test unknown model
        caps = registry.get_capabilities("non-existent-model")
        assert caps is None

    def test_multiple_aliases_same_model(self):
        """Test multiple aliases pointing to same model."""
        from providers.openrouter_registry import OpenRouterModelRegistry

        registry = OpenRouterModelRegistry()

        # All these should resolve to Claude Sonnet
        sonnet_aliases = ["sonnet", "claude", "claude-sonnet", "claude3-sonnet"]
        for alias in sonnet_aliases:
            config = registry.resolve(alias)
            assert config is not None
            assert config.model_name == "anthropic/claude-3-sonnet"


class TestOpenRouterFunctionality:
    """Test OpenRouter-specific functionality."""

    def test_openrouter_always_uses_correct_url(self):
        """Test that OpenRouter always uses the correct base URL."""
        provider = OpenRouterProvider(api_key="test-key")
        assert provider.base_url == "https://openrouter.ai/api/v1"

        # Even if we try to change it, it should remain the OpenRouter URL
        # (This is a characteristic of the OpenRouter provider)
        provider.base_url = "http://example.com"  # Try to change it
        # But new instances should always use the correct URL
        provider2 = OpenRouterProvider(api_key="test-key")
        assert provider2.base_url == "https://openrouter.ai/api/v1"

    def test_openrouter_headers_set_correctly(self):
        """Test that OpenRouter specific headers are set."""
        provider = OpenRouterProvider(api_key="test-key")

        # Check default headers
        assert "HTTP-Referer" in provider.DEFAULT_HEADERS
        assert "X-Title" in provider.DEFAULT_HEADERS
        assert provider.DEFAULT_HEADERS["X-Title"] == "Zen MCP Server"

    def test_openrouter_model_registry_initialized(self):
        """Test that model registry is properly initialized."""
        provider = OpenRouterProvider(api_key="test-key")

        # Registry should be initialized
        assert hasattr(provider, "_registry")
        assert provider._registry is not None
