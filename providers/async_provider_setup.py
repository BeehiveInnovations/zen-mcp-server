"""Setup and registration for async providers alongside existing sync providers."""

import logging
import os

from .async_gemini import AsyncGeminiModelProvider
from .async_openai_provider import AsyncOpenAIModelProvider
from .async_registry import AsyncModelProviderRegistry
from .base import ProviderType

logger = logging.getLogger(__name__)


def register_async_providers() -> list[str]:
    """Register async providers alongside existing sync providers.

    This function registers async versions of available providers while maintaining
    backward compatibility with the existing sync provider system.

    Returns:
        List of registered async provider names
    """
    registered_async_providers = []

    # Check and register async Gemini provider
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        try:
            AsyncModelProviderRegistry.register_async_provider(ProviderType.GOOGLE, AsyncGeminiModelProvider)
            registered_async_providers.append("Async Gemini")
            logger.info("Async Gemini provider registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register async Gemini provider: {e}")

    # Check and register async OpenAI provider
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key != "your_openai_api_key_here":
        try:
            AsyncModelProviderRegistry.register_async_provider(ProviderType.OPENAI, AsyncOpenAIModelProvider)
            registered_async_providers.append("Async OpenAI")
            logger.info("Async OpenAI provider registered successfully")
        except Exception as e:
            logger.warning(f"Failed to register async OpenAI provider: {e}")

    # TODO: Add other async providers as they are implemented
    # - AsyncXAIModelProvider
    # - AsyncOpenRouterProvider
    # - AsyncCustomProvider
    # - AsyncDIALModelProvider

    if registered_async_providers:
        logger.info(f"Registered async providers: {', '.join(registered_async_providers)}")
    else:
        logger.debug("No async providers registered (no valid API keys found)")

    return registered_async_providers


def get_async_provider_stats() -> dict:
    """Get statistics about async providers.

    Returns:
        Dictionary with async provider statistics
    """
    try:
        registry = AsyncModelProviderRegistry()
        stats = registry.get_connection_stats()

        # Add available async providers
        stats["available_async_providers"] = AsyncModelProviderRegistry.get_available_async_providers()

        return stats
    except Exception as e:
        logger.error(f"Failed to get async provider stats: {e}")
        return {"error": str(e)}


async def cleanup_async_providers() -> None:
    """Clean up all async providers and their resources.

    This should be called during server shutdown to ensure proper cleanup
    of async resources like HTTP connections and semaphores.
    """
    try:
        await AsyncModelProviderRegistry.cleanup_async_providers()
        logger.info("Async provider cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during async provider cleanup: {e}")


def is_async_provider_available(provider_type: ProviderType) -> bool:
    """Check if an async provider is available for the given provider type.

    Args:
        provider_type: The provider type to check

    Returns:
        True if async provider is available, False otherwise
    """
    try:
        available_providers = AsyncModelProviderRegistry.get_available_async_providers()
        return provider_type in available_providers
    except Exception as e:
        logger.debug(f"Error checking async provider availability: {e}")
        return False


async def test_async_provider_connectivity() -> dict[str, bool]:
    """Test connectivity of all registered async providers.

    Returns:
        Dictionary mapping provider names to connectivity status
    """
    connectivity_results = {}

    try:
        available_providers = AsyncModelProviderRegistry.get_available_async_providers()

        for provider_type in available_providers:
            try:
                provider = await AsyncModelProviderRegistry.get_async_provider(provider_type)
                if provider:
                    # Test with a simple token counting operation
                    provider.count_tokens("test", "test-model")
                    connectivity_results[provider_type.value] = True
                    logger.debug(f"Async {provider_type.value} provider connectivity: OK")
                else:
                    connectivity_results[provider_type.value] = False
                    logger.debug(f"Async {provider_type.value} provider: Not initialized")
            except Exception as e:
                connectivity_results[provider_type.value] = False
                logger.debug(f"Async {provider_type.value} provider connectivity failed: {e}")

    except Exception as e:
        logger.error(f"Error testing async provider connectivity: {e}")

    return connectivity_results


def configure_async_provider_logging() -> None:
    """Configure logging for async providers with appropriate levels."""
    # Set async provider loggers to appropriate levels
    async_loggers = [
        "providers.async_base",
        "providers.async_gemini",
        "providers.async_openai_provider",
        "providers.async_openai_compatible",
        "providers.async_registry",
    ]

    # Use DEBUG level for async providers to help with debugging connection issues
    log_level = os.getenv("ASYNC_PROVIDER_LOG_LEVEL", "DEBUG").upper()

    for logger_name in async_loggers:
        async_logger = logging.getLogger(logger_name)
        async_logger.setLevel(getattr(logging, log_level, logging.DEBUG))

    logger.debug(f"Configured async provider logging at {log_level} level")


# Export key functions for easy importing
__all__ = [
    "register_async_providers",
    "get_async_provider_stats",
    "cleanup_async_providers",
    "is_async_provider_available",
    "test_async_provider_connectivity",
    "configure_async_provider_logging",
]
