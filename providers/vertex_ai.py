"""Google Vertex AI model provider implementation."""

import dataclasses
import logging

import google.auth
import google.auth.exceptions
import google.genai as genai
import google.genai.types as genai_types

from .base import ModelCapabilities, ModelResponse, ProviderType, create_temperature_constraint
from .gemini import GeminiModelProvider

logger = logging.getLogger(__name__)


class VertexAIProvider(GeminiModelProvider):
    """Google Vertex AI model provider implementation."""

    # Inherit thinking budgets from parent
    THINKING_BUDGETS = GeminiModelProvider.THINKING_BUDGETS

    # Vertex AI specific model configurations
    SUPPORTED_MODELS = {
        # Inherit base Gemini models from parent class
        **GeminiModelProvider.SUPPORTED_MODELS,
        # Add Vertex AI specific models using ModelCapabilities
        "gemini-2.5-flash-lite-preview-06-17": ModelCapabilities(
            provider=ProviderType.VERTEX_AI,
            model_name="gemini-2.5-flash-lite-preview-06-17",
            friendly_name="Vertex AI",
            context_window=1_048_576,  # 1M tokens
            max_output_tokens=65_536,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # Vision capability
            max_image_size_mb=20.0,  # Conservative 20MB limit for reliability
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            max_thinking_tokens=24576,  # Flash 2.5 thinking budget limit
            description="Gemini 2.5 Flash Lite (Preview) - Vertex AI deployment",
        ),
        "gemini-2.5-pro-preview-06-05": ModelCapabilities(
            provider=ProviderType.VERTEX_AI,
            model_name="gemini-2.5-pro-preview-06-05",
            friendly_name="Vertex AI",
            context_window=1_048_576,  # 1M tokens
            max_output_tokens=65_536,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,  # Vision capability
            max_image_size_mb=32.0,  # Higher limit for Pro model
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            max_thinking_tokens=32768,  # Pro 2.5 thinking budget limit
            description="Gemini 2.5 Pro (Preview) - Vertex AI deployment",
        ),
        "gemini-2.0-flash": ModelCapabilities(
            provider=ProviderType.VERTEX_AI,
            model_name="gemini-2.0-flash",
            friendly_name="Vertex AI",
            context_window=1_048_576,  # 1M tokens
            max_output_tokens=65_536,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images=True,
            max_image_size_mb=20.0,
            supports_temperature=True,
            temperature_constraint=create_temperature_constraint("range"),
            description="Gemini 2.0 Flash - Vertex AI deployment",
        ),
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
                    scopes=["https://www.googleapis.com/auth/generative-language"]
                )
            except google.auth.exceptions.DefaultCredentialsError as e:
                logger.error(f"Failed to initialize Google credentials (DefaultCredentialsError): {e}")
                raise ValueError(
                    f"Could not initialize Google Cloud credentials: {e}. "
                    "Please run 'gcloud auth application-default login' or set "
                    "GOOGLE_APPLICATION_CREDENTIALS environment variable."
                ) from e
            except Exception as e:
                logger.error(f"An unexpected error occurred during Google credentials initialization: {e}")
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

    def get_all_model_aliases(self) -> dict[str, list[str]]:
        """Get all model aliases for Vertex AI provider.

        This includes both inherited Gemini aliases and Vertex-specific aliases.

        Returns:
            Dictionary mapping model names to their list of aliases
        """
        # Get base aliases from parent class (Gemini)
        aliases = super().get_all_model_aliases()

        # Add Vertex AI specific aliases from SUPPORTED_MODELS
        vertex_aliases = {
            "gemini-2.5-pro": ["vertex-pro", "vertex-2.5-pro"],
            "gemini-2.5-flash": ["vertex-flash", "vertex-2.5-flash"],
            "gemini-2.5-flash-lite-preview-06-17": ["vertex-lite", "vertex-2.5-flash-lite"],
            "gemini-2.0-flash": ["vertex-2.0-flash"],
        }

        # Merge with existing aliases
        for model_name, vertex_alias_list in vertex_aliases.items():
            if model_name in aliases:
                aliases[model_name].extend(vertex_alias_list)
            else:
                aliases[model_name] = vertex_alias_list

        # Handle direct model name aliases
        aliases["gemini-2.5-flash-lite-preview-06-17"] = aliases.get("gemini-2.5-flash-lite-preview-06-17", []) + [
            "gemini-2.5-flash-lite"
        ]

        return aliases

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Vertex AI model."""
        # Resolve model name first
        resolved_name = self._resolve_model_name(model_name)

        # If we have a Vertex-specific model in our SUPPORTED_MODELS, use it directly
        if resolved_name in self.SUPPORTED_MODELS and resolved_name not in GeminiModelProvider.SUPPORTED_MODELS:
            return self.SUPPORTED_MODELS[resolved_name]

        # Otherwise, get capabilities from parent class and override provider info
        capabilities = super().get_capabilities(resolved_name)

        # Override provider type and friendly name for inherited Gemini models
        return dataclasses.replace(
            capabilities,
            provider=ProviderType.VERTEX_AI,
            friendly_name="Vertex AI",
        )

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.VERTEX_AI

    def _build_contents(self, parts: list[dict]) -> list[dict]:
        """Build contents structure for Vertex AI API - requires role field.

        Overrides parent class method to add required "role" field for Vertex AI.
        This is a concrete implementation of the template method pattern.

        Args:
            parts: List of content parts (text, images, etc.)

        Returns:
            List of content dictionaries with required Vertex AI structure
        """
        return [{"role": "user", "parts": parts}]

    def _build_response(
        self,
        response: genai_types.GenerateContentResponse,
        model_name: str,
        thinking_mode: str,
        capabilities: ModelCapabilities,
        usage: dict[str, int],
    ) -> ModelResponse:
        """Build response object for Vertex AI provider.

        Overrides parent class method to customize response metadata for Vertex AI.
        Includes Vertex AI specific information like project_id and region.

        Args:
            response: Vertex AI API response object
            model_name: Name of the model used
            thinking_mode: Thinking mode configuration
            capabilities: Model capabilities object
            usage: Token usage information dictionary

        Returns:
            ModelResponse object with Vertex AI specific metadata
        """
        return ModelResponse(
            content=response.text,
            usage=usage,
            model_name=model_name,
            friendly_name="Vertex AI",
            provider=ProviderType.VERTEX_AI,
            metadata={
                "project_id": self.project_id,
                "region": self.region,
                "thinking_mode": (thinking_mode if capabilities.supports_extended_thinking else None),
                "finish_reason": (
                    getattr(response.candidates[0], "finish_reason", "STOP") if response.candidates else "STOP"
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
                if not restriction_service.is_allowed(ProviderType.VERTEX_AI, model_name):
                    continue

            models.append(model_name)

        return models
