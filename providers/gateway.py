"""
Unified Gateway Provider for LangGraph Migration.

This provider acts as a single entry point for all LLM interactions, routing requests
to a local Bifrost or LiteLLM gateway. It removes the need for individual provider
SDKs and secrets within the MCP server.
"""

import logging
import os
from typing import Optional

from .base import (
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class GatewayProvider(OpenAICompatibleProvider):
    """
    Unified Gateway Provider.

    Routes all requests to a configured gateway (Bifrost/LiteLLM).
    Inherits from OpenAICompatibleProvider as most gateways speak the OpenAI protocol.
    """

    FRIENDLY_NAME = "Unified Gateway"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **kwargs):
        """
        Initialize the Gateway Provider.

        Args:
            api_key: Gateway API key (optional, defaults to UNIFIED_LLM_API_KEY)
            base_url: Gateway URL (optional, defaults to UNIFIED_LLM_GATEWAY)
            **kwargs: Additional configuration
        """
        # Load defaults from environment if not provided
        api_key = api_key or os.getenv("UNIFIED_LLM_API_KEY", "sk-dummy-key")
        base_url = base_url or os.getenv("UNIFIED_LLM_GATEWAY", "http://localhost:8080/v1")

        # Ensure base_url ends with /v1 if it's an OpenAI-compatible gateway
        if not base_url.endswith("/v1") and not base_url.endswith("/v1/"):
            base_url = f"{base_url.rstrip('/')}/v1"

        # Check if we should force responses endpoint (e.g. for future-proofing)
        # This can be set via env var UNIFIED_LLM_USE_RESPONSES_ENDPOINT=true
        use_responses = os.getenv("UNIFIED_LLM_USE_RESPONSES_ENDPOINT", "false").lower() == "true"
        kwargs["use_responses_endpoint"] = use_responses

        super().__init__(api_key, base_url=base_url, **kwargs)
        logger.info(f"Initialized GatewayProvider pointing to {base_url} (use_responses={use_responses})")

    def get_provider_type(self) -> ProviderType:
        """Return the provider type."""
        # We map this to OPENAI for now to leverage existing compatibility logic,
        # or we could introduce a new ProviderType.GATEWAY in the future.
        return ProviderType.OPENAI

    def validate_model_name(self, model_name: str) -> bool:
        """
        Validate if the model is supported.

        The Gateway handles routing, so we generally accept any model name
        and let the gateway reject it if invalid.
        """
        return True

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """
        Get capabilities for a model.

        Since the gateway abstracts the underlying model, we return generic
        capabilities unless we have specific overrides.
        """
        # TODO: Implement a way to query the gateway for model capabilities
        # For now, return safe defaults
        return ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name=model_name,
            friendly_name=f"Gateway Model ({model_name})",
            context_window=128000,  # Safe default for modern models
            max_output_tokens=4096,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            supports_images=True,  # Assume modern gateway supports vision
            supports_system_prompts=True,
        )

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        images: Optional[list[str]] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content via the gateway."""
        # The base OpenAICompatibleProvider handles the actual API call
        return super().generate_content(
            prompt=prompt,
            model_name=model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            images=images,
            **kwargs,
        )
