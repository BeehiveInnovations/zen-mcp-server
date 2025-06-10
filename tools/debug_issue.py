"""
Debug Issue tool - Root cause analysis and debugging assistance
"""

from typing import Any, Optional

from mcp.types import TextContent
from pydantic import Field

from config import TEMPERATURE_ANALYTICAL
from prompts import DEBUG_ISSUE_PROMPT
from utils import read_files

from .base import BaseTool, ToolRequest
from .models import ToolOutput


class DebugIssueRequest(ToolRequest):
    """Request model for debug_issue tool"""

    error_description: str = Field(..., description="Error message, symptoms, or issue description")
    error_context: Optional[str] = Field(None, description="Stack trace, logs, or additional error context")
    files: Optional[list[str]] = Field(
        None,
        description="Files or directories that might be related to the issue (must be absolute paths)",
    )
    runtime_info: Optional[str] = Field(None, description="Environment, versions, or runtime information")
    previous_attempts: Optional[str] = Field(None, description="What has been tried already")


class DebugIssueTool(BaseTool):
    """Advanced debugging and root cause analysis tool"""

    def get_name(self) -> str:
        return "debug_issue"

    def get_description(self) -> str:
        return (
            "DEBUG & ROOT CAUSE ANALYSIS - Expert debugging for complex issues. "
            "Use this when you need help tracking down bugs or understanding errors. "
            "Triggers: 'debug this', 'why is this failing', 'root cause', 'trace error'. "
            "I'll analyze the issue, find root causes, and provide step-by-step solutions. "
            "Include error messages, stack traces, and relevant code for best results. "
            "Choose thinking_mode based on issue complexity: 'low' for simple errors, "
            "'medium' for standard debugging (default), 'high' for complex system issues, "
            "'max' for extremely challenging bugs requiring deepest analysis."
        )

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "error_description": {
                    "type": "string",
                    "description": "Error message, symptoms, or issue description",
                },
                "error_context": {
                    "type": "string",
                    "description": "Stack trace, logs, or additional error context",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files or directories that might be related to the issue (must be absolute paths)",
                },
                "runtime_info": {
                    "type": "string",
                    "description": "Environment, versions, or runtime information",
                },
                "previous_attempts": {
                    "type": "string",
                    "description": "What has been tried already",
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature (0-1, default 0.2 for accuracy)",
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth: minimal (128), low (2048), medium (8192), high (16384), max (32768)",
                },
            },
            "required": ["error_description"],
        }

    def get_system_prompt(self) -> str:
        return DEBUG_ISSUE_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_request_model(self):
        return DebugIssueRequest

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Override execute to check error_description and error_context size before processing"""
        # First validate request
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Check error_description size
        size_check = self.check_prompt_size(request.error_description)
        if size_check:
            return [TextContent(type="text", text=ToolOutput(**size_check).model_dump_json())]

        # Check error_context size if provided
        if request.error_context:
            size_check = self.check_prompt_size(request.error_context)
            if size_check:
                return [TextContent(type="text", text=ToolOutput(**size_check).model_dump_json())]

        # Continue with normal execution
        return await super().execute(arguments)

    async def prepare_prompt(self, request: DebugIssueRequest) -> str:
        """Prepare the debugging prompt"""
        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # If prompt.txt was found, use it as error_description or error_context
        # Priority: if error_description is empty, use it there, otherwise use as error_context
        if prompt_content:
            if not request.error_description or request.error_description == "":
                request.error_description = prompt_content
            else:
                request.error_context = prompt_content

        # Update request files list
        if updated_files is not None:
            request.files = updated_files

        # Build context sections
        context_parts = [f"=== ISSUE DESCRIPTION ===\n{request.error_description}\n=== END DESCRIPTION ==="]

        if request.error_context:
            context_parts.append(f"\n=== ERROR CONTEXT/STACK TRACE ===\n{request.error_context}\n=== END CONTEXT ===")

        if request.runtime_info:
            context_parts.append(f"\n=== RUNTIME INFORMATION ===\n{request.runtime_info}\n=== END RUNTIME ===")

        if request.previous_attempts:
            context_parts.append(f"\n=== PREVIOUS ATTEMPTS ===\n{request.previous_attempts}\n=== END ATTEMPTS ===")

        # Add relevant files if provided
        if request.files:
            file_content = read_files(request.files)
            context_parts.append(f"\n=== RELEVANT CODE ===\n{file_content}\n=== END CODE ===")

        full_context = "\n".join(context_parts)

        # Check token limits
        self._validate_token_limit(full_context, "Context")

        # Combine everything
        full_prompt = f"""{self.get_system_prompt()}

{full_context}

Please debug this issue following the structured format in the system prompt.
Focus on finding the root cause and providing actionable solutions."""

        return full_prompt

    def format_response(self, response: str, request: DebugIssueRequest) -> str:
        """Format the debugging response"""
        return f"Debug Analysis\n{'=' * 50}\n\n{response}\n\n---\n\n**Next Steps:** Evaluate Gemini's recommendations, synthesize the best fix considering potential regressions, test thoroughly, and ensure the solution doesn't introduce new issues."
