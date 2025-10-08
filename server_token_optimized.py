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
    Create a smart stub tool that actually works by internally handling the two-stage flow.

    This maintains full backward compatibility - users can call original tool names
    and get real results without needing to understand the two-stage architecture.

    The stub automatically:
    1. Selects the appropriate mode (internal, no user interaction)
    2. Transforms simple request to valid schema format
    3. Executes the tool and returns actual results
    """

    class SmartStub:
        def __init__(self):
            self.name = original_name
            self.original_name = original_name
            self.description = f"{self.original_name.title()} - Auto-optimized with 82% token reduction"

        def get_name(self):
            return self.name

        def get_description(self):
            return self.description

        def get_annotations(self):
            """Return tool annotations for MCP protocol compliance"""
            return {"readOnlyHint": False}  # These tools can execute actions

        def requires_model(self) -> bool:
            """SmartStub tools need AI model access for processing"""
            return True

        def get_model_category(self):
            """Return model category for SmartStub tools"""
            from tools.models import ToolModelCategory

            return ToolModelCategory.FAST_RESPONSE

        def get_input_schema(self):
            # Simple schema that accepts common fields
            return {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": f"Your {self.original_name} request (automatically optimized)",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Relevant file paths",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional: Additional context",
                    },
                },
                "required": ["request"],
                "additionalProperties": True,
            }

        def _build_simple_request(self, mode: str, user_args: dict) -> dict:
            """
            Transform user's simple arguments to valid mode-specific schema.

            CRITICAL: This must match the schemas defined in mode_selector.py exactly.
            Many "simple" modes now require workflow fields (step, step_number, etc.)
            """
            request_text = user_args.get("request", "")
            files = user_args.get("files", [])
            context = user_args.get("context", "")

            # Common workflow fields used by many modes
            workflow_base = {
                "step": request_text[:100] if request_text else "Processing request",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": request_text or "Starting task"
            }

            # Mode-specific request building (matching mode_selector.py schemas)
            if mode == "debug":
                # debug/simple only needs: problem (+ optional files, confidence, hypothesis)
                return {
                    "problem": request_text,
                    "files": files or [],
                    "confidence": "medium"
                }

            elif mode == "codereview":
                # codereview/simple only needs: files (per ReviewSimpleRequest)
                return {
                    "files": files or ["/code"],
                    "review_type": "full",
                    "focus": context or None
                }

            elif mode == "analyze":
                # analyze/simple needs: workflow fields + relevant_files
                return {
                    **workflow_base,
                    "relevant_files": files or ["/"],
                    "analysis_type": "architecture",
                    "files_checked": [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            elif mode == "chat":
                # chat/simple needs: prompt + working_directory (required by ChatRequest)
                return {
                    "prompt": request_text,
                    "working_directory": "/tmp"  # Default safe directory for generated code
                }

            elif mode == "consensus":
                # consensus/simple needs: prompt + models
                return {
                    "prompt": request_text,
                    "models": [{"model": "o3", "stance": "neutral"}],  # Default model
                    "relevant_files": files or None
                }

            elif mode == "security":
                # security/simple needs: workflow fields (all security requests need them)
                return {
                    **workflow_base,
                    "relevant_files": files or [],
                    "security_scope": "comprehensive",
                    "files_checked": [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            elif mode == "refactor":
                # refactor/simple needs: workflow fields
                return {
                    **workflow_base,
                    "relevant_files": files or [],
                    "refactor_type": "codesmells",
                    "files_checked": [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "incomplete"
                }

            elif mode == "testgen":
                # testgen/simple needs: workflow fields + relevant_files
                return {
                    **workflow_base,
                    "relevant_files": files or ["/code"],
                    "files_checked": [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            elif mode == "planner":
                # planner/simple needs: workflow fields (planning is inherently workflow-based)
                return {
                    **workflow_base,
                    "relevant_files": files or [],
                    "files_checked": [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            elif mode == "tracer":
                # tracer/simple needs: workflow fields + target
                return {
                    **workflow_base,
                    "target": request_text[:50] if request_text else "main",
                    "trace_mode": "ask",
                    "files": files or [],
                    "relevant_files": [],
                    "files_checked": [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            else:
                # Fallback with workflow fields (safest default)
                return {
                    **workflow_base,
                    "prompt": request_text,
                    "context": context
                }

        def _build_workflow_request(self, mode: str, user_args: dict) -> dict:
            """
            Build workflow request structure with mode-specific required fields.

            CRITICAL: Must match the workflow schemas in mode_selector.py
            """
            request_text = user_args.get("request", "")
            files = user_args.get("files", [])
            context = user_args.get("context", "")

            # Base workflow fields
            workflow_base = {
                "step": request_text[:100] if request_text else "Processing request",
                "step_number": 1,
                "total_steps": 3,  # Workflow typically has multiple steps
                "findings": request_text or "Starting investigation",
                "next_step_required": True
            }

            # Add mode-specific required fields for workflow complexity
            if mode == "debug":
                # debug/workflow: workflow fields only
                return {
                    **workflow_base,
                    "files_checked": [],
                    "confidence": "exploring"
                }

            elif mode == "codereview":
                # codereview/workflow: workflow fields + review context
                return {
                    **workflow_base,
                    "files_checked": [],
                    "relevant_files": files or [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            elif mode == "analyze":
                # analyze/workflow: workflow fields + relevant_files (REQUIRED)
                return {
                    **workflow_base,
                    "relevant_files": files or ["/"],  # Required field!
                    "files_checked": [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium",
                    "analysis_type": "architecture"
                }

            elif mode == "consensus":
                # consensus/workflow: workflow fields + models (REQUIRED)
                return {
                    **workflow_base,
                    "models": [{"model": "o3", "stance": "neutral"}],  # Required field!
                    "files_checked": [],
                    "relevant_files": files or [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            elif mode == "security":
                # security/workflow: workflow fields + security context
                return {
                    **workflow_base,
                    "files_checked": [],
                    "relevant_files": files or [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium",
                    "security_scope": "comprehensive"
                }

            elif mode == "refactor":
                # refactor/workflow: workflow fields + refactor context
                return {
                    **workflow_base,
                    "files_checked": [],
                    "relevant_files": files or [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "incomplete",
                    "refactor_type": "codesmells"
                }

            elif mode == "testgen":
                # testgen/workflow: workflow fields + relevant_files (REQUIRED)
                return {
                    **workflow_base,
                    "relevant_files": files or ["/code"],  # Required field!
                    "files_checked": [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            elif mode == "planner":
                # planner/workflow: workflow fields + planning context
                return {
                    **workflow_base,
                    "files_checked": [],
                    "relevant_files": files or [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium"
                }

            elif mode == "tracer":
                # tracer/workflow: workflow fields + target (REQUIRED)
                return {
                    **workflow_base,
                    "target": request_text[:50] if request_text else "main",  # Required field!
                    "files_checked": [],
                    "relevant_files": files or [],
                    "relevant_context": [],
                    "issues_found": [],
                    "confidence": "medium",
                    "trace_mode": "ask"
                }

            elif mode == "chat":
                # chat/workflow: Uses ChatRequest which needs working_directory
                return {
                    "prompt": request_text,
                    "working_directory": "/tmp"
                }

            else:
                # Fallback: generic workflow fields
                return workflow_base

        async def execute(self, arguments: dict) -> list:
            """
            Execute tool by internally handling two-stage flow.

            This provides seamless backward compatibility - users call the tool
            by its original name and get real results automatically.
            """
            try:
                # Step 1: Force mode to match tool name (smart stubs always use their original mode)
                selected_mode = self.original_name

                # Determine complexity based on task complexity
                # For smart stubs, default to "simple" for straightforward use
                complexity = "simple"

                # Check if this looks like a multi-step workflow task
                task_description = arguments.get("request", "")
                if any(indicator in task_description.lower() for indicator in
                       ["step", "systematic", "comprehensive", "thorough", "investigate"]):
                    complexity = "workflow"

                # Step 2: Transform user's simple request to valid zen_execute format
                if complexity == "workflow":
                    request = self._build_workflow_request(selected_mode, arguments)
                else:  # simple or other
                    request = self._build_simple_request(selected_mode, arguments)

                # Step 3: Execute with mode executor and return actual result
                executor = create_mode_executor(selected_mode, complexity)
                result = await executor.execute(request)

                # Record telemetry for successful smart stub execution
                token_config.record_tool_execution(f"smart_stub_{self.original_name}", True)

                return result

            except Exception as e:
                logger.error(f"SmartStub '{self.original_name}' execution failed: {e}")
                token_config.record_tool_execution(f"smart_stub_{self.original_name}", False)

                # Return helpful error message
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "status": "error",
                            "tool": self.original_name,
                            "error": str(e),
                            "suggestion": (
                                f"The '{self.original_name}' tool encountered an error. "
                                f"Try providing more context in your 'request' field. "
                                f"You can also use the two-stage flow directly: "
                                f"zen_select_mode → zen_execute for more control."
                            )
                        }, indent=2)
                    )
                ]

    return SmartStub()


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
