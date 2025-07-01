"""Async Gemini model provider implementation."""

import asyncio
import base64
import logging
import os
from typing import Optional

from google import genai
from google.genai import types

from .async_base import AsyncModelProvider
from .base import ModelCapabilities, ModelResponse, ProviderType, create_temperature_constraint

logger = logging.getLogger(__name__)


class AsyncGeminiModelProvider(AsyncModelProvider):
    """Async Google Gemini model provider implementation."""

    FRIENDLY_NAME = "Async Gemini"

    # Thinking mode token allocation
    THINKING_BUDGETS = {
        "deep": 1.0,  # Use full budget for deep thinking
        "moderate": 0.6,  # Use 60% of max thinking tokens
        "light": 0.3,  # Use 30% of max thinking tokens
        "off": 0.0,  # No thinking tokens
    }

    # Model configurations using ModelCapabilities objects
    SUPPORTED_MODELS = {
        "gemini-2.0-flash": ModelCapabilities(
            provider=ProviderType.GOOGLE,
            model_name="gemini-2.0-flash",
            friendly_name="Gemini (Flash 2.0)",
            context_window=1_048_576,  # 1M tokens
            max_output_tokens=65_536,
            supports_extended_thinking=True,  # Experimental thinking mode
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # Vision capability
            max_image_size_mb=20.0,  # Conservative 20MB limit for reliability
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            max_thinking_tokens=24576,  # Same as 2.5 flash for consistency
            description="Gemini 2.0 Flash (1M context) - Latest fast model with experimental thinking, supports audio/video input",
            aliases=["flash-2.0", "flash2"],
        ),
        "gemini-2.0-flash-lite": ModelCapabilities(
            provider=ProviderType.GOOGLE,
            model_name="gemini-2.0-flash-lite",
            friendly_name="Gemini (Flash Lite 2.0)",
            context_window=1_048_576,  # 1M tokens
            max_output_tokens=65_536,
            supports_extended_thinking=False,  # Not supported per user request
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # Vision capability
            max_image_size_mb=20.0,  # Conservative 20MB limit for reliability
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            max_thinking_tokens=0,  # No thinking support
            description="Gemini 2.0 Flash Lite (1M context) - Lightweight version of Flash 2.0, faster responses",
            aliases=["flash-lite-2.0", "flash2-lite"],
        ),
        "gemini-2.5-flash": ModelCapabilities(
            provider=ProviderType.GOOGLE,
            model_name="gemini-2.5-flash",
            friendly_name="Gemini (Flash 2.5)",
            context_window=1_048_576,  # 1M tokens
            max_output_tokens=65_536,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            max_thinking_tokens=24576,  # 24K thinking tokens
            description="Gemini 2.5 Flash (1M context) - Fast, efficient model with thinking capabilities",
            aliases=["flash", "flash-2.5", "flashlite"],
        ),
        "gemini-2.5-pro": ModelCapabilities(
            provider=ProviderType.GOOGLE,
            model_name="gemini-2.5-pro",
            friendly_name="Gemini (Pro 2.5)",
            context_window=2_097_152,  # 2M tokens
            max_output_tokens=65_536,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            max_thinking_tokens=65536,  # 64K thinking tokens for deeper reasoning
            description="Gemini 2.5 Pro (2M context) - Advanced reasoning with extensive thinking capabilities",
            aliases=["pro", "pro-2.5"],
        ),
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize the async Gemini provider.

        Args:
            api_key: Google API key
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, **kwargs)

        # Configure the Gemini client
        genai.configure(api_key=api_key)

        # Cache for model clients
        self._model_clients = {}
        self._client_lock = asyncio.Lock()

    async def get_model_client(self, model_name: str):
        """Get or create a model client for the specified model.

        Args:
            model_name: Name of the model

        Returns:
            Configured Gemini model client
        """
        if model_name not in self._model_clients:
            async with self._client_lock:
                if model_name not in self._model_clients:
                    self._model_clients[model_name] = genai.GenerativeModel(model_name)
        return self._model_clients[model_name]

    async def generate_content_async(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        images: Optional[list[str]] = None,
        thinking_mode: str = "off",
        **kwargs,
    ) -> ModelResponse:
        """Generate content using the Gemini API asynchronously.

        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature
            max_output_tokens: Maximum tokens to generate
            images: Optional list of image paths/URLs
            thinking_mode: Thinking mode for models that support it
            **kwargs: Additional provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        # Validate model name
        if not self.validate_model_name(model_name):
            raise ValueError(f"Model '{model_name}' is not supported or allowed")

        resolved_name = self._resolve_model_name(model_name)

        # Get effective temperature
        effective_temperature = self.get_effective_temperature(resolved_name, temperature)

        # Validate parameters if temperature is supported
        if effective_temperature is not None:
            self.validate_parameters(resolved_name, effective_temperature)

        # Get model client
        model = await self.get_model_client(resolved_name)

        # Prepare content parts
        content_parts = []

        # Add text content
        content_parts.append(prompt)

        # Add images if provided and supported
        if images and self._supports_vision(resolved_name):
            for image_path in images:
                try:
                    image_content = await self._process_image_async(image_path)
                    if image_content:
                        content_parts.append(image_content)
                except Exception as e:
                    logger.warning(f"Failed to process image {image_path}: {e}")
                    continue
        elif images and not self._supports_vision(resolved_name):
            logger.warning(f"Model {resolved_name} does not support images, ignoring {len(images)} image(s)")

        # Prepare generation config
        config = {}

        if effective_temperature is not None:
            config["temperature"] = effective_temperature

        if max_output_tokens:
            config["max_output_tokens"] = max_output_tokens

        # Handle thinking mode for supported models
        if self.supports_thinking_mode(resolved_name) and thinking_mode != "off":
            thinking_budget = self.get_thinking_budget(resolved_name, thinking_mode)
            if thinking_budget > 0:
                config["response_schema"] = types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "thinking": types.Schema(
                            type=types.Type.STRING,
                            description=f"Your internal reasoning and analysis (max {thinking_budget} tokens)",
                        ),
                        "response": types.Schema(type=types.Type.STRING, description="Your final response to the user"),
                    },
                    required=["thinking", "response"],
                )

        generation_config = genai.GenerationConfig(**config) if config else None

        # Prepare system instruction
        system_instruction = system_prompt if system_prompt else None

        # Create request with system instruction if provided
        if system_instruction:
            model_with_system = genai.GenerativeModel(model_name=resolved_name, system_instruction=system_instruction)
            model_to_use = model_with_system
        else:
            model_to_use = model

        # Retry logic with progressive delays
        max_retries = 4
        retry_delays = [1, 3, 5, 8]
        last_exception = None

        for attempt in range(max_retries):
            try:
                # Generate content asynchronously
                response = await asyncio.to_thread(
                    model_to_use.generate_content, content_parts, generation_config=generation_config
                )

                # Extract content
                content = ""
                if response.text:
                    content = response.text
                elif response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if hasattr(candidate, "content") and candidate.content:
                        if hasattr(candidate.content, "parts") and candidate.content.parts:
                            content = "".join(part.text for part in candidate.content.parts if hasattr(part, "text"))

                # Extract usage information
                usage = self._extract_usage(response)

                return ModelResponse(
                    content=content,
                    usage=usage,
                    model_name=model_name,
                    friendly_name=self.FRIENDLY_NAME,
                    provider=self.get_provider_type(),
                    metadata={
                        "model": resolved_name,
                        "finish_reason": (
                            getattr(response.candidates[0], "finish_reason", None) if response.candidates else None
                        ),
                        "safety_ratings": (
                            getattr(response.candidates[0], "safety_ratings", []) if response.candidates else []
                        ),
                    },
                )

            except Exception as e:
                last_exception = e

                # Check if this is a retryable error
                is_retryable = self._is_error_retryable(e)

                # If this is the last attempt or not retryable, give up
                if attempt == max_retries - 1 or not is_retryable:
                    break

                # Get progressive delay
                delay = retry_delays[attempt]

                # Log retry attempt
                logger.warning(
                    f"Gemini API error for model {resolved_name}, attempt {attempt + 1}/{max_retries}: {str(e)}. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

        # If we get here, all retries failed
        actual_attempts = attempt + 1
        error_msg = f"Gemini API error for model {resolved_name} after {actual_attempts} attempt{'s' if actual_attempts > 1 else ''}: {str(last_exception)}"
        raise RuntimeError(error_msg) from last_exception

    async def count_tokens_async(self, text: str, model_name: str) -> int:
        """Count tokens for the given text asynchronously.

        Args:
            text: Text to count tokens for
            model_name: Model name for tokenizer selection

        Returns:
            Estimated token count
        """
        # For now, use synchronous implementation
        # Could be enhanced to use async Gemini token counting in the future
        return self.count_tokens(text, model_name)

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text using Gemini's tokenizer."""
        self._resolve_model_name(model_name)

        # For now, use a simple estimation
        # TODO: Use actual Gemini tokenizer when available in SDK
        # Rough estimation: ~4 characters per token for English text
        return len(text) // 4

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
        """Get the provider type."""
        return ProviderType.GOOGLE

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported and allowed."""
        resolved_name = self._resolve_model_name(model_name)

        # First check if model is supported
        if resolved_name not in self.SUPPORTED_MODELS:
            return False

        # Then check if model is allowed by restrictions
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.GOOGLE, resolved_name, model_name):
            logger.debug(f"Gemini model '{model_name}' -> '{resolved_name}' blocked by restrictions")
            return False

        return True

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        try:
            capabilities = self.get_capabilities(model_name)
            return capabilities.supports_extended_thinking
        except ValueError:
            return False

    def get_thinking_budget(self, model_name: str, thinking_mode: str) -> int:
        """Get actual thinking token budget for a model and thinking mode."""
        resolved_name = self._resolve_model_name(model_name)
        model_config = self.SUPPORTED_MODELS.get(resolved_name)

        if not model_config or not model_config.supports_extended_thinking:
            return 0

        if thinking_mode not in self.THINKING_BUDGETS:
            return 0

        max_thinking_tokens = model_config.max_thinking_tokens
        if max_thinking_tokens == 0:
            return 0

        return int(max_thinking_tokens * self.THINKING_BUDGETS[thinking_mode])

    def _extract_usage(self, response) -> dict[str, int]:
        """Extract token usage from Gemini response."""
        usage = {}

        # Try to extract usage metadata from response
        if hasattr(response, "usage_metadata"):
            metadata = response.usage_metadata

            # Extract token counts with explicit None checks
            input_tokens = None
            output_tokens = None

            if hasattr(metadata, "prompt_token_count"):
                value = metadata.prompt_token_count
                if value is not None:
                    input_tokens = value
                    usage["input_tokens"] = value

            if hasattr(metadata, "candidates_token_count"):
                value = metadata.candidates_token_count
                if value is not None:
                    output_tokens = value
                    usage["output_tokens"] = value

            # Calculate total only if both values are available and valid
            if input_tokens is not None and output_tokens is not None:
                usage["total_tokens"] = input_tokens + output_tokens

        return usage

    def _supports_vision(self, model_name: str) -> bool:
        """Check if the model supports vision (image processing)."""
        # Gemini models with vision support
        vision_models = {
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        }
        return model_name in vision_models

    def _is_error_retryable(self, error: Exception) -> bool:
        """Determine if an error should be retried."""
        error_str = str(error).lower()

        # Check for 429 errors first
        if "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
            # These typically indicate permanent failures or quota/size limits
            non_retryable_indicators = [
                "quota exceeded",
                "resource exhausted",
                "context length",
                "token limit",
                "request too large",
                "invalid request",
                "quota_exceeded",
                "resource_exhausted",
            ]

            # Check for structured error details
            try:
                if hasattr(error, "details") or hasattr(error, "reason"):
                    error_details = getattr(error, "details", "") or getattr(error, "reason", "")
                    error_details_str = str(error_details).lower()

                    if any(indicator in error_details_str for indicator in non_retryable_indicators):
                        logger.debug(f"Non-retryable Gemini error: {error_details}")
                        return False
            except Exception:
                pass

            # Check main error string for non-retryable patterns
            if any(indicator in error_str for indicator in non_retryable_indicators):
                logger.debug(f"Non-retryable Gemini error based on message: {error_str[:200]}...")
                return False

            # If it's a quota error but doesn't match non-retryable patterns, it might be retryable
            logger.debug(f"Retryable Gemini rate limiting error: {error_str[:100]}...")
            return True

        # Check for other retryable errors
        retryable_indicators = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "unavailable",
            "retry",
            "internal error",
            "408",  # Request timeout
            "500",  # Internal server error
            "502",  # Bad gateway
            "503",  # Service unavailable
            "504",  # Gateway timeout
            "ssl",  # SSL errors
            "handshake",  # Handshake failures
        ]

        return any(indicator in error_str for indicator in retryable_indicators)

    async def _process_image_async(self, image_path: str) -> Optional[dict]:
        """Process an image for Gemini API asynchronously."""
        try:
            if image_path.startswith("data:image/"):
                # Handle data URL: data:image/png;base64,iVBORw0...
                header, data = image_path.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1]
                return {"inline_data": {"mime_type": mime_type, "data": data}}
            else:
                # Handle file path - could be made async with aiofiles in the future
                if not os.path.exists(image_path):
                    logger.warning(f"Image file not found: {image_path}")
                    return None

                # Detect MIME type from file extension
                from utils.file_types import get_image_mime_type

                ext = os.path.splitext(image_path)[1].lower()
                mime_type = get_image_mime_type(ext)
                logger.debug(f"Processing image '{image_path}' with extension '{ext}' as MIME type '{mime_type}'")

                # Read and encode the image
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()

                return {"inline_data": {"mime_type": mime_type, "data": image_data}}
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None

    async def aclose(self):
        """Async cleanup of Gemini resources."""
        # Clear model client cache
        async with self._client_lock:
            self._model_clients.clear()

        # Call parent cleanup
        await super().aclose()
