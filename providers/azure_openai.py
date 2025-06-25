"""Azure OpenAI model provider implementation."""

import logging
import os
from typing import Optional

from openai import AzureOpenAI

from .base import (
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    create_temperature_constraint,
)
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class AzureOpenAIModelProvider(OpenAICompatibleProvider):
    """Azure OpenAI API provider."""

    FRIENDLY_NAME = "Azure OpenAI"

    # Model configurations using ModelCapabilities objects
    # Only supporting O3 and O4-mini as requested
    SUPPORTED_MODELS = {
        "o3": ModelCapabilities(
            provider=ProviderType.AZURE_OPENAI,
            model_name="o3",
            friendly_name="Azure OpenAI (O3)",
            context_window=200_000,  # 200K tokens
            max_output_tokens=65536,  # 64K max output tokens
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # O3 models support vision
            max_image_size_mb=20.0,  # 20MB per OpenAI docs
            supports_temperature=False,  # O3 models don't accept temperature parameter
            temperature_constraint=create_temperature_constraint("fixed"),
            description="Strong reasoning via Azure (200K context) - Logical problems, code generation, systematic analysis",
            aliases=[],
        ),
        "o4-mini": ModelCapabilities(
            provider=ProviderType.AZURE_OPENAI,
            model_name="o4-mini",
            friendly_name="Azure OpenAI (O4-mini)",
            context_window=200_000,  # 200K tokens
            max_output_tokens=65536,  # 64K max output tokens
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # O4 models support vision
            max_image_size_mb=20.0,  # 20MB per OpenAI docs
            supports_temperature=False,  # O4 models don't accept temperature parameter
            temperature_constraint=create_temperature_constraint("fixed"),
            description="Latest reasoning model via Azure (200K context) - Optimized for shorter contexts, rapid reasoning",
            aliases=["mini", "o4mini"],
        ),
    }

    def __init__(self, resource_name: str = None, endpoint: str = None, api_key: str = None, api_version: str = "2025-01-01-preview", **kwargs):
        """Initialize Azure OpenAI provider with resource name or endpoint and API key.
        
        Args:
            resource_name: Azure OpenAI resource name (e.g., "mycompany-openai")
            endpoint: Full Azure endpoint URL (alternative to resource_name)
            api_key: Azure OpenAI API key
            api_version: Azure OpenAI API version (default: "2025-01-01-preview")
            **kwargs: Additional configuration options
        """
        # Determine Azure endpoint
        if endpoint:
            # Use provided endpoint directly
            azure_endpoint = endpoint.rstrip('/')  # Remove trailing slash if present
            # Extract resource name from endpoint if possible
            import re
            match = re.match(r'https://([^.]+)\.openai\.azure\.com', azure_endpoint)
            self.resource_name = match.group(1) if match else "azure-openai"
        elif resource_name:
            # Construct Azure endpoint from resource name
            azure_endpoint = f"https://{resource_name}.openai.azure.com"
            self.resource_name = resource_name
        else:
            raise ValueError("Either resource_name or endpoint must be provided")
        
        # Store Azure-specific configuration
        self.api_version = api_version
        self._azure_client = None
        
        # Initialize parent with constructed endpoint
        # Note: We pass the endpoint as base_url for compatibility
        super().__init__(api_key, base_url=azure_endpoint, **kwargs)
        
        logger.info(f"Initialized Azure OpenAI provider with endpoint: {azure_endpoint}")

    @property
    def client(self):
        """Override client property to use AzureOpenAI client."""
        if self._azure_client is None:
            # Use the Azure-specific OpenAI client
            self._azure_client = AzureOpenAI(
                azure_endpoint=self.base_url,
                api_key=self.api_key,
                api_version=self.api_version,
            )
            logger.debug(f"Created AzureOpenAI client with endpoint: {self.base_url}")
        return self._azure_client

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Azure OpenAI model."""
        # Resolve shorthand
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported Azure OpenAI model: {model_name}")

        # Check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.AZURE_OPENAI, resolved_name, model_name):
            raise ValueError(f"Azure OpenAI model '{model_name}' is not allowed by restriction policy.")

        # Return the ModelCapabilities object directly from SUPPORTED_MODELS
        return self.SUPPORTED_MODELS[resolved_name]

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.AZURE_OPENAI

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported and allowed."""
        resolved_name = self._resolve_model_name(model_name)

        # First check if model is supported
        if resolved_name not in self.SUPPORTED_MODELS:
            return False

        # Then check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.AZURE_OPENAI, resolved_name, model_name):
            logger.debug(f"Azure OpenAI model '{model_name}' -> '{resolved_name}' blocked by restrictions")
            return False

        return True

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using Azure OpenAI API with proper model name resolution.
        
        Note: Azure OpenAI uses deployment names, not model names. The model_name
        parameter here represents the deployment name in your Azure resource.
        """
        # Resolve model alias before making API call
        resolved_model_name = self._resolve_model_name(model_name)

        # For Azure, the deployment name might be different from the model name
        # Users can configure custom deployment names via environment variables
        deployment_name = os.getenv(f"AZURE_OPENAI_{resolved_model_name.upper().replace('-', '_')}_DEPLOYMENT", resolved_model_name)

        # Call parent implementation with deployment name
        return super().generate_content(
            prompt=prompt,
            model_name=deployment_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs,
        )

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        # Currently no Azure OpenAI models support extended thinking
        return False

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model name aliases to canonical model names.
        
        Args:
            model_name: Input model name or alias
            
        Returns:
            Canonical model name
        """
        # Convert to lowercase for case-insensitive comparison
        lower_name = model_name.lower()
        
        # Check each supported model's aliases
        for canonical_name, capabilities in self.SUPPORTED_MODELS.items():
            if lower_name == canonical_name.lower() or lower_name in [alias.lower() for alias in capabilities.aliases]:
                return canonical_name
                
        # If no alias match, return original name (will fail in validation)
        return model_name

    def list_models(self, respect_restrictions: bool = True) -> list[str]:
        """List available Azure OpenAI models.
        
        Args:
            respect_restrictions: Whether to filter by model restrictions
            
        Returns:
            List of available model names
        """
        models = []
        
        if respect_restrictions:
            from utils.model_restrictions import get_restriction_service
            restriction_service = get_restriction_service()
            
            for model_name in self.SUPPORTED_MODELS:
                if restriction_service.is_allowed(ProviderType.AZURE_OPENAI, model_name):
                    models.append(model_name)
        else:
            models = list(self.SUPPORTED_MODELS.keys())
            
        return models