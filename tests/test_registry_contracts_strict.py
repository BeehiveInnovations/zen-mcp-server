"""
Focused contract tests for the provider registry that avoid brittle
dependencies on concrete provider implementations.
"""

from collections.abc import Iterator

import pytest

from providers.base import ModelCapabilities, ModelProvider, ModelResponse, ProviderType, RangeTemperatureConstraint
from providers.registry import ModelProviderRegistry

pytestmark = pytest.mark.no_mock_provider


class FakeProvider(ModelProvider):
    """Minimal concrete provider used to test registry behavior."""

    SUPPORTED_MODELS = {
        "base-model": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="base-model",
            friendly_name="Base Model",
            context_window=1024,
            max_output_tokens=256,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=False,
            supports_json_mode=False,
            supports_images=False,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            aliases=["alias-1", "alias-2"],
            description="Stub base model for registry tests",
        ),
        "slow-model": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="slow-model",
            friendly_name="Slow Model",
            context_window=1024,
            max_output_tokens=256,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=False,
            supports_function_calling=False,
            supports_json_mode=False,
            supports_images=False,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            aliases=["slow"],
            description="Stub slow model for restriction filtering",
        ),
    }

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        resolved = self._resolve_model_name(model_name)
        return self.SUPPORTED_MODELS[resolved]

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
        **kwargs,
    ) -> ModelResponse:
        resolved = self._resolve_model_name(model_name)
        return ModelResponse(content=prompt, model_name=resolved, provider=self.get_provider_type())

    def generate_stream(
        self,
        prompt: str,
        model_name: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int | None = None,
        **kwargs,
    ) -> Iterator[ModelResponse]:
        yield self.generate_content(prompt, model_name, system_prompt, temperature, max_output_tokens, **kwargs)

    def count_tokens(self, text: str, model_name: str) -> int:
        return len(text.split())

    def get_provider_type(self) -> ProviderType:
        return ProviderType.OPENAI

    def validate_model_name(self, model_name: str) -> bool:
        resolved = self._resolve_model_name(model_name)
        return resolved in self.SUPPORTED_MODELS

    def supports_thinking_mode(self, model_name: str) -> bool:
        resolved = self._resolve_model_name(model_name)
        return self.SUPPORTED_MODELS[resolved].supports_extended_thinking


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch):
    """Reset registry state between tests."""
    ModelProviderRegistry._instance = None
    # Ensure required API key is present for provider instantiation
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    yield
    ModelProviderRegistry._instance = None


def test_list_all_known_models_handles_aliases_and_targets():
    ModelProviderRegistry.register_provider(ProviderType.OPENAI, FakeProvider)
    provider = ModelProviderRegistry.get_provider(ProviderType.OPENAI)

    known = provider.list_all_known_models()

    # Should include bases and aliases without duplicates and with consistent casing
    assert set(known) == {"base-model", "alias-1", "alias-2", "slow-model", "slow"}


def test_registry_resolves_aliases_before_provider_lookup():
    ModelProviderRegistry.register_provider(ProviderType.OPENAI, FakeProvider)

    provider = ModelProviderRegistry.get_provider_for_model("alias-1")

    assert isinstance(provider, FakeProvider)
    # Alias should map to canonical base model for downstream calls
    assert provider.validate_model_name("alias-1")


def test_available_models_apply_restrictions_once_per_base(monkeypatch):
    ModelProviderRegistry.register_provider(ProviderType.OPENAI, FakeProvider)

    class StubRestriction:
        def is_allowed(self, provider_type: ProviderType, model_name: str, original_name: str | None = None) -> bool:
            # Block only slow-model and its aliases
            return model_name != "slow-model"

    monkeypatch.setenv("DEFAULT_MODEL", "base-model")
    monkeypatch.setattr("utils.model_restrictions.get_restriction_service", lambda: StubRestriction())

    provider = ModelProviderRegistry.get_provider(ProviderType.OPENAI)
    allowed_models = provider.list_models(respect_restrictions=True)

    # slow-model and its alias should be filtered out, base-model and aliases should remain
    assert set(allowed_models) == {"base-model", "alias-1", "alias-2"}
