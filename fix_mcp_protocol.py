#!/usr/bin/env python3
"""
Create a minimal working MCP server to compare with our broken one.
"""

import asyncio

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, Tool, ToolsCapability

# Create server
server = Server("minimal-zen")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return list of tools."""
    return [
        Tool(
            name="test",
            description="A test tool",
            inputSchema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list:
    """Handle tool calls."""
    return [{"type": "text", "text": f"Called {name}"}]


async def main():
    """Run the server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="minimal-zen",
                server_version="1.0.0",
                capabilities=ServerCapabilities(tools=ToolsCapability()),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
