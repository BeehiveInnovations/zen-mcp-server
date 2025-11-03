import sys
import types

import pytest

if "openai" not in sys.modules:  # pragma: no cover - test shim for optional dependency
    stub = types.ModuleType("openai")
    stub.AzureOpenAI = object  # Replaced with a mock inside tests
    sys.modules["openai"] = stub

from providers.azure_openai import AzureOpenAIProvider
from providers.shared import ModelCapabilities, ProviderType


class _DummyResponse:
    def __init__(self):
        self.choices = [
            types.SimpleNamespace(
                message=types.SimpleNamespace(content="hello"),
                finish_reason="stop",
            )
        ]
        self.model = "prod-gpt4o"
        self.id = "resp-123"
        self.created = 0
        self.usage = types.SimpleNamespace(
            prompt_tokens=5,
            completion_tokens=3,
            total_tokens=8,
        )


@pytest.fixture
def dummy_azure_client(monkeypatch):
    captured = {}

    class _DummyAzureClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create_completion))
            self.responses = types.SimpleNamespace(create=self._create_response)

        def _create_completion(self, **kwargs):
            captured["request_kwargs"] = kwargs
            return _DummyResponse()

        def _create_response(self, **kwargs):
            captured["responses_kwargs"] = kwargs
            return _DummyResponse()

    monkeypatch.delenv("AZURE_OPENAI_ALLOWED_MODELS", raising=False)
    monkeypatch.setattr("providers.azure_openai.AzureOpenAI", _DummyAzureClient)
    return captured


def test_generate_content_uses_deployment_mapping(dummy_azure_client):
    provider = AzureOpenAIProvider(
        api_key="key",
        azure_endpoint="https://example.openai.azure.com/",
        deployments={"gpt-4o": "prod-gpt4o"},
    )

    result = provider.generate_content("hello", "gpt-4o")

    assert dummy_azure_client["request_kwargs"]["model"] == "prod-gpt4o"
    assert result.model_name == "gpt-4o"
    assert result.provider == ProviderType.AZURE
    assert provider.validate_model_name("prod-gpt4o")


def test_generate_content_accepts_deployment_alias(dummy_azure_client):
    provider = AzureOpenAIProvider(
        api_key="key",
        azure_endpoint="https://example.openai.azure.com/",
        deployments={"gpt-4o-mini": "mini-deployment"},
    )

    # Calling with the deployment alias should still resolve properly.
    result = provider.generate_content("hi", "mini-deployment")

    assert dummy_azure_client["request_kwargs"]["model"] == "mini-deployment"
    assert result.model_name == "gpt-4o-mini"


def test_client_initialization_uses_endpoint_and_version(dummy_azure_client):
    provider = AzureOpenAIProvider(
        api_key="key",
        azure_endpoint="https://example.openai.azure.com/",
        api_version="2024-03-15-preview",
        deployments={"gpt-4o": "prod"},
    )

    _ = provider.client

    assert dummy_azure_client["client_kwargs"]["azure_endpoint"] == "https://example.openai.azure.com"
    assert dummy_azure_client["client_kwargs"]["api_version"] == "2024-03-15-preview"


def test_deployment_overrides_capabilities(dummy_azure_client):
    provider = AzureOpenAIProvider(
        api_key="key",
        azure_endpoint="https://example.openai.azure.com/",
        deployments={
            "gpt-4o": {
                "deployment": "prod-gpt4o",
                "friendly_name": "Azure GPT-4o EU",
                "intelligence_score": 19,
                "supports_temperature": False,
                "temperature_constraint": "fixed",
            }
        },
    )

    caps = provider.get_capabilities("gpt-4o")
    assert caps.friendly_name == "Azure GPT-4o EU"
    assert caps.intelligence_score == 19
    assert not caps.supports_temperature


def test_registry_configuration_merges_capabilities(dummy_azure_client, monkeypatch):
    def fake_registry_entries(self):
        capability = ModelCapabilities(
            provider=ProviderType.AZURE,
            model_name="gpt-4o",
            friendly_name="Azure GPT-4o Registry",
            context_window=500_000,
            max_output_tokens=128_000,
        )
        return {"gpt-4o": {"deployment": "registry-deployment", "capability": capability}}

    monkeypatch.setattr(AzureOpenAIProvider, "_load_registry_entries", fake_registry_entries)

    provider = AzureOpenAIProvider(
        api_key="key",
        azure_endpoint="https://example.openai.azure.com/",
    )

    # Capability should come from registry
    caps = provider.get_capabilities("gpt-4o")
    assert caps.friendly_name == "Azure GPT-4o Registry"
    assert caps.context_window == 500_000

    # API call should use deployment defined in registry
    provider.generate_content("hello", "gpt-4o")
    assert dummy_azure_client["request_kwargs"]["model"] == "registry-deployment"
