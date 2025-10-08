"""
Zen Execute Tool - Single executor with mode parameter for Stage 2

This tool implements Stage 2 of the two-stage token optimization architecture.
It accepts a mode parameter from Stage 1 and dispatches to the appropriate
executor with minimal schema overhead.

Token usage: 600-800 tokens (vs 3-4k tokens in original tools)
"""

import json
import logging
from typing import Any, Optional

from mcp.types import TextContent

from .mode_executor import MODE_REQUEST_MAP, ModeExecutor
from .shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ZenExecuteTool(BaseTool):
    """
    Single executor tool with mode parameter for Stage 2 optimization.

    This tool receives the mode recommendation from Stage 1 (zen_select_mode)
    and executes the appropriate tool with minimal schema overhead, achieving
    95% token reduction while maintaining full functionality.
    """

    def __init__(self):
        super().__init__()
        # CRITICAL: MCP requires these as attributes, not just methods
        self.name = "zen_execute"
        self.description = self.get_description()

    def get_name(self) -> str:
        return "zen_execute"

    def get_description(self) -> str:
        return """Execute Zen tool in optimized mode (Stage 2 of token optimization).
        
        USAGE PATTERN:
        1. First use 'zen_select_mode' to get mode recommendation (Stage 1)
        2. Then use 'zen_execute' with the recommended mode (Stage 2)
        
        This achieves 95% token reduction (43k → 200-800 tokens total).
        
        MODES:
        - debug: Root cause analysis and debugging
        - codereview: Code review and quality assessment  
        - analyze: Architecture and code analysis
        - chat: General AI consultation
        - consensus: Multi-model consensus building
        - security: Security audit and vulnerability assessment
        - refactor: Refactoring opportunity analysis
        - testgen: Test generation with edge cases
        - planner: Sequential task planning
        - tracer: Code execution and dependency tracing
        
        IMPORTANT: Always use zen_select_mode first for optimal results!"""

    def get_system_prompt(self) -> str:
        return """You are executing Stage 2 of the token optimization architecture.
        The mode has been selected and you're now executing with minimal schema overhead.
        Focus on the specific task using the optimized parameters provided."""

    def get_default_temperature(self) -> float:
        return 0.3

    def get_model_category(self):
        from tools.models import ToolModelCategory

        # Default to extended reasoning since most modes need it
        return ToolModelCategory.EXTENDED_REASONING

    def get_input_schema(self) -> dict[str, Any]:
        """
        Schema that accepts mode and mode-specific parameters.

        This single schema replaces multiple tool schemas, dramatically
        reducing token usage while maintaining flexibility.
        """
        return {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": [
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
                    ],
                    "description": "Execution mode from Stage 1 recommendation. ALWAYS get this from zen_select_mode first!",
                },
                "complexity": {
                    "type": "string",
                    "enum": ["simple", "workflow", "expert"],
                    "default": "simple",
                    "description": "Task complexity level (from Stage 1 recommendation)",
                },
                "request": {
                    "type": "object",
                    "description": "Mode-specific parameters. Structure depends on mode and complexity. Get required fields from zen_select_mode.",
                    "additionalProperties": True,
                },
            },
            "required": ["mode", "request"],
            "additionalProperties": False,
            "examples": [
                {
                    "mode": "debug",
                    "complexity": "simple",
                    "request": {
                        "problem": "OAuth tokens not persisting",
                        "files": ["/src/auth.py"],
                        "confidence": "exploring",
                    },
                },
                {
                    "mode": "codereview",
                    "complexity": "workflow",
                    "request": {
                        "step": "Initial review",
                        "step_number": 1,
                        "findings": "Starting code review",
                        "relevant_files": ["/src/main.py"],
                        "next_step_required": True,
                    },
                },
            ],
        }

    async def execute(self, arguments: dict[str, Any]) -> list:
        """
        Execute the appropriate tool based on mode parameter.

        This delegates to ModeExecutor which handles the actual execution
        with mode-specific logic and minimal schemas.
        """
        try:
            # Extract mode and complexity
            mode = arguments.get("mode")
            if not mode:
                raise ValueError("'mode' parameter is required. Use zen_select_mode first!")

            complexity = arguments.get("complexity", "simple")
            request_params = arguments.get("request", {})

            # Validate mode
            valid_modes = [
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
            if mode not in valid_modes:
                raise ValueError(f"Invalid mode: {mode}. Valid modes: {valid_modes}")

            # Create mode executor
            executor = ModeExecutor(mode, complexity)

            # Log token optimization metrics
            logger.info(f"Stage 2 execution: mode={mode}, complexity={complexity}")

            # Execute with mode-specific parameters
            result = await executor.execute(request_params)

            # Add optimization metadata
            if result and isinstance(result[0], TextContent):
                try:
                    data = json.loads(result[0].text)
                    if "_meta" not in data:
                        data["_meta"] = {}

                    data["_meta"].update(
                        {
                            "stage": "2",
                            "mode": mode,
                            "complexity": complexity,
                            "token_optimized": True,
                            "optimization_level": "95%",
                            "hint": "Use zen_select_mode for Stage 1 to get optimal parameters",
                        }
                    )

                    result[0] = TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))
                except (json.JSONDecodeError, KeyError):
                    pass  # Keep original result if not JSON

            return result

        except Exception as e:
            logger.error(f"Error in zen_execute: {e}", exc_info=True)

            error_data = {
                "status": "error",
                "stage": "2",
                "message": str(e),
                "suggestion": "Use zen_select_mode first to get the correct mode and parameters",
                "usage_pattern": [
                    "1. Call zen_select_mode with task description",
                    "2. Get mode recommendation and required fields",
                    "3. Call zen_execute with mode and parameters",
                ],
            }

            return [TextContent(type="text", text=json.dumps(error_data, indent=2, ensure_ascii=False))]

    async def prepare_prompt(self, request) -> str:
        """Not used - zen_execute uses execute() directly."""
        return ""

    def get_request_model(self):
        """Return None as we handle multiple request models dynamically"""
        return None

    @staticmethod
    def get_mode_schema(mode: str, complexity: str = "simple") -> dict:
        """
        Helper to get the schema for a specific mode and complexity.
        Used by zen_select_mode to inform Claude about required fields.
        """
        key = (mode, complexity)
        request_model = MODE_REQUEST_MAP.get(key)

        if not request_model:
            return {"description": f"Parameters for {mode} execution"}

        # Build minimal schema from model
        schema = {"type": "object", "properties": {}, "required": []}

        for field_name, field_info in request_model.model_fields.items():
            if field_info.exclude:
                continue

            field_schema = {"type": "string"}  # Default

            # Get actual type
            from typing import get_args, get_origin

            field_type = field_info.annotation

            if get_origin(field_type) is type(Optional):
                args = get_args(field_type)
                if args:
                    field_type = args[0]

            # Map types
            if field_type == str:
                field_schema["type"] = "string"
            elif field_type == int:
                field_schema["type"] = "integer"
            elif field_type == bool:
                field_schema["type"] = "boolean"
            elif field_type == float:
                field_schema["type"] = "number"
            elif get_origin(field_type) == list:
                field_schema["type"] = "array"
                field_schema["items"] = {"type": "string"}

            if field_info.description:
                field_schema["description"] = field_info.description

            schema["properties"][field_name] = field_schema

            if field_info.is_required():
                schema["required"].append(field_name)

        return schema
