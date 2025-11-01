"""Z.AI provider implementation for GLM models."""

import logging

from utils.env import get_env

from .openai_compatible import OpenAICompatibleProvider
from .shared import ModelCapabilities, ProviderType


class ZAIProvider(OpenAICompatibleProvider):
    """Provider for Z.AI's GLM models.

    Z.AI provides access to GLM-4.6 and other models through an OpenAI-compatible
    API endpoint. This provider handles the specific endpoint configuration and
    model capabilities for Z.AI's services.

    Key differences from standard OpenAI:
        * Uses custom endpoint: /api/paas/v4/chat/completions
        * Supports GLM models with multimodal capabilities
        * Requires Bearer token authentication
    """

    FRIENDLY_NAME = "Z.AI"

    def __init__(self, api_key: str = "", **kwargs):
        """Initialize Z.AI provider.

        Args:
            api_key: Z.AI API key (get from https://z.ai/manage-apikey/apikey-list).
                    Falls back to ZAI_API_KEY environment variable if not provided.
            **kwargs: Additional configuration passed to parent provider
        """
        # Fall back to environment variable if not provided
        if not api_key:
            api_key = get_env("ZAI_API_KEY", "") or ""

        if not api_key:
            raise ValueError(
                "Z.AI API key must be provided via api_key parameter or ZAI_API_KEY environment variable"
            )

        # Z.AI uses a specific endpoint path for coding applications
        base_url = "https://api.z.ai/api/coding/paas/v4"

        logging.info(f"Initializing Z.AI provider with endpoint: {base_url}")

        super().__init__(api_key, base_url=base_url, **kwargs)

    def get_provider_type(self) -> ProviderType:
        """Identify this provider as Z.AI."""
        return ProviderType.ZAI

    def _lookup_capabilities(
        self,
        canonical_name: str,
        requested_name: str | None = None,
    ) -> ModelCapabilities | None:
        """Return capabilities for Z.AI models."""
        logging.debug(f"Z.AI _lookup_capabilities called with canonical_name='{canonical_name}', requested_name='{requested_name}'")

        # Define GLM-4.6 capabilities - check case-insensitively
        normalized_name = canonical_name.lower()
        if normalized_name in ["glm-4.6", "glm-4", "glm4.6", "glm"]:
            logging.debug(f"Z.AI matched model '{canonical_name}' -> glm-4.6")
            return ModelCapabilities(
                model_name="glm-4.6",
                aliases=["glm4.6", "glm-4", "glm"],
                context_window=128000,
                max_output_tokens=8000,
                supports_extended_thinking=True,
                supports_json_mode=True,
                supports_function_calling=True,
                supports_images=True,
                max_image_size_mb=10.0,
                supports_temperature=True,
                description="GLM-4.6 model via Z.AI API - 128K context window with multimodal support",
                intelligence_score=85,
                provider=ProviderType.ZAI,
                friendly_name="GLM-4.6 (Z.AI)",
            )

        logging.debug(f"Z.AI provider cannot resolve model '{canonical_name}' (normalized: '{normalized_name}')")
        return None

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model aliases to canonical names."""
        # Map common aliases to canonical model name
        alias_map = {
            "glm": "glm-4.6",
            "glm-4": "glm-4.6",
            "glm4.6": "glm-4.6",
        }

        normalized = model_name.lower()
        resolved = alias_map.get(normalized, model_name)

        if resolved != model_name:
            logging.debug(f"Resolved Z.AI model alias '{model_name}' to '{resolved}'")

        return resolved

    def get_all_model_capabilities(self) -> dict[str, ModelCapabilities]:
        """Return all available Z.AI model capabilities."""
        glm46 = self._lookup_capabilities("glm-4.6")
        if glm46:
            return {
                "glm-4.6": glm46,
                "glm4.6": glm46,
                "glm-4": glm46,
                "glm": glm46,
            }
        return {}
