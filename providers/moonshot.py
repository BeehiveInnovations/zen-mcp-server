"""Moonshot AI provider for Kimi models."""

import logging

from .base import ModelCapabilities, ProviderType, RangeTemperatureConstraint
from .openai_provider import OpenAIModelProvider

logger = logging.getLogger(__name__)


class MoonshotProvider(OpenAIModelProvider):
    """Moonshot AI provider for Kimi models.

    Uses OpenAI-compatible API with Moonshot's endpoint.
    """

    FRIENDLY_NAME = "Moonshot"

    SUPPORTED_MODELS = {
        "kimi-latest": ModelCapabilities(
            provider=ProviderType.MOONSHOT,
            model_name="kimi-latest",
            friendly_name="Moonshot (Kimi Latest)",
            context_window=200000,
            max_output_tokens=8192,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="Kimi latest model with advanced reasoning capabilities",
            aliases=["kimi-latest", "moonshot-latest"],
            supports_json_mode=True,
        ),
        "kimi-thinking-preview": ModelCapabilities(
            provider=ProviderType.MOONSHOT,
            model_name="kimi-thinking-preview",
            friendly_name="Moonshot (Kimi Thinking)",
            context_window=200000,
            max_output_tokens=8192,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.3),
            description="Kimi thinking preview model with extended reasoning",
            aliases=["kimi-thinking", "moonshot-thinking"],
            supports_json_mode=True,
            max_thinking_tokens=32768,
        ),
    }

    def __init__(self, api_key: str, base_url: str = None, **kwargs):
        """Initialize the Moonshot provider.

        Args:
            api_key: Moonshot API key for authentication
            base_url: Optional custom base URL. Defaults to Moonshot's official endpoint
            **kwargs: Additional arguments passed to the parent OpenAI provider
        """
        # Use Moonshot's official API endpoint
        if base_url is None:
            base_url = "https://api.moonshot.ai/v1"
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)

    def get_provider_type(self) -> ProviderType:
        """Return the provider type identifier.

        Returns:
            ProviderType.MOONSHOT constant
        """
        return ProviderType.MOONSHOT

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Moonshot model.

        Args:
            model_name: Name or alias of the Moonshot model

        Returns:
            ModelCapabilities object with model specifications including context window,
            thinking support, temperature constraints, and feature availability

        Raises:
            ValueError: If the model is not supported by this provider
        """
        # Resolve model name (handle aliases)
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name in self.SUPPORTED_MODELS:
            return self.SUPPORTED_MODELS[resolved_name]

        raise ValueError(f"Unsupported Moonshot model: {model_name}")

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported and allowed.

        Checks both model support and any configured usage restrictions.
        Resolves model aliases before validation.

        Args:
            model_name: Name or alias of the Moonshot model to validate

        Returns:
            True if the model is supported and allowed by restrictions, False otherwise
        """
        resolved_name = self._resolve_model_name(model_name)

        # First check if model is supported
        if resolved_name not in self.SUPPORTED_MODELS:
            return False

        # Then check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.MOONSHOT, resolved_name, model_name):
            logger.debug(f"Moonshot model '{model_name}' -> '{resolved_name}' blocked by restrictions")
            return False

        return True

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode.

        Extended thinking mode allows models to perform step-by-step reasoning
        before generating the final response.

        Args:
            model_name: Name or alias of the Moonshot model to check

        Returns:
            True if the model supports extended thinking, False otherwise
        """
        try:
            capabilities = self.get_capabilities(model_name)
            return capabilities.supports_extended_thinking
        except ValueError:
            return False
