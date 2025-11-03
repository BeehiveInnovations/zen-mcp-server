"""Registry loader for Azure OpenAI model configurations."""

from __future__ import annotations

import logging

from ..shared import ModelCapabilities, ProviderType, TemperatureConstraint
from .base import CAPABILITY_FIELD_NAMES, CustomModelRegistryBase

logger = logging.getLogger(__name__)


class AzureModelRegistry(CustomModelRegistryBase):
    """Load Azure-specific model metadata from configuration files."""

    def __init__(self, config_path: str | None = None) -> None:
        super().__init__(
            env_var_name="AZURE_MODELS_CONFIG_PATH",
            default_filename="azure_models.json",
            config_path=config_path,
        )
        self.reload()

    def _extra_keys(self) -> set[str]:
        return {"deployment", "deployment_name"}

    def _provider_default(self) -> ProviderType:
        return ProviderType.AZURE

    def _default_friendly_name(self, model_name: str) -> str:
        return f"Azure OpenAI ({model_name})"

    def _finalise_entry(self, entry: dict) -> tuple[ModelCapabilities, dict]:
        deployment = entry.pop("deployment", None) or entry.pop("deployment_name", None)
        if not deployment:
            raise ValueError(f"Azure model '{entry.get('model_name')}' is missing required 'deployment' field")

        temp_hint = entry.get("temperature_constraint")
        if isinstance(temp_hint, str):
            entry["temperature_constraint"] = TemperatureConstraint.create(temp_hint)

        filtered = {k: v for k, v in entry.items() if k in CAPABILITY_FIELD_NAMES}
        filtered.setdefault("provider", ProviderType.AZURE)
        capability = ModelCapabilities(**filtered)
        return capability, {"deployment": deployment}
