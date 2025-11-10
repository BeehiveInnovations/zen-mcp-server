"""Model provider abstractions for supporting multiple AI providers."""

from .azure_openai import AzureOpenAIProvider
from .base import ModelProvider
from .openai import OpenAIModelProvider
from .openai_compatible import OpenAICompatibleProvider
from .openrouter import OpenRouterProvider
from .registry import ModelProviderRegistry
from .shared import ModelCapabilities, ModelResponse

# Optional Gemini provider - requires google-genai package
try:
    from .gemini import GeminiModelProvider
    _gemini_available = True
except ImportError:
    GeminiModelProvider = None  # type: ignore
    _gemini_available = False

__all__ = [
    "ModelProvider",
    "ModelResponse",
    "ModelCapabilities",
    "ModelProviderRegistry",
    "AzureOpenAIProvider",
    "GeminiModelProvider",
    "OpenAIModelProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
]
