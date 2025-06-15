"""
Tests for the main server functionality
"""

from unittest.mock import Mock, patch

import pytest

from server import handle_call_tool, handle_list_tools
from tests.mock_helpers import create_mock_provider


class TestServerTools:
    """Test server tool handling"""

    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test listing all available tools"""
        tools = await handle_list_tools()
        tool_names = [tool.name for tool in tools]

        # Check all core tools are present
        assert "thinkdeep" in tool_names
        assert "codereview" in tool_names
        assert "debug" in tool_names
        assert "analyze" in tool_names
        assert "chat" in tool_names
        assert "precommit" in tool_names
        assert "testgen" in tool_names
        assert "refactor" in tool_names
        assert "tracer" in tool_names
        assert "version" in tool_names

        # Should have exactly 10 tools (including refactor and tracer)
        assert len(tools) == 10

        # Check descriptions are verbose
        for tool in tools:
            assert len(tool.description) > 50  # All should have detailed descriptions

    @pytest.mark.asyncio
    async def test_handle_call_tool_unknown(self):
        """Test calling an unknown tool"""
        result = await handle_call_tool("unknown_tool", {})
        assert len(result) == 1
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    @patch("tools.base.BaseTool.get_model_provider")
    async def test_handle_chat(self, mock_get_provider):
        """Test chat functionality"""
        # Set test environment
        import os

        os.environ["PYTEST_CURRENT_TEST"] = "test"

        # Create a mock for the provider
        mock_provider = create_mock_provider()
        mock_provider.get_provider_type.return_value = Mock(value="google")
        mock_provider.supports_thinking_mode.return_value = False
        mock_provider.generate_content.return_value = Mock(
            content="Chat response", usage={}, model_name="gemini-2.5-flash-preview-05-20", metadata={}
        )
        mock_get_provider.return_value = mock_provider

        result = await handle_call_tool("chat", {"prompt": "Hello Gemini"})

        assert len(result) == 1
        # Parse JSON response
        import json

        response_data = json.loads(result[0].text)
        assert response_data["status"] == "success"
        assert "Chat response" in response_data["content"]
        assert "Claude's Turn" in response_data["content"]

    @pytest.mark.asyncio
    async def test_handle_version(self):
        """Test getting version info"""
        result = await handle_call_tool("version", {})
        assert len(result) == 1

        response = result[0].text
        assert "Zen MCP Server v" in response  # Version agnostic check
        assert "Available Tools:" in response
        assert "thinkdeep" in response
