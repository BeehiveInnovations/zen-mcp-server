"""Async OpenAI model provider implementation."""

import logging

from .async_openai_compatible import AsyncOpenAICompatibleProvider
from .base import ModelCapabilities, ProviderType, create_temperature_constraint

logger = logging.getLogger(__name__)


class AsyncOpenAIModelProvider(AsyncOpenAICompatibleProvider):
    """Async official OpenAI API provider (api.openai.com)."""

    FRIENDLY_NAME = "Async OpenAI"

    # Model configurations using ModelCapabilities objects
    SUPPORTED_MODELS = {
        "o3": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="o3",
            friendly_name="OpenAI (O3)",
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
            description="Strong reasoning (200K context) - Logical problems, code generation, systematic analysis",
            aliases=[],
        ),
        "o3-mini": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="o3-mini",
            friendly_name="OpenAI (O3-mini)",
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
            description="Fast O3 variant (200K context) - Balanced performance/speed, moderate complexity",
            aliases=["o3mini", "o3-mini"],
        ),
        "o3-pro-2025-06-10": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="o3-pro-2025-06-10",
            friendly_name="OpenAI (O3-Pro)",
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
            description="Professional-grade reasoning (200K context) - EXTREMELY EXPENSIVE: Only for the most complex problems requiring universe-scale complexity analysis OR when the user explicitly asks for this model. Use sparingly for critical architectural decisions or exceptionally complex debugging that other models cannot handle.",
            aliases=["o3-pro"],
        ),
        "o4-mini": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="o4-mini",
            friendly_name="OpenAI (O4-mini)",
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
            description="Latest reasoning model (200K context) - Optimized for shorter contexts, rapid reasoning",
            aliases=["mini", "o4mini", "o4-mini"],
        ),
        "gpt-4.1-2025-04-14": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="gpt-4.1-2025-04-14",
            friendly_name="OpenAI (GPT 4.1)",
            context_window=1_000_000,  # 1M tokens
            max_output_tokens=32_768,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # GPT-4.1 supports vision
            max_image_size_mb=20.0,  # 20MB per OpenAI docs
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="Optimized GPT-4 variant (1M context) - General tasks, creative writing, analysis",
            aliases=["gpt-4.1", "gpt41"],
        ),
        "gpt-4o": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="gpt-4o",
            friendly_name="OpenAI (GPT-4o)",
            context_window=128_000,
            max_output_tokens=16_384,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="High-performance text and vision model (128K context) - Multimodal tasks, vision analysis",
            aliases=["gpt4o"],
        ),
        "gpt-4o-mini": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="gpt-4o-mini",
            friendly_name="OpenAI (GPT-4o-mini)",
            context_window=128_000,
            max_output_tokens=16_384,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="Cost-effective vision model (128K context) - Lightweight multimodal tasks",
            aliases=["gpt4o-mini"],
        ),
        "gpt-4-turbo": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="gpt-4-turbo",
            friendly_name="OpenAI (GPT-4 Turbo)",
            context_window=128_000,
            max_output_tokens=4_096,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="Fast GPT-4 variant (128K context) - Quick responses, efficient processing",
            aliases=["gpt4-turbo"],
        ),
        "gpt-3.5-turbo": ModelCapabilities(
            provider=ProviderType.OPENAI,
            model_name="gpt-3.5-turbo",
            friendly_name="OpenAI (GPT-3.5 Turbo)",
            context_window=16_385,
            max_output_tokens=4_096,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="Fast and cost-effective model (16K context) - Simple tasks, quick responses",
            aliases=["gpt35-turbo", "gpt3.5"],
        ),
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize the async OpenAI provider.

        Args:
            api_key: OpenAI API key
            **kwargs: Additional configuration options
        """
        # Set base URL for OpenAI API
        super().__init__(api_key, base_url="https://api.openai.com/v1", **kwargs)

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific model.

        Args:
            model_name: Name of the model to get capabilities for

        Returns:
            ModelCapabilities object for the specified model

        Raises:
            ValueError: If model is not supported
        """
        resolved_model = self._resolve_model_name(model_name)

        if resolved_model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")

        return self.SUPPORTED_MODELS[resolved_model]

    def get_provider_type(self) -> ProviderType:
        """Get the provider type.

        Returns:
            ProviderType.OPENAI
        """
        return ProviderType.OPENAI

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported by this provider.

        Args:
            model_name: Model name to validate

        Returns:
            True if model is supported, False otherwise
        """
        # If allow-list is configured, check against it
        if self.allowed_models:
            return model_name.lower() in self.allowed_models

        # Check against our supported models
        resolved_model = self._resolve_model_name(model_name)
        return resolved_model in self.SUPPORTED_MODELS

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode.

        Args:
            model_name: Model name to check

        Returns:
            True if model supports thinking mode, False otherwise
        """
        try:
            capabilities = self.get_capabilities(model_name)
            return capabilities.supports_extended_thinking
        except ValueError:
            return False
