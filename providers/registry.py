"""Model provider registry for managing available providers."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

from .base import ModelProvider, ProviderType

if TYPE_CHECKING:
    from tools.models import ToolModelCategory


class ModelProviderRegistry:
    """Registry for managing model providers."""

    _instance = None
    _providers: dict[ProviderType, list[type[ModelProvider]]]
    _initialized_providers: dict[ProviderType, list[ModelProvider | None]]

    # Provider priority order for model selection
    # Native APIs first, then custom endpoints, then catch-all providers
    PROVIDER_PRIORITY_ORDER = [
        ProviderType.GOOGLE,  # Direct Gemini access
        ProviderType.OPENAI,  # Direct OpenAI access
        ProviderType.XAI,  # Direct X.AI GROK access
        ProviderType.DIAL,  # DIAL unified API access
        ProviderType.CUSTOM,  # Local/self-hosted models
        ProviderType.OPENROUTER,  # Catch-all for cloud models
    ]

    def __new__(cls):
        """Singleton pattern for registry."""
        if cls._instance is None:
            logging.debug("REGISTRY: Creating new registry instance")
            cls._instance = super().__new__(cls)
            # Initialize instance dictionaries on first creation
            # Map ProviderType -> list of provider classes
            cls._instance._providers = {}
            # Map ProviderType -> list of initialized provider instances (aligned by index)
            cls._instance._initialized_providers = {}
            logging.debug(f"REGISTRY: Created instance {cls._instance}")
        return cls._instance

    @classmethod
    def register_provider(
        cls,
        provider_type: ProviderType,
        provider_class: type[ModelProvider],
        append: bool = False,
    ) -> None:
        """Register a new provider class.

        Args:
            provider_type: Type of the provider (e.g., ProviderType.GOOGLE)
            provider_class: Class that implements ModelProvider interface
            append: If True, append to existing providers instead of overwriting.
                   Useful for multi-CLI scenarios where multiple providers of the same type
                   (e.g., CUSTOM) need to coexist.
        """
        instance = cls()
        if provider_type not in instance._providers:
            instance._providers[provider_type] = []

        if append:
            instance._providers[provider_type].append(provider_class)
        else:
            # Default behavior: Overwrite existing registration (fixes regression)
            instance._providers[provider_type] = [provider_class]
            # Clear initialized instances for this type since class changed
            instance._initialized_providers.pop(provider_type, None)

    @classmethod
    def get_provider(cls, provider_type: ProviderType, force_new: bool = False, index: int = 0) -> ModelProvider | None:
        """Get an initialized provider instance.

        Args:
            provider_type: Type of provider to get
            force_new: Force creation of new instance instead of using cached
            index: Index of the provider to get (for multi-provider types)

        Returns:
            Initialized ModelProvider instance or None if not available
        """
        instance = cls()

        # Check if provider class is registered
        if provider_type not in instance._providers or not instance._providers[provider_type]:
            return None

        if index >= len(instance._providers[provider_type]):
            return None

        # Initialize storage for this type if needed
        if provider_type not in instance._initialized_providers:
            instance._initialized_providers[provider_type] = [None] * len(instance._providers[provider_type])

        # Extend storage if new providers were appended
        current_list = instance._initialized_providers[provider_type]
        if len(current_list) < len(instance._providers[provider_type]):
            current_list.extend([None] * (len(instance._providers[provider_type]) - len(current_list)))

        # Return cached instance if available and not forcing new
        if not force_new and current_list[index] is not None:
            return current_list[index]

        # Get API key from environment
        api_key = cls._get_api_key_for_provider(provider_type)

        # Get provider class or factory function
        provider_class = instance._providers[provider_type][index]

        # For custom providers, handle special initialization requirements
        if provider_type == ProviderType.CUSTOM:
            # Check if it's a factory function (callable but not a class)
            if callable(provider_class) and not isinstance(provider_class, type):
                # Factory function - call it with api_key parameter
                provider = provider_class(api_key=api_key)
            else:
                # Regular class - need to handle URL requirement
                custom_url = os.getenv("CUSTOM_API_URL", "")
                if not custom_url:
                    if api_key:  # Key is set but URL is missing
                        logging.warning("CUSTOM_API_KEY set but CUSTOM_API_URL missing – skipping Custom provider")
                    return None
                # Use empty string as API key for custom providers that don't need auth (e.g., Ollama)
                # This allows the provider to be created even without CUSTOM_API_KEY being set
                api_key = api_key or ""
                # Initialize custom provider with both API key and base URL
                provider = provider_class(api_key=api_key, base_url=custom_url)
        else:
            if not api_key:
                return None
            # Initialize non-custom provider with just API key
            provider = provider_class(api_key=api_key)

        # Cache the instance
        instance._initialized_providers[provider_type][index] = provider

        return provider

    @classmethod
    def get_provider_for_model(cls, model_name: str) -> ModelProvider | None:
        """Get provider instance for a specific model name.

        Provider priority order:
        1. Native APIs (GOOGLE, OPENAI) - Most direct and efficient
        2. CUSTOM - For local/private models with specific endpoints
        3. OPENROUTER - Catch-all for cloud models via unified API

        Args:
            model_name: Name of the model (e.g., "gemini-2.5-flash", "gpt5")

        Returns:
            ModelProvider instance that supports this model
        """
        # Check providers in priority order
        instance = cls()

        for provider_type in cls.PROVIDER_PRIORITY_ORDER:
            if provider_type in instance._providers:
                # Iterate through all providers of this type (e.g., multiple CLIs)
                provider_list = instance._providers[provider_type]
                for i in range(len(provider_list)):
                    # Get or create provider instance
                    provider = cls.get_provider(provider_type, index=i)
                    if provider and provider.validate_model_name(model_name):
                        return provider

        return None

    @classmethod
    def get_available_providers(cls) -> list[ProviderType]:
        """Get list of registered provider types."""
        instance = cls()
        return list(instance._providers.keys())

    @classmethod
    def get_available_models(cls, respect_restrictions: bool = True) -> dict[str, ProviderType]:
        """Get mapping of all available models to their providers.

        Args:
            respect_restrictions: If True, filter out models not allowed by restrictions

        Returns:
            Dict mapping model names to provider types
        """
        # Import here to avoid circular imports
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service() if respect_restrictions else None
        models: dict[str, ProviderType] = {}
        instance = cls()

        for provider_type in instance._providers:
            # Iterate through all providers of this type
            provider_count = len(instance._providers[provider_type])
            for i in range(provider_count):
                provider = cls.get_provider(provider_type, index=i)
                if not provider:
                    continue

                try:
                    available = provider.list_models(respect_restrictions=respect_restrictions)
                except NotImplementedError:
                    logging.warning("Provider %s (index %d) does not implement list_models", provider_type, i)
                    continue

                for model_name in available:
                    # =====================================================================================
                    # CRITICAL: Prevent double restriction filtering (Fixed Issue #98)
                    # =====================================================================================
                    # Previously, both the provider AND registry applied restrictions, causing
                    # double-filtering that resulted in "no models available" errors.
                    #
                    # Logic: If respect_restrictions=True, provider already filtered models,
                    # so registry should NOT filter them again.
                    # TEST COVERAGE: tests/test_provider_routing_bugs.py::TestOpenRouterAliasRestrictions
                    # =====================================================================================
                    if (
                        restriction_service
                        and not respect_restrictions  # Only filter if provider didn't already filter
                        and not restriction_service.is_allowed(provider_type, model_name)
                    ):
                        logging.debug("Model %s filtered by restrictions", model_name)
                        continue
                    models[model_name] = provider_type

        return models

    @classmethod
    def get_available_model_names(cls, provider_type: ProviderType | None = None) -> list[str]:
        """Get list of available model names, optionally filtered by provider.

        This respects model restrictions automatically.

        Args:
            provider_type: Optional provider to filter by

        Returns:
            List of available model names
        """
        available_models = cls.get_available_models(respect_restrictions=True)

        if provider_type:
            # Filter by specific provider
            return [name for name, ptype in available_models.items() if ptype == provider_type]
        else:
            # Return all available models
            return list(available_models.keys())

    @classmethod
    def _get_api_key_for_provider(cls, provider_type: ProviderType) -> str | None:
        """Get API key for a provider from environment variables.

        Args:
            provider_type: Provider type to get API key for

        Returns:
            API key string or None if not found
        """
        # Special handling for OpenRouter/Kilo priority
        if provider_type == ProviderType.OPENROUTER:
            kilo_key = os.getenv("KILO_API_KEY")
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            kilo_preferred = os.getenv("KILO_PREFERRED", "").lower() in ("true", "1", "yes")

            if kilo_preferred and kilo_key:
                return kilo_key
            if openrouter_key:
                return openrouter_key
            # Fallback to Kilo key if OpenRouter key is missing
            return kilo_key

        key_mapping = {
            ProviderType.GOOGLE: "GEMINI_API_KEY",
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.XAI: "XAI_API_KEY",
            ProviderType.OPENROUTER: "OPENROUTER_API_KEY",
            ProviderType.CUSTOM: "CUSTOM_API_KEY",  # Can be empty for providers that don't need auth
            ProviderType.DIAL: "DIAL_API_KEY",
        }

        env_var = key_mapping.get(provider_type)
        if not env_var:
            return None

        return os.getenv(env_var)

    @classmethod
    def _get_allowed_models_for_provider(cls, provider: ModelProvider, provider_type: ProviderType) -> list[str]:
        """Get a list of allowed canonical model names for a given provider.

        Args:
            provider: The provider instance to get models for
            provider_type: The provider type for restriction checking

        Returns:
            List of model names that are both supported and allowed
        """
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()

        allowed_models = []

        # Get the provider's supported models
        try:
            # Use list_models to get all supported models (handles both regular and custom providers)
            supported_models = provider.list_models(respect_restrictions=False)
        except (NotImplementedError, AttributeError):
            # Fallback to SUPPORTED_MODELS if list_models not implemented
            try:
                supported_models = list(provider.SUPPORTED_MODELS.keys())
            except AttributeError:
                supported_models = []

        # Filter by restrictions
        for model_name in supported_models:
            if restriction_service.is_allowed(provider_type, model_name):
                allowed_models.append(model_name)

        return allowed_models

    @classmethod
    def get_preferred_fallback_model(cls, tool_category: ToolModelCategory | None = None) -> str:
        """Get the preferred fallback model, optionally considering tool category.

        Args:
            tool_category: Optional category to influence model selection

        Returns:
            Model name to use as fallback
        """
        from tools.models import ToolModelCategory

        effective_category = tool_category or ToolModelCategory.BALANCED
        first_available_model = None
        instance = cls()

        # Ask each provider for their preference in priority order
        for provider_type in cls.PROVIDER_PRIORITY_ORDER:
            if provider_type not in instance._providers:
                continue

            # Iterate through all providers of this type
            provider_count = len(instance._providers[provider_type])
            for i in range(provider_count):
                provider = cls.get_provider(provider_type, index=i)
                if provider:
                    # 1. Registry filters the models first
                    allowed_models = cls._get_allowed_models_for_provider(provider, provider_type)

                    if not allowed_models:
                        continue

                    # 2. Keep track of the first available model as fallback
                    if not first_available_model:
                        first_available_model = sorted(allowed_models)[0]

                    # 3. Ask provider to pick from allowed list
                    preferred_model = provider.get_preferred_model(effective_category, allowed_models)

                    if preferred_model:
                        logging.debug(
                            f"Provider {provider_type.value} (index {i}) selected '{preferred_model}' for category '{effective_category.value}'"
                        )
                        return preferred_model

        # If no provider returned a preference, use first available model
        if first_available_model:
            logging.debug(f"No provider preference, using first available: {first_available_model}")
            return first_available_model

        # Ultimate fallback if no providers have models
        logging.warning("No models available from any provider, using default fallback")
        return "gemini-2.5-flash"

    @classmethod
    def get_available_providers_with_keys(cls) -> list[ProviderType]:
        """Get list of provider types that have valid API keys.

        Returns:
            List of ProviderType values for providers with valid API keys
        """
        available = []
        instance = cls()
        for provider_type in instance._providers:
            # Check if ANY provider of this type has a key/is valid
            provider_count = len(instance._providers[provider_type])
            for i in range(provider_count):
                if cls.get_provider(provider_type, index=i) is not None:
                    available.append(provider_type)
                    break
        return available

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached provider instances."""
        instance = cls()
        instance._initialized_providers.clear()

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset the registry to a clean state for testing.

        This provides a safe, public API for tests to clean up registry state
        without directly manipulating private attributes.
        """
        cls._instance = None
        if hasattr(cls, "_providers"):
            cls._providers = {}

    @classmethod
    def unregister_provider(cls, provider_type: ProviderType) -> None:
        """Unregister a provider (mainly for testing)."""
        instance = cls()
        instance._providers.pop(provider_type, None)
        instance._initialized_providers.pop(provider_type, None)


# Load _ModelLibrary.json for upstream_provider checks


def load_model_library():
    try:
        with open("docs/_ModelLibrary.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


MODEL_LIBRARY = load_model_library()
