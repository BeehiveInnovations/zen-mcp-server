"""
Gemini MCP Server - Main server implementation

This module implements the core MCP (Model Context Protocol) server that provides
AI-powered tools for code analysis, review, and assistance using Google's Gemini models.

The server follows the MCP specification to expose various AI tools as callable functions
that can be used by MCP clients (like Claude). Each tool provides specialized functionality
such as code review, debugging, deep thinking, and general chat capabilities.

Key Components:
- MCP Server: Handles protocol communication and tool discovery
- Tool Registry: Maps tool names to their implementations
- Request Handler: Processes incoming tool calls and returns formatted responses
- Configuration: Manages API keys and model settings

The server runs on stdio (standard input/output) and communicates using JSON-RPC messages
as defined by the MCP protocol.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool, ToolsCapability

from config import (
    GEMINI_MODEL,
    MAX_CONTEXT_TOKENS,
    __author__,
    __updated__,
    __version__,
)
from tools import (
    AnalyzeTool,
    ChatTool,
    CodeReviewTool,
    DebugIssueTool,
    Precommit,
    ThinkDeepTool,
)

# Configure logging for server operations
# Set to INFO level to capture important operational messages without being too verbose
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance with a unique name identifier
# This name is used by MCP clients to identify and connect to this specific server
server: Server = Server("gemini-server")

# Initialize the tool registry with all available AI-powered tools
# Each tool provides specialized functionality for different development tasks
# Tools are instantiated once and reused across requests (stateless design)
TOOLS = {
    "thinkdeep": ThinkDeepTool(),  # Extended reasoning for complex problems
    "codereview": CodeReviewTool(),  # Comprehensive code review and quality analysis
    "debug": DebugIssueTool(),  # Root cause analysis and debugging assistance
    "analyze": AnalyzeTool(),  # General-purpose file and code analysis
    "chat": ChatTool(),  # Interactive development chat and brainstorming
    "precommit": Precommit(),  # Pre-commit validation of git changes
}


def configure_gemini():
    """
    Configure Gemini API with the provided API key.

    This function validates that the GEMINI_API_KEY environment variable is set.
    The actual API key is used when creating Gemini clients within individual tools
    to ensure proper isolation and error handling.

    Raises:
        ValueError: If GEMINI_API_KEY environment variable is not set
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required. " "Please set it with your Gemini API key.")
    # Note: We don't store the API key globally for security reasons
    # Each tool creates its own Gemini client with the API key when needed
    logger.info("Gemini API key found")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    List all available tools with their descriptions and input schemas.

    This handler is called by MCP clients during initialization to discover
    what tools are available. Each tool provides:
    - name: Unique identifier for the tool
    - description: Detailed explanation of what the tool does
    - inputSchema: JSON Schema defining the expected parameters

    Returns:
        List of Tool objects representing all available tools
    """
    tools = []

    # Add all registered AI-powered tools from the TOOLS registry
    for tool in TOOLS.values():
        tools.append(
            Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.get_input_schema(),
            )
        )

    # Add utility tools that provide server metadata and configuration info
    # These tools don't require AI processing but are useful for clients
    tools.extend(
        [
            Tool(
                name="get_version",
                description=(
                    "VERSION & CONFIGURATION - Get server version, configuration details, "
                    "and list of available tools. Useful for debugging and understanding capabilities."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
        ]
    )

    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Handle incoming tool execution requests from MCP clients.

    This is the main request dispatcher that routes tool calls to their
    appropriate handlers. It supports both AI-powered tools (from TOOLS registry)
    and utility tools (implemented as static functions).

    Args:
        name: The name of the tool to execute
        arguments: Dictionary of arguments to pass to the tool

    Returns:
        List of TextContent objects containing the tool's response
    """

    # Route to AI-powered tools that require Gemini API calls
    if name in TOOLS:
        tool = TOOLS[name]
        return await tool.execute(arguments)

    # Route to utility tools that provide server information
    elif name == "get_version":
        return await handle_get_version()

    # Handle unknown tool requests gracefully
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_get_version() -> list[TextContent]:
    """
    Get comprehensive version and configuration information about the server.

    Provides details about the server version, configuration settings,
    available tools, and runtime environment. Useful for debugging and
    understanding the server's capabilities.

    Returns:
        Formatted text with version and configuration details
    """
    # Gather comprehensive server information
    version_info = {
        "version": __version__,
        "updated": __updated__,
        "author": __author__,
        "gemini_model": GEMINI_MODEL,
        "max_context_tokens": f"{MAX_CONTEXT_TOKENS:,}",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "server_started": datetime.now().isoformat(),
        "available_tools": list(TOOLS.keys()) + ["get_version"],
    }

    # Format the information in a human-readable way
    text = f"""Gemini MCP Server v{__version__}
Updated: {__updated__}
Author: {__author__}

Configuration:
- Gemini Model: {GEMINI_MODEL}
- Max Context: {MAX_CONTEXT_TOKENS:,} tokens
- Python: {version_info["python_version"]}
- Started: {version_info["server_started"]}

Available Tools:
{chr(10).join(f"  - {tool}" for tool in version_info["available_tools"])}

For updates, visit: https://github.com/BeehiveInnovations/gemini-mcp-server"""

    return [TextContent(type="text", text=text)]


async def main():
    """
    Main entry point for the MCP server.

    Initializes the Gemini API configuration and starts the server using
    stdio transport. The server will continue running until the client
    disconnects or an error occurs.

    The server communicates via standard input/output streams using the
    MCP protocol's JSON-RPC message format.
    """
    # Validate that Gemini API key is available before starting
    configure_gemini()

    # Run the server using stdio transport (standard input/output)
    # This allows the server to be launched by MCP clients as a subprocess
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gemini",
                server_version=__version__,
                capabilities=ServerCapabilities(tools=ToolsCapability()),  # Advertise tool support capability
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
