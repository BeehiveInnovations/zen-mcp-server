"""Model provider abstractions for supporting multiple AI providers."""

from .azure_openai import AzureOpenAIModelProvider
from .base import ModelCapabilities, ModelProvider, ModelResponse
from .gemini import GeminiModelProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_provider import OpenAIModelProvider
from .openrouter import OpenRouterProvider
from .registry import ModelProviderRegistry

__all__ = [
    "ModelProvider",
    "ModelResponse",
    "ModelCapabilities",
    "ModelProviderRegistry",
    "GeminiModelProvider",
    "OpenAIModelProvider",
    "AzureOpenAIModelProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
]
