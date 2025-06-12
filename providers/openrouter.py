"""OpenRouter provider implementation."""

import logging
import os

from .base import (
    ModelCapabilities,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter unified API provider.
    
    OpenRouter provides access to multiple AI models through a single API endpoint.
    See https://openrouter.ai for available models and pricing.
    """
    
    FRIENDLY_NAME = "OpenRouter"
    
    # Custom headers required by OpenRouter
    DEFAULT_HEADERS = {
        "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://github.com/BeehiveInnovations/zen-mcp-server"),
        "X-Title": os.getenv("OPENROUTER_TITLE", "Zen MCP Server"),
    }
    
    def __init__(self, api_key: str, **kwargs):
        """Initialize OpenRouter provider.
        
        Args:
            api_key: OpenRouter API key
            **kwargs: Additional configuration
        """
        # Always use OpenRouter's base URL
        super().__init__(api_key, base_url="https://openrouter.ai/api/v1", **kwargs)
        
        # Log warning about model allow-list if not configured
        if not self.allowed_models:
            logging.warning(
                "OpenRouter provider initialized without model allow-list. "
                "Consider setting OPENROUTER_ALLOWED_MODELS environment variable "
                "to restrict model access and control costs."
            )
    
    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a model.
        
        Since OpenRouter supports many models dynamically, we return
        generic capabilities with conservative defaults.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Generic ModelCapabilities with warnings logged
        """
        logging.warning(
            f"Using generic capabilities for '{model_name}' via OpenRouter. "
            "Actual model capabilities may differ. Consider querying OpenRouter's "
            "/models endpoint for accurate information."
        )
        
        # Create generic capabilities with conservative defaults
        capabilities = ModelCapabilities(
            provider=ProviderType.OPENROUTER,
            model_name=model_name,
            friendly_name=self.FRIENDLY_NAME,
            max_tokens=32_768,  # Conservative default
            supports_extended_thinking=False,  # Most models don't support this
            supports_system_prompts=True,  # Most models support this
            supports_streaming=True,
            supports_function_calling=False,  # Varies by model
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 1.0),
        )
        
        # Mark as generic for validation purposes
        capabilities._is_generic = True
        
        return capabilities
    
    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.OPENROUTER
    
    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is allowed.
        
        For OpenRouter, we accept any model name unless an allow-list
        is configured via OPENROUTER_ALLOWED_MODELS environment variable.
        
        Args:
            model_name: Model name to validate
            
        Returns:
            True if model is allowed, False otherwise
        """
        if self.allowed_models:
            # Case-insensitive validation against allow-list
            return model_name.lower() in self.allowed_models
        
        # Accept any model if no allow-list configured
        # The API will return an error if the model doesn't exist
        return True
    
    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode.
        
        Currently, no models via OpenRouter support extended thinking.
        This may change as new models become available.
        
        Args:
            model_name: Model to check
            
        Returns:
            False (no OpenRouter models currently support thinking mode)
        """
        return False