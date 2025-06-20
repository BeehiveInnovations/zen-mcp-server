"""Tests for Vertex AI provider implementation."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from providers.base import ProviderType
from providers.vertex_ai import VertexAIProvider


class TestVertexAIProvider:
    """Test Vertex AI provider functionality."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = VertexAIProvider(project_id="test-project", region="us-central1")
        assert provider.project_id == "test-project"
        assert provider.region == "us-central1"
        assert provider.get_provider_type() == ProviderType.VERTEX_AI

    def test_model_validation(self):
        """Test model name validation."""
        provider = VertexAIProvider(project_id="test-project")

        # Test valid models
        assert provider.validate_model_name("gemini-2.5-pro") is True
        assert provider.validate_model_name("gemini-2.5-flash") is True
        assert provider.validate_model_name("gemini-2.5-flash-lite") is True
        assert provider.validate_model_name("gemini-2.0-flash") is True
        assert provider.validate_model_name("vertex-pro") is True  # alias
        assert provider.validate_model_name("vertex-flash") is True  # alias
        assert provider.validate_model_name("vertex-lite") is True  # alias

        # Test invalid model
        assert provider.validate_model_name("invalid-model") is False

    def test_resolve_model_name(self):
        """Test model name resolution."""
        provider = VertexAIProvider(project_id="test-project")

        # Test shorthand resolution
        assert provider._resolve_model_name("vertex-pro") == "gemini-2.5-pro"
        assert provider._resolve_model_name("vertex-flash") == "gemini-2.5-flash"
        assert provider._resolve_model_name("vertex-lite") == "gemini-2.5-flash-lite-preview-06-17"
        assert provider._resolve_model_name("vertex-2.0-flash") == "gemini-2.0-flash"

        # Test that gemini-2.5-flash-lite also maps to the preview version
        assert provider._resolve_model_name("gemini-2.5-flash-lite") == "gemini-2.5-flash-lite-preview-06-17"

        # Test full name passthrough
        assert provider._resolve_model_name("gemini-2.5-pro") == "gemini-2.5-pro"

    @patch("providers.vertex_ai.google.auth.default")
    def test_get_capabilities(self, mock_auth):
        """Test getting model capabilities."""
        # Mock Google auth
        mock_credentials = MagicMock()
        mock_auth.return_value = (mock_credentials, "test-project")

        provider = VertexAIProvider(project_id="test-project")

        capabilities = provider.get_capabilities("vertex-pro")
        assert capabilities.model_name == "gemini-2.5-pro"
        assert capabilities.friendly_name == "Vertex AI"
        assert capabilities.context_window == 1_048_576
        assert capabilities.provider == ProviderType.VERTEX_AI
        assert capabilities.supports_extended_thinking is True
        assert capabilities.supports_images is True

        # Test temperature range
        assert capabilities.temperature_constraint.get_default() == 1.0
        min_temp, max_temp = capabilities.temperature_range
        assert min_temp == 0.0
        assert max_temp == 2.0

    def test_build_endpoint(self):
        """Test endpoint URL building."""
        provider = VertexAIProvider(project_id="test-project", region="us-west1")

        # Test non-streaming endpoint
        endpoint = provider._build_endpoint("gemini-2.5-pro", stream=False)
        expected = (
            "https://us-west1-aiplatform.googleapis.com/v1/"
            "projects/test-project/locations/us-west1/"
            "publishers/google/models/gemini-2.5-pro:generateContent"
        )
        assert endpoint == expected

        # Test streaming endpoint
        endpoint = provider._build_endpoint("gemini-2.5-pro", stream=True)
        expected = (
            "https://us-west1-aiplatform.googleapis.com/v1/"
            "projects/test-project/locations/us-west1/"
            "publishers/google/models/gemini-2.5-pro:streamGenerateContent"
        )
        assert endpoint == expected

    def test_build_request_payload(self):
        """Test request payload building."""
        provider = VertexAIProvider(project_id="test-project")

        # Test basic payload
        payload = provider._build_request_payload(prompt="Hello world", temperature=0.7, max_output_tokens=1000)

        expected = {
            "contents": [{"role": "user", "parts": [{"text": "Hello world"}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000},
        }
        assert payload == expected

    def test_build_request_payload_with_system_prompt(self):
        """Test request payload building with system prompt."""
        provider = VertexAIProvider(project_id="test-project")

        payload = provider._build_request_payload(
            prompt="Hello world", system_prompt="You are a helpful assistant", temperature=0.5
        )

        # With new format, system prompt is included as user/model conversation
        assert len(payload["contents"]) == 3  # system user, system model, actual user
        assert payload["contents"][0]["role"] == "user"
        assert payload["contents"][0]["parts"][0]["text"] == "You are a helpful assistant"
        assert payload["contents"][1]["role"] == "model"
        assert payload["contents"][1]["parts"][0]["text"] == "I understand."
        assert payload["contents"][2]["role"] == "user"
        assert payload["contents"][2]["parts"][0]["text"] == "Hello world"
        assert payload["generationConfig"]["temperature"] == 0.5

    def test_parse_response(self):
        """Test response parsing."""
        provider = VertexAIProvider(project_id="test-project")

        # Mock Vertex AI response
        response_data = {
            "candidates": [
                {"content": {"parts": [{"text": "Hello! How can I help you today?"}]}, "finishReason": "STOP"}
            ],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 10, "totalTokenCount": 15},
        }

        response = provider._parse_response(response_data, "gemini-1.5-pro")

        assert response.content == "Hello! How can I help you today?"
        assert response.model_name == "gemini-1.5-pro"
        assert response.friendly_name == "Vertex AI"
        assert response.provider == ProviderType.VERTEX_AI
        assert response.usage["input_tokens"] == 5
        assert response.usage["output_tokens"] == 10
        assert response.usage["total_tokens"] == 15
        assert response.metadata["finish_reason"] == "STOP"

    def test_parse_response_multiple_parts(self):
        """Test response parsing with multiple text parts."""
        provider = VertexAIProvider(project_id="test-project")

        response_data = {
            "candidates": [{"content": {"parts": [{"text": "Hello "}, {"text": "world!"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 2, "totalTokenCount": 4},
        }

        response = provider._parse_response(response_data, "gemini-1.5-pro")
        assert response.content == "Hello world!"

    def test_parse_response_error_no_candidates(self):
        """Test response parsing error when no candidates."""
        provider = VertexAIProvider(project_id="test-project")

        response_data = {"candidates": []}

        with pytest.raises(ValueError, match="No candidates in response"):
            provider._parse_response(response_data, "gemini-1.5-pro")

    def test_parse_response_error_no_content_parts(self):
        """Test response parsing error when no content parts."""
        provider = VertexAIProvider(project_id="test-project")

        response_data = {"candidates": [{"content": {"parts": []}, "finishReason": "STOP"}]}

        with pytest.raises(ValueError, match="No content parts in response"):
            provider._parse_response(response_data, "gemini-1.5-pro")

    @patch("providers.vertex_ai.google.auth.default")
    @patch("providers.vertex_ai.AuthorizedSession")
    def test_generate_content_success(self, mock_session_class, mock_auth):
        """Test successful content generation."""
        # Mock Google auth
        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_auth.return_value = (mock_credentials, "test-project")

        # Mock HTTP session
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Generated response"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2, "totalTokenCount": 5},
        }
        mock_session.post.return_value = mock_response

        provider = VertexAIProvider(project_id="test-project")

        response = provider.generate_content(prompt="Test prompt", model_name="vertex-pro", temperature=0.7)

        assert response.content == "Generated response"
        assert response.model_name == "gemini-2.5-pro"  # Resolved from alias
        assert response.usage["total_tokens"] == 5

        # Verify API call was made correctly
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "generateContent" in call_args[0][0]  # URL
        # Find the user prompt in the contents (it's the last one in our format)
        user_content = [
            c
            for c in call_args[1]["json"]["contents"]
            if c["role"] == "user" and c["parts"][0]["text"] == "Test prompt"
        ]
        assert len(user_content) == 1

    @patch("providers.vertex_ai.google.auth.default")
    @patch("providers.vertex_ai.AuthorizedSession")
    def test_generate_content_api_error(self, mock_session_class, mock_auth):
        """Test content generation with API error."""
        # Mock Google auth
        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_auth.return_value = (mock_credentials, "test-project")

        # Mock HTTP session
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock API error
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"message": "Invalid request"}}
        mock_session.post.side_effect = requests.exceptions.HTTPError("400 Bad Request", response=mock_response)

        provider = VertexAIProvider(project_id="test-project")

        with pytest.raises(RuntimeError, match="Vertex AI API error"):
            provider.generate_content(prompt="Test prompt", model_name="vertex-pro")

    @patch("providers.vertex_ai.google.auth.default")
    def test_credentials_error(self, mock_auth):
        """Test error when credentials cannot be initialized."""
        mock_auth.side_effect = Exception("Credentials error")

        provider = VertexAIProvider(project_id="test-project")

        with pytest.raises(ValueError, match="Could not initialize Google Cloud credentials"):
            _ = provider.credentials

    def test_list_models(self):
        """Test listing available models."""
        provider = VertexAIProvider(project_id="test-project")

        models = provider.list_models(respect_restrictions=False)

        # Should include actual models but not aliases
        assert "gemini-2.5-pro" in models
        assert "gemini-2.5-flash" in models
        assert "gemini-2.5-flash-lite-preview-06-17" in models
        assert "gemini-2.0-flash" in models

        # Should not include aliases
        assert "gemini-2.5-flash-lite" not in models

        # Should not include aliases
        assert "vertex-pro" not in models
        assert "vertex-flash" not in models

    def test_list_all_known_models(self):
        """Test listing all known models including aliases."""
        provider = VertexAIProvider(project_id="test-project")

        models = provider.list_all_known_models()

        # Should include both actual models and aliases
        assert "gemini-2.5-pro" in models
        assert "vertex-pro" in models
        assert "vertex-flash" in models

    def test_supports_thinking_mode(self):
        """Test checking thinking mode support."""
        provider = VertexAIProvider(project_id="test-project")

        # Models that support thinking
        assert provider.supports_thinking_mode("gemini-2.5-pro") is True
        assert provider.supports_thinking_mode("vertex-pro") is True

        # Models that don't support thinking
        assert provider.supports_thinking_mode("gemini-2.0-flash") is False

    def test_count_tokens(self):
        """Test token counting estimation."""
        provider = VertexAIProvider(project_id="test-project")

        # Test estimation (roughly 4 characters per token, with ceiling and minimum 1)
        assert provider.count_tokens("hello", "gemini-2.5-pro") == 2  # 5 chars / 4 = 1.25 -> ceil(1.25) = 2
        assert provider.count_tokens("hello world", "gemini-2.5-pro") == 3  # 11 chars / 4 = 2.75 -> ceil(2.75) = 3
        assert provider.count_tokens("a" * 100, "gemini-2.5-pro") == 25  # 100 chars / 4 = 25
        assert provider.count_tokens("a", "gemini-2.5-pro") == 1  # Minimum 1 token

    def test_supports_audio(self):
        """Test checking audio support."""
        provider = VertexAIProvider(project_id="test-project")

        # Models that support audio
        assert provider.supports_audio("gemini-2.5-pro") is True
        assert provider.supports_audio("gemini-2.5-flash") is True

        # Models that don't support audio
        assert provider.supports_audio("gemini-2.0-flash") is False

    def test_supports_video(self):
        """Test checking video support."""
        provider = VertexAIProvider(project_id="test-project")

        # Models that support video
        assert provider.supports_video("gemini-2.5-pro") is True
        assert provider.supports_video("gemini-2.5-flash") is True

        # Models that don't support video
        assert provider.supports_video("gemini-2.0-flash") is False

    def test_get_max_output_tokens(self):
        """Test getting max output tokens."""
        provider = VertexAIProvider(project_id="test-project")

        # Standard models
        assert provider.get_max_output_tokens("gemini-2.5-pro") == 65_535
        assert provider.get_max_output_tokens("gemini-2.0-flash") == 65_535
        assert provider.get_max_output_tokens("gemini-2.5-flash-lite") == 65_535
