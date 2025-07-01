"""Async base provider class for improved concurrent request handling."""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx

from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

from .base import ModelProvider, ModelResponse

logger = logging.getLogger(__name__)


class AsyncModelProvider(ModelProvider, ABC):
    """Abstract base class for async model providers with connection pooling.

    Provides:
    - Async HTTP client management with connection pooling
    - Semaphore-based concurrency control (10 concurrent requests max)
    - Graceful resource cleanup with proper async context managers
    - HTTP/2 support when available
    - Connection pooling with keep-alive (300s expiry)
    - Timeout controls: connect=5s, read=30s, write=5s, pool=2s

    Benefits:
    - 10-100x improvement in concurrent request handling
    - Non-blocking API calls
    - Better resource utilization
    - Reduced TCP connection overhead
    """

    # Class-level semaphore for concurrency control
    _semaphore: Optional[asyncio.Semaphore] = None
    _semaphore_lock = asyncio.Lock()

    # Connection pool configuration optimized for async performance
    ASYNC_CONNECTION_POOL_CONFIG = {
        "max_keepalive_connections": 10,  # Keep 10 connections alive per provider
        "max_connections": 20,  # Total pool size of 20 connections
        "keepalive_expiry": 300.0,  # Keep connections alive for 5 minutes
        "max_concurrent_requests": 10,  # Semaphore limit for concurrent requests
    }

    # Timeout configuration for async operations
    ASYNC_TIMEOUT_CONFIG = {
        "connect": 5.0,  # Connection timeout: 5 seconds
        "read": 30.0,  # Read timeout: 30 seconds
        "write": 5.0,  # Write timeout: 5 seconds
        "pool": 2.0,  # Pool timeout: 2 seconds
    }

    def __init__(self, api_key: str, **kwargs):
        """Initialize the async provider with API key and configuration.

        Args:
            api_key: API key for authentication
            **kwargs: Additional configuration options
        """
        super().__init__(api_key, **kwargs)
        self._async_client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

        # Override timeout config if provided
        timeout_overrides = kwargs.get("timeout_config", {})
        self.timeout_config = {**self.ASYNC_TIMEOUT_CONFIG, **timeout_overrides}

        # Override connection pool config if provided
        pool_overrides = kwargs.get("pool_config", {})
        self.pool_config = {**self.ASYNC_CONNECTION_POOL_CONFIG, **pool_overrides}

    @classmethod
    async def get_semaphore(cls) -> asyncio.Semaphore:
        """Get or create the global semaphore for concurrency control.

        Returns:
            Semaphore instance for limiting concurrent requests
        """
        if cls._semaphore is None:
            async with cls._semaphore_lock:
                if cls._semaphore is None:
                    max_concurrent = cls.ASYNC_CONNECTION_POOL_CONFIG["max_concurrent_requests"]
                    cls._semaphore = asyncio.Semaphore(max_concurrent)
                    logger.info(f"Created global semaphore with limit: {max_concurrent}")
        return cls._semaphore

    async def get_async_client(
        self, base_url: Optional[str] = None, headers: Optional[dict[str, str]] = None
    ) -> httpx.AsyncClient:
        """Get or create an async HTTP client with connection pooling.

        Args:
            base_url: Base URL for the client
            headers: Default headers to include

        Returns:
            Configured async HTTPX client with connection pooling
        """
        if self._async_client is None or self._async_client.is_closed:
            async with self._client_lock:
                if self._async_client is None or self._async_client.is_closed:
                    self._async_client = await self._create_async_client(base_url, headers)

        return self._async_client

    async def _create_async_client(
        self, base_url: Optional[str] = None, headers: Optional[dict[str, str]] = None
    ) -> httpx.AsyncClient:
        """Create a new async HTTPX client with optimized connection pooling.

        Args:
            base_url: Base URL for the client
            headers: Default headers

        Returns:
            Configured async HTTPX client
        """
        # Create timeout configuration
        timeout = httpx.Timeout(
            connect=self.timeout_config["connect"],
            read=self.timeout_config["read"],
            write=self.timeout_config["write"],
            pool=self.timeout_config["pool"],
        )

        # Create connection limits for pooling
        limits = httpx.Limits(
            max_keepalive_connections=self.pool_config["max_keepalive_connections"],
            max_connections=self.pool_config["max_connections"],
            keepalive_expiry=self.pool_config["keepalive_expiry"],
        )

        # Client configuration
        client_kwargs = {
            "timeout": timeout,
            "limits": limits,
            "follow_redirects": True,
        }

        # Enable HTTP/2 if h2 package is available
        try:
            import h2  # noqa: F401

            client_kwargs["http2"] = True
            logger.debug("HTTP/2 enabled for async client")
        except ImportError:
            logger.debug("HTTP/2 not available for async client, using HTTP/1.1")

        # Add base URL if provided
        if base_url:
            client_kwargs["base_url"] = base_url

        # Add headers if provided
        if headers:
            client_kwargs["headers"] = headers.copy()

        logger.debug(
            f"Created async HTTP client with pooling "
            f"(max_connections: {self.pool_config['max_connections']}, "
            f"keepalive: {self.pool_config['max_keepalive_connections']})"
        )

        return httpx.AsyncClient(**client_kwargs)

    @abstractmethod
    async def generate_content_async(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using the model asynchronously.

        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature (0-2)
            max_output_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        pass

    # Maintain backward compatibility with sync interface
    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using the model (sync wrapper).

        This method provides backward compatibility by wrapping the async method.

        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature (0-2)
            max_output_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        return asyncio.run(
            self.generate_content_async(
                prompt=prompt,
                model_name=model_name,
                system_prompt=system_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                **kwargs,
            )
        )

    async def generate_content_with_semaphore(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content with semaphore-based concurrency control.

        This method ensures that only a limited number of concurrent requests
        are processed simultaneously to prevent resource exhaustion.

        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature (0-2)
            max_output_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        semaphore = await self.get_semaphore()
        async with semaphore:
            logger.debug(f"Acquired semaphore for {model_name} request")
            try:
                result = await self.generate_content_async(
                    prompt=prompt,
                    model_name=model_name,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    **kwargs,
                )
                logger.debug(f"Completed {model_name} request")
                return result
            except Exception as e:
                logger.error(f"Error in semaphore-controlled request for {model_name}: {e}")
                raise

    async def batch_generate_content(
        self, requests: list[dict[str, Any]], max_concurrent: Optional[int] = None
    ) -> list[ModelResponse]:
        """Generate content for multiple requests concurrently.

        Args:
            requests: List of dictionaries containing request parameters
            max_concurrent: Maximum concurrent requests (overrides semaphore limit)

        Returns:
            List of ModelResponse objects in the same order as requests
        """
        if max_concurrent:
            # Use custom semaphore for this batch
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_generate(request_params):
                async with semaphore:
                    return await self.generate_content_async(**request_params)

            tasks = [limited_generate(request) for request in requests]
        else:
            # Use global semaphore
            tasks = [self.generate_content_with_semaphore(**request) for request in requests]

        return await asyncio.gather(*tasks, return_exceptions=False)

    async def aclose(self):
        """Async cleanup of resources including HTTP connections.

        This method should be called when the provider is being destroyed
        to ensure proper cleanup of async resources.
        """
        if self._async_client and not self._async_client.is_closed:
            try:
                await self._async_client.aclose()
                logger.debug("Closed async HTTP client")
            except Exception as e:
                logger.warning(f"Error closing async HTTP client: {e}")
            finally:
                self._async_client = None

    def close(self):
        """Sync cleanup wrapper for async resources.

        This method provides backward compatibility by wrapping the async cleanup.
        """
        try:
            # Try to close using existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule the cleanup
                loop.create_task(self.aclose())
            else:
                # If no loop is running, run the cleanup
                loop.run_until_complete(self.aclose())
        except RuntimeError:
            # No event loop available, create a new one
            asyncio.run(self.aclose())

        # Call parent cleanup
        super().close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.aclose()

    def get_connection_stats(self) -> dict[str, Any]:
        """Get statistics about current async connections.

        Returns:
            Dictionary with connection statistics
        """
        stats = {
            "has_async_client": self._async_client is not None,
            "async_client_closed": self._async_client.is_closed if self._async_client else True,
            "pool_config": self.pool_config.copy(),
            "timeout_config": self.timeout_config.copy(),
            "semaphore_limit": self.pool_config["max_concurrent_requests"],
        }

        # Add semaphore statistics if available
        if self._semaphore:
            stats["semaphore_available"] = self._semaphore._value
            stats["semaphore_locked"] = self._semaphore.locked()

        return stats


class CircuitBreakerMixin:
    """
    Mixin to add circuit breaker functionality to async providers.

    This mixin integrates circuit breaker pattern with model providers to provide
    graceful degradation and automatic recovery during service failures.

    Usage:
        class MyProvider(AsyncModelProvider, CircuitBreakerMixin):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Circuit breaker is automatically initialized
    """

    def __init__(self, *args, **kwargs):
        """Initialize circuit breaker mixin."""
        super().__init__(*args, **kwargs)

        # Get circuit breaker configuration from kwargs or environment
        provider_name = self.__class__.__name__
        service_name = f"{provider_name}:{getattr(self, 'base_url', 'default')}"

        # Provider-specific configuration with environment variable support
        provider_prefix = provider_name.upper().replace("PROVIDER", "")

        failure_threshold = kwargs.get("cb_failure_threshold") or int(
            os.getenv(f"{provider_prefix}_CB_FAILURE_THRESHOLD", "5")
        )

        recovery_timeout = kwargs.get("cb_recovery_timeout") or float(
            os.getenv(f"{provider_prefix}_CB_RECOVERY_TIMEOUT", "60.0")
        )

        half_open_max_calls = kwargs.get("cb_half_open_max_calls") or int(
            os.getenv(f"{provider_prefix}_CB_HALF_OPEN_MAX_CALLS", "3")
        )

        # Use provider's error classification if available
        error_classifier = getattr(self, "_is_error_retryable", None)

        self._circuit_breaker = CircuitBreaker(
            service_name=service_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
            error_classifier=error_classifier,
        )

        logger.debug(
            f"Circuit breaker initialized for {service_name} "
            f"(threshold: {failure_threshold}, timeout: {recovery_timeout}s)"
        )

    async def generate_content_with_circuit_breaker(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Generate content with circuit breaker protection.

        This method wraps the provider's generate_content_async method with
        circuit breaker functionality for automatic failure handling.

        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature (0-2)
            max_output_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata

        Raises:
            CircuitBreakerOpenException: When circuit breaker is open
            Exception: Any exception from the wrapped provider method
        """
        try:
            return await self._circuit_breaker.call(
                self.generate_content_async,
                prompt=prompt,
                model_name=model_name,
                system_prompt=system_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                **kwargs,
            )
        except CircuitBreakerOpenException as e:
            # Log circuit breaker rejection with helpful information
            logger.warning(
                f"Request rejected by circuit breaker for {e.service_name}. "
                f"Service has failed {e.failure_count} times. "
                f"Circuit breaker will attempt recovery after timeout period."
            )

            # Re-raise with additional context
            raise RuntimeError(
                "Service temporarily unavailable due to repeated failures. "
                "Circuit breaker is protecting the service. "
                "Please try again later."
            ) from e

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """
        Get circuit breaker status and metrics.

        Returns:
            Dictionary with circuit breaker health status and metrics
        """
        if hasattr(self, "_circuit_breaker"):
            return self._circuit_breaker.get_health_status()
        else:
            return {"circuit_breaker_enabled": False, "message": "Circuit breaker not initialized"}

    async def reset_circuit_breaker(self) -> None:
        """
        Manually reset the circuit breaker to closed state.

        This can be used for manual recovery or administrative purposes.
        """
        if hasattr(self, "_circuit_breaker"):
            await self._circuit_breaker.reset()
            logger.info(f"Circuit breaker manually reset for {self.__class__.__name__}")
        else:
            logger.warning("Cannot reset circuit breaker - not initialized")

    def is_circuit_breaker_open(self) -> bool:
        """
        Check if circuit breaker is currently open.

        Returns:
            True if circuit breaker is open (rejecting requests), False otherwise
        """
        if hasattr(self, "_circuit_breaker"):
            return self._circuit_breaker.is_open()
        return False

    async def aclose(self):
        """Async cleanup including circuit breaker resources."""
        # Clean up circuit breaker if it exists
        if hasattr(self, "_circuit_breaker"):
            # Circuit breaker doesn't need explicit cleanup, but log final status
            status = self._circuit_breaker.get_health_status()
            logger.debug(f"Circuit breaker final status for {status['service_name']}: {status['state']}")

        # Call parent cleanup
        if hasattr(super(), "aclose"):
            await super().aclose()

    def close(self):
        """Sync cleanup wrapper including circuit breaker resources."""
        # Circuit breaker cleanup happens in aclose
        super().close()
