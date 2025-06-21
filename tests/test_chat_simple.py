"""
Tests for ChatSimple tool - validating migration from Chat tool

This module contains unit tests to ensure that the ChatSimple tool
maintains 100% compatibility with the original Chat tool behavior.
"""

from unittest.mock import patch

import pytest

from tools.chat import ChatRequest, ChatTool
from tools.simple.chat_simple import ChatSimpleRequest, ChatSimpleTool


class TestChatSimpleTool:
    """Test suite for ChatSimple tool"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tool = ChatSimpleTool()
        self.original_tool = ChatTool()

    def test_tool_metadata(self):
        """Test that tool metadata matches requirements"""
        assert self.tool.get_name() == "chat_simple"
        assert self.tool.get_description() == self.original_tool.get_description()
        assert self.tool.get_system_prompt() == self.original_tool.get_system_prompt()
        assert self.tool.get_default_temperature() == self.original_tool.get_default_temperature()
        assert self.tool.get_model_category() == self.original_tool.get_model_category()

    def test_schema_compatibility(self):
        """Test that schemas are identical between Chat and ChatSimple"""
        simple_schema = self.tool.get_input_schema()
        original_schema = self.original_tool.get_input_schema()

        # Schemas should be identical except for internal structure differences
        assert simple_schema["type"] == original_schema["type"]
        assert simple_schema["required"] == original_schema["required"]
        assert set(simple_schema["properties"].keys()) == set(original_schema["properties"].keys())

        # Model field should be compatible (enum presence depends on auto mode)
        simple_model = simple_schema["properties"]["model"]
        original_model = original_schema["properties"]["model"]

        # Both should have same type and description structure
        assert simple_model["type"] == original_model["type"]
        assert "description" in simple_model
        assert "description" in original_model

        # If both have enums, they should match
        if "enum" in simple_model and "enum" in original_model:
            assert simple_model["enum"] == original_model["enum"]
            assert len(simple_model["enum"]) > 0

    def test_request_model_validation(self):
        """Test that the request model validates correctly"""
        # Test valid request
        request_data = {
            "prompt": "Test prompt",
            "files": ["test.txt"],
            "images": ["test.png"],
            "model": "anthropic/claude-3-opus",
            "temperature": 0.7,
        }

        request = ChatSimpleRequest(**request_data)
        assert request.prompt == "Test prompt"
        assert request.files == ["test.txt"]
        assert request.images == ["test.png"]
        assert request.model == "anthropic/claude-3-opus"
        assert request.temperature == 0.7

    def test_required_fields(self):
        """Test that required fields are enforced"""
        # Missing prompt should raise validation error
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ChatSimpleRequest(model="anthropic/claude-3-opus")

    def test_model_availability(self):
        """Test that model availability matches original Chat tool"""
        simple_models = self.tool._get_available_models()
        original_models = self.original_tool._get_available_models()

        assert len(simple_models) == len(original_models)
        assert set(simple_models) == set(original_models)
        assert len(simple_models) > 0  # Should have some models

    def test_model_field_schema(self):
        """Test that model field schema generation works correctly"""
        schema = self.tool.get_model_field_schema()

        assert schema["type"] == "string"
        assert "description" in schema

        # In auto mode, should have enum. In normal mode, should have model descriptions
        if self.tool.is_effective_auto_mode():
            assert "enum" in schema
            assert len(schema["enum"]) > 0
            assert "IMPORTANT:" in schema["description"]
        else:
            # Normal mode - should have model descriptions in description
            assert "Model to use" in schema["description"]
            assert "Native models:" in schema["description"]

    @pytest.mark.asyncio
    async def test_prompt_preparation(self):
        """Test that prompt preparation works correctly"""
        request = ChatSimpleRequest(prompt="Test prompt", files=[], use_websearch=True)

        # Mock the system prompt and file handling
        with patch.object(self.tool, "get_system_prompt", return_value="System prompt"):
            with patch.object(self.tool, "handle_prompt_file_with_fallback", return_value="Test prompt"):
                with patch.object(self.tool, "_prepare_file_content_for_prompt", return_value=("", [])):
                    with patch.object(self.tool, "_validate_token_limit"):
                        with patch.object(self.tool, "get_websearch_instruction", return_value=""):
                            prompt = await self.tool.prepare_prompt(request)

                            assert "Test prompt" in prompt
                            assert "System prompt" in prompt
                            assert "USER REQUEST" in prompt

    def test_response_formatting(self):
        """Test that response formatting matches original Chat tool"""
        response = "Test response content"
        request = ChatSimpleRequest(prompt="Test")

        formatted = self.tool.format_response(response, request)

        assert "Test response content" in formatted
        assert "Claude's Turn:" in formatted
        assert "Evaluate this perspective" in formatted

        # Should match original Chat tool format
        original_formatted = self.original_tool.format_response(response, ChatRequest(prompt="Test"))
        assert formatted == original_formatted

    def test_tool_name(self):
        """Test tool name is correct"""
        assert self.tool.get_name() == "chat_simple"  # Current name during migration

    def test_websearch_guidance(self):
        """Test web search guidance matches Chat tool style"""
        guidance = self.tool.get_websearch_guidance()
        chat_style_guidance = self.tool.get_chat_style_websearch_guidance()

        assert guidance == chat_style_guidance
        assert "Documentation for any technologies" in guidance
        assert "Current best practices" in guidance

    def test_convenience_methods(self):
        """Test SimpleTool convenience methods work correctly"""
        assert self.tool.supports_custom_request_model()

        # Test that the tool fields are defined correctly
        tool_fields = self.tool.get_tool_fields()
        assert "prompt" in tool_fields
        assert "files" in tool_fields
        assert "images" in tool_fields

        required_fields = self.tool.get_required_fields()
        assert "prompt" in required_fields


class TestChatSimpleRequestModel:
    """Test suite for ChatSimpleRequest model"""

    def test_field_descriptions(self):
        """Test that field descriptions match original Chat tool"""
        from tools.chat import CHAT_FIELD_DESCRIPTIONS as ORIGINAL_DESCRIPTIONS
        from tools.simple.chat_simple import CHAT_FIELD_DESCRIPTIONS

        # Field descriptions should be identical
        assert CHAT_FIELD_DESCRIPTIONS["prompt"] == ORIGINAL_DESCRIPTIONS["prompt"]
        assert CHAT_FIELD_DESCRIPTIONS["files"] == ORIGINAL_DESCRIPTIONS["files"]
        assert CHAT_FIELD_DESCRIPTIONS["images"] == ORIGINAL_DESCRIPTIONS["images"]

    def test_default_values(self):
        """Test that default values work correctly"""
        request = ChatSimpleRequest(prompt="Test")

        assert request.prompt == "Test"
        assert request.files == []  # Should default to empty list
        assert request.images == []  # Should default to empty list

    def test_inheritance(self):
        """Test that ChatSimpleRequest properly inherits from ToolRequest"""
        from tools.shared.base_models import ToolRequest

        request = ChatSimpleRequest(prompt="Test")
        assert isinstance(request, ToolRequest)

        # Should have inherited fields
        assert hasattr(request, "model")
        assert hasattr(request, "temperature")
        assert hasattr(request, "thinking_mode")
        assert hasattr(request, "use_websearch")
        assert hasattr(request, "continuation_id")
        assert hasattr(request, "images")  # From base model too


if __name__ == "__main__":
    pytest.main([__file__])
