"""Base class for OpenAI-compatible API providers."""

import ipaddress
import logging
import os
from abc import abstractmethod
from typing import Optional
from urllib.parse import urlparse

from openai import OpenAI

from .base import (
    ModelCapabilities,
    ModelProvider,
    ModelResponse,
    ProviderType,
)


class OpenAICompatibleProvider(ModelProvider):
    """Base class for any provider using an OpenAI-compatible API.

    This includes:
    - Direct OpenAI API
    - OpenRouter
    - Any other OpenAI-compatible endpoint
    """

    DEFAULT_HEADERS = {}
    FRIENDLY_NAME = "OpenAI Compatible"

    def __init__(self, api_key: str, base_url: str = None, **kwargs):
        """Initialize the provider with API key and optional base URL.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the API endpoint
            **kwargs: Additional configuration options including timeout
        """
        super().__init__(api_key, **kwargs)
        self._client = None
        self.base_url = base_url
        self.organization = kwargs.get("organization")
        self.allowed_models = self._parse_allowed_models()

        # Configure timeouts - especially important for custom/local endpoints
        self.timeout_config = self._configure_timeouts(**kwargs)

        # Validate base URL for security
        if self.base_url:
            self._validate_base_url()

        # Warn if using external URL without authentication
        if self.base_url and not self._is_localhost_url() and not api_key:
            logging.warning(
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
                logging.info(f"Configured allowed models for {self.FRIENDLY_NAME}: {sorted(models)}")
                return models

        # Log info if no allow-list configured for proxy providers
        if self.get_provider_type() not in [ProviderType.GOOGLE, ProviderType.OPENAI]:
            logging.info(
                f"Model allow-list not configured for {self.FRIENDLY_NAME} - all models permitted. "
                f"To restrict access, set {env_var} with comma-separated model names."
            )

        return None

    def _configure_timeouts(self, **kwargs):
        """Configure timeout settings based on provider type and custom settings.

        Custom URLs and local models often need longer timeouts due to:
        - Network latency on local networks
        - Extended thinking models taking longer to respond
        - Local inference being slower than cloud APIs

        Returns:
            httpx.Timeout object with appropriate timeout settings
        """
        import httpx

        # Default timeouts - more generous for custom/local endpoints
        default_connect = 30.0  # 30 seconds for connection (vs OpenAI's 5s)
        default_read = 600.0  # 10 minutes for reading (same as OpenAI default)
        default_write = 600.0  # 10 minutes for writing
        default_pool = 600.0  # 10 minutes for pool

        # For custom/local URLs, use even longer timeouts
        if self.base_url and self._is_localhost_url():
            default_connect = 60.0  # 1 minute for local connections
            default_read = 1800.0  # 30 minutes for local models (extended thinking)
            default_write = 1800.0  # 30 minutes for local models
            default_pool = 1800.0  # 30 minutes for local models
            logging.info(f"Using extended timeouts for local endpoint: {self.base_url}")
        elif self.base_url:
            default_connect = 45.0  # 45 seconds for custom remote endpoints
            default_read = 900.0  # 15 minutes for custom remote endpoints
            default_write = 900.0  # 15 minutes for custom remote endpoints
            default_pool = 900.0  # 15 minutes for custom remote endpoints
            logging.info(f"Using extended timeouts for custom endpoint: {self.base_url}")

        # Allow override via kwargs or environment variables in future, for now...
        connect_timeout = kwargs.get("connect_timeout", float(os.getenv("CUSTOM_CONNECT_TIMEOUT", default_connect)))
        read_timeout = kwargs.get("read_timeout", float(os.getenv("CUSTOM_READ_TIMEOUT", default_read)))
        write_timeout = kwargs.get("write_timeout", float(os.getenv("CUSTOM_WRITE_TIMEOUT", default_write)))
        pool_timeout = kwargs.get("pool_timeout", float(os.getenv("CUSTOM_POOL_TIMEOUT", default_pool)))

        timeout = httpx.Timeout(connect=connect_timeout, read=read_timeout, write=write_timeout, pool=pool_timeout)

        logging.debug(
            f"Configured timeouts - Connect: {connect_timeout}s, Read: {read_timeout}s, "
            f"Write: {write_timeout}s, Pool: {pool_timeout}s"
        )

        return timeout

    def _is_localhost_url(self) -> bool:
        """Check if the base URL points to localhost or local network.

        Returns:
            True if URL is localhost or local network, False otherwise
        """
        if not self.base_url:
            return False

        try:
            parsed = urlparse(self.base_url)
            hostname = parsed.hostname

            # Check for common localhost patterns
            if hostname in ["localhost", "127.0.0.1", "::1"]:
                return True

            # Check for Docker internal hostnames (like host.docker.internal)
            if hostname and ("docker.internal" in hostname or "host.docker.internal" in hostname):
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
        """Validate base URL for security (SSRF protection).

        Raises:
            ValueError: If URL is invalid or potentially unsafe
        """
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

    @property
    def client(self):
        """Lazy initialization of OpenAI client with security checks and timeout configuration."""
        if self._client is None:
            client_kwargs = {
                "api_key": self.api_key,
            }

            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            if self.organization:
                client_kwargs["organization"] = self.organization

            # Add default headers if any
            if self.DEFAULT_HEADERS:
                client_kwargs["default_headers"] = self.DEFAULT_HEADERS.copy()

            # Add configured timeout settings
            if hasattr(self, "timeout_config") and self.timeout_config:
                client_kwargs["timeout"] = self.timeout_config
                logging.debug(f"OpenAI client initialized with custom timeout: {self.timeout_config}")

            self._client = OpenAI(**client_kwargs)

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
        """Generate content using the OpenAI-compatible API.

        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature
            max_output_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        # Validate model name against allow-list
        if not self.validate_model_name(model_name):
            raise ValueError(
                f"Model '{model_name}' not in allowed models list. " f"Allowed models: {self.allowed_models}"
            )

        # Validate parameters
        self.validate_parameters(model_name, temperature)

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Prepare completion parameters
        completion_params = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }

        # Add max tokens if specified
        if max_output_tokens:
            completion_params["max_tokens"] = max_output_tokens

        # Add any additional OpenAI-specific parameters
        for key, value in kwargs.items():
            if key in ["top_p", "frequency_penalty", "presence_penalty", "seed", "stop", "stream"]:
                completion_params[key] = value

        try:
            # Generate completion
            response = self.client.chat.completions.create(**completion_params)

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
                    "model": response.model,  # Actual model used
                    "id": response.id,
                    "created": response.created,
                },
            )

        except Exception as e:
            # Log error and re-raise with more context
            error_msg = f"{self.FRIENDLY_NAME} API error for model {model_name}: {str(e)}"
            logging.error(error_msg)
            raise RuntimeError(error_msg) from e

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for the given text.

        Uses a layered approach:
        1. Try provider-specific token counting endpoint
        2. Try tiktoken for known model families
        3. Fall back to character-based estimation

        Args:
            text: Text to count tokens for
            model_name: Model name for tokenizer selection

        Returns:
            Estimated token count
        """
        # 1. Check if provider has a remote token counting endpoint
        if hasattr(self, "count_tokens_remote"):
            try:
                return self.count_tokens_remote(text, model_name)
            except Exception as e:
                logging.debug(f"Remote token counting failed: {e}")

        # 2. Try tiktoken for known models
        try:
            import tiktoken

            # Try to get encoding for the specific model
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
            logging.debug(f"Tiktoken not available or failed: {e}")

        # 3. Fall back to character-based estimation
        logging.warning(
            f"No specific tokenizer available for '{model_name}'. "
            "Using character-based estimation (~4 chars per token)."
        )
        return len(text) // 4

    def validate_parameters(self, model_name: str, temperature: float, **kwargs) -> None:
        """Validate model parameters.

        For proxy providers, this may use generic capabilities.

        Args:
            model_name: Model to validate for
            temperature: Temperature to validate
            **kwargs: Additional parameters to validate
        """
        try:
            capabilities = self.get_capabilities(model_name)

            # Check if we're using generic capabilities
            if hasattr(capabilities, "_is_generic"):
                logging.debug(
                    f"Using generic parameter validation for {model_name}. " "Actual model constraints may differ."
                )

            # Validate temperature using parent class method
            super().validate_parameters(model_name, temperature, **kwargs)

        except Exception as e:
            # For proxy providers, we might not have accurate capabilities
            # Log warning but don't fail
            logging.warning(f"Parameter validation limited for {model_name}: {e}")

    def _extract_usage(self, response) -> dict[str, int]:
        """Extract token usage from OpenAI response.

        Args:
            response: OpenAI API response object

        Returns:
            Dictionary with usage statistics
        """
        usage = {}

        if hasattr(response, "usage") and response.usage:
            usage["input_tokens"] = getattr(response.usage, "prompt_tokens", 0)
            usage["output_tokens"] = getattr(response.usage, "completion_tokens", 0)
            usage["total_tokens"] = getattr(response.usage, "total_tokens", 0)

        return usage

    @abstractmethod
    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific model.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def get_provider_type(self) -> ProviderType:
        """Get the provider type.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported.

        Must be implemented by subclasses.
        """
        pass

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode.

        Default is False for OpenAI-compatible providers.
        """
        return False
