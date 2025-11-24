"""Helper functions for creating mock providers used in tests."""

from unittest.mock import Mock


def create_mock_provider(
    model_name: str = "gemini-2.5-flash",
    context_window: int = 1_000_000,
    provider_type: str = "google",
    base_url: str | None = None,
    organization: str | None = None,
    **kwargs,
):
    """
    Return a fully mocked ModelProvider that implements minimal
    abstract methods required by test suite.

    The mock provides:
    * ``generate_content`` – returns a ``Mock`` with ``content`` attribute.
    * ``generate_stream`` – returns a generator with mock response.
    * ``count_tokens`` – returns an integer token count.
    * ``list_models`` – returns a list of model names.
    * ``get_model_capabilities`` – returns a mock with typical capability
      attributes (``context_window``, ``supports_extended_thinking``,
      ``input_cost_per_1k``, ``output_cost_per_1k``).
    * ``get_provider_type`` – returns a ``Mock`` with a ``value`` attribute.
    * ``supports_thinking_mode`` – returns ``False`` by default.
    * ``api_key`` – attribute for API key.
    * ``use_responses_endpoint`` – attribute for responses endpoint flag.
    """
    # Basic mock provider
    provider = Mock(name="FakeModelProvider")

    # Add required attributes that tests expect
    provider.api_key = "test-key"
    provider.base_url = base_url or "https://api.example.com/v1"
    provider.organization = organization or "test-org"
    provider.use_responses_endpoint = False
    
    # Mock the internal client for providers that use it
    mock_client = Mock()
    
    # Mock chat completions response
    mock_response = Mock()
    mock_message = Mock()
    mock_message.content = "Mock response content"
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock responses endpoint (for o3-pro)
    mock_responses_response = Mock()
    mock_responses_response.output_text = "Mock response content"
    mock_responses_response.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    mock_client.responses.create.return_value = mock_responses_response
    
    provider._client = mock_client

    # Mock for ``generate_content``; tests set ``content`` on the returned mock.
    provider.generate_content.return_value = Mock(content="", usage={}, model_name=model_name, metadata={})

    # Mock for ``generate_stream`` – returns a generator
    def mock_generate_stream(*args, **kwargs):
        yield Mock(content="[STREAM_RESPONSE]", usage={}, model_name=model_name, metadata={})
    provider.generate_stream = mock_generate_stream

    # Token counting
    provider.count_tokens.return_value = 0

    # Model listings
    provider.list_models.return_value = [model_name]
    provider.get_all_model_aliases.return_value = {}
    provider.list_all_known_models.return_value = [model_name]
    provider.get_model_configurations.return_value = {
        model_name: Mock(
            context_window=context_window,
            supports_extended_thinking=False,
            input_cost_per_1k=0.075,
            output_cost_per_1k=0.3,
        )
    }

    # Provider type information
    provider.get_provider_type.return_value = Mock(value=provider_type)

    # Thinking mode support
    provider.supports_thinking_mode.return_value = False

    # Add missing abstract methods
    provider.get_capabilities.return_value = Mock(
        provider=Mock(value=provider_type),
        model_name=model_name,
        friendly_name=f"Mock {model_name}",
        context_window=context_window,
        max_output_tokens=8_192,
        supports_extended_thinking=False,
        supports_system_prompts=True,
        supports_streaming=True,
        supports_function_calling=True,
        supports_json_mode=True,
        supports_images=True,
        max_image_size_mb=20.0,
        supports_temperature=True,
        temperature_constraint=Mock(validate=lambda x: True, get_corrected_value=lambda x: x),
        description="Mock model for testing",
        aliases=["flash"],
    )

    provider.validate_model_name.return_value = True

    # Mock for get_preferred_model method that many tests expect
    provider.get_preferred_model.return_value = model_name

    return provider
