import pytest

from providers.gemini import GeminiModelProvider
from providers.registry import ModelProviderRegistry, ProviderType
from server import configure_providers


@pytest.fixture
def mock_gemini_client(monkeypatch):
    """Mocks the genai.Client and captures its initialization arguments."""
    captured_kwargs = {}

    class MockGenAIClient:
        def __init__(self, **kwargs):
            captured_kwargs["client"] = kwargs

    monkeypatch.setattr("providers.gemini.genai.Client", MockGenAIClient)
    return captured_kwargs


def test_initialization_with_api_key(mock_gemini_client):
    """Tests that the provider initializes the client with the API key."""
    provider = GeminiModelProvider(api_key="test-api-key")
    _ = provider.client  # Trigger client creation
    assert "client" in mock_gemini_client
    assert mock_gemini_client["client"].get("api_key") == "test-api-key"


def test_initialization_with_adc(mock_gemini_client):
    """Tests that the provider initializes the client without an API key for ADC."""
    provider = GeminiModelProvider(api_key=None)
    _ = provider.client  # Trigger client creation
    assert "client" in mock_gemini_client
    assert "api_key" not in mock_gemini_client["client"]


def test_configure_providers_registers_gemini_with_adc(monkeypatch):
    """Tests that configure_providers registers Gemini when no key is present (for ADC)."""

    # Reset the registry to a known state
    ModelProviderRegistry.reset_for_testing()

    # Mock get_env to simulate no Gemini API key
    def mock_get_env(key):
        if key == "GEMINI_API_KEY":
            return None
        # Return a dummy key for other providers to prevent them from being registered
        if key == "OPENAI_API_KEY":
            return "dummy_key"
        return None

    monkeypatch.setattr("server.get_env", mock_get_env)

    # Mock _has_google_adc to return True (simulating available ADC)
    monkeypatch.setattr(ModelProviderRegistry, "_has_google_adc", lambda: True)

    # Spy on register_provider
    registered_with = []
    original_register = ModelProviderRegistry.register_provider

    def spy_register_provider(provider_type, provider_class):
        registered_with.append(provider_type)
        original_register(provider_type, provider_class)

    monkeypatch.setattr(ModelProviderRegistry, "register_provider", spy_register_provider)

    # Run the configuration
    configure_providers()

    # Assert that Google provider was registered
    assert ProviderType.GOOGLE in registered_with
