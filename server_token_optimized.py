"""
Token-Optimized Server Module

This module provides the integration points for the two-stage token optimization
architecture. It modifies the tool registration and execution flow to support
dynamic tool loading based on mode selection.

This is a companion module to server.py that provides the optimized tool handling.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from mcp.types import TextContent, Tool

from token_optimization_config import estimate_token_savings, token_config
from tools.mode_executor import create_mode_executor
from tools.mode_selector import ModeSelectorTool

logger = logging.getLogger(__name__)


def get_optimized_tools() -> Dict[str, Any]:
    """
    Get the optimized tool set for token reduction.

    In two-stage mode, this returns only the mode selector initially.
    The actual tools are loaded dynamically based on mode selection.

    Returns:
        Dictionary of tool instances for the optimized architecture
    """
    if not token_config.is_enabled():
        # Return None to indicate original tools should be used
        return None

    if token_config.is_two_stage():
        # Two-stage architecture: Expose both Stage 1 and Stage 2 tools
        from tools.zen_execute import ZenExecuteTool

        tools = {
            "zen_select_mode": ModeSelectorTool(),  # Stage 1: Mode selection
            "zen_execute": ZenExecuteTool(),  # Stage 2: Mode execution
        }

        # Add lightweight tool stubs for backward compatibility
        # These will redirect to the mode selector
        tools.update(_create_compatibility_stubs())

        logger.info("Two-stage token optimization enabled - Stage 1 (zen_select_mode) and Stage 2 (zen_execute) ready")
        return tools

    # Other optimization modes could be added here
    return None


def _create_compatibility_stubs() -> Dict[str, Any]:
    """
    Create lightweight compatibility stubs for existing tool names.

    These stubs redirect to the two-stage flow while maintaining
    backward compatibility with existing tool names.
    """
    stubs = {}

    # Tool names that should redirect to mode selector
    redirect_tools = [
        "debug",
        "codereview",
        "analyze",
        "chat",
        "consensus",
        "security",
        "refactor",
        "testgen",
        "planner",
        "tracer",
    ]

    for tool_name in redirect_tools:
        stubs[tool_name] = _create_redirect_stub(tool_name)

    return stubs


def _create_redirect_stub(original_name: str):
    """
    Create a stub tool that redirects to the two-stage flow.

    This maintains compatibility with existing tool calls while
    leveraging the optimized architecture.
    """

    class RedirectStub:
        def __init__(self):
            self.name = original_name
            self.original_name = original_name
            self.description = f"Optimized {self.original_name} - redirects to two-stage flow for 95% token reduction"

        def get_name(self):
            return self.name

        def get_description(self):
            return self.description

        def get_annotations(self):
            """Return tool annotations for MCP protocol compliance"""
            return {"readOnlyHint": False}  # These tools can execute actions

        def requires_model(self) -> bool:
            """RedirectStub tools need AI model access for processing"""
            return True

        def get_model_category(self):
            """Return model category for RedirectStub tools"""
            from tools.models import ToolModelCategory

            return ToolModelCategory.FAST_RESPONSE

        def get_input_schema(self):
            # Minimal schema that accepts anything and redirects
            return {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": f"Your {self.original_name} request - will be routed through optimized flow",
                    }
                },
                "required": ["request"],
                "additionalProperties": True,
            }

        async def execute(self, arguments: dict) -> list:
            # Redirect to mode selector
            mode_selector = ModeSelectorTool()

            # Build task description from the original request
            task_description = arguments.get("request", "")
            if not task_description:
                # Try to extract from other common fields
                task_description = (
                    arguments.get("prompt", "")
                    or arguments.get("problem", "")
                    or arguments.get("query", "")
                    or arguments.get("question", "")
                    or f"Execute {self.original_name} task"
                )

            # Execute mode selection
            result = await mode_selector.execute({"task_description": task_description})

            # Parse the mode selection result
            if result and isinstance(result[0], TextContent):
                try:
                    selection = json.loads(result[0].text)

                    # Add guidance for using the selected mode
                    selection["compatibility_note"] = (
                        f"Tool '{self.original_name}' has been optimized. "
                        f"Please use '{selection['next_step']['tool']}' with the parameters shown above."
                    )

                    result[0] = TextContent(type="text", text=json.dumps(selection, indent=2))
                except (json.JSONDecodeError, KeyError):
                    pass

            return result

    return RedirectStub()


async def handle_dynamic_tool_execution(name: str, arguments: dict) -> Optional[list]:
    """
    Handle dynamic tool execution for the two-stage architecture.

    This function intercepts tool calls for dynamically created executors
    and handles them appropriately.

    Args:
        name: Tool name (e.g., "zen_execute_debug")
        arguments: Tool arguments

    Returns:
        Tool execution result or None if not a dynamic tool
    """
    if not token_config.is_enabled():
        return None

    # Check if this is a dynamic executor call
    if name.startswith("zen_execute_"):
        start_time = time.time()

        # Extract mode from the tool name
        mode = name.replace("zen_execute_", "")

        # Determine complexity from arguments if provided
        complexity = arguments.pop("complexity", "simple")

        # Create and execute the mode-specific executor
        executor = create_mode_executor(mode, complexity)

        # Record telemetry
        token_config.record_tool_execution(name, True)

        try:
            result = await executor.execute(arguments)

            # Record successful execution
            duration_ms = (time.time() - start_time) * 1000
            token_config.record_latency(f"execute_{mode}", duration_ms)

            # Estimate and log token savings
            original_size = 3500  # Average size of original tool schemas
            optimized_size = len(json.dumps(executor.get_input_schema()))
            savings = estimate_token_savings(original_size, optimized_size)

            # Use debug level to avoid stdio interference (stderr logging breaks MCP protocol)
            logger.debug(f"Dynamic executor '{name}' completed - saved ~{savings:.1f}% tokens")

            return result

        except Exception as e:
            logger.error(f"Dynamic executor '{name}' failed: {e}")
            token_config.record_tool_execution(name, False)

            # Return error as tool result
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "status": "error",
                            "tool": name,
                            "error": str(e),
                            "suggestion": "Check parameters match the mode-specific schema",
                        },
                        indent=2,
                    ),
                )
            ]

    return None


def get_dynamic_tool_schema(name: str) -> Optional[Tool]:
    """
    Get the schema for a dynamically created tool.

    This is called when the MCP client requests tool information
    for a tool that was created dynamically.

    Args:
        name: Tool name (e.g., "zen_execute_debug")

    Returns:
        Tool schema or None if not a dynamic tool
    """
    if not token_config.is_enabled():
        return None

    if name.startswith("zen_execute_"):
        # Extract mode from the tool name
        mode = name.replace("zen_execute_", "")

        # Create executor to get its schema
        executor = create_mode_executor(mode, "simple")

        # Build MCP Tool object
        return Tool(name=name, description=executor.get_description(), inputSchema=executor.get_input_schema())

    return None


def log_token_optimization_stats():
    """
    Log token optimization statistics for monitoring and debugging.

    This is called periodically or at shutdown to provide insights
    into the effectiveness of the optimization.
    """
    if not token_config.telemetry_enabled:
        return

    stats = token_config.get_stats_summary()

    logger.info("Token Optimization Statistics:")
    logger.info(f"  Version: {stats['version']}")
    logger.info(f"  Mode: {stats['mode']}")
    logger.info(f"  Total executions: {stats['total_tool_executions']}")
    logger.info(f"  Avg tokens/call: {stats['average_tokens_per_call']:.0f}")

    if stats["mode_selections"]:
        logger.info("  Mode selections:")
        for mode_combo, count in stats["mode_selections"].items():
            logger.info(f"    - {mode_combo}: {count}")

    if stats["retry_rates"]:
        logger.info("  Retry rates:")
        for tool, rate in stats["retry_rates"].items():
            logger.info(f"    - {tool}: {rate:.1%}")


# Initialize configuration on module load
token_config.log_configuration()
