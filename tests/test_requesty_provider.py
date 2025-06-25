"""Tests for Requesty provider implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from providers.base import ProviderType, RangeTemperatureConstraint
from providers.registry import ModelProviderRegistry
from providers.requesty import RequestyProvider


class TestRequestyProvider:
    """Test Requesty provider functionality."""

    @patch.dict(os.environ, {"REQUESTY_API_KEY": "test-key"})
    def test_initialization(self):
        """Test provider initialization with correct base URL."""
        provider = RequestyProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.get_provider_type() == ProviderType.REQUESTY
        # Check that base URL is set correctly
        assert provider.client.base_url.host == "router.requesty.ai"

    def test_model_validation(self):
        """Test model name validation for known and unknown models."""
        provider = RequestyProvider("test-key")

        # Test valid known models
        assert provider.validate_model_name("claude-4-sonnet") is True
        assert provider.validate_model_name("coding/claude-4-sonnet") is True
        assert provider.validate_model_name("o3") is True
        assert provider.validate_model_name("openai/o3") is True

    def test_resolve_model_name(self):
        """Test model name resolution for aliases."""
        provider = RequestyProvider("test-key")

        # Test shorthand resolution
        assert provider._resolve_model_name("claude-4-sonnet") == "coding/claude-4-sonnet"
        assert provider._resolve_model_name("o3") == "openai/o3"
        assert provider._resolve_model_name("claude-haiku") == "anthropic/claude-3-5-haiku-latest"
        assert provider._resolve_model_name("gemini-pro") == "google/gemini-2.5-pro-preview-06-05"
        assert provider._resolve_model_name("mistral-large") == "mistral/mistral-large-latest"

        # Test full name passthrough
        assert provider._resolve_model_name("openai/o3") == "openai/o3"
        assert provider._resolve_model_name("coding/claude-4-sonnet") == "coding/claude-4-sonnet"

        # Test unknown models passthrough
        assert provider._resolve_model_name("unknown-model") == "unknown-model"

    def test_get_capabilities(self):
        """Test getting capabilities."""
        provider = RequestyProvider("test-key")

        # Test Claude 4 Sonnet model
        capabilities = provider.get_capabilities("claude-4-sonnet")
        assert capabilities.model_name == "coding/claude-4-sonnet"
        assert capabilities.friendly_name == "Requesty"
        assert capabilities.context_window == 200_000
        assert capabilities.provider == ProviderType.REQUESTY
        assert capabilities.supports_function_calling is True
        assert capabilities.supports_extended_thinking is True

        # Test O3 model
        capabilities = provider.get_capabilities("o3")
        assert capabilities.model_name == "openai/o3"
        assert capabilities.context_window == 200_000
        assert capabilities.supports_extended_thinking is True

        # Test temperature constraint
        assert isinstance(capabilities.temperature_constraint, RangeTemperatureConstraint)
        assert capabilities.temperature_constraint.min_temp == 0.0
        assert capabilities.temperature_constraint.max_temp == 1.0
        assert capabilities.temperature_constraint.default_temp == 0.7

    def test_list_models(self):
        """Test list_models method returns all supported models."""
        provider = RequestyProvider("test-key")

        # Test with restrictions disabled (get all models)
        all_models = provider.list_models(respect_restrictions=False)

        # Should include both base models and aliases
        expected_base_models = [
            "coding/claude-4-sonnet",
            "anthropic/claude-3-5-haiku-latest",
            "anthropic/claude-opus-4-20250514",
            "openai/o3",
            "openai/o3-mini",
            "perplexity/sonar",
            "mistral/devstral-small-latest",
            "mistral/mistral-large-latest",
            "google/gemini-2.5-pro-preview-06-05",
            "google/gemini-2.5-flash-preview-05-20",
        ]

        expected_aliases = [
            "claude-4-sonnet",
            "claude-haiku",
            "claude-opus-4",
            "o3",
            "o3-mini",
            "sonar",
            "devstral",
            "mistral-large",
            "gemini-pro",
            "gemini-flash",
            "flash",
            "pro",
        ]

        # Check all base models are present
        for model in expected_base_models:
            assert model in all_models, f"Base model {model} should be in list"

        # Check all aliases are present
        for alias in expected_aliases:
            assert alias in all_models, f"Alias {alias} should be in list"

        # Verify total count
        assert len(all_models) == len(expected_base_models) + len(expected_aliases)

    @patch("utils.model_restrictions.get_restriction_service")
    def test_list_models_with_restrictions(self, mock_get_restriction_service):
        """Test list_models respects restrictions when enabled."""
        provider = RequestyProvider("test-key")

        # Set up mock restriction service
        mock_restriction_service = MagicMock()
        mock_get_restriction_service.return_value = mock_restriction_service

        # Configure allowed models - only allow claude models
        def is_allowed_side_effect(provider_type, resolved_name, original_name):
            # Allow only claude-related models
            allowed_models = [
                "coding/claude-4-sonnet",
                "anthropic/claude-3-5-haiku-latest",
                "anthropic/claude-opus-4-20250514",
            ]
            allowed_aliases = ["claude-4-sonnet", "claude-haiku", "claude-opus-4"]
            return resolved_name in allowed_models or original_name in allowed_aliases

        mock_restriction_service.is_allowed.side_effect = is_allowed_side_effect

        # Test with restrictions enabled
        restricted_models = provider.list_models(respect_restrictions=True)

        # Should only include allowed models
        expected_allowed = [
            "coding/claude-4-sonnet",
            "anthropic/claude-3-5-haiku-latest",
            "anthropic/claude-opus-4-20250514",
            "claude-4-sonnet",
            "claude-haiku",
            "claude-opus-4",
        ]

        # Verify only allowed models are present
        assert len(restricted_models) == len(expected_allowed)
        for model in restricted_models:
            assert model in expected_allowed, f"Model {model} should be allowed"

        # Verify non-allowed models are excluded
        excluded_models = ["o3", "openai/o3", "gemini-pro", "sonar"]
        for model in excluded_models:
            assert model not in restricted_models, f"Model {model} should be excluded"

    def test_list_all_known_models(self):
        """Test list_all_known_models returns all models including alias targets."""
        provider = RequestyProvider("test-key")

        all_known = provider.list_all_known_models()

        # Should include all model names in lowercase
        expected_models = [
            # Base models
            "coding/claude-4-sonnet",
            "anthropic/claude-3-5-haiku-latest",
            "anthropic/claude-opus-4-20250514",
            "openai/o3",
            "openai/o3-mini",
            "perplexity/sonar",
            "mistral/devstral-small-latest",
            "mistral/mistral-large-latest",
            "google/gemini-2.5-pro-preview-06-05",
            "google/gemini-2.5-flash-preview-05-20",
            # Aliases
            "claude-4-sonnet",
            "claude-haiku",
            "claude-opus-4",
            "o3",
            "o3-mini",
            "sonar",
            "devstral",
            "mistral-large",
            "gemini-pro",
            "gemini-flash",
            "flash",
            "pro",
        ]

        # All models should be in lowercase
        for model in expected_models:
            assert model.lower() in all_known, f"Model {model.lower()} should be in all_known_models"

        # Check no duplicates
        assert len(all_known) == len(set(all_known)), "Should have no duplicate models"


class TestRequestyAutoMode:
    """Test auto mode functionality when only Requesty is configured."""

    def setup_method(self):
        """Store original state before each test."""
        self.registry = ModelProviderRegistry()
        self._original_providers = self.registry._providers.copy()
        self._original_initialized = self.registry._initialized_providers.copy()

        self.registry._providers.clear()
        self.registry._initialized_providers.clear()

        self._original_env = {}
        for key in ["REQUESTY_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "DEFAULT_MODEL"]:
            self._original_env[key] = os.environ.get(key)

    def teardown_method(self):
        """Restore original state after each test."""
        self.registry._providers.clear()
        self.registry._initialized_providers.clear()
        self.registry._providers.update(self._original_providers)
        self.registry._initialized_providers.update(self._original_initialized)

        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    @pytest.mark.no_mock_provider
    def test_requesty_only_auto_mode(self):
        """Test that auto mode works when only Requesty is configured."""
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ["REQUESTY_API_KEY"] = "test-requesty-key"
        os.environ["DEFAULT_MODEL"] = "auto"

        ModelProviderRegistry.register_provider(ProviderType.REQUESTY, RequestyProvider)

        provider = ModelProviderRegistry.get_provider(ProviderType.REQUESTY)
        assert provider is not None, "Requesty provider should be available with API key"

        available_models = ModelProviderRegistry.get_available_models(respect_restrictions=True)

        assert len(available_models) > 0, "Should find Requesty models in auto mode"
        assert all(provider_type == ProviderType.REQUESTY for provider_type in available_models.values())

        # Check that Requesty-specific models are available
        expected_models = [
            "coding/claude-4-sonnet",
            "anthropic/claude-3-5-haiku-latest",
            "perplexity/sonar",
            "mistral/devstral-small-latest",
        ]
        for model in expected_models:
            assert model in available_models, f"Model {model} should be available"

    @patch("utils.model_restrictions.get_restriction_service")
    def test_requesty_with_restrictions(self, mock_get_restriction_service):
        """Test that Requesty respects model restrictions."""
        # Set up mock restriction service
        mock_restriction_service = MagicMock()
        mock_get_restriction_service.return_value = mock_restriction_service

        # Configure allowed models
        def is_allowed_side_effect(provider_type, resolved_name, original_name):
            # Allow claude-4-sonnet and sonar, reject others
            allowed_resolved = ["coding/claude-4-sonnet", "perplexity/sonar"]
            allowed_aliases = ["claude-4-sonnet", "sonar"]
            return resolved_name in allowed_resolved or original_name in allowed_aliases

        mock_restriction_service.is_allowed.side_effect = is_allowed_side_effect

        provider = RequestyProvider("test-key")

        # Test that allowed models work (get capabilities without error)
        caps = provider.get_capabilities("claude-4-sonnet")
        assert caps is not None
        assert caps.model_name == "coding/claude-4-sonnet"

        caps = provider.get_capabilities("sonar")
        assert caps is not None
        assert caps.model_name == "perplexity/sonar"

        # Test that non-allowed models raise an error
        mock_restriction_service.is_allowed.return_value = False

        with pytest.raises(ValueError, match="not allowed by restriction policy"):
            provider.get_capabilities("devstral")

        with pytest.raises(ValueError, match="not allowed by restriction policy"):
            provider.get_capabilities("mistral-large")


class TestRequestyProviderPriority:
    """Test provider priority when multiple providers are available."""

    def setup_method(self):
        """Store original state before each test."""
        self._original_env = {}
        for key in ["REQUESTY_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"]:
            self._original_env[key] = os.environ.get(key)

    def teardown_method(self):
        """Restore original state after each test."""
        for key, value in self._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    @pytest.mark.no_mock_provider
    def test_native_provider_priority_over_requesty(self):
        """Test that native providers take priority over Requesty for shared models."""
        # Clean up existing providers through instance
        registry = ModelProviderRegistry()
        registry._providers.clear()
        registry._initialized_providers.clear()

        # Set up environment with both OpenAI and Requesty
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-openai-key",
                "REQUESTY_API_KEY": "test-requesty-key",
                "GEMINI_API_KEY": "",
                "XAI_API_KEY": "",
            },
        ):
            # Register providers
            from providers.openai_provider import OpenAIModelProvider

            ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)
            ModelProviderRegistry.register_provider(ProviderType.REQUESTY, RequestyProvider)

            # Check that O3 model is handled by OpenAI, not Requesty
            provider = ModelProviderRegistry.get_provider_for_model("o3")
            assert provider is not None
            assert provider.get_provider_type() == ProviderType.OPENAI

            # Check that Requesty-specific models are handled by Requesty
            provider = ModelProviderRegistry.get_provider_for_model("claude-4-sonnet")
            assert provider is not None
            assert provider.get_provider_type() == ProviderType.REQUESTY
