"""Enumeration describing which backend owns a given model."""

from enum import Enum

__all__ = ["ProviderType"]


class ProviderType(Enum):
    """Canonical identifiers for every supported provider backend."""

    GOOGLE = "google"
    OPENAI = "openai"
    XAI = "xai"
    OPENROUTER = "openrouter"
    AZURE = "azure"
    CUSTOM = "custom"
    DIAL = "dial"
