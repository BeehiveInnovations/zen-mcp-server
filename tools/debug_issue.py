"""
Debug Issue tool - Root cause analysis and debugging assistance
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from config import MAX_CONTEXT_TOKENS, TEMPERATURE_ANALYTICAL
from prompts import DEBUG_ISSUE_PROMPT
from utils import check_token_limit, read_files

from .base import BaseTool, ToolRequest


class DebugIssueRequest(ToolRequest):
    """Request model for debug_issue tool"""

    error_description: str = Field(
        ..., description="Error message, symptoms, or issue description"
    )
    error_context: Optional[str] = Field(
        None, description="Stack trace, logs, or additional error context"
    )
    files: Optional[List[str]] = Field(
        None,
        description="Files or directories that might be related to the issue (must be absolute paths)",
    )
    runtime_info: Optional[str] = Field(
        None, description="Environment, versions, or runtime information"
    )
    previous_attempts: Optional[str] = Field(
        None, description="What has been tried already"
    )


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
            "Include error messages, stack traces, and relevant code for best results."
        )

    def get_input_schema(self) -> Dict[str, Any]:
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

    async def prepare_prompt(self, request: DebugIssueRequest) -> str:
        """Prepare the debugging prompt"""
        # Build context sections
        context_parts = [
            f"=== ISSUE DESCRIPTION ===\n{request.error_description}\n=== END DESCRIPTION ==="
        ]

        if request.error_context:
            context_parts.append(
                f"\n=== ERROR CONTEXT/STACK TRACE ===\n{request.error_context}\n=== END CONTEXT ==="
            )

        if request.runtime_info:
            context_parts.append(
                f"\n=== RUNTIME INFORMATION ===\n{request.runtime_info}\n=== END RUNTIME ==="
            )

        if request.previous_attempts:
            context_parts.append(
                f"\n=== PREVIOUS ATTEMPTS ===\n{request.previous_attempts}\n=== END ATTEMPTS ==="
            )

        # Add relevant files if provided
        if request.files:
            file_content, _ = read_files(request.files)
            context_parts.append(
                f"\n=== RELEVANT CODE ===\n{file_content}\n=== END CODE ==="
            )

        full_context = "\n".join(context_parts)

        # Check token limits
        within_limit, estimated_tokens = check_token_limit(full_context)
        if not within_limit:
            raise ValueError(
                f"Context too large (~{estimated_tokens:,} tokens). "
                f"Maximum is {MAX_CONTEXT_TOKENS:,} tokens."
            )

        # Combine everything
        full_prompt = f"""{self.get_system_prompt()}

{full_context}

Please debug this issue following the structured format in the system prompt.
Focus on finding the root cause and providing actionable solutions."""

        return full_prompt

    def format_response(self, response: str, request: DebugIssueRequest) -> str:
        """Format the debugging response"""
        return f"Debug Analysis\n{'=' * 50}\n\n{response}"
