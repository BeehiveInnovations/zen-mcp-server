"""Comprehensive FakeModelProvider for testing - fully ABC compliant test double."""

from typing import Optional

from providers.base import ModelCapabilities, ModelProvider, ModelResponse, ProviderType, create_temperature_constraint


class FakeModelProvider(ModelProvider):
    """Fully compliant test double implementing all ModelProvider abstract methods."""

    # Model configurations using ModelCapabilities objects
    SUPPORTED_MODELS = {
        "fake-model": ModelCapabilities(
            provider=ProviderType.GOOGLE,
            model_name="fake-model",
            friendly_name="Fake Model",
            context_window=1000,
            max_output_tokens=500,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="Fake model for testing purposes",
            aliases=["fake", "test"],
        ),
    }

    def __init__(self, api_key: str = "fake-key", **kwargs):
        """Initialize fake provider with dummy API key."""
        super().__init__(api_key, **kwargs)

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific fake model."""
        resolved_name = self._resolve_model_name(model_name)
        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported fake model: {model_name}")
        return self.SUPPORTED_MODELS[resolved_name]

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        thinking_mode: str = "medium",
        images: Optional[list[str]] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using fake model."""
        resolved_name = self._resolve_model_name(model_name)
        capabilities = self.get_capabilities(resolved_name)

        # Simple mock response
        content = f"[FAKE_RESPONSE] {prompt[:50]}..."

        return ModelResponse(
            content=content,
            usage={
                "input_tokens": len(prompt) // 4,
                "output_tokens": len(content) // 4,
                "total_tokens": (len(prompt) + len(content)) // 4,
            },
            model_name=resolved_name,
            friendly_name=capabilities.friendly_name,
            provider=ProviderType.GOOGLE,
            metadata={"finish_reason": "stop", "is_mock": True},
        )

    def generate_stream(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ):
        """Generate content using fake model in streaming mode."""
        resolved_name = self._resolve_model_name(model_name)
        capabilities = self.get_capabilities(resolved_name)

        # Yield a single mock response for testing purposes
        yield ModelResponse(
            content="[FAKE_STREAM_RESPONSE]",
            usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            model_name=resolved_name,
            friendly_name=capabilities.friendly_name,
            provider=ProviderType.GOOGLE,
            metadata={"finish_reason": "stop", "is_mock": True},
        )

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for given text using fake tokenizer."""
        self._resolve_model_name(model_name)
        # Simple estimation: ~4 characters per token
        return len(text) // 4

    def get_provider_type(self) -> ProviderType:
        """Get provider type."""
        return ProviderType.GOOGLE

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if model name is supported."""
        resolved_name = self._resolve_model_name(model_name)
        return resolved_name in self.SUPPORTED_MODELS

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if model supports extended thinking mode."""
        capabilities = self.get_capabilities(model_name)
        return capabilities.supports_extended_thinking

    def get_thinking_budget(self, model_name: str, thinking_mode: str) -> int:
        """Get thinking token budget for a model and thinking mode."""
        # Fake models don't support thinking
        return 0
