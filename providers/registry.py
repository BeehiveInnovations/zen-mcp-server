"""Model provider registry for managing available providers."""

import os
from typing import Optional

from .base import ModelProvider, ProviderType


class ModelProviderRegistry:
    """Registry for managing model providers."""

    _instance = None
    _providers: dict[ProviderType, type[ModelProvider]] = {}
    _initialized_providers: dict[ProviderType, ModelProvider] = {}

    def __new__(cls):
        """Singleton pattern for registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_provider(cls, provider_type: ProviderType, provider_class: type[ModelProvider]) -> None:
        """Register a new provider class.

        Args:
            provider_type: Type of the provider (e.g., ProviderType.GOOGLE)
            provider_class: Class that implements ModelProvider interface
        """
        cls._providers[provider_type] = provider_class

    @classmethod
    def get_provider(cls, provider_type: ProviderType, force_new: bool = False) -> Optional[ModelProvider]:
        """Get an initialized provider instance.

        Args:
            provider_type: Type of provider to get
            force_new: Force creation of new instance instead of using cached

        Returns:
            Initialized ModelProvider instance or None if not available
        """
        # Return cached instance if available and not forcing new
        if not force_new and provider_type in cls._initialized_providers:
            return cls._initialized_providers[provider_type]

        # Check if provider class is registered
        if provider_type not in cls._providers:
            return None

        # Get API key from environment
        api_key = cls._get_api_key_for_provider(provider_type)
        if not api_key:
            return None

        # Initialize provider
        provider_class = cls._providers[provider_type]
        provider = provider_class(api_key=api_key)

        # Cache the instance
        cls._initialized_providers[provider_type] = provider

        return provider

    @classmethod
    def get_provider_for_model(cls, model_name: str) -> Optional[ModelProvider]:
        """Get provider instance for a specific model name.

        Args:
            model_name: Name of the model (e.g., "gemini-2.5-flash-preview-05-20", "o3-mini")

        Returns:
            ModelProvider instance that supports this model
        """
        # Check each registered provider
        for provider_type, _provider_class in cls._providers.items():
            # Get or create provider instance
            provider = cls.get_provider(provider_type)
            if provider and provider.validate_model_name(model_name):
                return provider

        return None

    @classmethod
    def get_available_providers(cls) -> list[ProviderType]:
        """Get list of registered provider types."""
        return list(cls._providers.keys())

    @classmethod
    def get_available_models(cls) -> dict[str, ProviderType]:
        """Get mapping of all available models to their providers.

        Returns:
            Dict mapping model names to provider types
        """
        models = {}

        for provider_type in cls._providers:
            provider = cls.get_provider(provider_type)
            if provider:
                # This assumes providers have a method to list supported models
                # We'll need to add this to the interface
                pass

        return models

    @classmethod
    def _get_api_key_for_provider(cls, provider_type: ProviderType) -> Optional[str]:
        """Get API key for a provider from environment variables.

        Args:
            provider_type: Provider type to get API key for

        Returns:
            API key string or None if not found
        """
        key_mapping = {
            ProviderType.GOOGLE: "GEMINI_API_KEY",
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.OPENROUTER: "OPENROUTER_API_KEY",
        }

        env_var = key_mapping.get(provider_type)
        if not env_var:
            return None

        return os.getenv(env_var)

    @classmethod
    def get_preferred_fallback_model(cls) -> str:
        """Get the preferred fallback model based on available API keys.

        This method checks which providers have valid API keys and returns
        a sensible default model for auto mode fallback situations.

        Priority order:
        1. OpenAI o3-mini (balanced performance/cost) if OpenAI API key available
        2. Gemini 2.0 Flash (fast and efficient) if Gemini API key available
        3. OpenAI o3 (high performance) if OpenAI API key available
        4. Gemini 2.5 Pro (deep reasoning) if Gemini API key available
        5. Fallback to gemini-2.5-flash-preview-05-20 (most common case)

        Returns:
            Model name string for fallback use
        """
        # Check provider availability by trying to get instances
        openai_available = cls.get_provider(ProviderType.OPENAI) is not None
        gemini_available = cls.get_provider(ProviderType.GOOGLE) is not None

        # Priority order: prefer balanced models first, then high-performance
        if openai_available:
            return "o3-mini"  # Balanced performance/cost
        elif gemini_available:
            return "gemini-2.5-flash-preview-05-20"  # Fast and efficient
        else:
            # No API keys available - return a reasonable default
            # This maintains backward compatibility for tests
            return "gemini-2.5-flash-preview-05-20"

    @classmethod
    def get_available_providers_with_keys(cls) -> list[ProviderType]:
        """Get list of provider types that have valid API keys.

        Returns:
            List of ProviderType values for providers with valid API keys
        """
        available = []
        for provider_type in cls._providers:
            if cls.get_provider(provider_type) is not None:
                available.append(provider_type)
        return available

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached provider instances."""
        cls._initialized_providers.clear()

    @classmethod
    def unregister_provider(cls, provider_type: ProviderType) -> None:
        """Unregister a provider (mainly for testing)."""
        cls._providers.pop(provider_type, None)
        cls._initialized_providers.pop(provider_type, None)
