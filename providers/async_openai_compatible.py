"""Async OpenAI-compatible provider implementation."""

import asyncio
import base64
import ipaddress
import logging
import os
from abc import abstractmethod
from typing import Optional
from urllib.parse import urlparse

import httpx
from openai import AsyncOpenAI

from .async_base import AsyncModelProvider, CircuitBreakerMixin
from .base import ModelCapabilities, ModelResponse, ProviderType

logger = logging.getLogger(__name__)


class AsyncOpenAICompatibleProvider(AsyncModelProvider, CircuitBreakerMixin):
    """Async base class for any provider using an OpenAI-compatible API.

    This includes:
    - Direct OpenAI API
    - OpenRouter
    - Any other OpenAI-compatible endpoint

    Provides async support with:
    - Connection pooling and keep-alive
    - Semaphore-based concurrency control
    - Non-blocking API calls
    - Proper resource cleanup
    - Circuit breaker pattern for graceful failure handling

    Circuit breaker features:
    - Automatic failure detection and fast-fail behavior
    - Configurable failure thresholds and recovery timeouts
    - CLOSED/OPEN/HALF_OPEN state management
    - Resource protection during service outages
    - Observable metrics and health status
    """

    DEFAULT_HEADERS = {}
    FRIENDLY_NAME = "Async OpenAI Compatible"

    def __init__(self, api_key: str, base_url: str = None, **kwargs):
        """Initialize the async provider with API key and optional base URL.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the API endpoint
            **kwargs: Additional configuration options including timeout
        """
        super().__init__(api_key, **kwargs)
        self._async_openai_client = None
        self._openai_client_lock = asyncio.Lock()
        self.base_url = base_url
        self.organization = kwargs.get("organization")
        self.allowed_models = self._parse_allowed_models()

        # Configure timeouts - especially important for custom/local endpoints
        self.openai_timeout_config = self._configure_openai_timeouts(**kwargs)

        # Validate base URL for security
        if self.base_url:
            self._validate_base_url()

        # Warn if using external URL without authentication
        if self.base_url and not self._is_localhost_url() and not api_key:
            logger.warning(
                f"Using external URL '{self.base_url}' without API key. "
                "This may be insecure. Consider setting an API key for authentication."
            )

    def _parse_allowed_models(self) -> Optional[set[str]]:
        """Parse allowed models from environment variable.

        Returns:
            Set of allowed model names (lowercase) or None if not configured
        """
        # Get provider-specific allowed models
        provider_type = self.get_provider_type().value.upper()
        env_var = f"{provider_type}_ALLOWED_MODELS"
        models_str = os.getenv(env_var, "")

        if models_str:
            # Parse and normalize to lowercase for case-insensitive comparison
            models = {m.strip().lower() for m in models_str.split(",") if m.strip()}
            if models:
                logger.info(f"Configured allowed models for {self.FRIENDLY_NAME}: {sorted(models)}")
                return models

        # Log info if no allow-list configured for proxy providers
        if self.get_provider_type() not in [ProviderType.GOOGLE, ProviderType.OPENAI]:
            logger.info(
                f"Model allow-list not configured for {self.FRIENDLY_NAME} - all models permitted. "
                f"To restrict access, set {env_var} with comma-separated model names."
            )

        return None

    def _configure_openai_timeouts(self, **kwargs):
        """Configure timeout settings for OpenAI client.

        Returns:
            httpx.Timeout object with appropriate timeout settings
        """
        # Default timeouts - more generous for custom/local endpoints
        default_connect = 30.0  # 30 seconds for connection
        default_read = 600.0  # 10 minutes for reading
        default_write = 600.0  # 10 minutes for writing
        default_pool = 600.0  # 10 minutes for pool

        # For custom/local URLs, use even longer timeouts
        if self.base_url and self._is_localhost_url():
            default_connect = 60.0  # 1 minute for local connections
            default_read = 1800.0  # 30 minutes for local models
            default_write = 1800.0  # 30 minutes for local models
            default_pool = 1800.0  # 30 minutes for local models
            logger.info(f"Using extended timeouts for local endpoint: {self.base_url}")
        elif self.base_url:
            default_connect = 45.0  # 45 seconds for custom remote endpoints
            default_read = 900.0  # 15 minutes for custom remote endpoints
            default_write = 900.0  # 15 minutes for custom remote endpoints
            default_pool = 900.0  # 15 minutes for custom remote endpoints
            logger.info(f"Using extended timeouts for custom endpoint: {self.base_url}")

        # Allow override via kwargs
        connect_timeout = kwargs.get("connect_timeout", default_connect)
        read_timeout = kwargs.get("read_timeout", default_read)
        write_timeout = kwargs.get("write_timeout", default_write)
        pool_timeout = kwargs.get("pool_timeout", default_pool)

        timeout = httpx.Timeout(connect=connect_timeout, read=read_timeout, write=write_timeout, pool=pool_timeout)

        logger.debug(
            f"Configured OpenAI timeouts - Connect: {connect_timeout}s, Read: {read_timeout}s, "
            f"Write: {write_timeout}s, Pool: {pool_timeout}s"
        )

        return timeout

    def _is_localhost_url(self) -> bool:
        """Check if the base URL points to localhost or local network."""
        if not self.base_url:
            return False

        try:
            parsed = urlparse(self.base_url)
            hostname = parsed.hostname

            # Check for common localhost patterns
            if hostname in ["localhost", "127.0.0.1", "::1"]:
                return True

            # Check for private network ranges (local network)
            if hostname:
                try:
                    ip = ipaddress.ip_address(hostname)
                    return ip.is_private or ip.is_loopback
                except ValueError:
                    # Not an IP address, might be a hostname
                    pass

            return False
        except Exception:
            return False

    def _validate_base_url(self) -> None:
        """Validate base URL for security (SSRF protection)."""
        if not self.base_url:
            return

        try:
            parsed = urlparse(self.base_url)

            # Check URL scheme - only allow http/https
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")

            # Check hostname exists
            if not parsed.hostname:
                raise ValueError("URL must include a hostname")

            # Check port is valid (if specified)
            port = parsed.port
            if port is not None and (port < 1 or port > 65535):
                raise ValueError(f"Invalid port number: {port}. Must be between 1 and 65535.")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid base URL '{self.base_url}': {str(e)}")

    async def get_openai_client(self) -> AsyncOpenAI:
        """Get or create async OpenAI client with connection pooling."""
        if self._async_openai_client is None:
            async with self._openai_client_lock:
                if self._async_openai_client is None:
                    self._async_openai_client = await self._create_openai_client()
        return self._async_openai_client

    async def _create_openai_client(self) -> AsyncOpenAI:
        """Create async OpenAI client with pooled HTTP client."""
        # Get our async HTTP client with connection pooling
        http_client = await self.get_async_client(base_url=self.base_url, headers=self.DEFAULT_HEADERS)

        # Create OpenAI client with pooled HTTP client
        client_kwargs = {
            "api_key": self.api_key,
            "http_client": http_client,
        }

        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        if self.organization:
            client_kwargs["organization"] = self.organization

        # Add default headers if any
        if self.DEFAULT_HEADERS:
            client_kwargs["default_headers"] = self.DEFAULT_HEADERS.copy()

        logger.debug("Async OpenAI client initialized with pooled HTTP client")

        return AsyncOpenAI(**client_kwargs)

    async def generate_content_async(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        images: Optional[list[str]] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using the OpenAI-compatible API asynchronously.

        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature
            max_output_tokens: Maximum tokens to generate
            images: Optional list of image paths/URLs
            **kwargs: Additional provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        # Validate model name against allow-list
        if not self.validate_model_name(model_name):
            raise ValueError(f"Model '{model_name}' not in allowed models list. Allowed models: {self.allowed_models}")

        # Get effective temperature for this model
        effective_temperature = self.get_effective_temperature(model_name, temperature)

        # Only validate if temperature is not None (meaning the model supports it)
        if effective_temperature is not None:
            # Validate parameters with the effective temperature
            self.validate_parameters(model_name, effective_temperature)

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Prepare user message with text and potentially images
        user_content = []
        user_content.append({"type": "text", "text": prompt})

        # Add images if provided and model supports vision
        if images and self._supports_vision(model_name):
            for image_path in images:
                try:
                    image_content = await self._process_image_async(image_path)
                    if image_content:
                        user_content.append(image_content)
                except Exception as e:
                    logger.warning(f"Failed to process image {image_path}: {e}")
                    # Continue with other images and text
                    continue
        elif images and not self._supports_vision(model_name):
            logger.warning(f"Model {model_name} does not support images, ignoring {len(images)} image(s)")

        # Add user message
        if len(user_content) == 1:
            # Only text content, use simple string format for compatibility
            messages.append({"role": "user", "content": prompt})
        else:
            # Text + images, use content array format
            messages.append({"role": "user", "content": user_content})

        # Prepare completion parameters
        completion_params = {
            "model": model_name,
            "messages": messages,
        }

        # Check model capabilities once to determine parameter support
        resolved_model = self._resolve_model_name(model_name)

        # Use the effective temperature we calculated earlier
        if effective_temperature is not None:
            completion_params["temperature"] = effective_temperature
            supports_temperature = True
        else:
            # Model doesn't support temperature
            supports_temperature = False

        # Add max tokens if specified and model supports it
        if max_output_tokens and supports_temperature:
            completion_params["max_tokens"] = max_output_tokens

        # Add any additional OpenAI-specific parameters
        for key, value in kwargs.items():
            if key in ["top_p", "frequency_penalty", "presence_penalty", "seed", "stop", "stream"]:
                # Reasoning models (those that don't support temperature) also don't support these parameters
                if not supports_temperature and key in ["top_p", "frequency_penalty", "presence_penalty"]:
                    continue  # Skip unsupported parameters for reasoning models
                completion_params[key] = value

        # Check if this is o3-pro and needs the responses endpoint
        if resolved_model == "o3-pro-2025-06-10":
            # This model requires the /v1/responses endpoint
            return await self._generate_with_responses_endpoint_async(
                model_name=resolved_model,
                messages=messages,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                **kwargs,
            )

        # Retry logic with progressive delays
        max_retries = 4
        retry_delays = [1, 3, 5, 8]
        last_exception = None

        client = await self.get_openai_client()

        for attempt in range(max_retries):
            try:
                # Generate completion asynchronously
                response = await client.chat.completions.create(**completion_params)

                # Extract content and usage
                content = response.choices[0].message.content
                usage = self._extract_usage(response)

                return ModelResponse(
                    content=content,
                    usage=usage,
                    model_name=model_name,
                    friendly_name=self.FRIENDLY_NAME,
                    provider=self.get_provider_type(),
                    metadata={
                        "finish_reason": response.choices[0].finish_reason,
                        "model": response.model,
                        "id": response.id,
                        "created": response.created,
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
                    f"{self.FRIENDLY_NAME} error for model {model_name}, attempt {attempt + 1}/{max_retries}: {str(e)}. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

        # If we get here, all retries failed
        actual_attempts = attempt + 1
        error_msg = f"{self.FRIENDLY_NAME} API error for model {model_name} after {actual_attempts} attempt{'s' if actual_attempts > 1 else ''}: {str(last_exception)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from last_exception

    async def _generate_with_responses_endpoint_async(
        self,
        model_name: str,
        messages: list,
        temperature: float,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using the /v1/responses endpoint for o3-pro asynchronously."""
        # Convert messages to the correct format for responses endpoint
        input_messages = []

        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "system":
                input_messages.append({"role": "user", "content": [{"type": "input_text", "text": content}]})
            elif role == "user":
                input_messages.append({"role": "user", "content": [{"type": "input_text", "text": content}]})
            elif role == "assistant":
                input_messages.append({"role": "assistant", "content": [{"type": "output_text", "text": content}]})

        # Prepare completion parameters for responses endpoint
        completion_params = {
            "model": model_name,
            "input": input_messages,
            "reasoning": {"effort": "medium"},
            "store": True,
        }

        # Add max tokens if specified
        if max_output_tokens:
            completion_params["max_completion_tokens"] = max_output_tokens

        # Retry logic with progressive delays
        max_retries = 4
        retry_delays = [1, 3, 5, 8]
        last_exception = None

        client = await self.get_openai_client()

        for attempt in range(max_retries):
            try:
                # Use OpenAI client's responses endpoint asynchronously
                response = await client.responses.create(**completion_params)

                # Extract content and usage from responses endpoint format
                content = ""
                if hasattr(response, "output") and response.output:
                    if hasattr(response.output, "content") and response.output.content:
                        # Look for output_text in content
                        for content_item in response.output.content:
                            if hasattr(content_item, "type") and content_item.type == "output_text":
                                content = content_item.text
                                break
                    elif hasattr(response.output, "text"):
                        content = response.output.text

                # Try to extract usage information
                usage = None
                if hasattr(response, "usage"):
                    usage = self._extract_usage(response)
                elif hasattr(response, "input_tokens") and hasattr(response, "output_tokens"):
                    input_tokens = getattr(response, "input_tokens", 0) or 0
                    output_tokens = getattr(response, "output_tokens", 0) or 0
                    usage = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    }

                return ModelResponse(
                    content=content,
                    usage=usage,
                    model_name=model_name,
                    friendly_name=self.FRIENDLY_NAME,
                    provider=self.get_provider_type(),
                    metadata={
                        "model": getattr(response, "model", model_name),
                        "id": getattr(response, "id", ""),
                        "created": getattr(response, "created_at", 0),
                        "endpoint": "responses",
                    },
                )

            except Exception as e:
                last_exception = e

                # Check if this is a retryable error
                is_retryable = self._is_error_retryable(e)

                if is_retryable and attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(
                        f"Retryable error for o3-pro responses endpoint, attempt {attempt + 1}/{max_retries}: {str(e)}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    break

        # If we get here, all retries failed
        actual_attempts = attempt + 1
        error_msg = f"o3-pro responses endpoint error after {actual_attempts} attempt{'s' if actual_attempts > 1 else ''}: {str(last_exception)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from last_exception

    async def count_tokens_async(self, text: str, model_name: str) -> int:
        """Count tokens for the given text asynchronously.

        Args:
            text: Text to count tokens for
            model_name: Model name for tokenizer selection

        Returns:
            Estimated token count
        """
        # For now, use the synchronous implementation
        # In the future, this could be enhanced to use async token counting APIs
        return self.count_tokens(text, model_name)

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text (sync implementation)."""
        # Try tiktoken for known models
        try:
            import tiktoken

            try:
                encoding = tiktoken.encoding_for_model(model_name)
            except KeyError:
                # Try common encodings based on model patterns
                if "gpt-4" in model_name or "gpt-3.5" in model_name:
                    encoding = tiktoken.get_encoding("cl100k_base")
                else:
                    encoding = tiktoken.get_encoding("cl100k_base")  # Default

            return len(encoding.encode(text))

        except (ImportError, Exception) as e:
            logger.debug(f"Tiktoken not available or failed: {e}")

        # Fall back to character-based estimation
        logger.warning(
            f"No specific tokenizer available for '{model_name}'. "
            "Using character-based estimation (~4 chars per token)."
        )
        return len(text) // 4

    def _supports_vision(self, model_name: str) -> bool:
        """Check if the model supports vision (image processing)."""
        # Common vision-capable models
        vision_models = {
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4-vision-preview",
            "gpt-4.1-2025-04-14",
            "o3",
            "o3-mini",
            "o3-pro",
            "o4-mini",
        }
        supports = model_name.lower() in vision_models
        logger.debug(f"Model '{model_name}' vision support: {supports}")
        return supports

    def _is_error_retryable(self, error: Exception) -> bool:
        """Determine if an error should be retried."""
        error_str = str(error).lower()

        # Check for 429 errors first
        if "429" in error_str:
            # Token-related 429s are typically non-retryable
            if "tokens" in error_str or "context_length_exceeded" in error_str:
                return False
            # Other 429s (rate limiting) are retryable
            return True

        # Check for other retryable errors
        retryable_indicators = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "unavailable",
            "retry",
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
        """Process an image for OpenAI-compatible API asynchronously."""
        try:
            if image_path.startswith("data:image/"):
                # Handle data URL
                return {"type": "image_url", "image_url": {"url": image_path}}
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

                # Create data URL for OpenAI API
                data_url = f"data:{mime_type};base64,{image_data}"

                return {"type": "image_url", "image_url": {"url": data_url}}
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return None

    def _extract_usage(self, response) -> dict[str, int]:
        """Extract token usage from OpenAI response."""
        usage = {}

        if hasattr(response, "usage") and response.usage:
            usage["input_tokens"] = getattr(response.usage, "prompt_tokens", 0) or 0
            usage["output_tokens"] = getattr(response.usage, "completion_tokens", 0) or 0
            usage["total_tokens"] = getattr(response.usage, "total_tokens", 0) or 0

        return usage

    async def aclose(self):
        """Async cleanup of OpenAI client and base resources."""
        # Clean up OpenAI client
        if self._async_openai_client and not self._async_openai_client.is_closed:
            try:
                await self._async_openai_client.close()
                logger.debug("Closed async OpenAI client")
            except Exception as e:
                logger.warning(f"Error closing async OpenAI client: {e}")
            finally:
                self._async_openai_client = None

        # Call parent cleanup
        await super().aclose()

    @abstractmethod
    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific model."""
        pass

    @abstractmethod
    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        pass

    @abstractmethod
    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported."""
        pass

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        return False
