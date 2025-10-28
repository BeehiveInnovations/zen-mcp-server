"""GLM (Zhipu AI) model provider implementation using OpenAI-compatible API."""

import logging
from typing import TYPE_CHECKING, ClassVar, Optional

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from .openai_compatible import OpenAICompatibleProvider
from .shared import ModelCapabilities, ProviderType
from .shared.temperature import RangeTemperatureConstraint

class ZhipuModelProvider(OpenAICompatibleProvider):
    """Integration for GLM models exposed over OpenAI-compatible API.

    Publishes capability metadata for officially supported GLM models
    and maps tool-category preferences to appropriate GLM model.
    """

    FRIENDLY_NAME = "GLM"

    MODEL_CAPABILITIES: ClassVar[dict[str, ModelCapabilities]] = {
        "glm-4.5": ModelCapabilities(
            provider=ProviderType.ZHIPU,
            model_name="glm-4.5",
            friendly_name="GLM",
            context_window=128000,
            max_output_tokens=96000,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=False,
            supports_images=False,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(min_temp=0.0, max_temp=2.0),
            description="GLM-4.5: Advanced model with 128K context, optimized for tool use and software engineering",
            aliases=["glm45", "glm4"]
        ),
        "glm-4.6": ModelCapabilities(
            provider=ProviderType.ZHIPU,
            model_name="glm-4.6",
            friendly_name="GLM",
            context_window=200000,
            max_output_tokens=128000,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=False,
            supports_images=False,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(min_temp=0.0, max_temp=2.0),
            description="GLM-4.6: Latest GLM model with 200K context and enhanced reasoning capabilities",
            aliases=["glm46", "glm"]
        ),
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize GLM provider with API key."""
        # Set GLM base URL
        kwargs.setdefault("base_url", "https://api.z.ai/v1")
        super().__init__(api_key, **kwargs)
        self._invalidate_capability_cache()

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.ZHIPU

    def get_preferred_model(self, category: "ToolModelCategory", allowed_models: list[str]) -> Optional[str]:
        """Get GLM's preferred model for a given category from allowed models."""
        # For now, prefer GLM-4.6 as default for all categories
        preferred_models = ["glm-4.6", "glm-4.5"]
        for model in preferred_models:
            if model in allowed_models:
                return model

        # Fall back to first allowed model
        return allowed_models[0] if allowed_models else None

logger = logging.getLogger(__name__)
