"""
Debug Issue tool - Root cause analysis and debugging assistance
"""

from typing import TYPE_CHECKING, Any, Optional

from mcp.types import TextContent
from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_ANALYTICAL
from systemprompts import DEBUG_ISSUE_PROMPT

from .base import BaseTool, ToolRequest
from .models import ToolOutput


class DebugIssueRequest(ToolRequest):
    """Request model for debug tool"""

    prompt: str = Field(..., description="Error message, symptoms, or issue description")
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
        return "debug"

    def get_description(self) -> str:
        return (
            "DEBUG & ROOT CAUSE ANALYSIS - Expert debugging for complex issues with 1M token capacity. "
            "Use this when you need to debug code, find out why something is failing, identify root causes, "
            "trace errors, or diagnose issues. "
            "IMPORTANT: Share diagnostic files liberally! The model can handle up to 1M tokens, so include: "
            "large log files, full stack traces, memory dumps, diagnostic outputs, multiple related files, "
            "entire modules, test results, configuration files - anything that might help debug the issue. "
            "Claude should proactively use this tool whenever debugging is needed and share comprehensive "
            "file paths rather than snippets. Include error messages, stack traces, logs, and ALL relevant "
            "code files as absolute paths. The more context, the better the debugging analysis. "
            "Choose thinking_mode based on issue complexity: 'low' for simple errors, "
            "'medium' for standard debugging (default), 'high' for complex system issues, "
            "'max' for extremely challenging bugs requiring deepest analysis. "
            "Note: If you're not currently using a top-tier model such as Opus 4 or above, these tools can provide enhanced capabilities."
        )

    def get_input_schema(self) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Error message, symptoms, or issue description",
                },
                "model": self.get_model_field_schema(),
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
                    "description": "Thinking depth: minimal (0.5% of model max), low (8%), medium (33%), high (67%), max (100% of model max)",
                },
                "use_websearch": {
                    "type": "boolean",
                    "description": "Enable web search for documentation, best practices, and current information. Particularly useful for: brainstorming sessions, architectural design discussions, exploring industry best practices, working with specific frameworks/technologies, researching solutions to complex problems, or when current documentation and community insights would enhance the analysis.",
                    "default": True,
                },
                "continuation_id": {
                    "type": "string",
                    "description": "Thread continuation ID for multi-turn conversations. Can be used to continue conversations across different tools. Only provide this if continuing a previous conversation thread.",
                },
            },
            "required": ["prompt"] + (["model"] if self.is_effective_auto_mode() else []),
        }

        return schema

    def get_system_prompt(self) -> str:
        return DEBUG_ISSUE_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_model_category(self) -> "ToolModelCategory":
        """Debug requires deep analysis and reasoning"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.EXTENDED_REASONING

    def get_request_model(self):
        return DebugIssueRequest

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Override execute to check error_description and error_context size before processing"""
        # First validate request
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Check prompt size
        size_check = self.check_prompt_size(request.prompt)
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

        # If prompt.txt was found, use it as prompt or error_context
        if prompt_content:
            if not request.prompt or request.prompt == "":
                request.prompt = prompt_content
            else:
                request.error_context = prompt_content

        # Update request files list
        if updated_files is not None:
            request.files = updated_files

        # Build context sections
        context_parts = [f"=== ISSUE DESCRIPTION ===\n{request.prompt}\n=== END DESCRIPTION ==="]

        if request.error_context:
            context_parts.append(f"\n=== ERROR CONTEXT/STACK TRACE ===\n{request.error_context}\n=== END CONTEXT ===")

        if request.runtime_info:
            context_parts.append(f"\n=== RUNTIME INFORMATION ===\n{request.runtime_info}\n=== END RUNTIME ===")

        if request.previous_attempts:
            context_parts.append(f"\n=== PREVIOUS ATTEMPTS ===\n{request.previous_attempts}\n=== END ATTEMPTS ===")

        # Add relevant files if provided
        if request.files:
            # Use centralized file processing logic
            continuation_id = getattr(request, "continuation_id", None)
            file_content = self._prepare_file_content_for_prompt(request.files, continuation_id, "Code")

            if file_content:
                context_parts.append(f"\n=== RELEVANT CODE ===\n{file_content}\n=== END CODE ===")

        full_context = "\n".join(context_parts)

        # Check token limits
        self._validate_token_limit(full_context, "Context")

        # Add web search instruction if enabled
        websearch_instruction = self.get_websearch_instruction(
            request.use_websearch,
            """When debugging issues, consider if searches for these would help:
- The exact error message to find known solutions
- Framework-specific error codes and their meanings
- Similar issues in forums, GitHub issues, or Stack Overflow
- Workarounds and patches for known bugs
- Version-specific issues and compatibility problems""",
        )

        # Combine everything
        full_prompt = f"""{self.get_system_prompt()}{websearch_instruction}

{full_context}

Please debug this issue following the structured format in the system prompt.
Focus on finding the root cause and providing actionable solutions."""

        return full_prompt

    def format_response(self, response: str, request: DebugIssueRequest, model_info: Optional[dict] = None) -> str:
        """Format the debugging response"""
        # Get the friendly model name
        model_name = "the model"
        if model_info and model_info.get("model_response"):
            model_name = model_info["model_response"].friendly_name or "the model"

        return f"""{response}

---

**Next Steps:** Evaluate {model_name}'s recommendations, synthesize the best fix considering potential regressions, and if the root cause has been clearly identified, proceed with implementing the potential fixes."""
