"""
Test suite for intelligent auto mode fallback logic

Tests the new dynamic model selection based on available API keys
"""

import os
from unittest.mock import Mock, patch

import pytest

from providers.base import ProviderType
from providers.registry import ModelProviderRegistry


class TestIntelligentFallback:
    """Test intelligent model fallback logic"""

    def setup_method(self):
        """Setup for each test - clear registry cache"""
        ModelProviderRegistry.clear_cache()

    def teardown_method(self):
        """Cleanup after each test"""
        ModelProviderRegistry.clear_cache()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key", "GEMINI_API_KEY": ""}, clear=False)
    def test_prefers_openai_o3_mini_when_available(self):
        """Test that o3-mini is preferred when OpenAI API key is available"""
        ModelProviderRegistry.clear_cache()
        fallback_model = ModelProviderRegistry.get_preferred_fallback_model()
        assert fallback_model == "o3-mini"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": "test-gemini-key"}, clear=False)
    def test_prefers_gemini_flash_when_openai_unavailable(self):
        """Test that gemini-2.5-flash-preview-05-20 is used when only Gemini API key is available"""
        ModelProviderRegistry.clear_cache()
        fallback_model = ModelProviderRegistry.get_preferred_fallback_model()
        assert fallback_model == "gemini-2.5-flash-preview-05-20"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key", "GEMINI_API_KEY": "test-gemini-key"}, clear=False)
    def test_prefers_openai_when_both_available(self):
        """Test that OpenAI is preferred when both API keys are available"""
        ModelProviderRegistry.clear_cache()
        fallback_model = ModelProviderRegistry.get_preferred_fallback_model()
        assert fallback_model == "o3-mini"  # OpenAI has priority

    @patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": ""}, clear=False)
    def test_fallback_when_no_keys_available(self):
        """Test fallback behavior when no API keys are available"""
        ModelProviderRegistry.clear_cache()
        fallback_model = ModelProviderRegistry.get_preferred_fallback_model()
        assert fallback_model == "gemini-2.5-flash-preview-05-20"  # Default fallback

    def test_available_providers_with_keys(self):
        """Test the get_available_providers_with_keys method"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key", "GEMINI_API_KEY": ""}, clear=False):
            ModelProviderRegistry.clear_cache()
            available = ModelProviderRegistry.get_available_providers_with_keys()
            assert ProviderType.OPENAI in available
            assert ProviderType.GOOGLE not in available

        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": "test-key"}, clear=False):
            ModelProviderRegistry.clear_cache()
            available = ModelProviderRegistry.get_available_providers_with_keys()
            assert ProviderType.GOOGLE in available
            assert ProviderType.OPENAI not in available

    def test_auto_mode_conversation_memory_integration(self):
        """Test that conversation memory uses intelligent fallback in auto mode"""
        from utils.conversation_memory import ThreadContext, build_conversation_history

        # Mock auto mode - patch the config module where these values are defined
        with (
            patch("config.IS_AUTO_MODE", True),
            patch("config.DEFAULT_MODEL", "auto"),
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key", "GEMINI_API_KEY": ""}, clear=False),
        ):
            ModelProviderRegistry.clear_cache()

            # Create a context with at least one turn so it doesn't exit early
            from utils.conversation_memory import ConversationTurn

            context = ThreadContext(
                thread_id="test-123",
                created_at="2023-01-01T00:00:00Z",
                last_updated_at="2023-01-01T00:00:00Z",
                tool_name="chat",
                turns=[ConversationTurn(role="user", content="Test message", timestamp="2023-01-01T00:00:30Z")],
                initial_context={},
            )

            # This should use o3-mini for token calculations since OpenAI is available
            with patch("utils.model_context.ModelContext") as mock_context_class:
                mock_context_instance = Mock()
                mock_context_class.return_value = mock_context_instance
                mock_context_instance.calculate_token_allocation.return_value = Mock(
                    file_tokens=10000, history_tokens=5000
                )
                # Mock estimate_tokens to return integers for proper summing
                mock_context_instance.estimate_tokens.return_value = 100

                history, tokens = build_conversation_history(context, model_context=None)

                # Verify that ModelContext was called with o3-mini (the intelligent fallback)
                mock_context_class.assert_called_once_with("o3-mini")

    def test_auto_mode_with_gemini_only(self):
        """Test auto mode behavior when only Gemini API key is available"""
        from utils.conversation_memory import ThreadContext, build_conversation_history

        with (
            patch("config.IS_AUTO_MODE", True),
            patch("config.DEFAULT_MODEL", "auto"),
            patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": "test-key"}, clear=False),
        ):
            ModelProviderRegistry.clear_cache()

            from utils.conversation_memory import ConversationTurn

            context = ThreadContext(
                thread_id="test-456",
                created_at="2023-01-01T00:00:00Z",
                last_updated_at="2023-01-01T00:00:00Z",
                tool_name="analyze",
                turns=[ConversationTurn(role="assistant", content="Test response", timestamp="2023-01-01T00:00:30Z")],
                initial_context={},
            )

            with patch("utils.model_context.ModelContext") as mock_context_class:
                mock_context_instance = Mock()
                mock_context_class.return_value = mock_context_instance
                mock_context_instance.calculate_token_allocation.return_value = Mock(
                    file_tokens=10000, history_tokens=5000
                )
                # Mock estimate_tokens to return integers for proper summing
                mock_context_instance.estimate_tokens.return_value = 100

                history, tokens = build_conversation_history(context, model_context=None)

                # Should use gemini-2.5-flash-preview-05-20 when only Gemini is available
                mock_context_class.assert_called_once_with("gemini-2.5-flash-preview-05-20")

    def test_non_auto_mode_unchanged(self):
        """Test that non-auto mode behavior is unchanged"""
        from utils.conversation_memory import ThreadContext, build_conversation_history

        with patch("config.IS_AUTO_MODE", False), patch("config.DEFAULT_MODEL", "gemini-2.5-pro-preview-06-05"):
            from utils.conversation_memory import ConversationTurn

            context = ThreadContext(
                thread_id="test-789",
                created_at="2023-01-01T00:00:00Z",
                last_updated_at="2023-01-01T00:00:00Z",
                tool_name="thinkdeep",
                turns=[
                    ConversationTurn(role="user", content="Test in non-auto mode", timestamp="2023-01-01T00:00:30Z")
                ],
                initial_context={},
            )

            with patch("utils.model_context.ModelContext") as mock_context_class:
                mock_context_instance = Mock()
                mock_context_class.return_value = mock_context_instance
                mock_context_instance.calculate_token_allocation.return_value = Mock(
                    file_tokens=10000, history_tokens=5000
                )
                # Mock estimate_tokens to return integers for proper summing
                mock_context_instance.estimate_tokens.return_value = 100

                history, tokens = build_conversation_history(context, model_context=None)

                # Should use the configured DEFAULT_MODEL, not the intelligent fallback
                mock_context_class.assert_called_once_with("gemini-2.5-pro-preview-06-05")


if __name__ == "__main__":
    pytest.main([__file__])
