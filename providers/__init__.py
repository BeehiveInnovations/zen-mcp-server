"""Model provider abstractions for supporting multiple AI providers."""

from .azure_openai import AzureOpenAIProvider
from .base import ModelCapabilities, ModelProvider, ModelResponse
from .gemini import GeminiModelProvider
from .openai import OpenAIModelProvider
from .openai_compatible import OpenAICompatibleProvider
from .openrouter import OpenRouterProvider
from .registry import ModelProviderRegistry

__all__ = [
    "ModelProvider",
    "ModelResponse",
    "ModelCapabilities",
    "ModelProviderRegistry",
    "GeminiModelProvider",
    "OpenAIModelProvider",
    "AzureOpenAIProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
]
