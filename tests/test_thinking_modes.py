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
        """Test minimal thinking mode"""
        from unittest.mock import MagicMock
        from providers.base import ModelCapabilities, ProviderType

        with patch("tools.base.BaseTool.get_model_provider") as mock_get_provider:
            mock_provider = create_mock_provider()
            mock_provider.get_provider_type.return_value = Mock(value="google")
            mock_provider.supports_thinking_mode.return_value = True
            mock_provider.generate_content.return_value = Mock(
                content="Minimal thinking response", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
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

            tool = AnalyzeTool()
            result = await tool.execute(
                {
                    "files": ["/absolute/path/test.py"],
                    "prompt": "What is this?",
                    "thinking_mode": "minimal",
                }
            )

            # Verify create_model was called with correct thinking_mode
            assert mock_get_provider.called
            # Verify generate_content was called with thinking_mode
            mock_provider.generate_content.assert_called_once()
            call_kwargs = mock_provider.generate_content.call_args[1]
            assert call_kwargs.get("thinking_mode") == "minimal" or (
                not mock_provider.supports_thinking_mode.return_value and call_kwargs.get("thinking_mode") is None
            )  # thinking_mode parameter

            # Parse JSON response
            import json

            response_data = json.loads(result[0].text)
            assert response_data["status"] == "success"
            assert "Minimal thinking response" in response_data["content"] or "Analysis:" in response_data["content"]

    @pytest.mark.asyncio
    async def test_thinking_mode_low(self):
        """Test low thinking mode"""
        from unittest.mock import MagicMock
        from providers.base import ModelCapabilities, ProviderType

        with patch("tools.base.BaseTool.get_model_provider") as mock_get_provider:
            mock_provider = create_mock_provider()
            mock_provider.get_provider_type.return_value = Mock(value="google")
            mock_provider.supports_thinking_mode.return_value = True
            mock_provider.generate_content.return_value = Mock(
                content="Low thinking response", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
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

            tool = CodeReviewTool()
            result = await tool.execute(
                {
                    "files": ["/absolute/path/test.py"],
                    "thinking_mode": "low",
                    "prompt": "Test code review for validation purposes",
                }
            )

            # Verify create_model was called with correct thinking_mode
            assert mock_get_provider.called
            # Verify generate_content was called with thinking_mode
            mock_provider.generate_content.assert_called_once()
            call_kwargs = mock_provider.generate_content.call_args[1]
            assert call_kwargs.get("thinking_mode") == "low" or (
                not mock_provider.supports_thinking_mode.return_value and call_kwargs.get("thinking_mode") is None
            )

            assert "Low thinking response" in result[0].text or "Code Review" in result[0].text

    @pytest.mark.asyncio
    async def test_thinking_mode_medium(self):
        """Test medium thinking mode (default for most tools)"""
        from unittest.mock import MagicMock
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
        """Test high thinking mode"""
        from unittest.mock import MagicMock
        from providers.base import ModelCapabilities, ProviderType

        with patch("tools.base.BaseTool.get_model_provider") as mock_get_provider:
            mock_provider = create_mock_provider()
            mock_provider.get_provider_type.return_value = Mock(value="google")
            mock_provider.supports_thinking_mode.return_value = True
            mock_provider.generate_content.return_value = Mock(
                content="High thinking response", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
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

            tool = AnalyzeTool()
            await tool.execute(
                {
                    "files": ["/absolute/path/complex.py"],
                    "prompt": "Analyze architecture",
                    "thinking_mode": "high",
                }
            )

            # Verify create_model was called with correct thinking_mode
            assert mock_get_provider.called
            # Verify generate_content was called with thinking_mode
            mock_provider.generate_content.assert_called_once()
            call_kwargs = mock_provider.generate_content.call_args[1]
            assert call_kwargs.get("thinking_mode") == "high" or (
                not mock_provider.supports_thinking_mode.return_value and call_kwargs.get("thinking_mode") is None
            )

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
