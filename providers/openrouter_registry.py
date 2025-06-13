"""OpenRouter model registry for managing model configurations and aliases."""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .base import ModelCapabilities, ProviderType, RangeTemperatureConstraint


@dataclass
class OpenRouterModelConfig:
    """Configuration for an OpenRouter model."""

    model_name: str
    aliases: list[str] = field(default_factory=list)
    context_window: int = 32768  # Total context window size in tokens
    supports_extended_thinking: bool = False
    supports_system_prompts: bool = True
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_json_mode: bool = False
    description: str = ""

    def to_capabilities(self) -> ModelCapabilities:
        """Convert to ModelCapabilities object."""
        return ModelCapabilities(
            provider=ProviderType.OPENROUTER,
            model_name=self.model_name,
            friendly_name="OpenRouter",
            max_tokens=self.context_window,  # ModelCapabilities still uses max_tokens
            supports_extended_thinking=self.supports_extended_thinking,
            supports_system_prompts=self.supports_system_prompts,
            supports_streaming=self.supports_streaming,
            supports_function_calling=self.supports_function_calling,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 1.0),
        )


class OpenRouterModelRegistry:
    """Registry for managing OpenRouter model configurations and aliases."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the registry.

        Args:
            config_path: Path to config file. If None, uses default locations.
        """
        self.alias_map: dict[str, str] = {}  # alias -> model_name
        self.model_map: dict[str, OpenRouterModelConfig] = {}  # model_name -> config

        # Determine config path
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Check environment variable first
            env_path = os.getenv("OPENROUTER_MODELS_PATH")
            if env_path:
                self.config_path = Path(env_path)
            else:
                # Default to conf/openrouter_models.json
                self.config_path = Path(__file__).parent.parent / "conf" / "openrouter_models.json"

        # Load configuration
        self.reload()

    def reload(self) -> None:
        """Reload configuration from disk."""
        try:
            configs = self._read_config()
            self._build_maps(configs)
            logging.info(f"Loaded {len(self.model_map)} OpenRouter models with {len(self.alias_map)} aliases")
        except ValueError as e:
            # Re-raise ValueError only for duplicate aliases (critical config errors)
            logging.error(f"Failed to load OpenRouter model configuration: {e}")
            # Initialize with empty maps on failure
            self.alias_map = {}
            self.model_map = {}
            if "Duplicate alias" in str(e):
                raise
        except Exception as e:
            logging.error(f"Failed to load OpenRouter model configuration: {e}")
            # Initialize with empty maps on failure
            self.alias_map = {}
            self.model_map = {}

    def _read_config(self) -> list[OpenRouterModelConfig]:
        """Read configuration from file.

        Returns:
            List of model configurations
        """
        if not self.config_path.exists():
            logging.warning(f"OpenRouter model config not found at {self.config_path}")
            return []

        try:
            with open(self.config_path) as f:
                data = json.load(f)

            # Parse models
            configs = []
            for model_data in data.get("models", []):
                # Handle backwards compatibility - rename max_tokens to context_window
                if "max_tokens" in model_data and "context_window" not in model_data:
                    model_data["context_window"] = model_data.pop("max_tokens")

                config = OpenRouterModelConfig(**model_data)
                configs.append(config)

            return configs
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.config_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error reading config from {self.config_path}: {e}")

    def _build_maps(self, configs: list[OpenRouterModelConfig]) -> None:
        """Build alias and model maps from configurations.

        Args:
            configs: List of model configurations
        """
        alias_map = {}
        model_map = {}

        for config in configs:
            # Add to model map
            model_map[config.model_name] = config

            # Add aliases
            for alias in config.aliases:
                alias_lower = alias.lower()
                if alias_lower in alias_map:
                    existing_model = alias_map[alias_lower]
                    raise ValueError(
                        f"Duplicate alias '{alias}' found for models " f"'{existing_model}' and '{config.model_name}'"
                    )
                alias_map[alias_lower] = config.model_name

        # Atomic update
        self.alias_map = alias_map
        self.model_map = model_map

    def resolve(self, name_or_alias: str) -> Optional[OpenRouterModelConfig]:
        """Resolve a model name or alias to configuration.

        Args:
            name_or_alias: Model name or alias to resolve

        Returns:
            Model configuration if found, None otherwise
        """
        # Try alias first (case-insensitive)
        alias_lower = name_or_alias.lower()
        if alias_lower in self.alias_map:
            model_name = self.alias_map[alias_lower]
            return self.model_map.get(model_name)

        # Try as direct model name
        return self.model_map.get(name_or_alias)

    def get_capabilities(self, name_or_alias: str) -> Optional[ModelCapabilities]:
        """Get model capabilities for a name or alias.

        Args:
            name_or_alias: Model name or alias

        Returns:
            ModelCapabilities if found, None otherwise
        """
        config = self.resolve(name_or_alias)
        if config:
            return config.to_capabilities()
        return None

    def list_models(self) -> list[str]:
        """List all available model names."""
        return list(self.model_map.keys())

    def list_aliases(self) -> list[str]:
        """List all available aliases."""
        return list(self.alias_map.keys())
