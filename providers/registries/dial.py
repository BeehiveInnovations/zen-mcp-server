"""Registry loader for DIAL provider capabilities."""

from __future__ import annotations

from ..shared import ProviderType
from .base import CapabilityModelRegistry


class DialModelRegistry(CapabilityModelRegistry):
    """Capability registry backed by ``conf/dial_models.json``."""

    def __init__(self, config_path: str | None = None) -> None:
        super().__init__(
            env_var_name="DIAL_MODELS_CONFIG_PATH",
            default_filename="dial_models.json",
            provider=ProviderType.DIAL,
            friendly_prefix="DIAL ({model})",
            config_path=config_path,
        )
