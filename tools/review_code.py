"""
Code Review tool - Comprehensive code analysis and review
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from config import MAX_CONTEXT_TOKENS, TEMPERATURE_ANALYTICAL
from prompts import REVIEW_CODE_PROMPT
from utils import check_token_limit, read_files

from .base import BaseTool, ToolRequest


class ReviewCodeRequest(ToolRequest):
    """Request model for review_code tool"""

    files: List[str] = Field(..., description="Code files or directories to review")
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
    """Professional code review tool"""

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
                    "description": "Code files or directories to review",
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

    async def prepare_prompt(self, request: ReviewCodeRequest) -> str:
        """Prepare the code review prompt"""
        # Read all files
        file_content, summary = read_files(request.files)

        # Check token limits
        within_limit, estimated_tokens = check_token_limit(file_content)
        if not within_limit:
            raise ValueError(
                f"Code too large (~{estimated_tokens:,} tokens). "
                f"Maximum is {MAX_CONTEXT_TOKENS:,} tokens."
            )

        # Build review instructions
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

        if request.focus_on:
            review_focus.append(f"Pay special attention to: {request.focus_on}")

        if request.standards:
            review_focus.append(f"Enforce these standards: {request.standards}")

        if request.severity_filter != "all":
            review_focus.append(
                f"Only report issues of {request.severity_filter} severity or higher"
            )

        focus_instruction = "\n".join(review_focus) if review_focus else ""

        # Combine everything
        full_prompt = f"""{self.get_system_prompt()}

{focus_instruction}

=== CODE TO REVIEW ===
{file_content}
=== END CODE ===

Please provide a comprehensive code review following the format specified in the system prompt."""

        return full_prompt

    def format_response(self, response: str, request: ReviewCodeRequest) -> str:
        """Format the review response"""
        header = f"Code Review ({request.review_type.upper()})"
        if request.focus_on:
            header += f" - Focus: {request.focus_on}"
        return f"{header}\n{'=' * 50}\n\n{response}"
