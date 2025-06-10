"""
Code Review tool - Comprehensive code analysis and review

This tool provides professional-grade code review capabilities using
Gemini's understanding of code patterns, best practices, and common issues.
It can analyze individual files or entire codebases, providing actionable
feedback categorized by severity.

Key Features:
- Multi-file and directory support
- Configurable review types (full, security, performance, quick)
- Severity-based issue filtering
- Custom focus areas and coding standards
- Structured output with specific remediation steps
"""

from typing import Any, Dict, List, Optional

from mcp.types import TextContent
from pydantic import Field

from config import TEMPERATURE_ANALYTICAL
from prompts import REVIEW_CODE_PROMPT
from utils import read_files

from .base import BaseTool, ToolRequest
from .models import ToolOutput


class ReviewCodeRequest(ToolRequest):
    """
    Request model for the code review tool.

    This model defines all parameters that can be used to customize
    the code review process, from selecting files to specifying
    review focus and standards.
    """

    files: List[str] = Field(
        ...,
        description="Code files or directories to review (must be absolute paths)",
    )
    review_type: str = Field(
        "full", description="Type of review: full|security|performance|quick"
    )
    focus_on: Optional[str] = Field(
        None, description="Specific aspects to focus on during review"
    )
    standards: Optional[str] = Field(
        None, description="Coding standards or guidelines to enforce"
    )
    severity_filter: str = Field(
        "all",
        description="Minimum severity to report: critical|high|medium|all",
    )


class ReviewCodeTool(BaseTool):
    """
    Professional code review tool implementation.

    This tool analyzes code for bugs, security vulnerabilities, performance
    issues, and code quality problems. It provides detailed feedback with
    severity ratings and specific remediation steps.
    """

    def get_name(self) -> str:
        return "review_code"

    def get_description(self) -> str:
        return (
            "PROFESSIONAL CODE REVIEW - Comprehensive analysis for bugs, security, and quality. "
            "Supports both individual files and entire directories/projects. "
            "Use this for thorough code review with actionable feedback. "
            "Triggers: 'review this code', 'check for issues', 'find bugs', 'security audit'. "
            "I'll identify issues by severity (Critical→High→Medium→Low) with specific fixes. "
            "Supports focused reviews: security, performance, or quick checks."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code files or directories to review (must be absolute paths)",
                },
                "review_type": {
                    "type": "string",
                    "enum": ["full", "security", "performance", "quick"],
                    "default": "full",
                    "description": "Type of review to perform",
                },
                "focus_on": {
                    "type": "string",
                    "description": "Specific aspects to focus on",
                },
                "standards": {
                    "type": "string",
                    "description": "Coding standards to enforce",
                },
                "severity_filter": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "all"],
                    "default": "all",
                    "description": "Minimum severity level to report",
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature (0-1, default 0.2 for consistency)",
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth: minimal (128), low (2048), medium (8192), high (16384), max (32768)",
                },
            },
            "required": ["files"],
        }

    def get_system_prompt(self) -> str:
        return REVIEW_CODE_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_ANALYTICAL

    def get_request_model(self):
        return ReviewCodeRequest

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Override execute to check focus_on size before processing"""
        # First validate request
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Check focus_on size if provided
        if request.focus_on:
            size_check = self.check_prompt_size(request.focus_on)
            if size_check:
                return [
                    TextContent(
                        type="text", text=ToolOutput(**size_check).model_dump_json()
                    )
                ]

        # Continue with normal execution
        return await super().execute(arguments)

    async def prepare_prompt(self, request: ReviewCodeRequest) -> str:
        """
        Prepare the code review prompt with customized instructions.

        This method reads the requested files, validates token limits,
        and constructs a detailed prompt based on the review parameters.

        Args:
            request: The validated review request

        Returns:
            str: Complete prompt for the Gemini model

        Raises:
            ValueError: If the code exceeds token limits
        """
        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # If prompt.txt was found, use it as focus_on
        if prompt_content:
            request.focus_on = prompt_content

        # Update request files list
        if updated_files is not None:
            request.files = updated_files

        # Read all requested files, expanding directories as needed
        file_content, summary = read_files(request.files)

        # Validate that the code fits within model context limits
        self._validate_token_limit(file_content, "Code")

        # Build customized review instructions based on review type
        review_focus = []
        if request.review_type == "security":
            review_focus.append(
                "Focus on security vulnerabilities and authentication issues"
            )
        elif request.review_type == "performance":
            review_focus.append(
                "Focus on performance bottlenecks and optimization opportunities"
            )
        elif request.review_type == "quick":
            review_focus.append(
                "Provide a quick review focusing on critical issues only"
            )

        # Add any additional focus areas specified by the user
        if request.focus_on:
            review_focus.append(f"Pay special attention to: {request.focus_on}")

        # Include custom coding standards if provided
        if request.standards:
            review_focus.append(f"Enforce these standards: {request.standards}")

        # Apply severity filtering to reduce noise if requested
        if request.severity_filter != "all":
            review_focus.append(
                f"Only report issues of {request.severity_filter} severity or higher"
            )

        focus_instruction = "\n".join(review_focus) if review_focus else ""

        # Construct the complete prompt with system instructions and code
        full_prompt = f"""{self.get_system_prompt()}

{focus_instruction}

=== CODE TO REVIEW ===
{file_content}
=== END CODE ===

Please provide a comprehensive code review following the format specified in the system prompt."""

        return full_prompt

    def format_response(self, response: str, request: ReviewCodeRequest) -> str:
        """
        Format the review response with appropriate headers.

        Adds context about the review type and focus area to help
        users understand the scope of the review.

        Args:
            response: The raw review from the model
            request: The original request for context

        Returns:
            str: Formatted response with headers
        """
        header = f"Code Review ({request.review_type.upper()})"
        if request.focus_on:
            header += f" - Focus: {request.focus_on}"
        return f"{header}\n{'=' * 50}\n\n{response}"
