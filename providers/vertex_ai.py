"""Google Vertex AI model provider implementation."""

import logging

import google.auth
import google.auth.exceptions
import google.genai as genai

from .base import ModelCapabilities, ModelResponse, ProviderType
from .gemini import GeminiModelProvider

logger = logging.getLogger(__name__)


class VertexAIProvider(GeminiModelProvider):
    """Google Vertex AI model provider implementation."""

    # Inherit thinking budgets from parent
    THINKING_BUDGETS = GeminiModelProvider.THINKING_BUDGETS

    # Vertex AI specific model configurations and aliases
    SUPPORTED_MODELS = {
        # Inherit base Gemini models from parent class
        **GeminiModelProvider.SUPPORTED_MODELS,
        # Add Vertex AI specific models and aliases
        "gemini-2.5-flash-lite-preview-06-17": {
            "context_window": 1_048_576,  # 1M tokens
            "supports_extended_thinking": True,
            "max_thinking_tokens": 24576,  # Flash 2.5 thinking budget limit
            "supports_images": True,  # Vision capability
            "max_image_size_mb": 20.0,  # Conservative 20MB limit for reliability
        },
        "gemini-2.5-pro-preview-06-05": {
            "context_window": 1_048_576,  # 1M tokens
            "supports_extended_thinking": True,
            "max_thinking_tokens": 32768,  # Pro 2.5 thinking budget limit
            "supports_images": True,  # Vision capability
            "max_image_size_mb": 32.0,  # Higher limit for Pro model
        },
        "gemini-2.0-flash": {
            "context_window": 1_048_576,  # 1M tokens
            "supports_extended_thinking": False,
            "supports_images": True,
            "max_image_size_mb": 20.0,
        },
        # Vertex AI convenient aliases
        "vertex-pro": "gemini-2.5-pro",
        "vertex-lite": "gemini-2.5-flash-lite-preview-06-17",
        "vertex-flash": "gemini-2.5-flash",
        "vertex-2.5-pro": "gemini-2.5-pro",
        "vertex-2.5-flash": "gemini-2.5-flash",
        "vertex-2.5-flash-lite": "gemini-2.5-flash-lite-preview-06-17",
        "vertex-2.0-flash": "gemini-2.0-flash",
        # Direct model name aliases
        "gemini-2.5-flash-lite": "gemini-2.5-flash-lite-preview-06-17",
    }

    def __init__(self, project_id: str, region: str = "us-central1", **kwargs):
        """Initialize Vertex AI provider with project ID and region.

        Note: Unlike other providers, Vertex AI doesn't use an API key.
        It uses Application Default Credentials (ADC) or service account credentials.
        """
        # Initialize with empty api_key to satisfy parent class
        super().__init__("", **kwargs)
        self.project_id = project_id
        self.region = region
        self._credentials = None

    @property
    def credentials(self):
        """Lazy initialization of Google credentials."""
        if self._credentials is None:
            try:
                self._credentials, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            except google.auth.exceptions.DefaultCredentialsError as e:
                logger.error(
                    f"Failed to initialize Google credentials (DefaultCredentialsError): {e}"
                )
                raise ValueError(
                    "Could not initialize Google Cloud credentials. "
                    "Please run 'gcloud auth application-default login' or set "
                    "GOOGLE_APPLICATION_CREDENTIALS environment variable."
                ) from e
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during Google credentials initialization: {e}"
                )
                raise ValueError(
                    f"An unexpected error occurred while initializing Google Cloud credentials: {e}"
                ) from e
        return self._credentials

    @property
    def client(self):
        """Lazy initialization of Google GenAI client for Vertex AI."""
        if self._client is None:
            # Create Vertex AI client using credentials instead of API key
            self._client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.region,
                credentials=self.credentials,
            )
        return self._client

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Vertex AI model."""
        # Get capabilities from parent class
        capabilities = super().get_capabilities(model_name)

        # Override provider type and friendly name for Vertex AI
        return ModelCapabilities(
            provider=ProviderType.VERTEX_AI,
            model_name=capabilities.model_name,
            friendly_name="Vertex AI",
            context_window=capabilities.context_window,
            supports_extended_thinking=capabilities.supports_extended_thinking,
            supports_system_prompts=capabilities.supports_system_prompts,
            supports_streaming=capabilities.supports_streaming,
            supports_function_calling=capabilities.supports_function_calling,
            supports_images=capabilities.supports_images,
            max_image_size_mb=capabilities.max_image_size_mb,
            supports_temperature=capabilities.supports_temperature,
            temperature_constraint=capabilities.temperature_constraint,
        )

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.VERTEX_AI

    def _build_contents(self, parts: list[dict]) -> list[dict]:
        """Build contents structure for Vertex AI - requires role."""
        return [{"role": "user", "parts": parts}]

    def _build_response(
        self, response, model_name: str, thinking_mode: str, capabilities, usage: dict
    ) -> ModelResponse:
        """Build response object for Vertex AI."""
        return ModelResponse(
            content=response.text,
            usage=usage,
            model_name=model_name,
            friendly_name="Vertex AI",
            provider=ProviderType.VERTEX_AI,
            metadata={
                "project_id": self.project_id,
                "region": self.region,
                "thinking_mode": (
                    thinking_mode if capabilities.supports_extended_thinking else None
                ),
                "finish_reason": (
                    getattr(response.candidates[0], "finish_reason", "STOP")
                    if response.candidates
                    else "STOP"
                ),
            },
        )

    def list_models(self, respect_restrictions: bool = True) -> list[str]:
        """Return a list of model names supported by Vertex AI, excluding aliases."""
        from utils.model_restrictions import get_restriction_service

        models = []
        for model_name, config in self.SUPPORTED_MODELS.items():
            # Skip aliases (they point to actual model names)
            if isinstance(config, str):
                continue

            if respect_restrictions:
                restriction_service = get_restriction_service()
                if not restriction_service.is_allowed(
                    ProviderType.VERTEX_AI, model_name, model_name
                ):
                    continue

            models.append(model_name)

        return models
