"""Azure OpenAI model provider implementation using Responses API.

IMPORTANT: This implementation uses Azure OpenAI's **Responses API** exclusively,
which works with both **GPT-5** and **GPT-5-Codex** models, as well as O3 reasoning
models and GPT-4.1. The Responses API is required for GPT-5-Codex and provides
consistent behavior across all Azure OpenAI models.

This provider supports Azure OpenAI deployments using the Responses API format,
which is required for advanced models like gpt-5, gpt-5-codex, gpt-5-mini,
gpt-5-nano, o3-mini, and gpt-4.1.
"""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from openai import AzureOpenAI

from .base import ModelProvider
from .shared import ModelCapabilities, ModelResponse, ProviderType, TemperatureConstraint

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(ModelProvider):
    """Azure OpenAI provider using Responses API.

    IMPORTANT: This implementation uses Azure OpenAI's **Responses API** exclusively,
    which works with both **GPT-5** and **GPT-5-Codex** models, as well as all variants
    (gpt-5-mini, gpt-5-nano), O3 reasoning models (o3-mini), and GPT-4.1. The Responses
    API is required for GPT-5-Codex and provides consistent behavior across all Azure
    OpenAI models.

    This provider connects to Azure OpenAI deployments and uses the Responses API
    (client.responses.create) instead of the Chat Completions API. This is required
    for certain advanced models like gpt-5-codex and provides extended reasoning
    capabilities for gpt-5, gpt-5-mini, and o3-mini.

    Supported Models:
        - gpt-5: Advanced reasoning model (400K context, 128K output)
        - gpt-5-codex: Elite code generation (400K context, 128K output)
        - gpt-5-mini: Faster, cost-effective variant (400K context, 128K output)
        - gpt-5-nano: Fastest, most cost-effective (400K context, 128K output)
        - o3-mini: Strong reasoning model (200K context, 64K output)
        - gpt-4.1: Extended context window (1M context, 32K output)

    Configuration:
        - api_key: Azure OpenAI API key
        - azure_endpoint: Azure OpenAI endpoint URL
        - api_version: API version (must be 2025-03-01-preview or later)
        - deployment_name: The deployment name to use (e.g., "gpt-5", "gpt-5-codex")
    """

    # Model configurations using ModelCapabilities objects
    MODEL_CAPABILITIES = {
        "gpt-5": ModelCapabilities(
            provider=ProviderType.AZURE,
            model_name="gpt-5",
            friendly_name="Azure OpenAI (GPT-5)",
            intelligence_score=16,
            context_window=400_000,  # 400K tokens
            max_output_tokens=128_000,  # 128K max output tokens
            supports_extended_thinking=True,  # Supports reasoning tokens
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # GPT-5 supports vision
            max_image_size_mb=20.0,  # 20MB per OpenAI docs
            supports_temperature=False,  # Reasoning model: temperature not supported (fixed internally to 1.0)
            temperature_constraint=TemperatureConstraint.create("fixed"),
            description="Azure GPT-5 (400K context, 128K output) - Advanced reasoning model with extended thinking",
            aliases=["gpt5", "azure-gpt5", "azure-gpt-5"],
        ),
        "gpt-5-codex": ModelCapabilities(
            provider=ProviderType.AZURE,
            model_name="gpt-5-codex",
            friendly_name="Azure OpenAI (GPT-5 Codex)",
            intelligence_score=17,
            context_window=400_000,  # 400K tokens
            max_output_tokens=128_000,  # 128K max output tokens
            supports_extended_thinking=True,  # Codex supports advanced reasoning
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=False,  # Codex is code-focused
            max_image_size_mb=0.0,
            supports_temperature=False,  # Requires fixed temperature=1.0
            temperature_constraint=TemperatureConstraint.create("fixed"),
            description="Azure GPT-5 Codex (400K context, 128K output) - Elite code generation with deep reasoning (temperature=1.0 required)",
            aliases=["gpt5-codex", "gpt5codex", "codex", "azure-codex", "azure-gpt5-codex"],
        ),
        "gpt-5-mini": ModelCapabilities(
            provider=ProviderType.AZURE,
            model_name="gpt-5-mini",
            friendly_name="Azure OpenAI (GPT-5 Mini)",
            intelligence_score=14,
            context_window=400_000,  # 400K tokens
            max_output_tokens=128_000,  # 128K max output tokens
            supports_extended_thinking=True,  # Supports reasoning tokens
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # GPT-5 variants support vision
            max_image_size_mb=20.0,  # 20MB per OpenAI docs
            supports_temperature=False,  # Reasoning model: temperature not supported (fixed internally to 1.0)
            temperature_constraint=TemperatureConstraint.create("fixed"),
            description="Azure GPT-5-Mini - Faster, cost-effective variant",
            aliases=["gpt5-mini", "gpt5mini", "mini", "azure-mini"],
        ),
        "gpt-5-nano": ModelCapabilities(
            provider=ProviderType.AZURE,
            model_name="gpt-5-nano",
            friendly_name="Azure OpenAI (GPT-5 Nano)",
            intelligence_score=12,
            context_window=400_000,  # 400K tokens
            max_output_tokens=128_000,  # 128K max output tokens
            supports_extended_thinking=False,  # Nano does not support extended thinking
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # GPT-5 variants support vision
            max_image_size_mb=20.0,  # 20MB per OpenAI docs
            supports_temperature=False,  # Reasoning model: temperature not supported (fixed internally to 1.0)
            temperature_constraint=TemperatureConstraint.create("fixed"),
            description="Azure GPT-5-Nano - Fastest, most cost-effective",
            aliases=["gpt5-nano", "gpt5nano", "nano", "azure-nano"],
        ),
        "o3-mini": ModelCapabilities(
            provider=ProviderType.AZURE,
            model_name="o3-mini",
            friendly_name="Azure OpenAI (O3 Mini)",
            intelligence_score=15,
            context_window=200_000,  # 200K tokens
            max_output_tokens=64_000,  # 64K max output tokens
            supports_extended_thinking=True,  # O3 supports advanced reasoning
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=False,  # O3 is reasoning-focused, not vision
            max_image_size_mb=0.0,
            supports_temperature=False,  # Reasoning model requires fixed temperature=1.0
            temperature_constraint=TemperatureConstraint.create("fixed"),
            description="Azure O3-Mini - Strong reasoning model (temperature=1.0 required)",
            aliases=["o3mini", "azure-o3-mini"],
        ),
        "gpt-4.1": ModelCapabilities(
            provider=ProviderType.AZURE,
            model_name="gpt-4.1",
            friendly_name="Azure OpenAI (GPT-4.1)",
            intelligence_score=14,
            context_window=1_000_000,  # 1M tokens
            max_output_tokens=32_000,  # 32K max output tokens
            supports_extended_thinking=False,  # GPT-4.1 does not support extended thinking
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # GPT-4.1 supports vision
            max_image_size_mb=20.0,  # 20MB per OpenAI docs
            supports_temperature=True,
            temperature_constraint=TemperatureConstraint.create("range"),
            description="Azure GPT-4.1 - Extended context window",
            aliases=["gpt4.1", "azure-gpt4.1"],
        ),
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize Azure OpenAI provider.

        Args:
            api_key: Azure OpenAI API key
            **kwargs: Additional configuration including:
                - azure_endpoint: Azure OpenAI endpoint URL (required)
                - api_version: API version (required, must be 2025-03-01-preview or later)
                - deployment_name: Deployment name (required)

        Raises:
            ValueError: If required configuration is missing
        """
        super().__init__(api_key, **kwargs)

        # Validate required kwargs
        self.azure_endpoint = kwargs.get("azure_endpoint")
        self.api_version = kwargs.get("api_version")
        self.deployment_name = kwargs.get("deployment_name")

        if not self.azure_endpoint:
            raise ValueError("azure_endpoint is required for Azure OpenAI provider")
        if not self.api_version:
            raise ValueError("api_version is required for Azure OpenAI provider")
        if not self.deployment_name:
            raise ValueError("deployment_name is required for Azure OpenAI provider")

        # Validate API version supports Responses API
        if self.api_version < "2025-03-01-preview":
            logger.warning(
                f"API version {self.api_version} may not support Responses API. "
                "Recommended: 2025-03-01-preview or later"
            )

        # Lazy client initialization
        self._client: Optional[AzureOpenAI] = None

        logger.info(
            f"Initialized Azure OpenAI provider: endpoint={self.azure_endpoint}, "
            f"deployment={self.deployment_name}, api_version={self.api_version}"
        )

    def _get_client(self) -> AzureOpenAI:
        """Get or create the Azure OpenAI client (lazy initialization)."""
        if self._client is None:
            self._client = AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version,
            )
            logger.debug("Created Azure OpenAI client")
        return self._client

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.AZURE

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using Azure OpenAI Responses API.

        Args:
            prompt: User prompt/message
            model_name: Model name (will be resolved to deployment)
            system_prompt: Optional system prompt
            temperature: Temperature parameter (default 0.3)
            max_output_tokens: Maximum output tokens
            **kwargs: Additional parameters

        Returns:
            ModelResponse with generated content and usage data

        Raises:
            ValueError: If model is not supported
            Exception: If API call fails
        """
        # Resolve model name and get capabilities
        resolved_model = self._resolve_model_name(model_name)
        capabilities = self.get_capabilities(resolved_model)

        # Validate parameters
        # For reasoning models (no temperature support), skip temperature validation
        effective_temperature = temperature
        try:
            if not capabilities.supports_temperature:
                effective_temperature = None
            else:
                # Coerce into allowed range if needed
                effective_temperature = capabilities.temperature_constraint.get_corrected_value(temperature)
                self.validate_parameters(resolved_model, effective_temperature, **kwargs)
        except Exception:
            # If validation fails unexpectedly, fall back to omitting temperature
            effective_temperature = None

        # Build input messages in Responses API format
        input_messages = []
        if system_prompt:
            input_messages.append({"role": "system", "content": system_prompt})
        input_messages.append({"role": "user", "content": prompt})

        # Prepare API parameters
        api_params = {
            "model": self.deployment_name,
            "input": input_messages,
        }

        # Add max_output_tokens if specified
        if max_output_tokens:
            api_params["max_output_tokens"] = max_output_tokens
        elif capabilities.max_output_tokens:
            api_params["max_output_tokens"] = capabilities.max_output_tokens

        # Add temperature only when supported
        if capabilities.supports_temperature and effective_temperature is not None:
            api_params["temperature"] = effective_temperature

        logger.debug(
            f"Azure OpenAI Responses API request: deployment={self.deployment_name}, "
            f"model={resolved_model}, max_tokens={api_params.get('max_output_tokens')}"
        )

        try:
            # Get client and make API call
            client = self._get_client()
            response = client.responses.create(**api_params)

            # Extract content from response
            content = self._extract_content(response)

            # Extract usage data
            usage = self._extract_usage(response)

            # Build ModelResponse
            model_response = ModelResponse(
                content=content,
                usage=usage,
                model_name=resolved_model,
                friendly_name=capabilities.friendly_name,
                provider=ProviderType.AZURE,
                metadata={
                    "response_id": response.id if hasattr(response, "id") else None,
                    "status": response.status if hasattr(response, "status") else None,
                    "deployment_name": self.deployment_name,
                },
            )

            logger.debug(
                f"Azure OpenAI response: tokens={usage.get('total_tokens', 0)}, "
                f"status={response.status if hasattr(response, 'status') else 'N/A'}"
            )

            return model_response

        except Exception as exc:
            logger.error(f"Azure OpenAI API error: {exc}", exc_info=True)
            raise

    def _extract_content(self, response) -> str:
        """Extract text content from Responses API response.

        The Responses API returns content in different formats:
        1. output_text: Condensed text representation (preferred)
        2. output array: Array of output items (text, reasoning, etc.)

        Args:
            response: API response object

        Returns:
            Extracted text content

        Raises:
            ValueError: If no content can be extracted
        """
        # Try output_text first (condensed representation)
        if hasattr(response, "output_text") and response.output_text:
            logger.debug("Extracted content from output_text")
            return response.output_text

        # Parse output array for text items
        if hasattr(response, "output") and response.output:
            text_parts = []

            for item in response.output:
                item_type = getattr(item, "type", None)

                if item_type == "text" or item_type == "message":
                    # Text output item
                    if hasattr(item, "content") and item.content:
                        if isinstance(item.content, list) and len(item.content) > 0:
                            # Content is a list of text parts
                            text_parts.append(item.content[0].text)
                        elif isinstance(item.content, str):
                            # Content is a string
                            text_parts.append(item.content)
                    elif hasattr(item, "text"):
                        # Direct text attribute
                        text_parts.append(item.text)

                elif item_type == "reasoning":
                    # Reasoning output (optional: include summary)
                    if hasattr(item, "summary") and item.summary:
                        logger.debug(f"Reasoning summary: {item.summary}")
                        # Optionally include reasoning in output
                        # text_parts.append(f"[Reasoning: {item.summary}]")

            if text_parts:
                content = "\n".join(text_parts)
                logger.debug(f"Extracted content from output array ({len(text_parts)} parts)")
                return content

        # No content found
        logger.warning("No content found in response")
        raise ValueError("No content available in response")

    def _extract_usage(self, response) -> dict[str, int]:
        """Extract token usage from Responses API response.

        Args:
            response: API response object

        Returns:
            Dictionary with token usage (input_tokens, output_tokens, total_tokens)
        """
        usage = {}

        if hasattr(response, "usage") and response.usage:
            usage_obj = response.usage

            # Extract input tokens
            if hasattr(usage_obj, "input_tokens"):
                usage["input_tokens"] = usage_obj.input_tokens
                usage["prompt_tokens"] = usage_obj.input_tokens
            elif hasattr(usage_obj, "prompt_tokens"):
                usage["prompt_tokens"] = usage_obj.prompt_tokens
                usage["input_tokens"] = usage_obj.prompt_tokens

            # Extract output tokens
            if hasattr(usage_obj, "output_tokens"):
                usage["output_tokens"] = usage_obj.output_tokens
                usage["completion_tokens"] = usage_obj.output_tokens
            elif hasattr(usage_obj, "completion_tokens"):
                usage["completion_tokens"] = usage_obj.completion_tokens
                usage["output_tokens"] = usage_obj.completion_tokens

            # Extract total tokens
            if hasattr(usage_obj, "total_tokens"):
                usage["total_tokens"] = usage_obj.total_tokens
            else:
                # Calculate total if not provided
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                usage["total_tokens"] = input_tokens + output_tokens

            logger.debug(f"Token usage: {usage}")

        return usage

    def close(self) -> None:
        """Clean up resources."""
        if self._client is not None:
            # AzureOpenAI client doesn't require explicit cleanup
            self._client = None
            logger.debug("Closed Azure OpenAI client")

    def get_preferred_model(self, category: "ToolModelCategory", allowed_models: list[str]) -> Optional[str]:
        """Get Azure's preferred model for a given category from allowed models.

        Args:
            category: The tool category requiring a model
            allowed_models: Pre-filtered list of models allowed by restrictions

        Returns:
            Preferred model name or None
        """
        from tools.models import ToolModelCategory

        if not allowed_models:
            return None

        # Helper to find first available from preference list
        def find_first(preferences: list[str]) -> Optional[str]:
            """Return first available model from preference list."""
            for model in preferences:
                if model in allowed_models:
                    return model
            return None

        if category == ToolModelCategory.EXTENDED_REASONING:
            # Prefer models with extended thinking support
            # Order: gpt-5-codex > o3-mini > gpt-5 > gpt-5-mini
            preferred = find_first(["gpt-5-codex", "o3-mini", "gpt-5", "gpt-5-mini"])
            return preferred if preferred else allowed_models[0]

        elif category == ToolModelCategory.FAST_RESPONSE:
            # Prefer faster models with good performance
            # Order: gpt-5-mini > gpt-5-nano > gpt-5 > gpt-4.1
            preferred = find_first(["gpt-5-mini", "gpt-5-nano", "gpt-5", "gpt-4.1"])
            return preferred if preferred else allowed_models[0]

        else:  # BALANCED or default
            # Prefer gpt-5-codex for code tasks, then balanced options
            # Order: gpt-5-codex > gpt-5 > gpt-5-mini > o3-mini > gpt-4.1 > gpt-5-nano
            preferred = find_first(["gpt-5-codex", "gpt-5", "gpt-5-mini", "o3-mini", "gpt-4.1", "gpt-5-nano"])
            return preferred if preferred else allowed_models[0]
