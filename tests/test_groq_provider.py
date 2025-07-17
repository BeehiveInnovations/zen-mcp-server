"""Tests for Groq provider implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from providers.base import ProviderType
from providers.groq import GroqProvider


class TestGroqProvider:
    """Test Groq provider functionality."""

    def setup_method(self):
        """Set up clean state before each test."""
        # Clear restriction service cache before each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    def teardown_method(self):
        """Clean up after each test to avoid singleton issues."""
        # Clear restriction service cache after each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
    def test_initialization(self):
        """Test provider initialization."""
        provider = GroqProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.get_provider_type() == ProviderType.GROQ
        assert provider.base_url == "https://api.groq.com/openai/v1"

    def test_initialization_with_custom_url(self):
        """Test provider initialization with custom base URL."""
        provider = GroqProvider("test-key", base_url="https://custom.groq.com/v1")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://custom.groq.com/v1"

    def test_model_validation(self):
        """Test model name validation."""
        provider = GroqProvider("test-key")

        # Test valid production models
        assert provider.validate_model_name("gemma2-9b-it") is True
        assert provider.validate_model_name("llama-3.1-8b-instant") is True
        assert provider.validate_model_name("llama-3.3-70b-versatile") is True
        assert provider.validate_model_name("meta-llama/llama-guard-4-12b") is True

        # Test valid preview models
        assert provider.validate_model_name("deepseek-r1-distill-llama-70b") is True
        assert provider.validate_model_name("meta-llama/llama-4-maverick-17b-128e-instruct") is True
        assert provider.validate_model_name("meta-llama/llama-4-scout-17b-16e-instruct") is True
        assert provider.validate_model_name("mistral-saba-24b") is True
        assert provider.validate_model_name("moonshotai/kimi-k2-instruct") is True
        assert provider.validate_model_name("qwen/qwen3-32b") is True

        # Test valid preview systems
        assert provider.validate_model_name("compound-beta") is True
        assert provider.validate_model_name("compound-beta-mini") is True

        # Test valid aliases
        assert provider.validate_model_name("gemma2") is True
        assert provider.validate_model_name("llama-8b") is True
        assert provider.validate_model_name("llama-70b") is True
        assert provider.validate_model_name("guard-4") is True
        assert provider.validate_model_name("deepseek-r1") is True
        assert provider.validate_model_name("llama-4-maverick") is True
        assert provider.validate_model_name("kimi-k2") is True
        assert provider.validate_model_name("qwen3") is True

        # Test invalid models
        assert provider.validate_model_name("invalid-model") is False
        assert provider.validate_model_name("gpt-4") is False
        assert provider.validate_model_name("claude-3") is False
        assert provider.validate_model_name("llama-guard-3-8b") is False  # Old model
        assert provider.validate_model_name("llama3-8b-8192") is False  # Old model

    def test_resolve_model_name(self):
        """Test model name resolution."""
        provider = GroqProvider("test-key")

        # Test alias resolution
        assert provider._resolve_model_name("gemma2") == "gemma2-9b-it"
        assert provider._resolve_model_name("llama-8b") == "llama-3.1-8b-instant"
        assert provider._resolve_model_name("llama-70b") == "llama-3.3-70b-versatile"
        assert provider._resolve_model_name("guard-4") == "meta-llama/llama-guard-4-12b"
        assert provider._resolve_model_name("deepseek-r1") == "deepseek-r1-distill-llama-70b"
        assert provider._resolve_model_name("llama-4-maverick") == "meta-llama/llama-4-maverick-17b-128e-instruct"
        assert provider._resolve_model_name("kimi-k2") == "moonshotai/kimi-k2-instruct"
        assert provider._resolve_model_name("qwen3") == "qwen/qwen3-32b"
        assert provider._resolve_model_name("compound") == "compound-beta"
        assert provider._resolve_model_name("compound-mini") == "compound-beta-mini"

        # Test full name passthrough
        assert provider._resolve_model_name("gemma2-9b-it") == "gemma2-9b-it"
        assert provider._resolve_model_name("llama-3.1-8b-instant") == "llama-3.1-8b-instant"
        assert provider._resolve_model_name("meta-llama/llama-guard-4-12b") == "meta-llama/llama-guard-4-12b"
        assert provider._resolve_model_name("deepseek-r1-distill-llama-70b") == "deepseek-r1-distill-llama-70b"

    def test_get_capabilities_production_models(self):
        """Test getting model capabilities for production models."""
        provider = GroqProvider("test-key")

        # Test Gemma2
        capabilities = provider.get_capabilities("gemma2-9b-it")
        assert capabilities.model_name == "gemma2-9b-it"
        assert capabilities.friendly_name == "Groq (Gemma2 9B)"
        assert capabilities.context_window == 8192
        assert capabilities.max_output_tokens == 8192
        assert capabilities.provider == ProviderType.GROQ
        assert capabilities.supports_extended_thinking is False
        assert capabilities.supports_images is False
        assert capabilities.supports_json_mode is True

        # Test Llama 3.1 8B Instant
        capabilities = provider.get_capabilities("llama-3.1-8b-instant")
        assert capabilities.model_name == "llama-3.1-8b-instant"
        assert capabilities.friendly_name == "Groq (Llama 3.1 8B Instant)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 131072
        assert capabilities.supports_extended_thinking is False
        assert capabilities.supports_images is False

        # Test Llama 3.3 70B Versatile
        capabilities = provider.get_capabilities("llama-3.3-70b-versatile")
        assert capabilities.model_name == "llama-3.3-70b-versatile"
        assert capabilities.friendly_name == "Groq (Llama 3.3 70B Versatile)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 32768
        assert capabilities.supports_extended_thinking is False

        # Test Llama Guard 4
        capabilities = provider.get_capabilities("meta-llama/llama-guard-4-12b")
        assert capabilities.model_name == "meta-llama/llama-guard-4-12b"
        assert capabilities.friendly_name == "Groq (Llama Guard 4 12B)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 1024
        assert capabilities.supports_function_calling is False
        assert capabilities.max_image_size_mb == 20.0

    def test_get_capabilities_preview_models(self):
        """Test getting model capabilities for preview models."""
        provider = GroqProvider("test-key")

        # Test DeepSeek R1
        capabilities = provider.get_capabilities("deepseek-r1-distill-llama-70b")
        assert capabilities.model_name == "deepseek-r1-distill-llama-70b"
        assert capabilities.friendly_name == "Groq (DeepSeek R1 Distill Llama 70B)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 131072
        assert capabilities.supports_extended_thinking is True  # Only reasoning model

        # Test Llama 4 Maverick (multimodal)
        capabilities = provider.get_capabilities("meta-llama/llama-4-maverick-17b-128e-instruct")
        assert capabilities.model_name == "meta-llama/llama-4-maverick-17b-128e-instruct"
        assert capabilities.friendly_name == "Groq (Llama 4 Maverick 17B)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 8192
        assert capabilities.supports_images is True
        assert capabilities.max_image_size_mb == 20.0

        # Test Mistral Saba
        capabilities = provider.get_capabilities("mistral-saba-24b")
        assert capabilities.model_name == "mistral-saba-24b"
        assert capabilities.friendly_name == "Groq (Mistral Saba 24B)"
        assert capabilities.context_window == 32768
        assert capabilities.max_output_tokens == 32768

        # Test Kimi K2
        capabilities = provider.get_capabilities("moonshotai/kimi-k2-instruct")
        assert capabilities.model_name == "moonshotai/kimi-k2-instruct"
        assert capabilities.friendly_name == "Groq (Kimi K2 Instruct)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 16384

        # Test Qwen 3
        capabilities = provider.get_capabilities("qwen/qwen3-32b")
        assert capabilities.model_name == "qwen/qwen3-32b"
        assert capabilities.friendly_name == "Groq (Qwen 3 32B)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 40960

    def test_get_capabilities_preview_systems(self):
        """Test getting model capabilities for preview systems."""
        provider = GroqProvider("test-key")

        # Test Compound Beta
        capabilities = provider.get_capabilities("compound-beta")
        assert capabilities.model_name == "compound-beta"
        assert capabilities.friendly_name == "Groq (Compound Beta)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 8192
        assert capabilities.supports_function_calling is True

        # Test Compound Beta Mini
        capabilities = provider.get_capabilities("compound-beta-mini")
        assert capabilities.model_name == "compound-beta-mini"
        assert capabilities.friendly_name == "Groq (Compound Beta Mini)"
        assert capabilities.context_window == 131072
        assert capabilities.max_output_tokens == 8192

    def test_get_capabilities_with_aliases(self):
        """Test getting model capabilities with aliases."""
        provider = GroqProvider("test-key")

        capabilities = provider.get_capabilities("gemma2")
        assert capabilities.model_name == "gemma2-9b-it"  # Should resolve to full name
        assert capabilities.context_window == 8192

        capabilities_llama = provider.get_capabilities("llama-8b")
        assert capabilities_llama.model_name == "llama-3.1-8b-instant"  # Should resolve to full name
        assert capabilities_llama.context_window == 131072

        capabilities_deepseek = provider.get_capabilities("deepseek-r1")
        assert capabilities_deepseek.model_name == "deepseek-r1-distill-llama-70b"
        assert capabilities_deepseek.supports_extended_thinking is True

    def test_unsupported_model_capabilities(self):
        """Test error handling for unsupported models."""
        provider = GroqProvider("test-key")

        with pytest.raises(ValueError, match="Unsupported Groq model"):
            provider.get_capabilities("invalid-model")

        with pytest.raises(ValueError, match="Unsupported Groq model"):
            provider.get_capabilities("llama-guard-3-8b")  # Old model

    def test_thinking_mode_support(self):
        """Test that only DeepSeek R1 supports thinking mode."""
        provider = GroqProvider("test-key")

        # Only DeepSeek R1 supports thinking mode
        assert provider.supports_thinking_mode("deepseek-r1-distill-llama-70b") is True
        assert provider.supports_thinking_mode("deepseek-r1") is True

        # All other models are optimized for speed, not extended reasoning
        assert provider.supports_thinking_mode("gemma2-9b-it") is False
        assert provider.supports_thinking_mode("llama-3.1-8b-instant") is False
        assert provider.supports_thinking_mode("llama-3.3-70b-versatile") is False
        assert provider.supports_thinking_mode("meta-llama/llama-guard-4-12b") is False
        assert provider.supports_thinking_mode("meta-llama/llama-4-maverick-17b-128e-instruct") is False
        assert provider.supports_thinking_mode("mistral-saba-24b") is False
        assert provider.supports_thinking_mode("compound-beta") is False

    def test_vision_support(self):
        """Test vision support for Groq models."""
        provider = GroqProvider("test-key")

        # Only Llama 4 models support vision
        assert provider._supports_vision("meta-llama/llama-4-maverick-17b-128e-instruct") is True
        assert provider._supports_vision("meta-llama/llama-4-scout-17b-16e-instruct") is True
        assert provider._supports_vision("llama-4-maverick") is True
        assert provider._supports_vision("llama-4-scout") is True

        # All other models don't support vision
        assert provider._supports_vision("gemma2-9b-it") is False
        assert provider._supports_vision("llama-3.1-8b-instant") is False
        assert provider._supports_vision("llama-3.3-70b-versatile") is False
        assert provider._supports_vision("deepseek-r1-distill-llama-70b") is False
        assert provider._supports_vision("mistral-saba-24b") is False
        assert provider._supports_vision("compound-beta") is False

    def test_provider_type(self):
        """Test provider type identification."""
        provider = GroqProvider("test-key")
        assert provider.get_provider_type() == ProviderType.GROQ

    @patch.dict(os.environ, {"GROQ_ALLOWED_MODELS": "gemma2-9b-it,deepseek-r1-distill-llama-70b"})
    def test_model_restrictions(self):
        """Test model restrictions functionality."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = GroqProvider("test-key")

        # Listed models should be allowed
        assert provider.validate_model_name("gemma2-9b-it") is True
        assert provider.validate_model_name("deepseek-r1-distill-llama-70b") is True
        assert provider.validate_model_name("gemma2") is True  # Alias for gemma2-9b-it
        assert provider.validate_model_name("deepseek-r1") is True  # Alias for deepseek-r1

        # Other models should be blocked by restrictions
        assert provider.validate_model_name("llama-3.1-8b-instant") is False
        assert provider.validate_model_name("llama-8b") is False
        assert provider.validate_model_name("compound-beta") is False

    @patch.dict(os.environ, {"GROQ_ALLOWED_MODELS": "llama-8b,llama-4-maverick,compound"})
    def test_alias_restrictions(self):
        """Test restrictions with aliases."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = GroqProvider("test-key")

        # Aliases should be allowed
        assert provider.validate_model_name("llama-8b") is True
        assert provider.validate_model_name("llama-4-maverick") is True
        assert provider.validate_model_name("compound") is True

        # Full names should be blocked if not explicitly listed
        assert provider.validate_model_name("llama-3.1-8b-instant") is False
        assert provider.validate_model_name("meta-llama/llama-4-maverick-17b-128e-instruct") is False
        assert provider.validate_model_name("compound-beta") is False

    @patch.dict(os.environ, {"GROQ_ALLOWED_MODELS": ""})
    def test_empty_restrictions_allows_all(self):
        """Test that empty restrictions allow all models."""
        # Clear cached restriction service
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        provider = GroqProvider("test-key")

        # All models should be allowed
        assert provider.validate_model_name("gemma2-9b-it") is True
        assert provider.validate_model_name("llama-3.1-8b-instant") is True
        assert provider.validate_model_name("deepseek-r1-distill-llama-70b") is True
        assert provider.validate_model_name("meta-llama/llama-4-maverick-17b-128e-instruct") is True
        assert provider.validate_model_name("compound-beta") is True

    def test_friendly_name(self):
        """Test friendly name constant."""
        provider = GroqProvider("test-key")
        assert provider.FRIENDLY_NAME == "Groq"

        capabilities = provider.get_capabilities("gemma2-9b-it")
        assert capabilities.friendly_name == "Groq (Gemma2 9B)"

    def test_supported_models_structure(self):
        """Test that SUPPORTED_MODELS has the correct structure."""
        provider = GroqProvider("test-key")

        # Check that all expected models are present
        expected_models = [
            "gemma2-9b-it",
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "meta-llama/llama-guard-4-12b",
            "deepseek-r1-distill-llama-70b",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "mistral-saba-24b",
            "moonshotai/kimi-k2-instruct",
            "qwen/qwen3-32b",
            "compound-beta",
            "compound-beta-mini",
        ]

        for model in expected_models:
            assert model in provider.SUPPORTED_MODELS

        # Check model configs have required fields
        from providers.base import ModelCapabilities

        gemma2_config = provider.SUPPORTED_MODELS["gemma2-9b-it"]
        assert isinstance(gemma2_config, ModelCapabilities)
        assert hasattr(gemma2_config, "context_window")
        assert hasattr(gemma2_config, "supports_extended_thinking")
        assert hasattr(gemma2_config, "aliases")
        assert gemma2_config.context_window == 8192
        assert gemma2_config.supports_extended_thinking is False

        # Check aliases are correctly structured
        assert "gemma2-9b-it" in gemma2_config.aliases
        assert "gemma2" in gemma2_config.aliases

    @patch("providers.openai_compatible.OpenAI")
    def test_generate_content_resolves_alias_before_api_call(self, mock_openai_class):
        """Test that generate_content resolves aliases before making API calls."""
        # Set up mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.model = "gemma2-9b-it"  # API returns the resolved model name
        mock_response.id = "test-id"
        mock_response.created = 1234567890
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider("test-key")

        # Call generate_content with alias 'gemma2'
        result = provider.generate_content(
            prompt="Test prompt",
            model_name="gemma2",
            temperature=0.7,  # This should be resolved to "gemma2-9b-it"
        )

        # Verify the API was called with the RESOLVED model name
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]

        # CRITICAL ASSERTION: The API should receive "gemma2-9b-it", not "gemma2"
        assert (
            call_kwargs["model"] == "gemma2-9b-it"
        ), f"Expected 'gemma2-9b-it' but API received '{call_kwargs['model']}'"

        # Verify other parameters
        assert call_kwargs["temperature"] == 0.7
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        assert call_kwargs["messages"][0]["content"] == "Test prompt"

        # Verify response
        assert result.content == "Test response"
        assert result.model_name == "gemma2"  # Should be the requested name

    @patch("providers.openai_compatible.OpenAI")
    def test_generate_content_other_aliases(self, mock_openai_class):
        """Test other alias resolutions in generate_content."""
        from unittest.mock import MagicMock

        # Set up mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider("test-key")

        # Test llama-8b -> llama-3.1-8b-instant
        mock_response.model = "llama-3.1-8b-instant"
        provider.generate_content(prompt="Test", model_name="llama-8b", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "llama-3.1-8b-instant"

        # Test deepseek-r1 -> deepseek-r1-distill-llama-70b
        mock_response.model = "deepseek-r1-distill-llama-70b"
        provider.generate_content(prompt="Test", model_name="deepseek-r1", temperature=0.7)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "deepseek-r1-distill-llama-70b"

    def test_removed_prompt_guard_models(self):
        """Test that prompt guard models are no longer supported."""
        provider = GroqProvider("test-key")

        # These models should no longer be supported (incompatible with conversational format)
        assert provider.validate_model_name("meta-llama/llama-prompt-guard-2-22m") is False
        assert provider.validate_model_name("meta-llama/llama-prompt-guard-2-86m") is False
        assert provider.validate_model_name("guard-22m") is False
        assert provider.validate_model_name("guard-86m") is False
        assert provider.validate_model_name("prompt-guard-2-22m") is False
        assert provider.validate_model_name("prompt-guard-2-86m") is False
