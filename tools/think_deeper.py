"""
Think Deeper tool - Extended reasoning and problem-solving
"""

from typing import Any, Optional

from mcp.types import TextContent
from pydantic import Field

from config import TEMPERATURE_CREATIVE
from prompts import THINK_DEEPER_PROMPT
from utils import read_files

from .base import BaseTool, ToolRequest
from .models import ToolOutput


class ThinkDeeperRequest(ToolRequest):
    """Request model for think_deeper tool"""

    current_analysis: str = Field(..., description="Claude's current thinking/analysis to extend")
    problem_context: Optional[str] = Field(None, description="Additional context about the problem or goal")
    focus_areas: Optional[list[str]] = Field(
        None,
        description="Specific aspects to focus on (architecture, performance, security, etc.)",
    )
    files: Optional[list[str]] = Field(
        None,
        description="Optional file paths or directories for additional context (must be absolute paths)",
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
            "I'll challenge assumptions, find edge cases, and provide alternative solutions. "
            "IMPORTANT: Choose the appropriate thinking_mode based on task complexity - "
            "'low' for quick analysis, 'medium' for standard problems, 'high' for complex issues (default), "
            "'max' for extremely complex challenges requiring deepest analysis. "
            "When in doubt, err on the side of a higher mode for truly deep thought and evaluation."
        )

    def get_input_schema(self) -> dict[str, Any]:
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
                    "description": "Optional file paths or directories for additional context (must be absolute paths)",
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
                    "default": "high",
                },
                "use_websearch": {
                    "type": "boolean",
                    "description": "Enable web search for documentation, best practices, and current information. Particularly useful for: brainstorming sessions, architectural design discussions, exploring industry best practices, working with specific frameworks/technologies, researching solutions to complex problems, or when current documentation and community insights would enhance the analysis.",
                    "default": False,
                },
            },
            "required": ["current_analysis"],
        }

    def get_system_prompt(self) -> str:
        return THINK_DEEPER_PROMPT

    def get_default_temperature(self) -> float:
        return TEMPERATURE_CREATIVE

    def get_default_thinking_mode(self) -> str:
        """ThinkDeeper uses high thinking by default"""
        return "high"

    def get_request_model(self):
        return ThinkDeeperRequest

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Override execute to check current_analysis size before processing"""
        # First validate request
        request_model = self.get_request_model()
        request = request_model(**arguments)

        # Check current_analysis size
        size_check = self.check_prompt_size(request.current_analysis)
        if size_check:
            return [TextContent(type="text", text=ToolOutput(**size_check).model_dump_json())]

        # Continue with normal execution
        return await super().execute(arguments)

    async def prepare_prompt(self, request: ThinkDeeperRequest) -> str:
        """Prepare the full prompt for extended thinking"""
        # Check for prompt.txt in files
        prompt_content, updated_files = self.handle_prompt_file(request.files)

        # Use prompt.txt content if available, otherwise use the current_analysis field
        current_analysis = prompt_content if prompt_content else request.current_analysis

        # Update request files list
        if updated_files is not None:
            request.files = updated_files

        # Build context parts
        context_parts = [f"=== CLAUDE'S CURRENT ANALYSIS ===\n{current_analysis}\n=== END ANALYSIS ==="]

        if request.problem_context:
            context_parts.append(f"\n=== PROBLEM CONTEXT ===\n{request.problem_context}\n=== END CONTEXT ===")

        # Add reference files if provided
        if request.files:
            file_content = read_files(request.files)
            context_parts.append(f"\n=== REFERENCE FILES ===\n{file_content}\n=== END FILES ===")

        full_context = "\n".join(context_parts)

        # Check token limits
        self._validate_token_limit(full_context, "Context")

        # Add focus areas instruction if specified
        focus_instruction = ""
        if request.focus_areas:
            areas = ", ".join(request.focus_areas)
            focus_instruction = f"\n\nFOCUS AREAS: Please pay special attention to {areas} aspects."

        # Add web search instruction if enabled
        websearch_instruction = self.get_websearch_instruction(
            request.use_websearch,
            """Specifically search for:
- Current documentation for technologies, frameworks, or APIs being discussed
- Similar issues and their solutions from the community
- Best practices and recent developments
- Official sources to verify information""",
        )

        # Combine system prompt with context
        full_prompt = f"""{self.get_system_prompt()}{focus_instruction}{websearch_instruction}

{full_context}

Please provide deep analysis that extends Claude's thinking with:
1. Alternative approaches and solutions
2. Edge cases and potential failure modes
3. Critical evaluation of assumptions
4. Concrete implementation suggestions
5. Risk assessment and mitigation strategies"""

        return full_prompt

    def format_response(self, response: str, request: ThinkDeeperRequest) -> str:
        """Format the response with clear attribution and critical thinking prompt"""
        return f"""## Extended Analysis by Gemini

{response}

---

## Critical Evaluation Required

Claude, please critically evaluate Gemini's analysis by considering:

1. **Technical merit** - Which suggestions are valuable vs. have limitations?
2. **Constraints** - Fit with codebase patterns, performance, security, architecture
3. **Risks** - Hidden complexities, edge cases, potential failure modes
4. **Final recommendation** - Synthesize both perspectives, then think deeply further to explore additional considerations and arrive at the best technical solution

Remember: Use Gemini's insights to enhance, not replace, your analysis."""
