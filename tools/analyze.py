"""
Analyze tool - General-purpose code and file analysis
"""

from typing import Any, Optional

from mcp.types import TextContent
from pydantic import Field

from config import TEMPERATURE_ANALYTICAL
from prompts import ANALYZE_PROMPT

from .base import BaseTool, ToolRequest
from .models import ToolOutput


class AnalyzeRequest(ToolRequest):
    """Request model for analyze tool"""

    files: list[str] = Field(..., description="Files or directories to analyze (must be absolute paths)")
    prompt: str = Field(..., description="What to analyze or look for")
    analysis_type: Optional[str] = Field(
        None,
        description="Type of analysis: architecture|performance|security|quality|general",
    )
    output_format: Optional[str] = Field("detailed", description="Output format: summary|detailed|actionable")


class AnalyzeTool(BaseTool):
    """General-purpose file and code analysis tool"""

    def get_name(self) -> str:
        return "analyze"

    def get_description(self) -> str:
        return (
            "ANALYZE FILES & CODE - General-purpose analysis for understanding code. "
            "Supports both individual files and entire directories. "
            "Use this when you need to analyze files, examine code, or understand specific aspects of a codebase. "
            "Perfect for: codebase exploration, dependency analysis, pattern detection. "
            "Always uses file paths for clean terminal output."
        )

    def get_input_schema(self) -> dict[str, Any]:
        from config import IS_AUTO_MODE

        schema = {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files or directories to analyze (must be absolute paths)",
                },
                "model": self.get_model_field_schema(),
                "prompt": {
                    "type": "string",
                    "description": "What to analyze or look for",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": [
                        "architecture",
                        "performance",
                        "security",
                        "quality",
                        "general",
                    ],
                    "description": "Type of analysis to perform",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["summary", "detailed", "actionable"],
                    "default": "detailed",
                    "description": "How to format the output",
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature (0-1, default 0.2)",
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
            "required": ["files", "prompt"] + (["model"] if IS_AUTO_MODE else []),
        }

        return schema

    def get_system_prompt(self) -> str:
        return ANALYZE_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_request_model(self):
        return AnalyzeRequest

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Override execute to check question size before processing"""
        # First validate request
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Check prompt size
        size_check = self.check_prompt_size(request.prompt)
        if size_check:
            return [TextContent(type="text", text=ToolOutput(**size_check).model_dump_json())]

        # Continue with normal execution
        return await super().execute(arguments)

    async def prepare_prompt(self, request: AnalyzeRequest) -> str:
        """Prepare the analysis prompt"""
        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # If prompt.txt was found, use it as the prompt
        if prompt_content:
            request.prompt = prompt_content

        # Update request files list
        if updated_files is not None:
            request.files = updated_files

        # Use centralized file processing logic
        continuation_id = getattr(request, "continuation_id", None)
        file_content = self._prepare_file_content_for_prompt(request.files, continuation_id, "Files")

        # Build analysis instructions
        analysis_focus = []

        if request.analysis_type:
            type_focus = {
                "architecture": "Focus on architectural patterns, structure, and design decisions",
                "performance": "Focus on performance characteristics and optimization opportunities",
                "security": "Focus on security implications and potential vulnerabilities",
                "quality": "Focus on code quality, maintainability, and best practices",
                "general": "Provide a comprehensive general analysis",
            }
            analysis_focus.append(type_focus.get(request.analysis_type, ""))

        if request.output_format == "summary":
            analysis_focus.append("Provide a concise summary of key findings")
        elif request.output_format == "actionable":
            analysis_focus.append("Focus on actionable insights and specific recommendations")

        focus_instruction = "\n".join(analysis_focus) if analysis_focus else ""

        # Add web search instruction if enabled
        websearch_instruction = self.get_websearch_instruction(
            request.use_websearch,
            """When analyzing code, consider if searches for these would help:
- Documentation for technologies or frameworks found in the code
- Best practices and design patterns relevant to the analysis
- API references and usage examples
- Known issues or solutions for patterns you identify""",
        )

        # Combine everything
        full_prompt = f"""{self.get_system_prompt()}

{focus_instruction}{websearch_instruction}

=== USER QUESTION ===
{request.prompt}
=== END QUESTION ===

=== FILES TO ANALYZE ===
{file_content}
=== END FILES ===

Please analyze these files to answer the user's question."""

        return full_prompt

    def format_response(self, response: str, request: AnalyzeRequest, model_info: Optional[dict] = None) -> str:
        """Format the analysis response"""
        return f"{response}\n\n---\n\n**Next Steps:** Use this analysis to actively continue your task. Investigate deeper into any findings, implement solutions based on these insights, and carry out the necessary work. Only pause to ask the user if you need their explicit approval for major changes or if critical decisions require their input."
