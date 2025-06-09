"""
Chat tool - General development chat and collaborative thinking
"""

from typing import Any, Dict, List, Optional

from pydantic import Field

from config import MAX_CONTEXT_TOKENS, TEMPERATURE_BALANCED
from prompts import CHAT_PROMPT
from utils import check_token_limit, read_files

from .base import BaseTool, ToolRequest


class ChatRequest(ToolRequest):
    """Request model for chat tool"""

    prompt: str = Field(
        ...,
        description="Your question, topic, or current thinking to discuss with Gemini",
    )
    context_files: Optional[List[str]] = Field(
        default_factory=list, description="Optional files for context"
    )


class ChatTool(BaseTool):
    """General development chat and collaborative thinking tool"""

    def get_name(self) -> str:
        return "chat"

    def get_description(self) -> str:
        return (
            "GENERAL CHAT & COLLABORATIVE THINKING - Use Gemini as your thinking partner! "
            "Perfect for: bouncing ideas during your own analysis, getting second opinions on your plans, "
            "collaborative brainstorming, validating your checklists and approaches, exploring alternatives. "
            "Also great for: explanations, comparisons, general development questions. "
            "Triggers: 'ask gemini', 'brainstorm with gemini', 'get gemini's opinion', 'discuss with gemini', "
            "'share my thinking with gemini', 'explain', 'what is', 'how do I'."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Your question, topic, or current thinking to discuss with Gemini",
                },
                "context_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional files for context",
                },
                "temperature": {
                    "type": "number",
                    "description": "Response creativity (0-1, default 0.5)",
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth: minimal (128), low (2048), medium (8192), high (16384), max (32768)",
                },
            },
            "required": ["prompt"],
        }

    def get_system_prompt(self) -> str:
        return CHAT_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_BALANCED

    def get_request_model(self):
        return ChatRequest

    async def prepare_prompt(self, request: ChatRequest) -> str:
        """Prepare the chat prompt with optional context files"""
        user_content = request.prompt

        # Add context files if provided
        if request.context_files:
            file_content, _ = read_files(request.context_files)
            user_content = f"{request.prompt}\n\n=== CONTEXT FILES ===\n{file_content}\n=== END CONTEXT ==="

        # Check token limits
        within_limit, estimated_tokens = check_token_limit(user_content)
        if not within_limit:
            raise ValueError(
                f"Content too large (~{estimated_tokens:,} tokens). "
                f"Maximum is {MAX_CONTEXT_TOKENS:,} tokens."
            )

        # Combine system prompt with user content
        full_prompt = f"""{self.get_system_prompt()}

=== USER REQUEST ===
{user_content}
=== END REQUEST ===

Please provide a thoughtful, comprehensive response:"""

        return full_prompt

    def format_response(self, response: str, request: ChatRequest) -> str:
        """Format the chat response (no special formatting needed)"""
        return response
