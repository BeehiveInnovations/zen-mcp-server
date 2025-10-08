#!/usr/bin/env python3
"""
Minimal MCP server for debugging tools/list issue
"""
import asyncio
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

# Create server
server = Server("debug-minimal")


@server.list_tools()
async def list_tools():
    """List available tools."""
    print("=== MINIMAL SERVER: list_tools called! ===", file=sys.stderr)
    return [
        Tool(
            name="test-tool",
            description="A test tool",
            inputSchema={
                "type": "object",
                "properties": {"message": {"type": "string", "description": "A test message"}},
                "required": ["message"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    print(f"=== MINIMAL SERVER: call_tool called with {name} ===", file=sys.stderr)
    return [{"type": "text", "text": f"Called {name} with {arguments}"}]


async def main():
    print("=== MINIMAL SERVER STARTING ===", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
