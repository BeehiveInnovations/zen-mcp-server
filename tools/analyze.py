"""
Analyze tool - General-purpose code and file analysis
"""

from typing import Any, Dict, List, Optional

from mcp.types import TextContent
from pydantic import Field

from config import TEMPERATURE_ANALYTICAL
from prompts import ANALYZE_PROMPT
from utils import read_files

from .base import BaseTool, ToolRequest
from .models import ToolOutput


class AnalyzeRequest(ToolRequest):
    """Request model for analyze tool"""

    files: List[str] = Field(
        ..., description="Files or directories to analyze (must be absolute paths)"
    )
    question: str = Field(..., description="What to analyze or look for")
    analysis_type: Optional[str] = Field(
        None,
        description="Type of analysis: architecture|performance|security|quality|general",
    )
    output_format: Optional[str] = Field(
        "detailed", description="Output format: summary|detailed|actionable"
    )


class AnalyzeTool(BaseTool):
    """General-purpose file and code analysis tool"""

    def get_name(self) -> str:
        return "analyze"

    def get_description(self) -> str:
        return (
            "ANALYZE FILES & CODE - General-purpose analysis for understanding code. "
            "Supports both individual files and entire directories. "
            "Use this for examining files, understanding architecture, or investigating specific aspects. "
            "Triggers: 'analyze these files', 'examine this code', 'understand this'. "
            "Perfect for: codebase exploration, dependency analysis, pattern detection. "
            "Always uses file paths for clean terminal output."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files or directories to analyze (must be absolute paths)",
                },
                "question": {
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
                    "description": "Thinking depth: minimal (128), low (2048), medium (8192), high (16384), max (32768)",
                },
            },
            "required": ["files", "question"],
        }

    def get_system_prompt(self) -> str:
        return ANALYZE_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_request_model(self):
        return AnalyzeRequest

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Override execute to check question size before processing"""
        # First validate request
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Check question size
        size_check = self.check_prompt_size(request.question)
        if size_check:
            return [
                TextContent(
                    type="text", text=ToolOutput(**size_check).model_dump_json()
                )
            ]

        # Continue with normal execution
        return await super().execute(arguments)

    async def prepare_prompt(self, request: AnalyzeRequest) -> str:
        """Prepare the analysis prompt"""
        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # If prompt.txt was found, use it as the question
        if prompt_content:
            request.question = prompt_content

        # Update request files list
        if updated_files is not None:
            request.files = updated_files

        # Read all files
        file_content, summary = read_files(request.files)

        # Check token limits
        self._validate_token_limit(file_content, "Files")

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
            analysis_focus.append(
                "Focus on actionable insights and specific recommendations"
            )

        focus_instruction = "\n".join(analysis_focus) if analysis_focus else ""

        # Combine everything
        full_prompt = f"""{self.get_system_prompt()}

{focus_instruction}

=== USER QUESTION ===
{request.question}
=== END QUESTION ===

=== FILES TO ANALYZE ===
{file_content}
=== END FILES ===

Please analyze these files to answer the user's question."""

        return full_prompt

    def format_response(self, response: str, request: AnalyzeRequest) -> str:
        """Format the analysis response"""
        header = f"Analysis: {request.question[:50]}..."
        if request.analysis_type:
            header = f"{request.analysis_type.upper()} Analysis"

        summary_text = f"Analyzed {len(request.files)} file(s)"

        return f"{header}\n{summary_text}\n{'=' * 50}\n\n{response}"
