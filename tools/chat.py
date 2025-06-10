"""
Chat tool - General development chat and collaborative thinking
"""

from typing import Any, Optional

from mcp.types import TextContent
from pydantic import Field

from config import TEMPERATURE_BALANCED
from prompts import CHAT_PROMPT
from utils import read_files

from .base import BaseTool, ToolRequest
from .models import ToolOutput


class ChatRequest(ToolRequest):
    """Request model for chat tool"""

    prompt: str = Field(
        ...,
        description="Your question, topic, or current thinking to discuss with Gemini",
    )
    files: Optional[list[str]] = Field(
        default_factory=list,
        description="Optional files for context (must be absolute paths)",
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
            "Use this when you want to ask Gemini questions, brainstorm ideas, get opinions, discuss topics, "
            "share your thinking, or need explanations about concepts and approaches."
        )

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Your question, topic, or current thinking to discuss with Gemini",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional files for context (must be absolute paths)",
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
                "use_websearch": {
                    "type": "boolean",
                    "description": "Enable web search for documentation, best practices, and current information. Particularly useful for: brainstorming sessions, architectural design discussions, exploring industry best practices, working with specific frameworks/technologies, researching solutions to complex problems, or when current documentation and community insights would enhance the analysis.",
                    "default": True,
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

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Override execute to check prompt size before processing"""
        # First validate request
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Check prompt size
        size_check = self.check_prompt_size(request.prompt)
        if size_check:
            return [TextContent(type="text", text=ToolOutput(**size_check).model_dump_json())]

        # Continue with normal execution
        return await super().execute(arguments)

    async def prepare_prompt(self, request: ChatRequest) -> str:
        """Prepare the chat prompt with optional context files"""
        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # Use prompt.txt content if available, otherwise use the prompt field
        user_content = prompt_content if prompt_content else request.prompt

        # Update request files list
        if updated_files is not None:
            request.files = updated_files

        # Add context files if provided
        if request.files:
            file_content = read_files(request.files)
            user_content = f"{user_content}\n\n=== CONTEXT FILES ===\n{file_content}\n=== END CONTEXT ===="

        # Check token limits
        self._validate_token_limit(user_content, "Content")

        # Add web search instruction if enabled
        websearch_instruction = self.get_websearch_instruction(
            request.use_websearch,
            """When discussing topics, consider if searches for these would help:
- Documentation for any technologies or concepts mentioned
- Current best practices and patterns
- Recent developments or updates
- Community discussions and solutions""",
        )

        # Combine system prompt with user content
        full_prompt = f"""{self.get_system_prompt()}{websearch_instruction}

=== USER REQUEST ===
{user_content}
=== END REQUEST ===

Please provide a thoughtful, comprehensive response:"""

        return full_prompt

    def format_response(self, response: str, request: ChatRequest) -> str:
        """Format the chat response with actionable guidance"""
        return f"{response}\n\n---\n\n**Claude's Turn:** Evaluate this perspective alongside your analysis to form a comprehensive solution and continue with the user's request and task at hand."
