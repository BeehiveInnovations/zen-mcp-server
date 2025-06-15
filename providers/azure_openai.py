"""Azure OpenAI model provider implementation."""

import logging
import os
from typing import Optional

from openai import AzureOpenAI

from .base import (
    FixedTemperatureConstraint,
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(OpenAICompatibleProvider):
    """Azure OpenAI API provider."""

    FRIENDLY_NAME = "Azure OpenAI"

    # Model configurations - Azure OpenAI supports the same models as OpenAI
    # but they are accessed via deployment names
    SUPPORTED_MODELS = {
        "o3": {
            "context_window": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
        "o3-mini": {
            "context_window": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
        "o3-pro": {
            "context_window": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
        "o4-mini": {
            "context_window": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
        "o4-mini-high": {
            "context_window": 200_000,  # 200K tokens
            "supports_extended_thinking": False,
        },
        "gpt-4o": {
            "context_window": 128_000,  # 128K tokens
            "supports_extended_thinking": False,
        },
        "gpt-4o-mini": {
            "context_window": 128_000,  # 128K tokens
            "supports_extended_thinking": False,
        },
        # Shorthands
        "mini": "o4-mini",  # Default 'mini' to latest mini model
        "o3mini": "o3-mini",
        "o4mini": "o4-mini",
        "o4minihigh": "o4-mini-high",
        "o4minihi": "o4-mini-high",
        "gpt4o": "gpt-4o",
        "gpt4omini": "gpt-4o-mini",
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize Azure OpenAI provider.

        Args:
            api_key: Azure OpenAI API key
            **kwargs: Additional configuration options
        """
        # Get Azure-specific configuration from environment
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

        # Validate Azure endpoint first
        if not azure_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")

        if not azure_endpoint.startswith("https://"):
            raise ValueError("Azure OpenAI endpoint must use HTTPS")

        # Store Azure-specific parameters
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version

        # Set base_url for parent class compatibility
        self.base_url = azure_endpoint

        # Call parent constructor with base_url set
        super().__init__(api_key, base_url=azure_endpoint, **kwargs)

        # Azure OpenAI uses different client initialization
        self._client = None

    @property
    def client(self) -> AzureOpenAI:
        """Get or create the Azure OpenAI client."""
        if self._client is None:
            self._client = AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version,
                timeout=self.timeout_config,
                organization=self.organization,
            )
        return self._client

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using Azure OpenAI model.

        Args:
            prompt: User prompt to send to the model
            model_name: Model name or deployment name to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature (0-2)
            max_output_tokens: Maximum tokens to generate
            **kwargs: Additional parameters including deployment_name

        Returns:
            ModelResponse with generated content and metadata
        """
        try:
            # Resolve shorthand to actual model name
            resolved_name = self._resolve_model_name(model_name)

            # For Azure OpenAI, we need deployment name, not model name
            # Priority: kwargs > env var > resolved model name
            deployment_name = (
                kwargs.get("deployment_name") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or resolved_name
            )

            # Validate model before proceeding
            if not self.validate_model_name(model_name):
                raise ValueError(f"Unsupported or restricted Azure OpenAI model: {model_name}")

            # Validate parameters
            self.validate_parameters(model_name, temperature, **kwargs)

            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Prepare request parameters
            request_params = {
                "model": deployment_name,  # Use deployment name for Azure
                "messages": messages,
                "temperature": temperature,
            }

            # Add optional parameters
            if max_output_tokens:
                request_params["max_tokens"] = max_output_tokens

            # Filter out our custom parameters
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k not in ["deployment_name"] and not k.startswith("_")
            }
            request_params.update(filtered_kwargs)

            logger.debug(f"Azure OpenAI request - deployment: {deployment_name}, temp: {temperature}")

            # Make the API call
            response = self.client.chat.completions.create(**request_params)

            # Extract response data
            content = response.choices[0].message.content or ""

            # Calculate usage
            usage = {}
            if response.usage:
                usage = {
                    "input_tokens": response.usage.prompt_tokens or 0,
                    "output_tokens": response.usage.completion_tokens or 0,
                    "total_tokens": response.usage.total_tokens or 0,
                }

            return ModelResponse(
                content=content,
                usage=usage,
                model_name=deployment_name,
                friendly_name=self.FRIENDLY_NAME,
                provider=ProviderType.AZURE_OPENAI,
                metadata={
                    "response_id": response.id,
                    "azure_endpoint": self.azure_endpoint,
                    "api_version": self.api_version,
                    "deployment_name": deployment_name,
                    "original_model_name": model_name,
                },
            )

        except Exception as e:
            logger.error(f"Azure OpenAI API error for model {model_name}: {str(e)}")
            raise

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text using the specified model's tokenizer.

        Note: Azure OpenAI doesn't provide a direct token counting API.
        This uses a rough approximation based on character count.
        For more accurate counting, consider using tiktoken library.
        """
        # Rough approximation: 1 token ≈ 4 characters for most models
        return len(text) // 4

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Azure OpenAI model."""
        # Resolve shorthand
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS or isinstance(self.SUPPORTED_MODELS[resolved_name], str):
            raise ValueError(f"Unsupported Azure OpenAI model: {model_name}")

        # Check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.AZURE_OPENAI, resolved_name, model_name):
            raise ValueError(f"Azure OpenAI model '{model_name}' is not allowed by restriction policy.")

        config = self.SUPPORTED_MODELS[resolved_name]

        # Define temperature constraints per model
        if resolved_name in ["o3", "o3-mini", "o3-pro", "o4-mini", "o4-mini-high"]:
            # O3 and O4 reasoning models only support temperature=1.0
            temp_constraint = FixedTemperatureConstraint(1.0)
        else:
            # Other models support 0.0-2.0 range
            temp_constraint = RangeTemperatureConstraint(0.0, 2.0, 0.7)

        return ModelCapabilities(
            provider=ProviderType.AZURE_OPENAI,
            model_name=model_name,
            friendly_name=self.FRIENDLY_NAME,
            context_window=config["context_window"],
            supports_extended_thinking=config["supports_extended_thinking"],
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            temperature_constraint=temp_constraint,
        )

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.AZURE_OPENAI

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported and allowed."""
        resolved_name = self._resolve_model_name(model_name)

        # First check if model is supported
        if resolved_name not in self.SUPPORTED_MODELS or not isinstance(self.SUPPORTED_MODELS[resolved_name], dict):
            return False

        # Then check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.AZURE_OPENAI, resolved_name, model_name):
            logger.debug(f"Azure OpenAI model '{model_name}' -> '{resolved_name}' blocked by restrictions")
            return False

        return True

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        # Currently no Azure OpenAI models support extended thinking
        return False

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model shorthand to full name."""
        # Check if it's a shorthand
        shorthand_value = self.SUPPORTED_MODELS.get(model_name)
        if isinstance(shorthand_value, str):
            return shorthand_value
        return model_name

    def _is_localhost_url(self) -> bool:
        """Azure OpenAI endpoints are always external, never localhost."""
        return False

    def _validate_base_url(self):
        """Validate Azure OpenAI endpoint URL."""
        if not self.azure_endpoint.startswith("https://"):
            raise ValueError("Azure OpenAI endpoint must use HTTPS")

        if not self.azure_endpoint.endswith(".openai.azure.com/") and not self.azure_endpoint.endswith(
            ".openai.azure.com"
        ):
            logger.warning(f"Azure OpenAI endpoint doesn't follow expected format: {self.azure_endpoint}")
