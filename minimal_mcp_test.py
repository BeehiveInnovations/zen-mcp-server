#!/usr/bin/env python3
"""
Minimal MCP server to isolate validation issues.
Run with: python minimal_mcp_test.py
"""

import asyncio
import logging
from typing import Any, Dict

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MinimalTool:
    """Minimal tool that should pass MCP validation."""

    def __init__(self):
        # MCP requires these as attributes
        self.name = "test_tool"
        self.description = "A minimal test tool"

    def get_input_schema(self) -> Dict[str, Any]:
        """Return minimal valid JSON Schema."""
        return {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "Test message"}},
            "required": ["message"],
        }

    def get_annotations(self) -> Dict[str, Any]:
        """Return tool annotations."""
        return {"readOnlyHint": False}

    def requires_model(self) -> bool:
        """This tool doesn't need a model."""
        return False

    async def execute(self, arguments: Dict[str, Any]) -> list:
        """Execute the tool."""
        message = arguments.get("message", "No message")
        return [TextContent(type="text", text=f"Echo: {message}")]


class OptimizedTool:
    """Tool with Stage 1/2 optimization pattern."""

    def __init__(self):
        self.name = "optimized_tool"
        self.description = "Tool with token optimization"

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["fast", "deep"], "description": "Execution mode"},
                "request": {"type": "object", "description": "Mode-specific parameters"},
            },
            "required": ["mode", "request"],
            "additionalProperties": False,
        }

    def get_annotations(self) -> Dict[str, Any]:
        return {"readOnlyHint": False}

    def requires_model(self) -> bool:
        return False

    async def execute(self, arguments: Dict[str, Any]) -> list:
        mode = arguments.get("mode", "fast")
        return [TextContent(type="text", text=f"Executed in {mode} mode")]


# Create server and register tools
server = Server("minimal-test-server")
TOOLS = {"test_tool": MinimalTool(), "optimized_tool": OptimizedTool()}


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    logger.info(f"Listing {len(TOOLS)} tools")

    tools = []
    for tool in TOOLS.values():
        logger.debug(f"Registering tool: {tool.name}")
        logger.debug(f"  Has name attr: {hasattr(tool, 'name')}")
        logger.debug(f"  Has description attr: {hasattr(tool, 'description')}")
        logger.debug(f"  Schema: {tool.get_input_schema()}")

        tools.append(Tool(name=tool.name, description=tool.description, inputSchema=tool.get_input_schema()))

    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Calling tool: {name}")

    if name in TOOLS:
        tool = TOOLS[name]
        return await tool.execute(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the minimal server."""
    logger.info("Starting minimal MCP server...")

    # Test with stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="minimal-test", server_version="1.0.0", capabilities=ServerCapabilities(tools={})
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
