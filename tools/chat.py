"""
Chat tool - General development chat and collaborative thinking

This tool provides a conversational interface for general development assistance,
brainstorming, problem-solving, and collaborative thinking. It supports file context,
images, and conversation continuation for seamless multi-turn interactions.
"""

import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

if TYPE_CHECKING:
    from providers.shared import ModelCapabilities
    from tools.models import ToolModelCategory

from config import TEMPERATURE_BALANCED
from systemprompts import CHAT_PROMPT, GENERATE_CODE_PROMPT
from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest

from .simple.base import SimpleTool

# Field descriptions matching the original Chat tool exactly
CHAT_FIELD_DESCRIPTIONS = {
    "prompt": (
        "Your question or idea for collaborative thinking. Provide detailed context, including your goal, what you've tried, and any specific challenges. "
        "CRITICAL: To discuss code, use 'files' parameter instead of pasting code blocks here."
    ),
    "files": "absolute file or folder paths for code context (do NOT shorten).",
    "images": "Optional absolute image paths or base64 for visual context when helpful.",
    "working_directory": (
        "Absolute full directory path where the assistant AI can save generated code for implementation. The directory must already exist"
    ),
}


class ChatRequest(ToolRequest):
    """Request model for Chat tool"""

    prompt: str = Field(..., description=CHAT_FIELD_DESCRIPTIONS["prompt"])
    files: Optional[list[str]] = Field(default_factory=list, description=CHAT_FIELD_DESCRIPTIONS["files"])
    images: Optional[list[str]] = Field(default_factory=list, description=CHAT_FIELD_DESCRIPTIONS["images"])
    working_directory: str = Field(..., description=CHAT_FIELD_DESCRIPTIONS["working_directory"])


class ChatTool(SimpleTool):
    """
    General development chat and collaborative thinking tool using SimpleTool architecture.

    This tool provides identical functionality to the original Chat tool but uses the new
    SimpleTool architecture for cleaner code organization and better maintainability.

    Migration note: This tool is designed to be a drop-in replacement for the original
    Chat tool with 100% behavioral compatibility.
    """

    def __init__(self) -> None:
        super().__init__()
        self._last_recordable_response: Optional[str] = None

    def get_name(self) -> str:
        return "chat"

    def get_description(self) -> str:
        return (
            "General chat and collaborative thinking partner for brainstorming, development discussion, "
            "getting second opinions, and exploring ideas. Use for ideas, validations, questions, and thoughtful explanations."
        )

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """Chat writes generated artifacts when code-generation is enabled."""

        return {"readOnlyHint": False}

    def get_system_prompt(self) -> str:
        return CHAT_PROMPT

    def get_capability_system_prompts(self, capabilities: Optional["ModelCapabilities"]) -> list[str]:
        prompts = list(super().get_capability_system_prompts(capabilities))
        if capabilities and capabilities.allow_code_generation:
            prompts.append(GENERATE_CODE_PROMPT)
        return prompts

    def get_default_temperature(self) -> float:
        return TEMPERATURE_BALANCED

    def get_model_category(self) -> "ToolModelCategory":
        """Chat prioritizes fast responses and cost efficiency"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.FAST_RESPONSE

    def get_request_model(self):
        """Return the Chat-specific request model"""
        return ChatRequest

    # === Schema Generation ===
    # For maximum compatibility, we override get_input_schema() to match the original Chat tool exactly

    def get_input_schema(self) -> dict[str, Any]:
        """
        Generate input schema matching the original Chat tool exactly.

        This maintains 100% compatibility with the original Chat tool by using
        the same schema generation approach while still benefiting from SimpleTool
        convenience methods.
        """
        required_fields = ["prompt", "working_directory"]
        if self.is_effective_auto_mode():
            required_fields.append("model")

        schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": CHAT_FIELD_DESCRIPTIONS["prompt"],
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": CHAT_FIELD_DESCRIPTIONS["files"],
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": CHAT_FIELD_DESCRIPTIONS["images"],
                },
                "working_directory": {
                    "type": "string",
                    "description": CHAT_FIELD_DESCRIPTIONS["working_directory"],
                },
                "model": self.get_model_field_schema(),
                "temperature": {
                    "type": "number",
                    "description": COMMON_FIELD_DESCRIPTIONS["temperature"],
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": COMMON_FIELD_DESCRIPTIONS["thinking_mode"],
                },
                "continuation_id": {
                    "type": "string",
                    "description": COMMON_FIELD_DESCRIPTIONS["continuation_id"],
                },
            },
            "required": required_fields,
        }

        return schema

    # === Tool-specific field definitions (alternative approach for reference) ===
    # These aren't used since we override get_input_schema(), but they show how
    # the tool could be implemented using the automatic SimpleTool schema building

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """
        Tool-specific field definitions for ChatSimple.

        Note: This method isn't used since we override get_input_schema() for
        exact compatibility, but it demonstrates how ChatSimple could be
        implemented using automatic schema building.
        """
        return {
            "prompt": {
                "type": "string",
                "description": CHAT_FIELD_DESCRIPTIONS["prompt"],
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": CHAT_FIELD_DESCRIPTIONS["files"],
            },
            "images": {
                "type": "array",
                "items": {"type": "string"},
                "description": CHAT_FIELD_DESCRIPTIONS["images"],
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for ChatSimple tool"""
        return ["prompt", "working_directory"]

    # === Hook Method Implementations ===

    async def prepare_prompt(self, request: ChatRequest) -> str:
        """
        Prepare the chat prompt with optional context files.

        This implementation matches the original Chat tool exactly while using
        SimpleTool convenience methods for cleaner code.
        """
        # Use SimpleTool's Chat-style prompt preparation
        return self.prepare_chat_style_prompt(request)

    def _validate_file_paths(self, request) -> Optional[str]:
        """Extend validation to cover the working directory path."""

        error = super()._validate_file_paths(request)
        if error:
            return error

        working_directory = getattr(request, "working_directory", None)
        if working_directory:
            expanded = os.path.expanduser(working_directory)
            if not os.path.isabs(expanded):
                return (
                    "Error: 'working_directory' must be an absolute path (you may use '~' which will be expanded). "
                    f"Received: {working_directory}"
                )
        return None

    def format_response(self, response: str, request: ChatRequest, model_info: Optional[dict] = None) -> str:
        """
        Format the chat response to match the original Chat tool exactly.
        """
        self._last_recordable_response = None
        body = response
        recordable_override: Optional[str] = None

        if self._model_supports_code_generation():
            block, remainder = self._extract_generated_code_block(response)
            if block:
                sanitized_text = remainder.strip()
                try:
                    artifact_path = self._persist_generated_code_block(block, request.working_directory)
                except Exception as exc:  # pragma: no cover - rare filesystem failures
                    logger.error("Failed to persist generated code block: %s", exc, exc_info=True)
                    warning = (
                        f"WARNING: Unable to write zen_generated.code inside '{request.working_directory}'. "
                        "Check the path permissions and re-run. The generated code block is included below for manual handling."
                    )

                    history_copy = self._join_sections(sanitized_text, warning) if sanitized_text else warning
                    recordable_override = history_copy

                    sanitized_warning = history_copy.strip()
                    body = f"{sanitized_warning}\n\n{block.strip()}".strip()
                else:
                    if not sanitized_text:
                        sanitized_text = "Generated code saved to zen_generated.code. Follow the structured instructions in that file exactly before continuing."

                    instruction = self._build_agent_instruction(artifact_path)
                    body = self._join_sections(sanitized_text, instruction)

        final_output = (
            f"{body}\n\n---\n\nAGENT'S TURN: Evaluate this perspective alongside your analysis to "
            "form a comprehensive solution and continue with the user's request and task at hand."
        )

        if recordable_override is not None:
            self._last_recordable_response = (
                f"{recordable_override}\n\n---\n\nAGENT'S TURN: Evaluate this perspective alongside your analysis to "
                "form a comprehensive solution and continue with the user's request and task at hand."
            )
        else:
            self._last_recordable_response = final_output

        return final_output

    def _record_assistant_turn(
        self, continuation_id: str, response_text: str, request, model_info: Optional[dict]
    ) -> None:
        recordable = self._last_recordable_response if self._last_recordable_response is not None else response_text
        try:
            super()._record_assistant_turn(continuation_id, recordable, request, model_info)
        finally:
            self._last_recordable_response = None

    def _model_supports_code_generation(self) -> bool:
        context = getattr(self, "_model_context", None)
        if not context:
            return False

        try:
            capabilities = context.capabilities
        except Exception:  # pragma: no cover - defensive fallback
            return False

        return bool(capabilities.allow_code_generation)

    def _extract_generated_code_block(self, text: str) -> tuple[Optional[str], str]:
        match = re.search(r"<GENERATED-CODE>.*?</GENERATED-CODE>", text, flags=re.DOTALL | re.IGNORECASE)
        if not match:
            return None, text

        block = match.group(0)
        before = text[: match.start()].rstrip()
        after = text[match.end() :].lstrip()

        if before and after:
            remainder = f"{before}\n\n{after}"
        else:
            remainder = before or after

        return block, remainder or ""

    def _persist_generated_code_block(self, block: str, working_directory: str) -> Path:
        expanded = os.path.expanduser(working_directory)
        target_dir = Path(expanded).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / "zen_generated.code"
        if target_file.exists():
            try:
                target_file.unlink()
            except OSError as exc:
                logger.warning("Unable to remove existing zen_generated.code: %s", exc)

        content = block if block.endswith("\n") else f"{block}\n"
        target_file.write_text(content, encoding="utf-8")
        logger.info("Generated code artifact written to %s", target_file)
        return target_file

    @staticmethod
    def _build_agent_instruction(artifact_path: Path) -> str:
        return (
            f"CONTINUING FROM PREVIOUS DISCUSSION: The coding assistant has analyzed our conversation context and generated "
            f"a structured implementation plan at `{artifact_path}`. This is a direct continuation of our discussion—all previous "
            "context, requirements, and shared code remain relevant.\n"
            "\n"
            f"MANDATORY NEXT STEP: Open `{artifact_path}` immediately and review the implementation plan:\n"
            "1. Read the step-by-step instructions—they reference our previous discussion. You may need to read the file in parts if it's too long.\n"
            "2. Review each <NEWFILE:…> or <UPDATED_EXISTING_FILE:…> section in the context of what we've discussed\n"
            "3. Verify the proposed changes align with the requirements and code we've already shared\n"
            "4. Check for syntax errors, missing imports, or incomplete implementations\n"
            "\n"
            "Then systematically apply the changes:\n"
            "- Create new files or update existing ones as instructed, maintaining code style consistency\n"
            "- If updating existing code we discussed earlier, carefully preserve unmodified sections\n"
            "- Run syntax validation after each modification\n"
            "- Execute relevant tests to confirm functionality\n"
            "- Verify the implementation works end-to-end with existing code\n"
            "\n"
            "Remember: This builds upon our conversation. The generated code reflects the full context of what we've discussed, "
            "including any files, requirements, or constraints mentioned earlier. Proceed with implementation immediately."
            "Only after you finish applying ALL the changes completely: delete `zen_generated.code` so stale instructions do not linger."
        )

    @staticmethod
    def _join_sections(*sections: str) -> str:
        chunks: list[str] = []
        for section in sections:
            if section:
                trimmed = section.strip()
                if trimmed:
                    chunks.append(trimmed)
        return "\n\n".join(chunks)

    def get_websearch_guidance(self) -> str:
        """
        Return Chat tool-style web search guidance.
        """
        return self.get_chat_style_websearch_guidance()


logger = logging.getLogger(__name__)
