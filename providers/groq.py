"""Groq provider for ultra-fast AI inference."""

import logging
from typing import Optional

from .base import ModelCapabilities, ModelResponse, ProviderType, RangeTemperatureConstraint
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class GroqProvider(OpenAICompatibleProvider):
    """Groq provider for ultra-fast AI inference using their LPU technology.

    Groq provides OpenAI-compatible API endpoints with significantly faster
    inference speeds using their proprietary Language Processing Units (LPUs).
    """

    FRIENDLY_NAME = "Groq"

    SUPPORTED_MODELS = {
        # Production Models
        "gemma2-9b-it": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="gemma2-9b-it",
            friendly_name="Groq (Gemma2 9B)",
            context_window=8192,
            max_output_tokens=8192,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Gemma2 9B Instruct - Google's efficient model optimized for instruction following",
            aliases=["gemma2-9b-it", "gemma2"],
            supports_json_mode=True,
        ),
        "llama-3.1-8b-instant": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="llama-3.1-8b-instant",
            friendly_name="Groq (Llama 3.1 8B Instant)",
            context_window=131072,
            max_output_tokens=131072,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Llama 3.1 8B Instant - Meta's fast and efficient model with 131K context",
            aliases=["llama-3.1-8b-instant", "llama-8b", "llama3.1-8b"],
            supports_json_mode=True,
        ),
        "llama-3.3-70b-versatile": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="llama-3.3-70b-versatile",
            friendly_name="Groq (Llama 3.3 70B Versatile)",
            context_window=131072,
            max_output_tokens=32768,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Llama 3.3 70B Versatile - Meta's powerful model optimized for diverse tasks",
            aliases=["llama-3.3-70b-versatile", "llama-70b", "llama3.3-70b"],
            supports_json_mode=True,
        ),
        "meta-llama/llama-guard-4-12b": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="meta-llama/llama-guard-4-12b",
            friendly_name="Groq (Llama Guard 4 12B)",
            context_window=131072,
            max_output_tokens=1024,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=False,
            supports_images=False,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Llama Guard 4 12B - Meta's latest content safety and moderation model",
            aliases=["meta-llama/llama-guard-4-12b", "llama-guard-4", "guard-4"],
            supports_json_mode=True,
        ),
        # Preview Models
        "deepseek-r1-distill-llama-70b": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="deepseek-r1-distill-llama-70b",
            friendly_name="Groq (DeepSeek R1 Distill Llama 70B)",
            context_window=131072,
            max_output_tokens=131072,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="DeepSeek R1 Distill Llama 70B - Advanced reasoning model with chain-of-thought capabilities",
            aliases=["deepseek-r1-distill-llama-70b", "deepseek-r1", "r1-distill"],
            supports_json_mode=True,
        ),
        "meta-llama/llama-4-maverick-17b-128e-instruct": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
            friendly_name="Groq (Llama 4 Maverick 17B)",
            context_window=131072,
            max_output_tokens=8192,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Llama 4 Maverick 17B - Meta's multimodal model with text and image capabilities",
            aliases=["meta-llama/llama-4-maverick-17b-128e-instruct", "llama-4-maverick", "maverick-17b"],
            supports_json_mode=True,
        ),
        "meta-llama/llama-4-scout-17b-16e-instruct": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",
            friendly_name="Groq (Llama 4 Scout 17B)",
            context_window=131072,
            max_output_tokens=8192,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Llama 4 Scout 17B - Meta's multimodal model with text and image capabilities",
            aliases=["meta-llama/llama-4-scout-17b-16e-instruct", "llama-4-scout", "scout-17b"],
            supports_json_mode=True,
        ),
        # NOTE: Prompt Guard models are text classification models that require single user messages
        # and are incompatible with conversational format. Removed:
        # - meta-llama/llama-prompt-guard-2-22m
        # - meta-llama/llama-prompt-guard-2-86m
        "mistral-saba-24b": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="mistral-saba-24b",
            friendly_name="Groq (Mistral Saba 24B)",
            context_window=32768,
            max_output_tokens=32768,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Mistral Saba 24B - Mistral AI's efficient model for text generation (NOTE: May require terms acceptance at https://console.groq.com/playground?model=mistral-saba-24b)",
            aliases=["mistral-saba-24b", "saba-24b", "mistral-saba"],
            supports_json_mode=True,
        ),
        "moonshotai/kimi-k2-instruct": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="moonshotai/kimi-k2-instruct",
            friendly_name="Groq (Kimi K2 Instruct)",
            context_window=131072,
            max_output_tokens=16384,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Kimi K2 Instruct - Moonshot AI's instruction-following model",
            aliases=["moonshotai/kimi-k2-instruct", "kimi-k2", "k2-instruct"],
            supports_json_mode=True,
        ),
        "qwen/qwen3-32b": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="qwen/qwen3-32b",
            friendly_name="Groq (Qwen 3 32B)",
            context_window=131072,
            max_output_tokens=40960,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Qwen 3 32B - Alibaba Cloud's powerful text generation model",
            aliases=["qwen/qwen3-32b", "qwen3-32b", "qwen3"],
            supports_json_mode=True,
        ),
        # Preview Systems
        "compound-beta": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="compound-beta",
            friendly_name="Groq (Compound Beta)",
            context_window=131072,
            max_output_tokens=8192,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Compound Beta - Groq's experimental system combining multiple models",
            aliases=["compound-beta", "compound"],
            supports_json_mode=True,
        ),
        "compound-beta-mini": ModelCapabilities(
            provider=ProviderType.GROQ,
            model_name="compound-beta-mini",
            friendly_name="Groq (Compound Beta Mini)",
            context_window=131072,
            max_output_tokens=8192,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            max_image_size_mb=0.0,
            supports_temperature=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.7),
            description="Compound Beta Mini - Groq's experimental mini system for faster inference",
            aliases=["compound-beta-mini", "compound-mini"],
            supports_json_mode=True,
        ),
    }

    def __init__(self, api_key: str, base_url: str = None, **kwargs):
        """Initialize the Groq provider.

        Args:
            api_key: Groq API key for authentication
            base_url: Optional custom base URL. Defaults to Groq's official endpoint
            **kwargs: Additional arguments passed to the parent OpenAI-compatible provider
        """
        # Use Groq's official API endpoint
        if base_url is None:
            base_url = "https://api.groq.com/openai/v1"
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)

    def get_provider_type(self) -> ProviderType:
        """Return the provider type identifier.

        Returns:
            ProviderType.GROQ constant
        """
        return ProviderType.GROQ

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Groq model.

        Args:
            model_name: Name or alias of the Groq model

        Returns:
            ModelCapabilities object with model specifications including context window,
            inference speed optimizations, temperature constraints, and feature availability

        Raises:
            ValueError: If the model is not supported by this provider
        """
        # Resolve model name (handle aliases)
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name in self.SUPPORTED_MODELS:
            return self.SUPPORTED_MODELS[resolved_name]

        raise ValueError(f"Unsupported Groq model: {model_name}")

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported and allowed.

        Checks both model support and any configured usage restrictions.
        Resolves model aliases before validation.

        Args:
            model_name: Name or alias of the Groq model to validate

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
        if not restriction_service.is_allowed(ProviderType.GROQ, resolved_name, model_name):
            logger.debug(f"Groq model '{model_name}' -> '{resolved_name}' blocked by restrictions")
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
        """Generate content using Groq API with proper model name resolution.

        Args:
            prompt: User prompt to send to the model
            model_name: Name or alias of the Groq model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature (0-2)
            max_output_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        # Resolve model alias before making API call
        resolved_model_name = self._resolve_model_name(model_name)

        # Call parent implementation with resolved model name
        response = super().generate_content(
            prompt=prompt,
            model_name=resolved_model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs,
        )

        # Return the original model name in the response (not the resolved one)
        response.model_name = model_name
        return response

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode.

        Currently, most Groq models are optimized for fast inference and do not
        support extended thinking mode, except for reasoning models like DeepSeek R1.

        Args:
            model_name: Name or alias of the Groq model to check

        Returns:
            True if the model supports extended thinking mode, False otherwise
        """
        try:
            capabilities = self.get_capabilities(model_name)
            return capabilities.supports_extended_thinking
        except ValueError:
            return False

    def _supports_vision(self, model_name: str) -> bool:
        """Check if the model supports vision (image processing).

        Args:
            model_name: Name or alias of the Groq model to check

        Returns:
            True if the model supports image processing, False otherwise
        """
        try:
            capabilities = self.get_capabilities(model_name)
            return capabilities.supports_images
        except ValueError:
            return False
