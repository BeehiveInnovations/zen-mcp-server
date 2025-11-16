"""Registry loader for Gemini model capabilities."""

from __future__ import annotations

from ..shared import ProviderType
from .base import CapabilityModelRegistry


class GeminiModelRegistry(CapabilityModelRegistry):
    """Capability registry backed by ``conf/gemini_models.json``."""

    def __init__(self, config_path: str | None = None) -> None:
        super().__init__(
            env_var_name="GEMINI_MODELS_CONFIG_PATH",
            default_filename="gemini_models.json",
            provider=ProviderType.GOOGLE,
            friendly_prefix="Gemini ({model})",
            config_path=config_path,
        )
