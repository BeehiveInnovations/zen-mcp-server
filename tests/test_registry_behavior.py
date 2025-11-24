"""Tests for registry behavior including overwrite and append semantics."""

from typing import Optional
from unittest.mock import patch

import pytest

from providers.base import ModelCapabilities, ModelProvider, ModelResponse, ProviderType, RangeTemperatureConstraint
from providers.registry import ModelProviderRegistry

pytestmark = pytest.mark.no_mock_provider


class MockProvider(ModelProvider):
    def __init__(self, api_key=None, **kwargs):
        self.api_key = api_key
        self.config = kwargs

    def list_models(self, respect_restrictions=True):
        return ["mock-model"]

    def validate_model_name(self, model_name):
        return model_name == "mock-model"

    def count_tokens(self, text: str, model_name: str) -> int:
        return 0

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        return ModelResponse(content="mock response", model_name=model_name)

    def generate_stream(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ):
        yield self.generate_content(
            prompt=prompt,
            model_name=model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs,
        )

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        return ModelCapabilities(
            provider=ProviderType.CUSTOM,
            model_name=model_name,
            friendly_name="Mock Model",
            context_window=1000,
            max_output_tokens=100,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.5),
        )

    def get_provider_type(self):
        return ProviderType.CUSTOM

    def supports_thinking_mode(self, model_name):
        return False


class AnotherMockProvider(ModelProvider):
    def __init__(self, api_key=None, **kwargs):
        self.api_key = api_key
        self.config = kwargs

    def list_models(self, respect_restrictions=True):
        return ["another-mock-model"]

    def validate_model_name(self, model_name):
        return model_name == "another-mock-model"

    def count_tokens(self, text: str, model_name: str) -> int:
        return 0

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        return ModelResponse(content="another mock response", model_name=model_name)

    def generate_stream(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ):
        yield self.generate_content(
            prompt=prompt,
            model_name=model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs,
        )

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        return ModelCapabilities(
            provider=ProviderType.CUSTOM,
            model_name=model_name,
            friendly_name="Another Mock Model",
            context_window=1000,
            max_output_tokens=100,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.5),
        )

    def get_provider_type(self):
        return ProviderType.CUSTOM

    def supports_thinking_mode(self, model_name):
        return False


@pytest.fixture
def clean_registry():
    """Fixture to provide a clean registry and restore it afterwards."""
    # Snapshot existing providers
    original_providers = {}
    if ModelProviderRegistry._instance and hasattr(ModelProviderRegistry._instance, "_providers"):
        original_providers = ModelProviderRegistry._instance._providers.copy()

    # Reset
    ModelProviderRegistry.reset_for_testing()

    yield

    # Restore
    ModelProviderRegistry.reset_for_testing()
    instance = ModelProviderRegistry()
    instance._providers = original_providers


def test_register_provider_overwrite_default(clean_registry):
    """Test that register_provider overwrites by default (backward compatibility)."""
    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, MockProvider)

    registry = ModelProviderRegistry()
    assert len(registry._providers[ProviderType.CUSTOM]) == 1
    assert registry._providers[ProviderType.CUSTOM][0] == MockProvider

    # Registering again should overwrite
    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, AnotherMockProvider)
    assert len(registry._providers[ProviderType.CUSTOM]) == 1
    assert registry._providers[ProviderType.CUSTOM][0] == AnotherMockProvider


def test_register_provider_append(clean_registry):
    """Test that register_provider appends when requested."""
    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, MockProvider)

    # Append another provider
    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, AnotherMockProvider, append=True)

    registry = ModelProviderRegistry()
    assert len(registry._providers[ProviderType.CUSTOM]) == 2
    assert registry._providers[ProviderType.CUSTOM][0] == MockProvider
    assert registry._providers[ProviderType.CUSTOM][1] == AnotherMockProvider


@patch("providers.registry.ModelProviderRegistry._get_api_key_for_provider")
@patch.dict("os.environ", {"CUSTOM_API_URL": "http://mock-url"})
def test_get_provider_multi(mock_get_key, clean_registry):
    """Test retrieving multiple providers of the same type."""
    mock_get_key.return_value = "dummy-key"

    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, MockProvider)
    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, AnotherMockProvider, append=True)

    # Get first provider (default index=0)
    p1 = ModelProviderRegistry.get_provider(ProviderType.CUSTOM)
    assert isinstance(p1, MockProvider)

    # Get second provider
    p2 = ModelProviderRegistry.get_provider(ProviderType.CUSTOM, index=1)
    assert isinstance(p2, AnotherMockProvider)

    # Get invalid index
    p3 = ModelProviderRegistry.get_provider(ProviderType.CUSTOM, index=99)
    assert p3 is None


@patch("providers.registry.ModelProviderRegistry._get_api_key_for_provider")
@patch.dict("os.environ", {"CUSTOM_API_URL": "http://mock-url"})
def test_get_provider_for_model_routing(mock_get_key, clean_registry):
    """Test that get_provider_for_model checks all providers in the list."""
    mock_get_key.return_value = "dummy-key"

    # Register two providers for CUSTOM type
    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, MockProvider)
    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, AnotherMockProvider, append=True)

    # Should find model from first provider
    p1 = ModelProviderRegistry.get_provider_for_model("mock-model")
    assert isinstance(p1, MockProvider)

    # Should find model from second provider
    p2 = ModelProviderRegistry.get_provider_for_model("another-mock-model")
    assert isinstance(p2, AnotherMockProvider)

    # Should return None for unknown model
    p3 = ModelProviderRegistry.get_provider_for_model("unknown-model")
    assert p3 is None
