"""
Base class for simple MCP tools.

Simple tools follow a straightforward pattern:
1. Receive request
2. Prepare prompt (with files, context, etc.)
3. Call AI model
4. Format and return response

They use the shared SchemaBuilder for consistent schema generation
and inherit all the conversation, file processing, and model handling
capabilities from BaseTool.
"""

from abc import abstractmethod
from typing import Any, Optional

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from tools.shared.schema_builders import SchemaBuilder


class SimpleTool(BaseTool):
    """
    Base class for simple (non-workflow) tools.

    Simple tools are request/response tools that don't require multi-step workflows.
    They benefit from:
    - Automatic schema generation using SchemaBuilder
    - Inherited conversation handling and file processing
    - Standardized model integration
    - Consistent error handling and response formatting

    To create a simple tool:
    1. Inherit from SimpleTool
    2. Implement get_tool_fields() to define tool-specific fields
    3. Implement prepare_prompt() for prompt preparation
    4. Optionally override format_response() for custom formatting
    5. Optionally override get_required_fields() for custom requirements

    Example:
        class ChatTool(SimpleTool):
            def get_name(self) -> str:
                return "chat"

            def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
                return {
                    "prompt": {
                        "type": "string",
                        "description": "Your question or idea...",
                    },
                    "files": SimpleTool.FILES_FIELD,
                }

            def get_required_fields(self) -> List[str]:
                return ["prompt"]
    """

    # Common field definitions that simple tools can reuse
    FILES_FIELD = SchemaBuilder.COMMON_FIELD_SCHEMAS["files"]
    IMAGES_FIELD = SchemaBuilder.COMMON_FIELD_SCHEMAS["images"]

    @abstractmethod
    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """
        Return tool-specific field definitions.

        This method should return a dictionary mapping field names to their
        JSON schema definitions. Common fields (model, temperature, etc.)
        are added automatically by the base class.

        Returns:
            Dict mapping field names to JSON schema objects

        Example:
            return {
                "prompt": {
                    "type": "string",
                    "description": "The user's question or request",
                },
                "files": SimpleTool.FILES_FIELD,  # Reuse common field
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Maximum tokens for response",
                }
            }
        """
        pass

    def get_required_fields(self) -> list[str]:
        """
        Return list of required field names.

        Override this to specify which fields are required for your tool.
        The model field is automatically added if in auto mode.

        Returns:
            List of required field names
        """
        return []

    def get_input_schema(self) -> dict[str, Any]:
        """
        Generate the complete input schema using SchemaBuilder.

        This method automatically combines:
        - Tool-specific fields from get_tool_fields()
        - Common fields (temperature, thinking_mode, etc.)
        - Model field with proper auto-mode handling
        - Required fields from get_required_fields()

        Returns:
            Complete JSON schema for the tool
        """
        return SchemaBuilder.build_schema(
            tool_specific_fields=self.get_tool_fields(),
            required_fields=self.get_required_fields(),
            model_field_schema=self.get_model_field_schema(),
            auto_mode=self.is_effective_auto_mode(),
        )

    def get_request_model(self):
        """
        Return the request model class.

        Simple tools use the base ToolRequest by default.
        Override this if your tool needs a custom request model.
        """
        return ToolRequest

    # Convenience methods for common tool patterns

    def build_standard_prompt(
        self,
        system_prompt: str,
        user_content: str,
        request,
        file_context_title: str = "CONTEXT FILES"
    ) -> str:
        """
        Build a standard prompt with system prompt, user content, and optional files.

        This is a convenience method that handles the common pattern of:
        1. Adding file content if present
        2. Checking token limits
        3. Adding web search instructions
        4. Combining everything into a well-formatted prompt

        Args:
            system_prompt: The system prompt for the tool
            user_content: The main user request/content
            request: The validated request object
            file_context_title: Title for the file context section

        Returns:
            Complete formatted prompt ready for the AI model
        """
        # Add context files if provided
        if hasattr(request, 'files') and request.files:
            file_content, processed_files = self._prepare_file_content_for_prompt(
                request.files, request.continuation_id, "Context files"
            )
            self._actually_processed_files = processed_files
            if file_content:
                user_content = f"{user_content}\n\n=== {file_context_title} ===\n{file_content}\n=== END CONTEXT ===="

        # Check token limits
        self._validate_token_limit(user_content, "Content")

        # Add web search instruction if enabled
        websearch_instruction = ""
        if hasattr(request, 'use_websearch') and request.use_websearch:
            websearch_instruction = self.get_websearch_instruction(
                request.use_websearch,
                self.get_websearch_guidance()
            )

        # Combine system prompt with user content
        full_prompt = f"""{system_prompt}{websearch_instruction}

=== USER REQUEST ===
{user_content}
=== END REQUEST ===

Please provide a thoughtful, comprehensive response:"""

        return full_prompt

    def get_websearch_guidance(self) -> Optional[str]:
        """
        Return tool-specific web search guidance.

        Override this to provide tool-specific guidance for when web searches
        would be helpful. Return None to use the default guidance.

        Returns:
            Tool-specific web search guidance or None for default
        """
        return None

    def handle_prompt_file_with_fallback(self, request) -> str:
        """
        Handle prompt.txt files with fallback to request field.

        This is a convenience method for tools that accept prompts either
        as a field or as a prompt.txt file. It handles the extraction
        and validation automatically.

        Args:
            request: The validated request object

        Returns:
            The effective prompt content

        Raises:
            ValueError: If prompt is too large for MCP transport
        """
        # Check for prompt.txt in files
        if hasattr(request, 'files'):
            prompt_content, updated_files = self.handle_prompt_file(request.files)

            # Update request files list
            if updated_files is not None:
                request.files = updated_files
        else:
            prompt_content = None

        # Use prompt.txt content if available, otherwise use the prompt field
        user_content = prompt_content if prompt_content else getattr(request, 'prompt', '')

        # Check user input size at MCP transport boundary
        size_check = self.check_prompt_size(user_content)
        if size_check:
            from tools.models import ToolOutput
            raise ValueError(f"MCP_SIZE_CHECK:{ToolOutput(**size_check).model_dump_json()}")

        return user_content
