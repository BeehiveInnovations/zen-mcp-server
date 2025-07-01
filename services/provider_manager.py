"""
Provider Manager Service for handling provider resolution and validation.

This service extracts provider management logic from the monolithic request handler
to provide focused, testable provider resolution with caching capabilities.
"""

import logging
from typing import Any, Optional

from providers.registry import ModelProviderRegistry
from utils.model_context import ModelContext

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Handles provider resolution, validation, and model context creation.

    This service encapsulates the complex logic of resolving models to providers,
    validating model availability, and creating model contexts with proper caching.
    """

    def __init__(self):
        """Initialize the provider manager with an empty cache."""
        self._provider_cache: dict[str, Any] = {}
        self._context_cache: dict[str, ModelContext] = {}

    def parse_model_option(self, model_string: str) -> tuple[str, Optional[str]]:
        """
        Parse model:option format into model name and option.

        Handles different formats:
        - OpenRouter models: preserve :free, :beta, :preview suffixes as part of model name
        - Ollama/Custom models: split on : to extract tags like :latest
        - Consensus stance: extract options like :for, :against

        Args:
            model_string: String that may contain "model:option" format

        Returns:
            tuple: (model_name, option) where option may be None
        """
        if ":" in model_string and not model_string.startswith("http"):  # Avoid parsing URLs
            # Check if this looks like an OpenRouter model (contains /)
            if "/" in model_string and model_string.count(":") == 1:
                # Could be openai/gpt-4:something - check what comes after colon
                parts = model_string.split(":", 1)
                suffix = parts[1].strip().lower()

                # Known OpenRouter suffixes that should be preserved as part of model name
                openrouter_suffixes = ["free", "beta", "preview", "extended", "nitro"]
                if suffix in openrouter_suffixes:
                    return model_string.strip(), None  # Keep as full model name but strip whitespace
                else:
                    return parts[0].strip(), parts[1].strip()
            else:
                # Standard model:option format
                parts = model_string.split(":", 1)
                return parts[0].strip(), parts[1].strip()

        return model_string.strip(), None

    async def resolve_model_auto(self, tool_name: str, tool) -> str:
        """
        Resolve 'auto' model to specific model based on tool category with caching.

        Args:
            tool_name: Name of the tool requesting model resolution
            tool: Tool instance for getting model category

        Returns:
            Resolved model name
        """
        tool_category = tool.get_model_category()

        # Try enhanced caching first
        try:
            from utils.model_validation_cache import get_model_validation_cache

            cache = get_model_validation_cache()
            cached_model = cache.get_model_resolution(
                tool_name=tool_name, tool_category=tool_category.value, auto_mode=True
            )

            if cached_model is not None:
                logger.debug(f"Auto mode cache hit: {tool_name} -> {cached_model}")
                return cached_model

        except ImportError:
            logger.debug("Enhanced model resolution cache not available")

        # Resolve model
        resolved_model = ModelProviderRegistry.get_preferred_fallback_model(tool_category)

        # Cache the result
        try:
            from utils.model_validation_cache import get_model_validation_cache

            cache = get_model_validation_cache()
            cache.cache_model_resolution(
                tool_name=tool_name, tool_category=tool_category.value, resolved_model=resolved_model, auto_mode=True
            )
        except ImportError:
            pass  # No caching available

        logger.info(f"Auto mode resolved to {resolved_model} for {tool_name} (category: {tool_category.value})")
        return resolved_model

    async def validate_model_availability(self, model_name: str, tool_name: str, tool) -> Optional[dict[str, Any]]:
        """
        Validate that a model is available with current API keys using enhanced caching.

        Args:
            model_name: Name of the model to validate
            tool_name: Name of the tool requesting validation
            tool: Tool instance for getting model category

        Returns:
            None if model is valid, error dict if invalid
        """
        # Try enhanced caching first
        try:
            from utils.model_validation_cache import get_model_validation_cache

            cache = get_model_validation_cache()
            cached_result = cache.get_model_availability(model_name, tool_name)

            if cached_result is not None:
                if cached_result["is_available"]:
                    return None
                else:
                    # Return cached error
                    return {
                        "status": "error",
                        "content": cached_result.get("error_message", f"Model '{model_name}' is not available"),
                        "content_type": "text",
                        "metadata": {"tool_name": tool_name, "requested_model": model_name},
                    }
        except ImportError:
            logger.debug("Enhanced model validation cache not available, using fallback")

            # Fallback to existing cache
            cache_key = f"validation_{model_name}"
            if cache_key in self._provider_cache:
                return self._provider_cache[cache_key]

        # Perform actual validation
        provider = ModelProviderRegistry.get_provider_for_model(model_name)
        if not provider:
            # Get list of available models for error message
            available_models = list(ModelProviderRegistry.get_available_models(respect_restrictions=True).keys())
            tool_category = tool.get_model_category()
            suggested_model = ModelProviderRegistry.get_preferred_fallback_model(tool_category)

            error_message = (
                f"Model '{model_name}' is not available with current API keys. "
                f"Available models: {', '.join(available_models)}. "
                f"Suggested model for {tool_name}: '{suggested_model}' "
                f"(category: {tool_category.value})"
            )

            error_result = {
                "status": "error",
                "content": error_message,
                "content_type": "text",
                "metadata": {"tool_name": tool_name, "requested_model": model_name},
            }

            # Cache the error result in both caches
            try:
                from utils.model_validation_cache import get_model_validation_cache

                cache = get_model_validation_cache()
                cache.cache_model_availability(
                    model_name=model_name, tool_name=tool_name, is_available=False, error_message=error_message
                )
            except ImportError:
                # Fallback to existing cache
                cache_key = f"validation_{model_name}"
                self._provider_cache[cache_key] = error_result

            return error_result

        # Cache success (no error) in both caches
        try:
            from utils.model_validation_cache import get_model_validation_cache

            cache = get_model_validation_cache()
            cache.cache_model_availability(
                model_name=model_name, tool_name=tool_name, is_available=True, provider_name=provider.__class__.__name__
            )
        except ImportError:
            # Fallback to existing cache
            cache_key = f"validation_{model_name}"
            self._provider_cache[cache_key] = None

        return None

    async def create_model_context(self, model_name: str, model_option: Optional[str] = None) -> ModelContext:
        """
        Create a model context with resolved model and option.

        Args:
            model_name: Name of the model
            model_option: Optional model option/tag

        Returns:
            ModelContext instance
        """
        # Check cache first
        cache_key = f"context_{model_name}_{model_option}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        # Create new context
        model_context = ModelContext(model_name, model_option)

        # Cache the context
        self._context_cache[cache_key] = model_context

        logger.debug(
            f"Model context created for {model_name} with {model_context.capabilities.context_window} token capacity"
        )
        if model_option:
            logger.debug(f"Model option stored in context: '{model_option}'")

        return model_context

    async def get_provider_for_model(self, model_name: str):
        """
        Get provider for a specific model with caching.

        Args:
            model_name: Name of the model

        Returns:
            Provider instance or None if not found
        """
        cache_key = f"provider_{model_name}"
        if cache_key not in self._provider_cache:
            provider = ModelProviderRegistry.get_provider_for_model(model_name)
            self._provider_cache[cache_key] = provider

        return self._provider_cache[cache_key]

    def clear_cache(self):
        """Clear all cached data."""
        self._provider_cache.clear()
        self._context_cache.clear()
        logger.debug("Provider manager cache cleared")
