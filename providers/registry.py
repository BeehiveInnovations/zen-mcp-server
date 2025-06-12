"""Model provider registry for managing available providers."""

import os
from typing import Dict, Optional, Type, List
from .base import ModelProvider, ProviderType


class ModelProviderRegistry:
    """Registry for managing model providers."""
    
    _instance = None
    _providers: Dict[ProviderType, Type[ModelProvider]] = {}
    _initialized_providers: Dict[ProviderType, ModelProvider] = {}
    
    def __new__(cls):
        """Singleton pattern for registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register_provider(cls, provider_type: ProviderType, provider_class: Type[ModelProvider]) -> None:
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
            model_name: Name of the model (e.g., "gemini-2.0-flash-exp", "o3-mini")
            
        Returns:
            ModelProvider instance that supports this model
        """
        # Check each registered provider
        for provider_type, provider_class in cls._providers.items():
            # Get or create provider instance
            provider = cls.get_provider(provider_type)
            if provider and provider.validate_model_name(model_name):
                return provider
        
        return None
    
    @classmethod
    def get_available_providers(cls) -> List[ProviderType]:
        """Get list of registered provider types."""
        return list(cls._providers.keys())
    
    @classmethod
    def get_available_models(cls) -> Dict[str, ProviderType]:
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
        }
        
        env_var = key_mapping.get(provider_type)
        if not env_var:
            return None
        
        return os.getenv(env_var)
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached provider instances."""
        cls._initialized_providers.clear()
    
    @classmethod
    def unregister_provider(cls, provider_type: ProviderType) -> None:
        """Unregister a provider (mainly for testing)."""
        cls._providers.pop(provider_type, None)
        cls._initialized_providers.pop(provider_type, None)