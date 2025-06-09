"""
Gemini MCP Server - Main server implementation
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from google import genai
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from config import (
    DEFAULT_MODEL,
    MAX_CONTEXT_TOKENS,
    __author__,
    __updated__,
    __version__,
)
from tools import (
    AnalyzeTool,
    ChatTool,
    DebugIssueTool,
    ReviewCodeTool,
    ReviewPendingChanges,
    ThinkDeeperTool,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server instance
server: Server = Server("gemini-server")

# Initialize tools
TOOLS = {
    "think_deeper": ThinkDeeperTool(),
    "review_code": ReviewCodeTool(),
    "debug_issue": DebugIssueTool(),
    "analyze": AnalyzeTool(),
    "chat": ChatTool(),
    "review_pending_changes": ReviewPendingChanges(),
}


def configure_gemini():
    """Configure Gemini API with the provided API key"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is required. "
            "Please set it with your Gemini API key."
        )
    # API key is used when creating clients in tools
    logger.info("Gemini API key found")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all available tools with verbose descriptions"""
    tools = []

    for tool in TOOLS.values():
        tools.append(
            Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.get_input_schema(),
            )
        )

    # Add utility tools
    tools.extend(
        [
            Tool(
                name="list_models",
                description=(
                    "LIST AVAILABLE MODELS - Show all Gemini models you can use. "
                    "Lists model names, descriptions, and which one is the default."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
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
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool execution requests"""

    # Handle dynamic tools
    if name in TOOLS:
        tool = TOOLS[name]
        return await tool.execute(arguments)

    # Handle static tools
    elif name == "list_models":
        return await handle_list_models()

    elif name == "get_version":
        return await handle_get_version()

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_list_models() -> List[TextContent]:
    """List available Gemini models"""
    try:
        import json

        # Get API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return [TextContent(type="text", text="Error: GEMINI_API_KEY not set")]

        client = genai.Client(api_key=api_key)
        models = []

        # List models using the new API
        try:
            model_list = client.models.list()
            for model_info in model_list:
                models.append(
                    {
                        "name": getattr(model_info, "id", "Unknown"),
                        "display_name": getattr(
                            model_info,
                            "display_name",
                            getattr(model_info, "id", "Unknown"),
                        ),
                        "description": getattr(
                            model_info, "description", "No description"
                        ),
                        "is_default": getattr(model_info, "id", "").endswith(
                            DEFAULT_MODEL
                        ),
                    }
                )

        except Exception:
            # Fallback: return some known models
            models = [
                {
                    "name": "gemini-2.5-pro-preview-06-05",
                    "display_name": "Gemini 2.5 Pro",
                    "description": "Latest Gemini 2.5 Pro model",
                    "is_default": True,
                },
                {
                    "name": "gemini-2.0-flash-thinking-exp",
                    "display_name": "Gemini 2.0 Flash Thinking",
                    "description": "Enhanced reasoning model",
                    "is_default": False,
                },
            ]

        return [TextContent(type="text", text=json.dumps(models, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error listing models: {str(e)}")]


async def handle_get_version() -> List[TextContent]:
    """Get version and configuration information"""
    version_info = {
        "version": __version__,
        "updated": __updated__,
        "author": __author__,
        "default_model": DEFAULT_MODEL,
        "max_context_tokens": f"{MAX_CONTEXT_TOKENS:,}",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "server_started": datetime.now().isoformat(),
        "available_tools": list(TOOLS.keys()) + ["chat", "list_models", "get_version"],
    }

    text = f"""Gemini MCP Server v{__version__}
Updated: {__updated__}
Author: {__author__}

Configuration:
- Default Model: {DEFAULT_MODEL}
- Max Context: {MAX_CONTEXT_TOKENS:,} tokens
- Python: {version_info['python_version']}
- Started: {version_info['server_started']}

Available Tools:
{chr(10).join(f"  - {tool}" for tool in version_info['available_tools'])}

For updates, visit: https://github.com/BeehiveInnovations/gemini-mcp-server"""

    return [TextContent(type="text", text=text)]


async def main():
    """Main entry point for the server"""
    # Configure Gemini API
    configure_gemini()

    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gemini",
                server_version=__version__,
                capabilities={"tools": {}},
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
