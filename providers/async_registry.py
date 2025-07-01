"""Async-aware model provider registry for managing async providers."""

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Optional, Union

from .async_base import AsyncModelProvider
from .base import ModelProvider, ProviderType
from .registry import ModelProviderRegistry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AsyncModelProviderRegistry(ModelProviderRegistry):
    """Async-aware registry for managing both sync and async model providers.

    Extends the base ModelProviderRegistry to support AsyncModelProvider instances
    while maintaining backward compatibility with synchronous providers.
    """

    def __init__(self):
        super().__init__()
        self._async_providers = {}
        self._async_initialized_providers = {}

    @classmethod
    def register_async_provider(
        cls, provider_type: ProviderType, async_provider_class: type[AsyncModelProvider]
    ) -> None:
        """Register a new async provider class.

        Args:
            provider_type: Type of the provider (e.g., ProviderType.GOOGLE)
            async_provider_class: Class that implements AsyncModelProvider interface
        """
        instance = cls()
        instance._async_providers[provider_type] = async_provider_class
        # Also register in the sync registry for compatibility
        instance._providers[provider_type] = async_provider_class

    @classmethod
    async def get_async_provider(
        cls, provider_type: ProviderType, force_new: bool = False
    ) -> Optional[AsyncModelProvider]:
        """Get an initialized async provider instance.

        Args:
            provider_type: Type of provider to get
            force_new: Force creation of new instance instead of using cached

        Returns:
            Initialized AsyncModelProvider instance or None if not available
        """
        instance = cls()

        # Return cached instance if available and not forcing new
        if not force_new and provider_type in instance._async_initialized_providers:
            return instance._async_initialized_providers[provider_type]

        # Check if async provider class is registered
        if provider_type not in instance._async_providers:
            return None

        # Get API key from environment
        api_key = cls._get_api_key_for_provider(provider_type)

        # Get async provider class
        provider_class = instance._async_providers[provider_type]

        # Initialize async provider based on type
        try:
            if provider_type == ProviderType.CUSTOM:
                # Handle custom providers
                custom_url = os.getenv("CUSTOM_API_URL", "")
                if not custom_url:
                    if api_key:  # Key is set but URL is missing
                        logger.warning("CUSTOM_API_KEY set but CUSTOM_API_URL missing – skipping Custom async provider")
                    return None
                api_key = api_key or ""
                provider = provider_class(api_key=api_key, base_url=custom_url)
            else:
                if not api_key:
                    return None
                provider = provider_class(api_key=api_key)

            # Cache the instance
            instance._async_initialized_providers[provider_type] = provider
            return provider

        except Exception as e:
            logger.error(f"Failed to initialize async provider {provider_type}: {e}")
            return None

    @classmethod
    def get_provider(
        cls, provider_type: ProviderType, force_new: bool = False
    ) -> Optional[Union[ModelProvider, AsyncModelProvider]]:
        """Get an initialized provider instance (async or sync).

        This method prefers async providers if available, falling back to sync providers.

        Args:
            provider_type: Type of provider to get
            force_new: Force creation of new instance instead of using cached

        Returns:
            Initialized ModelProvider or AsyncModelProvider instance or None if not available
        """
        instance = cls()

        # First try to get async provider if available
        if provider_type in instance._async_providers:
            try:
                # Use asyncio.run only if we're not already in an async context
                try:
                    asyncio.get_running_loop()
                    # We're in an async context, but this is a sync method
                    # Return the sync provider instead to avoid issues
                    logger.debug(f"In async context, falling back to sync provider for {provider_type}")
                except RuntimeError:
                    # No running loop, safe to use asyncio.run
                    async_provider = asyncio.run(cls.get_async_provider(provider_type, force_new))
                    if async_provider:
                        return async_provider
            except Exception as e:
                logger.debug(f"Failed to get async provider {provider_type}: {e}")

        # Fall back to sync provider using parent method
        return super().get_provider(provider_type, force_new)

    @classmethod
    async def get_async_provider_for_model(cls, model_name: str) -> Optional[AsyncModelProvider]:
        """Get async provider instance for a specific model name.

        Args:
            model_name: Name of the model (e.g., "gemini-2.5-flash", "o3-mini")

        Returns:
            AsyncModelProvider instance that supports this model
        """
        logger.debug(f"get_async_provider_for_model called with model_name='{model_name}'")

        # Define provider priority order
        PROVIDER_PRIORITY_ORDER = [
            ProviderType.GOOGLE,
            ProviderType.OPENAI,
            ProviderType.XAI,
            ProviderType.DIAL,
            ProviderType.CUSTOM,
            ProviderType.OPENROUTER,
        ]

        instance = cls()

        for provider_type in PROVIDER_PRIORITY_ORDER:
            if provider_type in instance._async_providers:
                logger.debug(f"Found async {provider_type} in registry")
                # Get or create async provider instance
                provider = await cls.get_async_provider(provider_type)
                if provider and provider.validate_model_name(model_name):
                    logger.debug(f"Async {provider_type} validates model {model_name}")
                    return provider
                else:
                    logger.debug(f"Async {provider_type} does not validate model {model_name}")

        logger.debug(f"No async provider found for model {model_name}")
        return None

    @classmethod
    async def generate_content_async(
        cls,
        model_name: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ):
        """Generate content using async providers.

        Args:
            model_name: Name of the model to use
            prompt: User prompt to send to the model
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature
            max_output_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        provider = await cls.get_async_provider_for_model(model_name)
        if not provider:
            raise ValueError(f"No async provider available for model: {model_name}")

        return await provider.generate_content_with_semaphore(
            prompt=prompt,
            model_name=model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs,
        )

    @classmethod
    async def batch_generate_content(cls, requests: list[dict], max_concurrent: Optional[int] = None) -> list:
        """Generate content for multiple requests concurrently using async providers.

        Args:
            requests: List of request dictionaries, each containing model_name and other params
            max_concurrent: Maximum concurrent requests (defaults to provider's semaphore limit)

        Returns:
            List of ModelResponse objects in the same order as requests
        """
        # Group requests by provider to optimize connection reuse
        provider_requests = {}
        request_indices = {}

        for i, request in enumerate(requests):
            model_name = request.get("model_name")
            if not model_name:
                raise ValueError(f"Request {i} missing 'model_name' field")

            provider = await cls.get_async_provider_for_model(model_name)
            if not provider:
                raise ValueError(f"No async provider available for model: {model_name}")

            provider_key = provider.get_provider_type()
            if provider_key not in provider_requests:
                provider_requests[provider_key] = []
                request_indices[provider_key] = []

            provider_requests[provider_key].append(request)
            request_indices[provider_key].append(i)

        # Execute requests by provider
        all_results = [None] * len(requests)

        async def process_provider_requests(provider_type, provider_reqs, indices):
            provider = await cls.get_async_provider(provider_type)
            results = await provider.batch_generate_content(provider_reqs, max_concurrent)

            # Place results in correct positions
            for result, original_index in zip(results, indices):
                all_results[original_index] = result

        # Run all provider requests concurrently
        tasks = [
            process_provider_requests(provider_type, reqs, indices)
            for provider_type, reqs, indices in zip(
                provider_requests.keys(), provider_requests.values(), request_indices.values()
            )
        ]

        await asyncio.gather(*tasks)
        return all_results

    @classmethod
    def get_available_async_providers(cls) -> list[ProviderType]:
        """Get list of registered async provider types."""
        instance = cls()
        return list(instance._async_providers.keys())

    @classmethod
    async def cleanup_async_providers(cls) -> None:
        """Clean up all async provider instances."""
        instance = cls()
        cleanup_tasks = []

        for provider in instance._async_initialized_providers.values():
            if hasattr(provider, "aclose"):
                cleanup_tasks.append(provider.aclose())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        instance._async_initialized_providers.clear()
        logger.info(f"Cleaned up {len(cleanup_tasks)} async providers")

    @classmethod
    def clear_async_cache(cls) -> None:
        """Clear cached async provider instances."""
        instance = cls()
        instance._async_initialized_providers.clear()

    @classmethod
    def unregister_async_provider(cls, provider_type: ProviderType) -> None:
        """Unregister an async provider (mainly for testing)."""
        instance = cls()
        instance._async_providers.pop(provider_type, None)
        instance._async_initialized_providers.pop(provider_type, None)

    def get_connection_stats(self) -> dict:
        """Get connection statistics for all async providers."""
        stats = {
            "sync_providers": len(self._initialized_providers),
            "async_providers": len(self._async_initialized_providers),
            "provider_stats": {},
        }

        for provider_type, provider in self._async_initialized_providers.items():
            if hasattr(provider, "get_connection_stats"):
                stats["provider_stats"][provider_type.value] = provider.get_connection_stats()

        return stats
