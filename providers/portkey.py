"""Portkey provider implementation."""

import logging
import os
from typing import Optional

from .base import (
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider
from .portkey_registry import PortkeyModelRegistry


class PortkeyProvider(OpenAICompatibleProvider):
    """Portkey AI Gateway provider.

    Portkey provides access to multiple AI models through a unified gateway with
    enterprise features like observability, fallbacks, and load balancing.
    See https://portkey.ai for available features and providers.
    """

    FRIENDLY_NAME = "Portkey"

    # Custom headers required by Portkey
    DEFAULT_HEADERS = {
        "x-portkey-api-key": os.getenv("PORTKEY_API_KEY"),
        # x-portkey-config will be set dynamically based on model
    }

    @classmethod
    def _get_clean_headers(cls) -> dict:
        """Get headers with None values filtered out."""
        return {k: v for k, v in cls.DEFAULT_HEADERS.items() if v is not None}

    # Model registry for managing configurations and aliases
    _registry: Optional[PortkeyModelRegistry] = None

    def __init__(self, api_key: str, **kwargs):
        """Initialize Portkey provider.

        Args:
            api_key: Portkey API key
            **kwargs: Additional configuration including virtual_key
        """
        base_url = "https://api.portkey.ai/v1"
        super().__init__(api_key, base_url=base_url, **kwargs)

        # Store config mappings for model routing
        self.model_configs = self._load_model_configs()

        # Optional: Fall back to virtual key if configs not available
        self.virtual_key = kwargs.get("virtual_key") or os.getenv("PORTKEY_VIRTUAL_KEY")

        # Initialize model registry
        if PortkeyProvider._registry is None:
            PortkeyProvider._registry = PortkeyModelRegistry()
            # Log loaded models and aliases only on first load
            models = self._registry.list_models()
            aliases = self._registry.list_aliases()
            logging.info(f"Portkey loaded {len(models)} models with {len(aliases)} aliases")

    def _load_model_configs(self) -> dict[str, str]:
        """Load model-to-config mappings from environment variables.

        Expected format:
        PORTKEY_CONFIG_GPT4=pc-gpt4-config-id
        PORTKEY_CONFIG_CLAUDE=pc-claude-config-id
        PORTKEY_CONFIG_GEMINI=pc-gemini-config-id

        Returns:
            Dictionary mapping model names to config IDs
        """
        import os

        configs = {}

        # Look for PORTKEY_CONFIG_* environment variables
        for key, value in os.environ.items():
            if key.startswith("PORTKEY_CONFIG_"):
                model_key = key.replace("PORTKEY_CONFIG_", "").lower()
                configs[model_key] = value

        if configs:
            logging.info(f"Portkey model configs loaded: {list(configs.keys())}")
        else:
            logging.debug("No Portkey model configs found. Using virtual key fallback.")

        return configs

    def _get_config_for_model(self, model_name: str) -> Optional[str]:
        """Get Portkey config ID for a model.

        Args:
            model_name: Model name to get config for

        Returns:
            Config ID if found, None otherwise
        """
        # Try exact model name match
        if model_name.lower() in self.model_configs:
            return self.model_configs[model_name.lower()]

        # Try explicit provider_route from model registry
        from providers.portkey_registry import PORTKEY_MODEL_REGISTRY
        for model_info in PORTKEY_MODEL_REGISTRY.get("models", []):
            # Check if model name matches or is in aliases
            if (model_name.lower() == model_info["model_name"].lower() or 
                model_name.lower() in [alias.lower() for alias in model_info.get("aliases", [])]):
                provider_route = model_info.get("provider_route")
                if provider_route:
                    return self.model_configs.get(provider_route)
        
        # Fallback to provider-based matching (legacy logic)
        model_lower = model_name.lower()
        if any(x in model_lower for x in ["gpt", "openai"]):
            return self.model_configs.get("openai") or self.model_configs.get("gpt")
        elif any(x in model_lower for x in ["claude", "anthropic"]):
            return self.model_configs.get("claude") or self.model_configs.get("anthropic")
        elif any(x in model_lower for x in ["gemini", "google"]):
            return self.model_configs.get("gemini") or self.model_configs.get("google")
        elif any(x in model_lower for x in ["llama", "meta"]):
            return self.model_configs.get("llama") or self.model_configs.get("meta")
        elif any(x in model_lower for x in ["mistral"]):
            return self.model_configs.get("mistral")

        return None

    def _get_provider_for_model(self, model_name: str) -> Optional[str]:
        """Get provider name for x-portkey-provider header as fallback.

        Args:
            model_name: Model name to get provider for

        Returns:
            Provider name if determinable, None otherwise
        """
        model_lower = model_name.lower()
        if any(x in model_lower for x in ["gpt", "openai"]):
            return "openai"
        elif any(x in model_lower for x in ["claude", "anthropic"]):
            return "anthropic"
        elif any(x in model_lower for x in ["gemini", "google"]):
            return "google"
        elif any(x in model_lower for x in ["llama", "meta"]):
            return "meta-llama"
        elif any(x in model_lower for x in ["mistral"]):
            return "mistralai"

        return None

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model aliases to Portkey model names.

        Args:
            model_name: Input model name or alias

        Returns:
            Resolved Portkey model name
        """
        # Try to resolve through registry
        config = self._registry.resolve(model_name)

        if config:
            if config.model_name != model_name:
                logging.info(f"Resolved model alias '{model_name}' to '{config.model_name}'")
            return config.model_name
        else:
            # If not found in registry, return as-is
            # This allows using models not in our config file
            logging.debug(f"Model '{model_name}' not found in registry, using as-is")
            return model_name

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a model.

        Args:
            model_name: Name of the model (or alias)

        Returns:
            ModelCapabilities from registry or generic defaults
        """
        # Try to get from registry first
        capabilities = self._registry.get_capabilities(model_name)

        if capabilities:
            return capabilities
        else:
            # Resolve any potential aliases and create generic capabilities
            resolved_name = self._resolve_model_name(model_name)

            logging.debug(
                f"Using generic capabilities for '{resolved_name}' via Portkey. "
                "Consider adding to portkey_models.json for specific capabilities."
            )

            # Create generic capabilities with conservative defaults
            capabilities = ModelCapabilities(
                provider=ProviderType.PORTKEY,
                model_name=resolved_name,
                friendly_name=self.FRIENDLY_NAME,
                context_window=32_768,  # Conservative default context window
                max_output_tokens=32_768,
                supports_extended_thinking=False,
                supports_system_prompts=True,
                supports_streaming=True,
                supports_function_calling=False,
                temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 1.0),
            )

            # Mark as generic for validation purposes
            capabilities._is_generic = True

            return capabilities

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.PORTKEY

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is allowed.

        As a gateway provider, Portkey accepts any model name that wasn't
        handled by higher-priority providers. Portkey will validate based on
        the virtual key's permissions and local restrictions.

        Args:
            model_name: Model name to validate

        Returns:
            True if model is allowed, False if restricted
        """
        # Check model restrictions if configured
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service()
        if restriction_service:
            # Check if model name itself is allowed
            if restriction_service.is_allowed(self.get_provider_type(), model_name):
                return True

            # Also check aliases - model_name might be an alias
            model_config = self._registry.resolve(model_name)
            if model_config and model_config.aliases:
                for alias in model_config.aliases:
                    if restriction_service.is_allowed(self.get_provider_type(), alias):
                        return True

            # If restrictions are configured and model/alias not in allowed list, reject
            return False

        # No restrictions configured - accept any model name as the gateway provider
        return True

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using the Portkey API.

        Args:
            prompt: User prompt to send to the model
            model_name: Name of the model (or alias) to use
            system_prompt: Optional system prompt for model behavior
            temperature: Sampling temperature
            max_output_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            ModelResponse with generated content and metadata
        """
        # Resolve model alias to actual Portkey model name
        resolved_model = self._resolve_model_name(model_name)

        # Get config for dynamic routing
        config_id = self._get_config_for_model(resolved_model)

        # Set up headers for this request
        headers = self._get_clean_headers()
        logging.debug(f"Model configs available: {list(self.model_configs.keys())}")
        logging.debug(f"Looking for config for model: {resolved_model}")
        logging.debug(f"Found config_id: {config_id}")

        if self.virtual_key:
            headers["x-portkey-virtual-key"] = self.virtual_key
            logging.debug(f"Using Portkey virtual key for model '{resolved_model}'")
        elif config_id:
            headers["x-portkey-config"] = config_id
            logging.debug(f"Using Portkey config '{config_id}' for model '{resolved_model}'")
        else:
            # Fallback: Use x-portkey-provider header (requires Portkey virtual key setup)
            provider_name = self._get_provider_for_model(resolved_model)
            if provider_name:
                headers["x-portkey-provider"] = provider_name
                logging.debug(f"Using Portkey provider '{provider_name}' for model '{resolved_model}'")
                logging.warning(
                    f"No Portkey config or virtual key found for model '{resolved_model}'. "
                    f"Using x-portkey-provider='{provider_name}' header. "
                    f"This requires a Portkey virtual key to be configured for routing."
                )
            else:
                raise ValueError(
                    f"No Portkey routing method available for model '{resolved_model}'. "
                    f"Please configure one of: "
                    f"1) PORTKEY_CONFIG_OPENAI/CLAUDE/GEMINI environment variables, "
                    f"2) PORTKEY_VIRTUAL_KEY for unified routing, or "
                    f"3) Ensure model provider mapping is supported."
                )

        # Disable streaming by default for MCP compatibility
        if "stream" not in kwargs:
            kwargs["stream"] = False

        # Add headers to kwargs for OpenAI client
        if "extra_headers" not in kwargs:
            kwargs["extra_headers"] = {}
        kwargs["extra_headers"].update(headers)

        # Debug: Log final headers (excluding sensitive values)
        debug_headers = {k: "***" if "key" in k.lower() else v for k, v in kwargs["extra_headers"].items()}
        logging.debug(f"Final Portkey headers: {debug_headers}")

        # Call parent method with resolved model name
        return super().generate_content(
            prompt=prompt,
            model_name=resolved_model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            **kwargs,
        )

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode.

        This depends on the underlying model routed through Portkey.

        Args:
            model_name: Model to check

        Returns:
            True if model supports thinking mode (based on registry config)
        """
        capabilities = self.get_capabilities(model_name)
        return capabilities.supports_extended_thinking

    def list_models(self, respect_restrictions: bool = True) -> list[str]:
        """Return a list of model names supported by this provider.

        Args:
            respect_restrictions: Whether to apply provider-specific restriction logic.

        Returns:
            List of model names available from this provider
        """
        from utils.model_restrictions import get_restriction_service

        restriction_service = get_restriction_service() if respect_restrictions else None
        models = []

        if self._registry:
            for model_name in self._registry.list_models():
                if restriction_service:
                    # Get model config to check aliases as well
                    model_config = self._registry.resolve(model_name)
                    allowed = False

                    # Check if model name itself is allowed
                    if restriction_service.is_allowed(self.get_provider_type(), model_name):
                        allowed = True

                    # Also check aliases
                    if not allowed and model_config and model_config.aliases:
                        for alias in model_config.aliases:
                            if restriction_service.is_allowed(self.get_provider_type(), alias):
                                allowed = True
                                break

                    if not allowed:
                        continue

                models.append(model_name)

        return models

    def list_all_known_models(self) -> list[str]:
        """Return all model names known by this provider, including alias targets.

        Returns:
            List of all model names and alias targets known by this provider
        """
        all_models = set()

        if self._registry:
            # Get all models and aliases from the registry
            all_models.update(model.lower() for model in self._registry.list_models())
            all_models.update(alias.lower() for alias in self._registry.list_aliases())

            # For each alias, also add its target
            for alias in self._registry.list_aliases():
                config = self._registry.resolve(alias)
                if config:
                    all_models.add(config.model_name.lower())

        return list(all_models)

    def get_model_configurations(self) -> dict[str, ModelCapabilities]:
        """Get model configurations from the registry.

        For Portkey, we convert registry configurations to ModelCapabilities objects.

        Returns:
            Dictionary mapping model names to their ModelCapabilities objects
        """
        configs = {}

        if self._registry:
            # Get all models from registry
            for model_name in self._registry.list_models():
                # Only include models that this provider validates
                if self.validate_model_name(model_name):
                    config = self._registry.resolve(model_name)
                    if config:
                        # Use ModelCapabilities directly from registry
                        configs[model_name] = config

        return configs

    def get_all_model_aliases(self) -> dict[str, list[str]]:
        """Get all model aliases from the registry.

        Returns:
            Dictionary mapping model names to their list of aliases
        """
        # Since aliases are now included in the configurations,
        # we can use the base class implementation
        return super().get_all_model_aliases()
