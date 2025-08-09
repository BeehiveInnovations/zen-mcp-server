"""Functional tests for ChatGPT authentication integration."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestChatGPTFunctional:
    """Functional tests for the complete ChatGPT authentication flow."""

    def test_end_to_end_chatgpt_authentication(self):
        """Test complete ChatGPT authentication flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup: Create a realistic auth file
            codex_dir = Path(temp_dir) / ".codex"
            codex_dir.mkdir()
            auth_file = codex_dir / "auth.json"

            # Use realistic auth data structure (based on user's example)
            auth_data = {
                "OPENAI_API_KEY": None,
                "tokens": {
                    "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImIxZGQzZjhmLTlhYWQtNDdmZS1iMGU3LWVkYjAwOTc3N2Q2YiIsInR5cCI6IkpXVCJ9...",
                    "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "rt_Q5_RJlnifFDOFXQ2UxJYjJRIcDvDHj1wdR2ZVAtvSVc.aaFuBDVHEN-T-O1ndmpzLEqtzTl3xgJmTl8pT4T2e5w",
                    "account_id": "f213aaef-b15f-4084-a2c9-e5e1b54ba05c",
                },
                "last_refresh": "2025-08-08T23:04:28.373728Z",
            }

            with open(auth_file, "w") as f:
                json.dump(auth_data, f)

            # Test: Import and use the auth utilities
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                with patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"}):
                    from utils.chatgpt_auth import get_valid_chatgpt_auth

                    # Verify auth is loaded correctly
                    auth = get_valid_chatgpt_auth()
                    assert auth is not None
                    assert auth.access_token.startswith("eyJhbGciOiJSUzI1NiIs")
                    assert auth.account_id == "f213aaef-b15f-4084-a2c9-e5e1b54ba05c"
                    assert auth.is_valid()

    def test_provider_factory_integration(self):
        """Test that provider factory works with ChatGPT tokens."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup auth file
            codex_dir = Path(temp_dir) / ".codex"
            codex_dir.mkdir()
            auth_file = codex_dir / "auth.json"

            auth_data = {
                "tokens": {
                    "access_token": "test_chatgpt_token",
                    "account_id": "test_account_id",
                    "refresh_token": "test_refresh",
                    "id_token": "test_id_token",
                },
                "last_refresh": "2025-01-01T00:00:00Z",
            }

            with open(auth_file, "w") as f:
                json.dump(auth_data, f)

            # Test provider creation
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                with patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"}):
                    from providers.openai_provider import OpenAIModelProvider

                    # Create provider with ChatGPT token
                    provider = OpenAIModelProvider("test_chatgpt_token")

                    # Verify ChatGPT-specific configuration
                    assert provider.base_url == "https://chatgpt.com/backend-api/codex/"
                    assert hasattr(provider, "DEFAULT_HEADERS")
                    headers = provider.DEFAULT_HEADERS
                    assert headers["Authorization"] == "Bearer test_chatgpt_token"
                    assert headers["originator"] == "codex_cli_rs"
                    assert headers["chatgpt-account-id"] == "test_account_id"

    def test_mode_disabled_uses_standard_api(self):
        """Test that standard OpenAI API is used when ChatGPT mode is disabled."""
        with patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "false"}):
            from providers.openai_provider import OpenAIModelProvider

            provider = OpenAIModelProvider("sk-standard_api_key")

            # Verify standard OpenAI configuration
            assert provider.base_url == "https://api.openai.com/v1"
            # Should not have ChatGPT headers
            if hasattr(provider, "DEFAULT_HEADERS"):
                headers = provider.DEFAULT_HEADERS or {}
                assert "originator" not in headers
                assert "chatgpt-account-id" not in headers

    def test_missing_auth_file_fallback(self):
        """Test fallback behavior when auth file is missing."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"}):
                from utils.chatgpt_auth import get_valid_chatgpt_auth

                # Should return None when auth file doesn't exist
                auth = get_valid_chatgpt_auth()
                assert auth is None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_auth_file(self):
        """Test handling of malformed auth files."""
        test_cases = [
            # Missing tokens section
            {"last_refresh": "2025-01-01T00:00:00Z"},
            # Empty tokens
            {"tokens": {}, "last_refresh": "2025-01-01T00:00:00Z"},
            # Missing required fields
            {"tokens": {"access_token": "token"}, "last_refresh": "2025-01-01T00:00:00Z"},
            # Empty required fields
            {"tokens": {"access_token": "", "account_id": "account"}, "last_refresh": "2025-01-01T00:00:00Z"},
        ]

        for auth_data in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                codex_dir = Path(temp_dir) / ".codex"
                codex_dir.mkdir()
                auth_file = codex_dir / "auth.json"

                with open(auth_file, "w") as f:
                    json.dump(auth_data, f)

                with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                    with patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"}):
                        from utils.chatgpt_auth import get_valid_chatgpt_auth

                        # Should return None for invalid auth data
                        auth = get_valid_chatgpt_auth()
                        assert auth is None

    def test_environment_variable_variations(self):
        """Test different environment variable values."""
        from utils.chatgpt_auth import is_chatgpt_mode_enabled

        test_cases = [
            ("true", True),
            ("TRUE", True),
            ("True", True),
            ("false", False),
            ("FALSE", False),
            ("", False),
            ("invalid", False),
            ("1", False),
            ("yes", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": env_value}):
                assert is_chatgpt_mode_enabled() == expected
