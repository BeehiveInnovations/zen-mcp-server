"""
Test per-tool model default selection functionality
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from providers.registry import ModelProviderRegistry, ProviderType
from tools.analyze import AnalyzeTool
from tools.base import BaseTool
from tools.chat import ChatTool
from tools.codereview import CodeReviewTool
from tools.debug import DebugIssueTool
from tools.models import ToolModelCategory
from tools.precommit import Precommit
from tools.thinkdeep import ThinkDeepTool


class TestToolModelCategories:
    """Test that each tool returns the correct model category."""

    def test_thinkdeep_category(self):
        tool = ThinkDeepTool()
        assert tool.get_model_category() == ToolModelCategory.EXTENDED_REASONING

    def test_debug_category(self):
        tool = DebugIssueTool()
        assert tool.get_model_category() == ToolModelCategory.EXTENDED_REASONING

    def test_analyze_category(self):
        tool = AnalyzeTool()
        assert tool.get_model_category() == ToolModelCategory.EXTENDED_REASONING

    def test_precommit_category(self):
        tool = Precommit()
        assert tool.get_model_category() == ToolModelCategory.EXTENDED_REASONING

    def test_chat_category(self):
        tool = ChatTool()
        assert tool.get_model_category() == ToolModelCategory.FAST_RESPONSE

    def test_codereview_category(self):
        tool = CodeReviewTool()
        assert tool.get_model_category() == ToolModelCategory.BALANCED

    def test_base_tool_default_category(self):
        # Test that BaseTool defaults to BALANCED
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
                return MagicMock

            async def prepare_prompt(self, request):
                return "test"

        tool = TestTool()
        assert tool.get_model_category() == ToolModelCategory.BALANCED


class TestModelSelection:
    """Test model selection based on tool categories."""

    def test_extended_reasoning_with_openai(self):
        """Test EXTENDED_REASONING prefers o3 when OpenAI is available."""
        with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
            # Mock OpenAI models available
            mock_get_available.return_value = {
                "o3": ProviderType.OPENAI,
                "o3-mini": ProviderType.OPENAI,
                "o4-mini": ProviderType.OPENAI,
            }

            model = ModelProviderRegistry.get_preferred_fallback_model(ToolModelCategory.EXTENDED_REASONING)
            assert model == "o3"

    def test_extended_reasoning_with_gemini_only(self):
        """Test EXTENDED_REASONING prefers pro when only Gemini is available."""
        with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
            # Mock only Gemini models available
            mock_get_available.return_value = {
                "gemini-2.5-pro-preview-06-05": ProviderType.GOOGLE,
                "gemini-2.5-flash-preview-05-20": ProviderType.GOOGLE,
            }

            model = ModelProviderRegistry.get_preferred_fallback_model(ToolModelCategory.EXTENDED_REASONING)
            # Should find the pro model for extended reasoning
            assert "pro" in model or model == "gemini-2.5-pro-preview-06-05"

    def test_fast_response_with_openai(self):
        """Test FAST_RESPONSE prefers o4-mini when OpenAI is available."""
        with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
            # Mock OpenAI models available
            mock_get_available.return_value = {
                "o3": ProviderType.OPENAI,
                "o3-mini": ProviderType.OPENAI,
                "o4-mini": ProviderType.OPENAI,
            }

            model = ModelProviderRegistry.get_preferred_fallback_model(ToolModelCategory.FAST_RESPONSE)
            assert model == "o4-mini"

    def test_fast_response_with_gemini_only(self):
        """Test FAST_RESPONSE prefers flash when only Gemini is available."""
        with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
            # Mock only Gemini models available
            mock_get_available.return_value = {
                "gemini-2.5-pro-preview-06-05": ProviderType.GOOGLE,
                "gemini-2.5-flash-preview-05-20": ProviderType.GOOGLE,
            }

            model = ModelProviderRegistry.get_preferred_fallback_model(ToolModelCategory.FAST_RESPONSE)
            # Should find the flash model for fast response
            assert "flash" in model or model == "gemini-2.5-flash-preview-05-20"

    def test_balanced_category_fallback(self):
        """Test BALANCED category uses existing logic."""
        with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
            # Mock OpenAI models available
            mock_get_available.return_value = {
                "o3": ProviderType.OPENAI,
                "o3-mini": ProviderType.OPENAI,
                "o4-mini": ProviderType.OPENAI,
            }

            model = ModelProviderRegistry.get_preferred_fallback_model(ToolModelCategory.BALANCED)
            assert model == "o4-mini"  # Balanced prefers o4-mini when OpenAI available

    def test_no_category_uses_balanced_logic(self):
        """Test that no category specified uses balanced logic."""
        with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
            # Mock only Gemini models available
            mock_get_available.return_value = {
                "gemini-2.5-pro-preview-06-05": ProviderType.GOOGLE,
                "gemini-2.5-flash-preview-05-20": ProviderType.GOOGLE,
            }

            model = ModelProviderRegistry.get_preferred_fallback_model()
            # Should pick a reasonable default, preferring flash for balanced use
            assert "flash" in model or model == "gemini-2.5-flash-preview-05-20"


class TestFlexibleModelSelection:
    """Test that model selection handles various naming scenarios."""

    def test_fallback_handles_mixed_model_names(self):
        """Test that fallback selection works with mix of full names and shorthands."""
        # Test with mix of full names and shorthands
        test_cases = [
            # Case 1: Mix of OpenAI shorthands and full names
            {
                "available": {"o3": ProviderType.OPENAI, "o4-mini": ProviderType.OPENAI},
                "category": ToolModelCategory.EXTENDED_REASONING,
                "expected": "o3",
            },
            # Case 2: Mix of Gemini shorthands and full names
            {
                "available": {
                    "gemini-2.5-flash-preview-05-20": ProviderType.GOOGLE,
                    "gemini-2.5-pro-preview-06-05": ProviderType.GOOGLE,
                },
                "category": ToolModelCategory.FAST_RESPONSE,
                "expected_contains": "flash",
            },
            # Case 3: Only shorthands available
            {
                "available": {"o4-mini": ProviderType.OPENAI, "o3-mini": ProviderType.OPENAI},
                "category": ToolModelCategory.FAST_RESPONSE,
                "expected": "o4-mini",
            },
        ]

        for case in test_cases:
            with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
                mock_get_available.return_value = case["available"]

                model = ModelProviderRegistry.get_preferred_fallback_model(case["category"])

                if "expected" in case:
                    assert model == case["expected"], f"Failed for case: {case}"
                elif "expected_contains" in case:
                    assert (
                        case["expected_contains"] in model
                    ), f"Expected '{case['expected_contains']}' in '{model}' for case: {case}"


class TestCustomProviderFallback:
    """Test fallback to custom/openrouter providers."""

    @patch.object(ModelProviderRegistry, "_find_extended_thinking_model")
    def test_extended_reasoning_custom_fallback(self, mock_find_thinking):
        """Test EXTENDED_REASONING falls back to custom thinking model."""
        with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
            # No native models available, but OpenRouter is available
            mock_get_available.return_value = {"openrouter-model": ProviderType.OPENROUTER}
            mock_find_thinking.return_value = "custom/thinking-model"

            model = ModelProviderRegistry.get_preferred_fallback_model(ToolModelCategory.EXTENDED_REASONING)
            assert model == "custom/thinking-model"
            mock_find_thinking.assert_called_once()

    @patch.object(ModelProviderRegistry, "_find_extended_thinking_model")
    def test_extended_reasoning_final_fallback(self, mock_find_thinking):
        """Test EXTENDED_REASONING falls back to pro when no custom found."""
        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            # No providers available
            mock_get_provider.return_value = None
            mock_find_thinking.return_value = None

            model = ModelProviderRegistry.get_preferred_fallback_model(ToolModelCategory.EXTENDED_REASONING)
            assert model == "gemini-2.5-pro-preview-06-05"


class TestAutoModeErrorMessages:
    """Test that auto mode error messages include suggested models."""

    @pytest.mark.asyncio
    async def test_thinkdeep_auto_error_message(self):
        """Test ThinkDeep tool suggests appropriate model in auto mode."""
        with patch("config.IS_AUTO_MODE", True):
            with patch("config.DEFAULT_MODEL", "auto"):
                with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
                    # Mock only Gemini models available
                    mock_get_available.return_value = {
                        "gemini-2.5-pro-preview-06-05": ProviderType.GOOGLE,
                        "gemini-2.5-flash-preview-05-20": ProviderType.GOOGLE,
                    }

                    tool = ThinkDeepTool()
                    result = await tool.execute({"prompt": "test", "model": "auto"})

                    assert len(result) == 1
                    assert "Model parameter is required in auto mode" in result[0].text
                    # Should suggest a model suitable for extended reasoning (either full name or with 'pro')
                    response_text = result[0].text
                    assert "gemini-2.5-pro-preview-06-05" in response_text or "pro" in response_text
                    assert "(category: extended_reasoning)" in response_text

    @pytest.mark.asyncio
    async def test_chat_auto_error_message(self):
        """Test Chat tool suggests appropriate model in auto mode."""
        with patch("config.IS_AUTO_MODE", True):
            with patch("config.DEFAULT_MODEL", "auto"):
                with patch.object(ModelProviderRegistry, "get_available_models") as mock_get_available:
                    # Mock OpenAI models available
                    mock_get_available.return_value = {
                        "o3": ProviderType.OPENAI,
                        "o3-mini": ProviderType.OPENAI,
                        "o4-mini": ProviderType.OPENAI,
                    }

                    tool = ChatTool()
                    result = await tool.execute({"prompt": "test", "model": "auto"})

                    assert len(result) == 1
                    assert "Model parameter is required in auto mode" in result[0].text
                    # Should suggest a model suitable for fast response
                    response_text = result[0].text
                    assert "o4-mini" in response_text or "o3-mini" in response_text or "mini" in response_text
                    assert "(category: fast_response)" in response_text


class TestFileContentPreparation:
    """Test that file content preparation uses tool-specific model for capacity."""

    @patch("tools.base.read_files")
    @patch("tools.base.logger")
    def test_auto_mode_uses_tool_category(self, mock_logger, mock_read_files):
        """Test that auto mode uses tool-specific model for capacity estimation."""
        mock_read_files.return_value = "file content"

        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            # Mock provider with capabilities
            mock_provider = MagicMock()
            mock_provider.get_capabilities.return_value = MagicMock(context_window=1_000_000)
            mock_get_provider.side_effect = lambda ptype: mock_provider if ptype == ProviderType.GOOGLE else None

            # Create a tool and test file content preparation
            tool = ThinkDeepTool()
            tool._current_model_name = "auto"

            # Set up model context to simulate normal execution flow
            from utils.model_context import ModelContext

            tool._model_context = ModelContext("gemini-2.5-pro-preview-06-05")

            # Call the method
            content, processed_files = tool._prepare_file_content_for_prompt(["/test/file.py"], None, "test")

            # Check that it logged the correct message about using model context
            debug_calls = [call for call in mock_logger.debug.call_args_list if "Using model context" in str(call)]
            assert len(debug_calls) > 0
            debug_message = str(debug_calls[0])
            # Should mention the model being used
            assert "gemini-2.5-pro-preview-06-05" in debug_message
            # Should mention file tokens (not content tokens)
            assert "file tokens" in debug_message


class TestProviderHelperMethods:
    """Test the helper methods for finding models from custom/openrouter."""

    def test_find_extended_thinking_model_custom(self):
        """Test finding thinking model from custom provider."""
        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            from providers.custom import CustomProvider

            # Mock custom provider with thinking model
            mock_custom = MagicMock(spec=CustomProvider)
            mock_custom.model_registry = {
                "model1": {"supports_extended_thinking": False},
                "model2": {"supports_extended_thinking": True},
                "model3": {"supports_extended_thinking": False},
            }
            mock_get_provider.side_effect = lambda ptype: mock_custom if ptype == ProviderType.CUSTOM else None

            model = ModelProviderRegistry._find_extended_thinking_model()
            assert model == "model2"

    def test_find_extended_thinking_model_openrouter(self):
        """Test finding thinking model from openrouter."""
        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            # Mock openrouter provider
            mock_openrouter = MagicMock()
            mock_openrouter.validate_model_name.side_effect = lambda m: m == "anthropic/claude-3.5-sonnet"
            mock_get_provider.side_effect = lambda ptype: mock_openrouter if ptype == ProviderType.OPENROUTER else None

            model = ModelProviderRegistry._find_extended_thinking_model()
            assert model == "anthropic/claude-3.5-sonnet"

    def test_find_extended_thinking_model_none_found(self):
        """Test when no thinking model is found."""
        with patch.object(ModelProviderRegistry, "get_provider") as mock_get_provider:
            # No providers available
            mock_get_provider.return_value = None

            model = ModelProviderRegistry._find_extended_thinking_model()
            assert model is None


class TestEffectiveAutoMode:
    """Test the is_effective_auto_mode method."""

    def test_explicit_auto_mode(self):
        """Test when DEFAULT_MODEL is explicitly 'auto'."""
        with patch("config.DEFAULT_MODEL", "auto"):
            with patch("config.IS_AUTO_MODE", True):
                tool = ChatTool()
                assert tool.is_effective_auto_mode() is True

    def test_unavailable_model_triggers_auto_mode(self):
        """Test when DEFAULT_MODEL is set but not available."""
        with patch("config.DEFAULT_MODEL", "o3"):
            with patch("config.IS_AUTO_MODE", False):
                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    mock_get_provider.return_value = None  # Model not available

                    tool = ChatTool()
                    assert tool.is_effective_auto_mode() is True

    def test_available_model_no_auto_mode(self):
        """Test when DEFAULT_MODEL is set and available."""
        with patch("config.DEFAULT_MODEL", "pro"):
            with patch("config.IS_AUTO_MODE", False):
                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    mock_get_provider.return_value = MagicMock()  # Model is available

                    tool = ChatTool()
                    assert tool.is_effective_auto_mode() is False


class TestRuntimeModelSelection:
    """Test runtime model selection behavior."""

    @pytest.mark.asyncio
    async def test_explicit_auto_in_request(self):
        """Test when Claude explicitly passes model='auto'."""
        with patch("config.DEFAULT_MODEL", "pro"):  # DEFAULT_MODEL is a real model
            with patch("config.IS_AUTO_MODE", False):  # Not in auto mode
                tool = ThinkDeepTool()
                result = await tool.execute({"prompt": "test", "model": "auto"})

                # Should require model selection even though DEFAULT_MODEL is valid
                assert len(result) == 1
                assert "Model parameter is required in auto mode" in result[0].text

    @pytest.mark.asyncio
    async def test_unavailable_model_in_request(self):
        """Test when Claude passes an unavailable model."""
        with patch("config.DEFAULT_MODEL", "pro"):
            with patch("config.IS_AUTO_MODE", False):
                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    # Model is not available
                    mock_get_provider.return_value = None

                    tool = ChatTool()
                    result = await tool.execute({"prompt": "test", "model": "gpt-5-turbo"})

                    # Should require model selection
                    assert len(result) == 1
                    # When a specific model is requested but not available, error message is different
                    assert "gpt-5-turbo" in result[0].text
                    assert "is not available" in result[0].text
                    assert "(category: fast_response)" in result[0].text


class TestSchemaGeneration:
    """Test schema generation with different configurations."""

    def test_schema_with_explicit_auto_mode(self):
        """Test schema when DEFAULT_MODEL='auto'."""
        with patch("config.DEFAULT_MODEL", "auto"):
            with patch("config.IS_AUTO_MODE", True):
                tool = ChatTool()
                schema = tool.get_input_schema()

                # Model should be required
                assert "model" in schema["required"]

    def test_schema_with_unavailable_default_model(self):
        """Test schema when DEFAULT_MODEL is set but unavailable."""
        with patch("config.DEFAULT_MODEL", "o3"):
            with patch("config.IS_AUTO_MODE", False):
                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    mock_get_provider.return_value = None  # Model not available

                    tool = AnalyzeTool()
                    schema = tool.get_input_schema()

                    # Model should be required due to unavailable DEFAULT_MODEL
                    assert "model" in schema["required"]

    def test_schema_with_available_default_model(self):
        """Test schema when DEFAULT_MODEL is available."""
        with patch("config.DEFAULT_MODEL", "pro"):
            with patch("config.IS_AUTO_MODE", False):
                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    mock_get_provider.return_value = MagicMock()  # Model is available

                    tool = ThinkDeepTool()
                    schema = tool.get_input_schema()

                    # Model should NOT be required
                    assert "model" not in schema["required"]


class TestUnavailableModelFallback:
    """Test fallback behavior when DEFAULT_MODEL is not available."""

    @pytest.mark.asyncio
    async def test_unavailable_default_model_fallback(self):
        """Test that unavailable DEFAULT_MODEL triggers auto mode behavior."""
        with patch("config.DEFAULT_MODEL", "o3"):  # Set DEFAULT_MODEL to a specific model
            with patch("config.IS_AUTO_MODE", False):  # Not in auto mode
                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    # Model is not available (no provider)
                    mock_get_provider.return_value = None

                    tool = ThinkDeepTool()
                    result = await tool.execute({"prompt": "test"})  # No model specified

                    # Should get auto mode error since model is unavailable
                    assert len(result) == 1
                    # When DEFAULT_MODEL is unavailable, the error message indicates the model is not available
                    assert "o3" in result[0].text
                    assert "is not available" in result[0].text
                    # The suggested model depends on which providers are available
                    # Just check that it suggests a model for the extended_reasoning category
                    assert "(category: extended_reasoning)" in result[0].text

    @pytest.mark.asyncio
    async def test_available_default_model_no_fallback(self):
        """Test that available DEFAULT_MODEL works normally."""
        with patch("config.DEFAULT_MODEL", "pro"):
            with patch("config.IS_AUTO_MODE", False):
                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    # Model is available
                    mock_provider = MagicMock()
                    mock_provider.generate_content.return_value = MagicMock(content="Test response", metadata={})
                    mock_get_provider.return_value = mock_provider

                    # Mock the provider lookup in BaseTool.get_model_provider
                    with patch.object(BaseTool, "get_model_provider") as mock_get_model_provider:
                        mock_get_model_provider.return_value = mock_provider

                        tool = ChatTool()
                        result = await tool.execute({"prompt": "test"})  # No model specified

                        # Should work normally, not require model parameter
                        assert len(result) == 1
                        output = json.loads(result[0].text)
                        assert output["status"] == "success"
                        assert "Test response" in output["content"]
