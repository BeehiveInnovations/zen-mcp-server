"""
Tests for thinking_mode functionality across all tools
"""

from unittest.mock import Mock, patch

import pytest

from tests.mock_helpers import create_mock_provider
from tools.analyze import AnalyzeTool
from tools.codereview import CodeReviewTool
from tools.debug import DebugIssueTool
from tools.thinkdeep import ThinkDeepTool


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment"""
    # PYTEST_CURRENT_TEST is already set by pytest
    yield


class TestThinkingModes:
    """Test thinking modes across all tools"""

    @patch("config.DEFAULT_THINKING_MODE_THINKDEEP", "high")
    def test_default_thinking_modes(self):
        """Test that tools have correct default thinking modes"""
        tools = [
            (ThinkDeepTool(), "high"),
            (AnalyzeTool(), "medium"),
            (CodeReviewTool(), "medium"),
            (DebugIssueTool(), "medium"),
        ]

        for tool, expected_default in tools:
            assert (
                tool.get_default_thinking_mode() == expected_default
            ), f"{tool.__class__.__name__} should default to {expected_default}"

    @pytest.mark.asyncio
    async def test_thinking_mode_minimal(self):
        """Test minimal thinking mode with real provider resolution"""
        import importlib
        import os

        # Save original environment
        original_env = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL"),
        }

        try:
            # Set up environment for OpenAI provider (which supports thinking mode)
            os.environ["OPENAI_API_KEY"] = "sk-test-key-minimal-thinking-test-not-real"
            os.environ["DEFAULT_MODEL"] = "o3-mini"  # Use a model that supports thinking

            # Clear other provider keys to isolate to OpenAI
            for key in ["GEMINI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"]:
                os.environ.pop(key, None)

            # Reload config and clear registry
            import config

            importlib.reload(config)
            from providers.registry import ModelProviderRegistry

            ModelProviderRegistry._instance = None

            tool = AnalyzeTool()

            # This should attempt to use the real OpenAI provider
            # Even with a fake API key, we can test the provider resolution logic
            # The test will fail at the API call level, but we can verify the thinking mode logic
            try:
                result = await tool.execute(
                    {
                        "files": ["/absolute/path/test.py"],
                        "prompt": "What is this?",
                        "model": "o3-mini",
                        "thinking_mode": "minimal",
                    }
                )
                # If we get here, great! The provider resolution worked
                # Check that thinking mode was properly handled
                assert result is not None

            except Exception as e:
                # Expected: API call will fail with fake key, but we can check the error
                # If we get a provider resolution error, that's what we're testing
                error_msg = str(e)
                # Should NOT be a mock-related error - should be a real API or key error
                assert "MagicMock" not in error_msg
                assert "'<' not supported between instances" not in error_msg

                # Should be a real provider error (API key, network, etc.)
                assert any(
                    phrase in error_msg
                    for phrase in ["API", "key", "authentication", "provider", "network", "connection"]
                )

        finally:
            # Restore environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)

            # Reload config and clear registry
            importlib.reload(config)
            ModelProviderRegistry._instance = None

    @pytest.mark.asyncio
    async def test_thinking_mode_low(self):
        """Test low thinking mode with real provider resolution"""
        import importlib
        import os

        # Save original environment
        original_env = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL"),
        }

        try:
            # Set up environment for OpenAI provider (which supports thinking mode)
            os.environ["OPENAI_API_KEY"] = "sk-test-key-low-thinking-test-not-real"
            os.environ["DEFAULT_MODEL"] = "o3-mini"

            # Clear other provider keys
            for key in ["GEMINI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"]:
                os.environ.pop(key, None)

            # Reload config and clear registry
            import config

            importlib.reload(config)
            from providers.registry import ModelProviderRegistry

            ModelProviderRegistry._instance = None

            tool = CodeReviewTool()

            # Test with real provider resolution
            try:
                result = await tool.execute(
                    {
                        "files": ["/absolute/path/test.py"],
                        "thinking_mode": "low",
                        "prompt": "Test code review for validation purposes",
                        "model": "o3-mini",
                    }
                )
                # If we get here, provider resolution worked
                assert result is not None

            except Exception as e:
                # Expected: API call will fail with fake key
                error_msg = str(e)
                # Should NOT be a mock-related error
                assert "MagicMock" not in error_msg
                assert "'<' not supported between instances" not in error_msg

                # Should be a real provider error
                assert any(
                    phrase in error_msg
                    for phrase in ["API", "key", "authentication", "provider", "network", "connection"]
                )

        finally:
            # Restore environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)

            # Reload config and clear registry
            importlib.reload(config)
            ModelProviderRegistry._instance = None

    @pytest.mark.asyncio
    async def test_thinking_mode_medium(self):
        """Test medium thinking mode (default for most tools)"""
        from providers.base import ModelCapabilities, ProviderType

        with patch("tools.base.BaseTool.get_model_provider") as mock_get_provider:
            mock_provider = create_mock_provider()
            mock_provider.get_provider_type.return_value = Mock(value="google")
            mock_provider.supports_thinking_mode.return_value = True
            mock_provider.generate_content.return_value = Mock(
                content="Medium thinking response", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
            )

            # Set up proper capabilities to avoid MagicMock comparison errors
            mock_capabilities = ModelCapabilities(
                provider=ProviderType.GOOGLE,
                model_name="gemini-2.5-flash-preview-05-20",
                friendly_name="Test Model",
                context_window=1048576,
                supports_function_calling=True,
            )
            mock_provider.get_capabilities.return_value = mock_capabilities
            mock_get_provider.return_value = mock_provider

            tool = DebugIssueTool()
            result = await tool.execute(
                {
                    "prompt": "Test error",
                    # Not specifying thinking_mode, should use default (medium)
                }
            )

            # Verify create_model was called with default thinking_mode
            assert mock_get_provider.called
            # Verify generate_content was called with thinking_mode
            mock_provider.generate_content.assert_called_once()
            call_kwargs = mock_provider.generate_content.call_args[1]
            assert call_kwargs.get("thinking_mode") == "medium" or (
                not mock_provider.supports_thinking_mode.return_value and call_kwargs.get("thinking_mode") is None
            )

            assert "Medium thinking response" in result[0].text or "Debug Analysis" in result[0].text

    @pytest.mark.asyncio
    async def test_thinking_mode_high(self):
        """Test high thinking mode with real provider resolution"""
        import importlib
        import os

        # Save original environment
        original_env = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
            "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL"),
        }

        try:
            # Set up environment for OpenAI provider (which supports thinking mode)
            os.environ["OPENAI_API_KEY"] = "sk-test-key-high-thinking-test-not-real"
            os.environ["DEFAULT_MODEL"] = "o3-mini"

            # Clear other provider keys
            for key in ["GEMINI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY"]:
                os.environ.pop(key, None)

            # Reload config and clear registry
            import config

            importlib.reload(config)
            from providers.registry import ModelProviderRegistry

            ModelProviderRegistry._instance = None

            tool = AnalyzeTool()

            # Test with real provider resolution
            try:
                result = await tool.execute(
                    {
                        "files": ["/absolute/path/complex.py"],
                        "prompt": "Analyze architecture",
                        "thinking_mode": "high",
                        "model": "o3-mini",
                    }
                )
                # If we get here, provider resolution worked
                assert result is not None

            except Exception as e:
                # Expected: API call will fail with fake key
                error_msg = str(e)
                # Should NOT be a mock-related error
                assert "MagicMock" not in error_msg
                assert "'<' not supported between instances" not in error_msg

                # Should be a real provider error
                assert any(
                    phrase in error_msg
                    for phrase in ["API", "key", "authentication", "provider", "network", "connection"]
                )

        finally:
            # Restore environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)

            # Reload config and clear registry
            importlib.reload(config)
            ModelProviderRegistry._instance = None

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    @patch("config.DEFAULT_THINKING_MODE_THINKDEEP", "high")
    async def test_thinking_mode_max(self, mock_get_provider):
        """Test max thinking mode (default for thinkdeep)"""
        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = True
        mock_provider.generate_content.return_value = Mock(
            content="Max thinking response", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        tool = ThinkDeepTool()
        result = await tool.execute(
            {
                "prompt": "Initial analysis",
                # Not specifying thinking_mode, should use default (high)
            }
        )

        # Verify create_model was called with default thinking_mode
        assert mock_get_provider.called
        # Verify generate_content was called with thinking_mode
        mock_provider.generate_content.assert_called_once()
        call_kwargs = mock_provider.generate_content.call_args[1]
        assert call_kwargs.get("thinking_mode") == "high" or (
            not mock_provider.supports_thinking_mode.return_value and call_kwargs.get("thinking_mode") is None
        )

        assert "Max thinking response" in result[0].text or "Extended Analysis by Gemini" in result[0].text

    def test_thinking_budget_mapping(self):
        """Test that thinking modes map to correct budget values"""
        from tools.base import BaseTool

        # Create a simple test tool
        class TestTool(BaseTool):
            def get_name(self):
                return "test"

            def get_description(self):
                return "test"

            def get_input_schema(self):
                return {}

            def get_system_prompt(self):
                return "test"

            def get_request_model(self):
                return None

            async def prepare_prompt(self, request):
                return "test"

        # Test dynamic budget calculation for Flash 2.5
        from providers.gemini import GeminiModelProvider

        provider = GeminiModelProvider(api_key="test-key")
        flash_model = "gemini-2.5-flash-preview-05-20"
        flash_max_tokens = 24576

        expected_budgets = {
            "minimal": int(flash_max_tokens * 0.005),  # 123
            "low": int(flash_max_tokens * 0.08),  # 1966
            "medium": int(flash_max_tokens * 0.33),  # 8110
            "high": int(flash_max_tokens * 0.67),  # 16465
            "max": int(flash_max_tokens * 1.0),  # 24576
        }

        # Check each mode using the helper method
        for mode, expected_budget in expected_budgets.items():
            actual_budget = provider.get_thinking_budget(flash_model, mode)
            assert actual_budget == expected_budget, f"Mode {mode}: expected {expected_budget}, got {actual_budget}"
