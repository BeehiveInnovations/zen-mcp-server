"""Requesty AI provider implementation."""

import logging
from typing import Optional

from .base import (
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class RequestyProvider(OpenAICompatibleProvider):
    """Requesty AI unified API provider.

    Requesty provides access to multiple AI models through a single API endpoint
    with smart routing and fallback capabilities.
    See https://requesty.ai for available models and pricing.
    """

    FRIENDLY_NAME = "Requesty"

    # Define supported models based on Requesty's documentation
    # Model names follow the format: provider/model-name
    SUPPORTED_MODELS = {
        # Coding models
        "coding/claude-4-sonnet": {
            "context_window": 200_000,
            "supports_extended_thinking": True,
        },
        # Anthropic models
        "anthropic/claude-3-5-haiku-latest": {
            "context_window": 200_000,
            "supports_extended_thinking": False,
        },
        "anthropic/claude-opus-4-20250514": {
            "context_window": 200_000,
            "supports_extended_thinking": True,
        },
        # OpenAI models
        "openai/o3": {
            "context_window": 200_000,
            "supports_extended_thinking": True,
        },
        "openai/o3-mini": {
            "context_window": 200_000,
            "supports_extended_thinking": True,
        },
        # Perplexity models
        "perplexity/sonar": {
            "context_window": 131_072,
            "supports_extended_thinking": True,
        },
        # Mistral models
        "mistral/devstral-small-latest": {
            "context_window": 131_072,
            "supports_extended_thinking": False,
        },
        "mistral/mistral-large-latest": {
            "context_window": 131_072,
            "supports_extended_thinking": False,
        },
        # Google models
        "google/gemini-2.5-pro-preview-06-05": {
            "context_window": 1_048_576,
            "supports_extended_thinking": True,
        },
        "google/gemini-2.5-flash-preview-05-20": {
            "context_window": 1_048_576,
            "supports_extended_thinking": True,
        },
        # Shorthands/aliases for convenience
        "claude-4-sonnet": "coding/claude-4-sonnet",
        "claude-haiku": "anthropic/claude-3-5-haiku-latest",
        "claude-opus-4": "anthropic/claude-opus-4-20250514",
        "o3": "openai/o3",
        "o3-mini": "openai/o3-mini",
        "sonar": "perplexity/sonar",
        "devstral": "mistral/devstral-small-latest",
        "mistral-large": "mistral/mistral-large-latest",
        "gemini-pro": "google/gemini-2.5-pro-preview-06-05",
        "gemini-flash": "google/gemini-2.5-flash-preview-05-20",
        "flash": "google/gemini-2.5-flash-preview-05-20",
        "pro": "google/gemini-2.5-pro-preview-06-05",
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize Requesty provider with API key.

        Args:
            api_key: Requesty API key
            **kwargs: Additional configuration
        """
        # Set the Requesty API base URL
        kwargs.setdefault("base_url", "https://router.requesty.ai/v1")
        super().__init__(api_key, **kwargs)
        logger.info("Initialized Requesty provider")

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific model.

        Args:
            model_name: Name of the model (or alias)

        Returns:
            ModelCapabilities object

        Raises:
            ValueError: If model is not supported
        """
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")

        # Check restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.REQUESTY, resolved_name, model_name):
            raise ValueError(f"Model '{model_name}' is not allowed by restriction policy.")

        config = self.SUPPORTED_MODELS[resolved_name]

        return ModelCapabilities(
            provider=ProviderType.REQUESTY,
            model_name=resolved_name,
            friendly_name=self.FRIENDLY_NAME,
            context_window=config["context_window"],
            supports_extended_thinking=config["supports_extended_thinking"],
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 1.0, 0.7),
        )

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.REQUESTY

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported."""
        resolved_name = self._resolve_model_name(model_name)

        # Check if it's in our known models
        if resolved_name not in self.SUPPORTED_MODELS or not isinstance(self.SUPPORTED_MODELS[resolved_name], dict):
            return False

        # Check restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.REQUESTY, resolved_name, model_name):
            return False

        return True

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model shorthand to full name."""
        shorthand_value = self.SUPPORTED_MODELS.get(model_name)
        if isinstance(shorthand_value, str):
            return shorthand_value
        return model_name

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using API with proper model name resolution."""
        # CRITICAL: Resolve model alias before making API call
        # This ensures aliases like "large" get sent as "example-model-large" to the API
        resolved_model_name = self._resolve_model_name(model_name)

        # Call parent implementation with resolved model name
        return super().generate_content(
            prompt=prompt,
            model_name=resolved_model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs,
        )

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode.

        Args:
            model_name: Model name or alias

        Returns:
            True if model supports extended thinking
        """
        # Resolve alias to full model name
        resolved_name = self._resolve_model_name(model_name)

        # Check if it's a known model with capabilities
        if resolved_name in self.SUPPORTED_MODELS and isinstance(self.SUPPORTED_MODELS[resolved_name], dict):
            return self.SUPPORTED_MODELS[resolved_name].get("supports_extended_thinking", False)

        # Unknown models default to False
        return False


    def list_models(self, respect_restrictions: bool = True) -> list[str]:
        """Return a list of model names supported by this provider.

        Args:
            respect_restrictions: Whether to apply provider-specific restriction logic.

        Returns:
            List of model names available from this provider
        """
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service() if respect_restrictions else None
        models = []

        for model_name, config in self.SUPPORTED_MODELS.items():
            # Handle both base models (dict configs) and aliases (string values)
            if isinstance(config, str):
                # This is an alias - check if the target model would be allowed
                target_model = config
                if restriction_service and not restriction_service.is_allowed(
                    self.get_provider_type(), target_model, model_name
                ):
                    continue
                # Allow the alias
                models.append(model_name)
            else:
                # This is a base model with config dict
                # Check restrictions if enabled
                if restriction_service and not restriction_service.is_allowed(
                    self.get_provider_type(), model_name, model_name
                ):
                    continue
                models.append(model_name)

        return models

    def list_all_known_models(self) -> list[str]:
        """Return all model names known by this provider, including alias targets.

        Returns:
            List of all model names and alias targets known by this provider
        """
        all_models = set()

        for model_name, config in self.SUPPORTED_MODELS.items():
            # Add the model name itself
            all_models.add(model_name.lower())

            # If it's an alias (string value), add the target model too
            if isinstance(config, str):
                all_models.add(config.lower())

        return list(all_models)

    # Note: count_tokens is inherited from OpenAICompatibleProvider
