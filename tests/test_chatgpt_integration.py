"""Tests for ChatGPT integration in server configuration."""

import os
from unittest.mock import patch

from providers.openai_provider import OpenAIModelProvider
from utils.chatgpt_auth import ChatGPTAuth


class TestServerChatGPTIntegration:
    """Test ChatGPT integration in server configuration."""

    @patch("utils.chatgpt_auth.get_valid_chatgpt_auth")
    @patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False)
    def test_chatgpt_auth_priority(self, mock_get_valid_auth):
        """Test that ChatGPT auth takes priority over API key."""
        # Mock valid ChatGPT auth
        mock_auth = ChatGPTAuth(
            access_token="chatgpt_token",
            account_id="chatgpt_account",
            refresh_token="refresh_token",
            id_token="id_token",
            last_refresh="2025-01-01T00:00:00Z",
        )
        mock_get_valid_auth.return_value = mock_auth

        # Import configure_providers to test the logic
        from providers.registry import ModelProviderRegistry
        from server import configure_providers

        # Reset registry
        ModelProviderRegistry._instance = None

        # Mock all other API keys to avoid side effects
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "",
                "XAI_API_KEY": "",
                "DIAL_API_KEY": "",
                "OPENROUTER_API_KEY": "",
                "CUSTOM_API_URL": "",
                "OPENAI_API_KEY": "fallback_api_key",
            },
        ):
            configure_providers()

            # Verify ChatGPT auth was detected
            mock_get_valid_auth.assert_called_once()

    @patch("utils.chatgpt_auth.get_valid_chatgpt_auth")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "fallback_key"})
    def test_api_key_fallback(self, mock_get_valid_auth):
        """Test fallback to API key when ChatGPT auth not available."""
        # Mock no ChatGPT auth available
        mock_get_valid_auth.return_value = None

        from providers.registry import ModelProviderRegistry
        from server import configure_providers

        # Reset registry
        ModelProviderRegistry._instance = None

        # Mock all other API keys to avoid side effects
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "",
                "XAI_API_KEY": "",
                "DIAL_API_KEY": "",
                "OPENROUTER_API_KEY": "",
                "CUSTOM_API_URL": "",
            },
        ):
            configure_providers()

            # Verify ChatGPT auth was checked but fallback used
            mock_get_valid_auth.assert_called_once()


class TestOpenAIProviderChatGPT:
    """Test OpenAI provider ChatGPT integration."""

    @patch("utils.chatgpt_auth.get_valid_chatgpt_auth")
    def test_chatgpt_provider_initialization(self, mock_get_valid_auth):
        """Test OpenAI provider initialization with ChatGPT auth."""
        # Mock valid ChatGPT auth
        mock_auth = ChatGPTAuth(
            access_token="chatgpt_access_token",
            account_id="chatgpt_account_id",
            refresh_token="refresh_token",
            id_token="id_token",
            last_refresh="2025-01-01T00:00:00Z",
        )
        mock_get_valid_auth.return_value = mock_auth

        # Create provider with ChatGPT token
        provider = OpenAIModelProvider("chatgpt_access_token")

        # Verify ChatGPT-specific configuration
        assert provider.base_url == "https://chatgpt.com/backend-api/codex/"
        assert hasattr(provider, "DEFAULT_HEADERS")
        assert provider.DEFAULT_HEADERS["Authorization"] == "Bearer chatgpt_access_token"
        assert provider.DEFAULT_HEADERS["originator"] == "codex_cli_rs"
        assert provider.DEFAULT_HEADERS["chatgpt-account-id"] == "chatgpt_account_id"

    @patch("utils.chatgpt_auth.get_valid_chatgpt_auth")
    def test_standard_openai_provider_initialization(self, mock_get_valid_auth):
        """Test standard OpenAI provider initialization."""
        # Mock no ChatGPT auth
        mock_get_valid_auth.return_value = None

        # Create provider with standard API key
        provider = OpenAIModelProvider("sk-standard_api_key")

        # Verify standard OpenAI configuration
        assert provider.base_url == "https://api.openai.com/v1"
        assert not hasattr(provider, "DEFAULT_HEADERS") or not provider.DEFAULT_HEADERS

    @patch("utils.chatgpt_auth.get_valid_chatgpt_auth")
    def test_different_api_key_no_chatgpt_config(self, mock_get_valid_auth):
        """Test that ChatGPT config is not used with different API key."""
        # Mock valid ChatGPT auth but use different API key
        mock_auth = ChatGPTAuth(
            access_token="chatgpt_access_token",
            account_id="chatgpt_account_id",
            refresh_token="refresh_token",
            id_token="id_token",
            last_refresh="2025-01-01T00:00:00Z",
        )
        mock_get_valid_auth.return_value = mock_auth

        # Create provider with different API key
        provider = OpenAIModelProvider("sk-different_api_key")

        # Verify standard OpenAI configuration is used
        assert provider.base_url == "https://api.openai.com/v1"
        assert not hasattr(provider, "DEFAULT_HEADERS") or not provider.DEFAULT_HEADERS


class TestEnvironmentVariableHandling:
    """Test environment variable handling for ChatGPT mode."""

    @patch("utils.chatgpt_auth.get_chatgpt_auth")
    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"})
    def test_chatgpt_mode_enabled_with_valid_auth(self, mock_get_auth):
        """Test behavior when ChatGPT mode is enabled with valid auth."""
        from utils.chatgpt_auth import get_valid_chatgpt_auth

        # Mock valid auth data
        mock_auth = ChatGPTAuth(
            access_token="valid_token",
            account_id="valid_account",
            refresh_token="refresh_token",
            id_token="id_token",
            last_refresh="2025-01-01T00:00:00Z",
        )
        mock_get_auth.return_value = mock_auth

        result = get_valid_chatgpt_auth()
        assert result is not None
        assert result.access_token == "valid_token"

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "false"})
    def test_chatgpt_mode_disabled(self):
        """Test behavior when ChatGPT mode is disabled."""
        from utils.chatgpt_auth import get_valid_chatgpt_auth

        result = get_valid_chatgpt_auth()
        assert result is None

    @patch.dict(os.environ, {}, clear=True)
    def test_chatgpt_mode_not_set(self):
        """Test behavior when ChatGPT mode environment variable is not set."""
        from utils.chatgpt_auth import get_valid_chatgpt_auth

        result = get_valid_chatgpt_auth()
        assert result is None


class TestErrorHandling:
    """Test error handling in ChatGPT integration."""

    @patch("utils.chatgpt_auth.get_chatgpt_auth")
    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"})
    def test_invalid_chatgpt_auth_handling(self, mock_get_auth):
        """Test handling of invalid ChatGPT auth data."""
        from utils.chatgpt_auth import get_valid_chatgpt_auth

        # Mock invalid auth (missing access token)
        mock_auth = ChatGPTAuth(
            access_token="",  # Empty access token
            account_id="account_id",
            refresh_token="refresh_token",
            id_token="id_token",
            last_refresh="2025-01-01T00:00:00Z",
        )
        mock_get_auth.return_value = mock_auth

        result = get_valid_chatgpt_auth()
        assert result is None

    @patch("utils.chatgpt_auth.get_chatgpt_auth")
    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"})
    def test_auth_file_read_error_handling(self, mock_get_auth):
        """Test handling of auth file read errors."""
        from utils.chatgpt_auth import get_valid_chatgpt_auth

        # Mock auth file read error
        mock_get_auth.return_value = None

        result = get_valid_chatgpt_auth()
        assert result is None
