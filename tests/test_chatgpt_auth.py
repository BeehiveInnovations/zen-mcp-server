"""Tests for ChatGPT authentication utilities."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

from utils.chatgpt_auth import ChatGPTAuth, get_chatgpt_auth, get_valid_chatgpt_auth, is_chatgpt_mode_enabled


class TestChatGPTAuth:
    """Test ChatGPTAuth dataclass."""

    def test_valid_auth(self):
        """Test valid authentication data."""
        auth = ChatGPTAuth(
            access_token="access_123",
            account_id="account_456",
            refresh_token="refresh_789",
            id_token="id_abc",
            last_refresh="2025-01-01T00:00:00Z",
        )
        assert auth.is_valid() is True

    def test_invalid_auth_missing_access_token(self):
        """Test invalid auth with missing access token."""
        auth = ChatGPTAuth(
            access_token="",
            account_id="account_456",
            refresh_token="refresh_789",
            id_token="id_abc",
            last_refresh="2025-01-01T00:00:00Z",
        )
        assert auth.is_valid() is False

    def test_invalid_auth_missing_account_id(self):
        """Test invalid auth with missing account ID."""
        auth = ChatGPTAuth(
            access_token="access_123",
            account_id="",
            refresh_token="refresh_789",
            id_token="id_abc",
            last_refresh="2025-01-01T00:00:00Z",
        )
        assert auth.is_valid() is False


class TestGetChatGPTAuth:
    """Test get_chatgpt_auth function."""

    def test_auth_file_not_exists(self):
        """Test when auth file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = get_chatgpt_auth()
            assert result is None

    def test_auth_file_valid_data(self):
        """Test with valid auth file data."""
        auth_data = {
            "tokens": {
                "access_token": "access_123",
                "account_id": "account_456",
                "refresh_token": "refresh_789",
                "id_token": "id_abc",
            },
            "last_refresh": "2025-01-01T00:00:00Z",
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(auth_data))):
                result = get_chatgpt_auth()

                assert result is not None
                assert result.access_token == "access_123"
                assert result.account_id == "account_456"
                assert result.refresh_token == "refresh_789"
                assert result.id_token == "id_abc"
                assert result.last_refresh == "2025-01-01T00:00:00Z"

    def test_auth_file_missing_tokens(self):
        """Test with auth file missing tokens section."""
        auth_data = {"last_refresh": "2025-01-01T00:00:00Z"}

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(auth_data))):
                result = get_chatgpt_auth()

                assert result is not None
                assert result.access_token == ""
                assert result.account_id == ""

    def test_auth_file_invalid_json(self):
        """Test with invalid JSON in auth file."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid json")):
                result = get_chatgpt_auth()
                assert result is None

    def test_auth_file_read_error(self):
        """Test with file read error."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=OSError("Read error")):
                result = get_chatgpt_auth()
                assert result is None


class TestIsChatGPTModeEnabled:
    """Test is_chatgpt_mode_enabled function."""

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"})
    def test_mode_enabled_true(self):
        """Test when mode is enabled with 'true'."""
        assert is_chatgpt_mode_enabled() is True

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "TRUE"})
    def test_mode_enabled_uppercase(self):
        """Test when mode is enabled with 'TRUE'."""
        assert is_chatgpt_mode_enabled() is True

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "false"})
    def test_mode_disabled_false(self):
        """Test when mode is disabled with 'false'."""
        assert is_chatgpt_mode_enabled() is False

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "invalid"})
    def test_mode_disabled_invalid(self):
        """Test when mode has invalid value."""
        assert is_chatgpt_mode_enabled() is False

    @patch.dict(os.environ, {}, clear=True)
    def test_mode_not_set(self):
        """Test when environment variable is not set."""
        assert is_chatgpt_mode_enabled() is False


class TestGetValidChatGPTAuth:
    """Test get_valid_chatgpt_auth function."""

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "false"})
    def test_mode_disabled(self):
        """Test when ChatGPT mode is disabled."""
        result = get_valid_chatgpt_auth()
        assert result is None

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"})
    def test_mode_enabled_no_auth_file(self):
        """Test when mode is enabled but no auth file."""
        with patch("pathlib.Path.exists", return_value=False):
            result = get_valid_chatgpt_auth()
            assert result is None

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"})
    def test_mode_enabled_valid_auth(self):
        """Test when mode is enabled with valid auth."""
        auth_data = {
            "tokens": {
                "access_token": "access_123",
                "account_id": "account_456",
                "refresh_token": "refresh_789",
                "id_token": "id_abc",
            },
            "last_refresh": "2025-01-01T00:00:00Z",
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(auth_data))):
                result = get_valid_chatgpt_auth()

                assert result is not None
                assert result.access_token == "access_123"
                assert result.account_id == "account_456"

    @patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"})
    def test_mode_enabled_invalid_auth(self):
        """Test when mode is enabled but auth is invalid."""
        auth_data = {
            "tokens": {
                "access_token": "",  # Empty access token
                "account_id": "account_456",
                "refresh_token": "refresh_789",
                "id_token": "id_abc",
            },
            "last_refresh": "2025-01-01T00:00:00Z",
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(auth_data))):
                result = get_valid_chatgpt_auth()
                assert result is None


class TestIntegration:
    """Integration tests for ChatGPT auth functionality."""

    def test_real_file_system(self):
        """Test with real file system operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary auth file
            codex_dir = Path(temp_dir) / ".codex"
            codex_dir.mkdir()
            auth_file = codex_dir / "auth.json"

            auth_data = {
                "tokens": {
                    "access_token": "real_access_token",
                    "account_id": "real_account_id",
                    "refresh_token": "real_refresh_token",
                    "id_token": "real_id_token",
                },
                "last_refresh": "2025-01-01T12:00:00Z",
            }

            with open(auth_file, "w") as f:
                json.dump(auth_data, f)

            # Mock Path.home() to return our temp directory
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                with patch.dict(os.environ, {"OPENAI_CHATGPT_LOGIN_MODE": "true"}):
                    result = get_valid_chatgpt_auth()

                    assert result is not None
                    assert result.access_token == "real_access_token"
                    assert result.account_id == "real_account_id"
                    assert result.is_valid() is True
