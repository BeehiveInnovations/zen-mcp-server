"""Gemini model provider implementation."""

from typing import Optional

from google import genai
from google.genai import types

from .base import ModelCapabilities, ModelProvider, ModelResponse, ProviderType, RangeTemperatureConstraint


class GeminiModelProvider(ModelProvider):
    """Google Gemini model provider implementation."""

    # Model configurations
    SUPPORTED_MODELS = {
        "gemini-2.0-flash-exp": {
            "max_tokens": 1_048_576,  # 1M tokens
            "supports_extended_thinking": False,
        },
        "gemini-2.5-pro-preview-06-05": {
            "max_tokens": 1_048_576,  # 1M tokens
            "supports_extended_thinking": True,
        },
        # Shorthands
        "flash": "gemini-2.0-flash-exp",
        "pro": "gemini-2.5-pro-preview-06-05",
    }

    # Thinking mode configurations for models that support it
    THINKING_BUDGETS = {
        "minimal": 128,  # Minimum for 2.5 Pro - fast responses
        "low": 2048,  # Light reasoning tasks
        "medium": 8192,  # Balanced reasoning (default)
        "high": 16384,  # Complex analysis
        "max": 32768,  # Maximum reasoning depth
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize Gemini provider with API key."""
        super().__init__(api_key, **kwargs)
        self._client = None
        self._token_counters = {}  # Cache for token counting

    @property
    def client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Gemini model."""
        # Resolve shorthand
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported Gemini model: {model_name}")

        config = self.SUPPORTED_MODELS[resolved_name]

        # Gemini models support 0.0-2.0 temperature range
        temp_constraint = RangeTemperatureConstraint(0.0, 2.0, 0.7)

        return ModelCapabilities(
            provider=ProviderType.GOOGLE,
            model_name=resolved_name,
            friendly_name="Gemini",
            max_tokens=config["max_tokens"],
            supports_extended_thinking=config["supports_extended_thinking"],
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            temperature_constraint=temp_constraint,
        )

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        thinking_mode: str = "medium",
        **kwargs,
    ) -> ModelResponse:
        """Generate content using Gemini model."""
        # Validate parameters
        resolved_name = self._resolve_model_name(model_name)
        self.validate_parameters(resolved_name, temperature)

        # Combine system prompt with user prompt if provided
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt

        # Prepare generation config
        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            candidate_count=1,
        )

        # Add max output tokens if specified
        if max_output_tokens:
            generation_config.max_output_tokens = max_output_tokens

        # Add thinking configuration for models that support it
        capabilities = self.get_capabilities(resolved_name)
        if capabilities.supports_extended_thinking and thinking_mode in self.THINKING_BUDGETS:
            generation_config.thinking_config = types.ThinkingConfig(
                thinking_budget=self.THINKING_BUDGETS[thinking_mode]
            )

        try:
            # Generate content
            response = self.client.models.generate_content(
                model=resolved_name,
                contents=full_prompt,
                config=generation_config,
            )

            # Extract usage information if available
            usage = self._extract_usage(response)

            return ModelResponse(
                content=response.text,
                usage=usage,
                model_name=resolved_name,
                friendly_name="Gemini",
                provider=ProviderType.GOOGLE,
                metadata={
                    "thinking_mode": thinking_mode if capabilities.supports_extended_thinking else None,
                    "finish_reason": (
                        getattr(response.candidates[0], "finish_reason", "STOP") if response.candidates else "STOP"
                    ),
                },
            )

        except Exception as e:
            # Log error and re-raise with more context
            error_msg = f"Gemini API error for model {resolved_name}: {str(e)}"
            raise RuntimeError(error_msg) from e

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text using Gemini's tokenizer."""
        self._resolve_model_name(model_name)

        # For now, use a simple estimation
        # TODO: Use actual Gemini tokenizer when available in SDK
        # Rough estimation: ~4 characters per token for English text
        return len(text) // 4

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.GOOGLE

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported."""
        resolved_name = self._resolve_model_name(model_name)
        return resolved_name in self.SUPPORTED_MODELS and isinstance(self.SUPPORTED_MODELS[resolved_name], dict)

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        capabilities = self.get_capabilities(model_name)
        return capabilities.supports_extended_thinking

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model shorthand to full name."""
        # Check if it's a shorthand
        shorthand_value = self.SUPPORTED_MODELS.get(model_name.lower())
        if isinstance(shorthand_value, str):
            return shorthand_value
        return model_name

    def _extract_usage(self, response) -> dict[str, int]:
        """Extract token usage from Gemini response."""
        usage = {}

        # Try to extract usage metadata from response
        # Note: The actual structure depends on the SDK version and response format
        if hasattr(response, "usage_metadata"):
            metadata = response.usage_metadata
            if hasattr(metadata, "prompt_token_count"):
                usage["input_tokens"] = metadata.prompt_token_count
            if hasattr(metadata, "candidates_token_count"):
                usage["output_tokens"] = metadata.candidates_token_count
            if "input_tokens" in usage and "output_tokens" in usage:
                usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]

        return usage
