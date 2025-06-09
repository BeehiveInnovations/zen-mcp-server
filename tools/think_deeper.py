"""
Think Deeper tool - Extended reasoning and problem-solving
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from config import MAX_CONTEXT_TOKENS, TEMPERATURE_CREATIVE
from prompts import THINK_DEEPER_PROMPT
from utils import check_token_limit, read_files

from .base import BaseTool, ToolRequest


class ThinkDeeperRequest(ToolRequest):
    """Request model for think_deeper tool"""

    current_analysis: str = Field(
        ..., description="Claude's current thinking/analysis to extend"
    )
    problem_context: Optional[str] = Field(
        None, description="Additional context about the problem or goal"
    )
    focus_areas: Optional[List[str]] = Field(
        None,
        description="Specific aspects to focus on (architecture, performance, security, etc.)",
    )
    files: Optional[List[str]] = Field(
        None, description="Optional file paths or directories for additional context"
    )


class ThinkDeeperTool(BaseTool):
    """Extended thinking and reasoning tool"""

    def get_name(self) -> str:
        return "think_deeper"

    def get_description(self) -> str:
        return (
            "EXTENDED THINKING & REASONING - Your deep thinking partner for complex problems. "
            "Use this when you need to extend your analysis, explore alternatives, or validate approaches. "
            "Perfect for: architecture decisions, complex bugs, performance challenges, security analysis. "
            "Triggers: 'think deeper', 'ultrathink', 'extend my analysis', 'explore alternatives'. "
            "I'll challenge assumptions, find edge cases, and provide alternative solutions."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current_analysis": {
                    "type": "string",
                    "description": "Your current thinking/analysis to extend and validate",
                },
                "problem_context": {
                    "type": "string",
                    "description": "Additional context about the problem or goal",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific aspects to focus on (architecture, performance, security, etc.)",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional file paths or directories for additional context",
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature for creative thinking (0-1, default 0.7)",
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth: minimal (128), low (2048), medium (8192), high (16384), max (32768)",
                    "default": "max",
                },
            },
            "required": ["current_analysis"],
        }

    def get_system_prompt(self) -> str:
        return THINK_DEEPER_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_CREATIVE

    def get_default_thinking_mode(self) -> str:
        """ThinkDeeper uses maximum thinking by default"""
        return "max"

    def get_request_model(self):
        return ThinkDeeperRequest

    async def prepare_prompt(self, request: ThinkDeeperRequest) -> str:
        """Prepare the full prompt for extended thinking"""
        # Build context parts
        context_parts = [
            f"=== CLAUDE'S CURRENT ANALYSIS ===\n{request.current_analysis}\n=== END ANALYSIS ==="
        ]

        if request.problem_context:
            context_parts.append(
                f"\n=== PROBLEM CONTEXT ===\n{request.problem_context}\n=== END CONTEXT ==="
            )

        # Add reference files if provided
        if request.files:
            file_content, _ = read_files(request.files)
            context_parts.append(
                f"\n=== REFERENCE FILES ===\n{file_content}\n=== END FILES ==="
            )

        full_context = "\n".join(context_parts)

        # Check token limits
        within_limit, estimated_tokens = check_token_limit(full_context)
        if not within_limit:
            raise ValueError(
                f"Context too large (~{estimated_tokens:,} tokens). "
                f"Maximum is {MAX_CONTEXT_TOKENS:,} tokens."
            )

        # Add focus areas instruction if specified
        focus_instruction = ""
        if request.focus_areas:
            areas = ", ".join(request.focus_areas)
            focus_instruction = (
                f"\n\nFOCUS AREAS: Please pay special attention to {areas} aspects."
            )

        # Combine system prompt with context
        full_prompt = f"""{self.get_system_prompt()}{focus_instruction}

{full_context}

Please provide deep analysis that extends Claude's thinking with:
1. Alternative approaches and solutions
2. Edge cases and potential failure modes
3. Critical evaluation of assumptions
4. Concrete implementation suggestions
5. Risk assessment and mitigation strategies"""

        return full_prompt

    def format_response(self, response: str, request: ThinkDeeperRequest) -> str:
        """Format the response with clear attribution"""
        return f"Extended Analysis by Gemini:\n\n{response}"
