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
# Set to DEBUG level to capture detailed operational messages for troubleshooting
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
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
        raise ValueError("GEMINI_API_KEY environment variable is required. Please set it with your Gemini API key.")
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

    Thread Context Reconstruction:
    If the request contains a continuation_id, this function reconstructs
    the conversation history and injects it into the tool's context.

    Args:
        name: The name of the tool to execute
        arguments: Dictionary of arguments to pass to the tool

    Returns:
        List of TextContent objects containing the tool's response
    """

    # Handle thread context reconstruction if continuation_id is present
    if "continuation_id" in arguments and arguments["continuation_id"]:
        arguments = await reconstruct_thread_context(arguments)

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


def get_follow_up_instructions(current_turn_count: int, max_turns: int = None) -> str:
    """
    Generate dynamic follow-up instructions based on conversation turn count.

    Args:
        current_turn_count: Current number of turns in the conversation
        max_turns: Maximum allowed turns before conversation ends (defaults to MAX_CONVERSATION_TURNS)

    Returns:
        Follow-up instructions to append to the tool prompt
    """
    if max_turns is None:
        from utils.conversation_memory import MAX_CONVERSATION_TURNS

        max_turns = MAX_CONVERSATION_TURNS

    if current_turn_count >= max_turns - 1:
        # We're at or approaching the turn limit - no more follow-ups
        return """
IMPORTANT: This is approaching the final exchange in this conversation thread.
Do NOT include any follow-up questions in your response. Provide your complete
final analysis and recommendations."""
    else:
        # Normal follow-up instructions
        remaining_turns = max_turns - current_turn_count - 1
        return f"""

🤝 CONVERSATION THREADING: You can continue this discussion with Claude! ({remaining_turns} exchanges remaining)

If you'd like to ask a follow-up question, explore a specific aspect deeper, or need clarification,
add this JSON block at the very end of your response:

```json
{{
  "follow_up_question": "Would you like me to [specific action you could take]?",
  "suggested_params": {{"files": ["relevant/files"], "focus_on": "specific area"}},
  "ui_hint": "What this follow-up would accomplish"
}}
```

💡 Good follow-up opportunities:
- "Would you like me to examine the error handling in more detail?"
- "Should I analyze the performance implications of this approach?"
- "Would it be helpful to review the security aspects of this implementation?"
- "Should I dive deeper into the architecture patterns used here?"

Only ask follow-ups when they would genuinely add value to the discussion."""


async def reconstruct_thread_context(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Reconstruct conversation context for thread continuation.

    This function loads the conversation history from Redis and integrates it
    into the request arguments to provide full context to the tool.

    Args:
        arguments: Original request arguments containing continuation_id

    Returns:
        Modified arguments with conversation history injected
    """
    from utils.conversation_memory import add_turn, build_conversation_history, get_thread

    continuation_id = arguments["continuation_id"]

    # Get thread context from Redis
    context = get_thread(continuation_id)
    if not context:
        logger.warning(f"Thread not found: {continuation_id}")
        # Return error asking Claude to restart conversation with full context
        raise ValueError(
            f"Conversation thread '{continuation_id}' was not found or has expired. "
            f"This may happen if the conversation was created more than 1 hour ago or if there was an issue with Redis storage. "
            f"Please restart the conversation by providing your full question/prompt without the continuation_id parameter. "
            f"This will create a new conversation thread that can continue with follow-up exchanges."
        )

    # Add user's new input to the conversation
    user_prompt = arguments.get("prompt", "")
    if user_prompt:
        # Capture files referenced in this turn
        user_files = arguments.get("files", [])
        success = add_turn(continuation_id, "user", user_prompt, files=user_files)
        if not success:
            logger.warning(f"Failed to add user turn to thread {continuation_id}")

    # Build conversation history
    conversation_history = build_conversation_history(context)

    # Add dynamic follow-up instructions based on turn count
    follow_up_instructions = get_follow_up_instructions(len(context.turns))

    # Merge original context with new prompt and follow-up instructions
    original_prompt = arguments.get("prompt", "")
    if conversation_history:
        enhanced_prompt = (
            f"{conversation_history}\n\n=== NEW USER INPUT ===\n{original_prompt}\n\n{follow_up_instructions}"
        )
    else:
        enhanced_prompt = f"{original_prompt}\n\n{follow_up_instructions}"

    # Update arguments with enhanced context
    enhanced_arguments = arguments.copy()
    enhanced_arguments["prompt"] = enhanced_prompt

    # Merge original context parameters (files, etc.) with new request
    if context.initial_context:
        for key, value in context.initial_context.items():
            if key not in enhanced_arguments and key not in ["temperature", "thinking_mode", "model"]:
                enhanced_arguments[key] = value

    logger.info(f"Reconstructed context for thread {continuation_id} (turn {len(context.turns)})")
    return enhanced_arguments


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
