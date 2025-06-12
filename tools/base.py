"""
Base class for all Zen MCP tools

This module provides the abstract base class that all tools must inherit from.
It defines the contract that tools must implement and provides common functionality
for request validation, error handling, and response formatting.

Key responsibilities:
- Define the tool interface (abstract methods that must be implemented)
- Handle request validation and file path security
- Manage Gemini model creation with appropriate configurations
- Standardize response formatting and error handling
- Support for clarification requests when more information is needed
"""

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Literal, Optional

from mcp.types import TextContent
from pydantic import BaseModel, Field

from config import DEFAULT_MODEL, MAX_CONTEXT_TOKENS, MCP_PROMPT_SIZE_LIMIT
from providers import ModelProvider, ModelProviderRegistry
from utils import check_token_limit
from utils.conversation_memory import (
    MAX_CONVERSATION_TURNS,
    add_turn,
    create_thread,
    get_conversation_file_list,
    get_thread,
)
from utils.file_utils import read_file_content, read_files, translate_path_for_environment

from .models import ClarificationRequest, ContinuationOffer, FollowUpRequest, ToolOutput

logger = logging.getLogger(__name__)


class ToolRequest(BaseModel):
    """
    Base request model for all tools.

    This Pydantic model defines common parameters that can be used by any tool.
    Tools can extend this model to add their specific parameters while inheriting
    these common fields.
    """

    model: Optional[str] = Field(
        None,
        description="Model to use. See tool's input schema for available models and their capabilities.",
    )
    temperature: Optional[float] = Field(None, description="Temperature for response (tool-specific defaults)")
    # Thinking mode controls how much computational budget the model uses for reasoning
    # Higher values allow for more complex reasoning but increase latency and cost
    thinking_mode: Optional[Literal["minimal", "low", "medium", "high", "max"]] = Field(
        None,
        description="Thinking depth: minimal (128), low (2048), medium (8192), high (16384), max (32768)",
    )
    use_websearch: Optional[bool] = Field(
        False,
        description="Enable web search for documentation, best practices, and current information. Particularly useful for: brainstorming sessions, architectural design discussions, exploring industry best practices, working with specific frameworks/technologies, researching solutions to complex problems, or when current documentation and community insights would enhance the analysis.",
    )
    continuation_id: Optional[str] = Field(
        None,
        description="Thread continuation ID for multi-turn conversations. Can be used to continue conversations across different tools. Only provide this if continuing a previous conversation thread.",
    )


class BaseTool(ABC):
    """
    Abstract base class for all Gemini tools.

    This class defines the interface that all tools must implement and provides
    common functionality for request handling, model creation, and response formatting.

    To create a new tool:
    1. Create a new class that inherits from BaseTool
    2. Implement all abstract methods
    3. Define a request model that inherits from ToolRequest
    4. Register the tool in server.py's TOOLS dictionary
    """

    def __init__(self):
        # Cache tool metadata at initialization to avoid repeated calls
        self.name = self.get_name()
        self.description = self.get_description()
        self.default_temperature = self.get_default_temperature()

    @abstractmethod
    def get_name(self) -> str:
        """
        Return the unique name identifier for this tool.

        This name is used by MCP clients to invoke the tool and must be
        unique across all registered tools.

        Returns:
            str: The tool's unique name (e.g., "review_code", "analyze")
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Return a detailed description of what this tool does.

        This description is shown to MCP clients (like Claude) to help them
        understand when and how to use the tool. It should be comprehensive
        and include trigger phrases.

        Returns:
            str: Detailed tool description with usage examples
        """
        pass

    @abstractmethod
    def get_input_schema(self) -> dict[str, Any]:
        """
        Return the JSON Schema that defines this tool's parameters.

        This schema is used by MCP clients to validate inputs before
        sending requests. It should match the tool's request model.

        Returns:
            Dict[str, Any]: JSON Schema object defining required and optional parameters
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Return the system prompt that configures the AI model's behavior.

        This prompt sets the context and instructions for how the model
        should approach the task. It's prepended to the user's request.

        Returns:
            str: System prompt with role definition and instructions
        """
        pass

    def get_model_field_schema(self) -> dict[str, Any]:
        """
        Generate the model field schema based on auto mode configuration.

        When auto mode is enabled, the model parameter becomes required
        and includes detailed descriptions of each model's capabilities.

        Returns:
            Dict containing the model field JSON schema
        """
        from config import DEFAULT_MODEL, IS_AUTO_MODE, MODEL_CAPABILITIES_DESC

        if IS_AUTO_MODE:
            # In auto mode, model is required and we provide detailed descriptions
            model_desc_parts = ["Choose the best model for this task based on these capabilities:"]
            for model, desc in MODEL_CAPABILITIES_DESC.items():
                model_desc_parts.append(f"- '{model}': {desc}")

            return {
                "type": "string",
                "description": "\n".join(model_desc_parts),
                "enum": list(MODEL_CAPABILITIES_DESC.keys()),
            }
        else:
            # Normal mode - model is optional with default
            available_models = list(MODEL_CAPABILITIES_DESC.keys())
            models_str = ", ".join(f"'{m}'" for m in available_models)
            return {
                "type": "string",
                "description": f"Model to use. Available: {models_str}. Defaults to '{DEFAULT_MODEL}' if not specified.",
            }

    def get_default_temperature(self) -> float:
        """
        Return the default temperature setting for this tool.

        Override this method to set tool-specific temperature defaults.
        Lower values (0.0-0.3) for analytical tasks, higher (0.7-1.0) for creative tasks.

        Returns:
            float: Default temperature between 0.0 and 1.0
        """
        return 0.5

    def get_default_thinking_mode(self) -> str:
        """
        Return the default thinking mode for this tool.

        Thinking mode controls computational budget for reasoning.
        Override for tools that need more or less reasoning depth.

        Returns:
            str: One of "minimal", "low", "medium", "high", "max"
        """
        return "medium"  # Default to medium thinking for better reasoning

    def get_conversation_embedded_files(self, continuation_id: Optional[str]) -> list[str]:
        """
        Get list of files already embedded in conversation history.

        This method returns the list of files that have already been embedded
        in the conversation history for a given continuation thread. Tools can
        use this to avoid re-embedding files that are already available in the
        conversation context.

        Args:
            continuation_id: Thread continuation ID, or None for new conversations

        Returns:
            list[str]: List of file paths already embedded in conversation history
        """
        if not continuation_id:
            # New conversation, no files embedded yet
            return []

        thread_context = get_thread(continuation_id)
        if not thread_context:
            # Thread not found, no files embedded
            return []

        embedded_files = get_conversation_file_list(thread_context)
        logger.debug(f"[FILES] {self.name}: Found {len(embedded_files)} embedded files")
        return embedded_files

    def filter_new_files(self, requested_files: list[str], continuation_id: Optional[str]) -> list[str]:
        """
        Filter out files that are already embedded in conversation history.

        This method prevents duplicate file embeddings by filtering out files that have
        already been embedded in the conversation history. This optimizes token usage
        while ensuring tools still have logical access to all requested files through
        conversation history references.

        Args:
            requested_files: List of files requested for current tool execution
            continuation_id: Thread continuation ID, or None for new conversations

        Returns:
            list[str]: List of files that need to be embedded (not already in history)
        """
        logger.debug(f"[FILES] {self.name}: Filtering {len(requested_files)} requested files")

        if not continuation_id:
            # New conversation, all files are new
            logger.debug(f"[FILES] {self.name}: New conversation, all {len(requested_files)} files are new")
            return requested_files

        try:
            embedded_files = set(self.get_conversation_embedded_files(continuation_id))
            logger.debug(f"[FILES] {self.name}: Found {len(embedded_files)} embedded files in conversation")

            # Safety check: If no files are marked as embedded but we have a continuation_id,
            # this might indicate an issue with conversation history. Be conservative.
            if not embedded_files:
                logger.debug(f"{self.name} tool: No files found in conversation history for thread {continuation_id}")
                logger.debug(
                    f"[FILES] {self.name}: No embedded files found, returning all {len(requested_files)} requested files"
                )
                return requested_files

            # Return only files that haven't been embedded yet
            new_files = [f for f in requested_files if f not in embedded_files]
            logger.debug(
                f"[FILES] {self.name}: After filtering: {len(new_files)} new files, {len(requested_files) - len(new_files)} already embedded"
            )
            logger.debug(f"[FILES] {self.name}: New files to embed: {new_files}")

            # Log filtering results for debugging
            if len(new_files) < len(requested_files):
                skipped = [f for f in requested_files if f in embedded_files]
                logger.debug(
                    f"{self.name} tool: Filtering {len(skipped)} files already in conversation history: {', '.join(skipped)}"
                )
                logger.debug(f"[FILES] {self.name}: Skipped (already embedded): {skipped}")

            return new_files

        except Exception as e:
            # If there's any issue with conversation history lookup, be conservative
            # and include all files rather than risk losing access to needed files
            logger.warning(f"{self.name} tool: Error checking conversation history for {continuation_id}: {e}")
            logger.warning(f"{self.name} tool: Including all requested files as fallback")
            logger.debug(
                f"[FILES] {self.name}: Exception in filter_new_files, returning all {len(requested_files)} files as fallback"
            )
            return requested_files

    def _prepare_file_content_for_prompt(
        self,
        request_files: list[str],
        continuation_id: Optional[str],
        context_description: str = "New files",
        max_tokens: Optional[int] = None,
        reserve_tokens: int = 1_000,
        remaining_budget: Optional[int] = None,
        arguments: Optional[dict] = None,
    ) -> str:
        """
        Centralized file processing for tool prompts.

        This method handles the common pattern across all tools:
        1. Filter out files already embedded in conversation history
        2. Read content of only new files
        3. Generate informative note about skipped files

        Args:
            request_files: List of files requested for current tool execution
            continuation_id: Thread continuation ID, or None for new conversations
            context_description: Description for token limit validation (e.g. "Code", "New files")
            max_tokens: Maximum tokens to use (defaults to remaining budget or MAX_CONTENT_TOKENS)
            reserve_tokens: Tokens to reserve for additional prompt content (default 1K)
            remaining_budget: Remaining token budget after conversation history (from server.py)
            arguments: Original tool arguments (used to extract _remaining_tokens if available)

        Returns:
            str: Formatted file content string ready for prompt inclusion
        """
        if not request_files:
            return ""

        # Note: Even if conversation history is already embedded, we still need to process
        # any NEW files that aren't in the conversation history yet. The filter_new_files
        # method will correctly identify which files need to be embedded.

        # Extract remaining budget from arguments if available
        if remaining_budget is None:
            # Use provided arguments or fall back to stored arguments from execute()
            args_to_use = arguments or getattr(self, "_current_arguments", {})
            remaining_budget = args_to_use.get("_remaining_tokens")

        # Use remaining budget if provided, otherwise fall back to max_tokens or model-specific default
        if remaining_budget is not None:
            effective_max_tokens = remaining_budget - reserve_tokens
        elif max_tokens is not None:
            effective_max_tokens = max_tokens - reserve_tokens
        else:
            # Get model-specific limits
            # First check if model_context was passed from server.py
            model_context = None
            if arguments:
                model_context = arguments.get("_model_context") or getattr(self, "_current_arguments", {}).get(
                    "_model_context"
                )

            if model_context:
                # Use the passed model context
                try:
                    token_allocation = model_context.calculate_token_allocation()
                    effective_max_tokens = token_allocation.file_tokens - reserve_tokens
                    logger.debug(
                        f"[FILES] {self.name}: Using passed model context for {model_context.model_name}: "
                        f"{token_allocation.file_tokens:,} file tokens from {token_allocation.total_tokens:,} total"
                    )
                except Exception as e:
                    logger.warning(f"[FILES] {self.name}: Error using passed model context: {e}")
                    # Fall through to manual calculation
                    model_context = None

            if not model_context:
                # Manual calculation as fallback
                model_name = getattr(self, "_current_model_name", None) or DEFAULT_MODEL
                try:
                    provider = self.get_model_provider(model_name)
                    capabilities = provider.get_capabilities(model_name)

                    # Calculate content allocation based on model capacity
                    if capabilities.max_tokens < 300_000:
                        # Smaller context models: 60% content, 40% response
                        model_content_tokens = int(capabilities.max_tokens * 0.6)
                    else:
                        # Larger context models: 80% content, 20% response
                        model_content_tokens = int(capabilities.max_tokens * 0.8)

                    effective_max_tokens = model_content_tokens - reserve_tokens
                    logger.debug(
                        f"[FILES] {self.name}: Using model-specific limit for {model_name}: "
                        f"{model_content_tokens:,} content tokens from {capabilities.max_tokens:,} total"
                    )
                except (ValueError, AttributeError) as e:
                    # Handle specific errors: provider not found, model not supported, missing attributes
                    logger.warning(
                        f"[FILES] {self.name}: Could not get model capabilities for {model_name}: {type(e).__name__}: {e}"
                    )
                    # Fall back to conservative default for safety
                    from config import MAX_CONTENT_TOKENS

                    effective_max_tokens = min(MAX_CONTENT_TOKENS, 100_000) - reserve_tokens
                except Exception as e:
                    # Catch any other unexpected errors
                    logger.error(
                        f"[FILES] {self.name}: Unexpected error getting model capabilities: {type(e).__name__}: {e}"
                    )
                    from config import MAX_CONTENT_TOKENS

                    effective_max_tokens = min(MAX_CONTENT_TOKENS, 100_000) - reserve_tokens

        # Ensure we have a reasonable minimum budget
        effective_max_tokens = max(1000, effective_max_tokens)

        files_to_embed = self.filter_new_files(request_files, continuation_id)
        logger.debug(f"[FILES] {self.name}: Will embed {len(files_to_embed)} files after filtering")

        # Log the specific files for debugging/testing
        if files_to_embed:
            logger.info(
                f"[FILE_PROCESSING] {self.name} tool will embed new files: {', '.join([os.path.basename(f) for f in files_to_embed])}"
            )
        else:
            logger.info(
                f"[FILE_PROCESSING] {self.name} tool: No new files to embed (all files already in conversation history)"
            )

        content_parts = []

        # Read content of new files only
        if files_to_embed:
            logger.debug(f"{self.name} tool embedding {len(files_to_embed)} new files: {', '.join(files_to_embed)}")
            logger.debug(
                f"[FILES] {self.name}: Starting file embedding with token budget {effective_max_tokens + reserve_tokens:,}"
            )
            try:
                file_content = read_files(
                    files_to_embed, max_tokens=effective_max_tokens + reserve_tokens, reserve_tokens=reserve_tokens
                )
                self._validate_token_limit(file_content, context_description)
                content_parts.append(file_content)

                # Estimate tokens for debug logging
                from utils.token_utils import estimate_tokens

                content_tokens = estimate_tokens(file_content)
                logger.debug(
                    f"{self.name} tool successfully embedded {len(files_to_embed)} files ({content_tokens:,} tokens)"
                )
                logger.debug(f"[FILES] {self.name}: Successfully embedded files - {content_tokens:,} tokens used")
            except Exception as e:
                logger.error(f"{self.name} tool failed to embed files {files_to_embed}: {type(e).__name__}: {e}")
                logger.debug(f"[FILES] {self.name}: File embedding failed - {type(e).__name__}: {e}")
                raise
        else:
            logger.debug(f"[FILES] {self.name}: No files to embed after filtering")

        # Generate note about files already in conversation history
        if continuation_id and len(files_to_embed) < len(request_files):
            embedded_files = self.get_conversation_embedded_files(continuation_id)
            skipped_files = [f for f in request_files if f in embedded_files]
            if skipped_files:
                logger.debug(
                    f"{self.name} tool skipping {len(skipped_files)} files already in conversation history: {', '.join(skipped_files)}"
                )
                logger.debug(f"[FILES] {self.name}: Adding note about {len(skipped_files)} skipped files")
                if content_parts:
                    content_parts.append("\n\n")
                note_lines = [
                    "--- NOTE: Additional files referenced in conversation history ---",
                    "The following files are already available in our conversation context:",
                    "\n".join(f"  - {f}" for f in skipped_files),
                    "--- END NOTE ---",
                ]
                content_parts.append("\n".join(note_lines))
            else:
                logger.debug(f"[FILES] {self.name}: No skipped files to note")

        result = "".join(content_parts) if content_parts else ""
        logger.debug(f"[FILES] {self.name}: _prepare_file_content_for_prompt returning {len(result)} chars")
        return result

    def get_websearch_instruction(self, use_websearch: bool, tool_specific: Optional[str] = None) -> str:
        """
        Generate web search instruction based on the use_websearch parameter.

        Args:
            use_websearch: Whether web search is enabled
            tool_specific: Optional tool-specific search guidance

        Returns:
            str: Web search instruction to append to prompt, or empty string
        """
        if not use_websearch:
            return ""

        base_instruction = """

WEB SEARCH REASONING: As you analyze this request, consider whether web searches would enhance your response.
If you identify areas where current documentation, API references, or community solutions would be valuable,
please note in your response what specific searches Claude should perform and why they would be helpful."""

        if tool_specific:
            return f"""{base_instruction}

{tool_specific}

In your response, if web searches would be beneficial, include a section like:
**Recommended Web Searches for Claude:**
- [Specific topic/framework/library] - to verify/understand/confirm [specific aspect]
- [Another search topic] - to explore [specific concern or feature]"""

        # Default instruction for all tools
        return f"""{base_instruction}

Consider searches for:
- Current documentation and best practices
- Similar issues and community solutions
- API references and usage examples
- Recent developments and updates

If any of these would strengthen your analysis, specify what Claude should search for and why."""

    @abstractmethod
    def get_request_model(self):
        """
        Return the Pydantic model class used for validating requests.

        This model should inherit from ToolRequest and define all
        parameters specific to this tool.

        Returns:
            Type[ToolRequest]: The request model class
        """
        pass

    def validate_file_paths(self, request) -> Optional[str]:
        """
        Validate that all file paths in the request are absolute.

        This is a critical security function that prevents path traversal attacks
        and ensures all file access is properly controlled. All file paths must
        be absolute to avoid ambiguity and security issues.

        Args:
            request: The validated request object

        Returns:
            Optional[str]: Error message if validation fails, None if all paths are valid
        """
        # Check if request has 'files' attribute (used by most tools)
        if hasattr(request, "files") and request.files:
            for file_path in request.files:
                if not os.path.isabs(file_path):
                    return (
                        f"Error: All file paths must be absolute. "
                        f"Received relative path: {file_path}\n"
                        f"Please provide the full absolute path starting with '/'"
                    )

        # Check if request has 'path' attribute (used by review_changes tool)
        if hasattr(request, "path") and request.path:
            if not os.path.isabs(request.path):
                return (
                    f"Error: Path must be absolute. "
                    f"Received relative path: {request.path}\n"
                    f"Please provide the full absolute path starting with '/'"
                )

        return None

    def check_prompt_size(self, text: str) -> Optional[dict[str, Any]]:
        """
        Check if a text field is too large for MCP's token limits.

        The MCP protocol has a combined request+response limit of ~25K tokens.
        To ensure adequate space for responses, we limit prompt input to a
        configurable character limit (default 50K chars ~= 10-12K tokens).
        Larger prompts are handled by having Claude save them to a file,
        bypassing MCP's token constraints while preserving response capacity.

        Args:
            text: The text to check

        Returns:
            Optional[Dict[str, Any]]: Response asking for file handling if too large, None otherwise
        """
        if text and len(text) > MCP_PROMPT_SIZE_LIMIT:
            return {
                "status": "requires_file_prompt",
                "content": (
                    f"The prompt is too large for MCP's token limits (>{MCP_PROMPT_SIZE_LIMIT:,} characters). "
                    "Please save the prompt text to a temporary file named 'prompt.txt' and "
                    "resend the request with an empty prompt string and the absolute file path included "
                    "in the files parameter, along with any other files you wish to share as context."
                ),
                "content_type": "text",
                "metadata": {
                    "prompt_size": len(text),
                    "limit": MCP_PROMPT_SIZE_LIMIT,
                    "instructions": "Save prompt to 'prompt.txt' and include absolute path in files parameter",
                },
            }
        return None

    def handle_prompt_file(self, files: Optional[list[str]]) -> tuple[Optional[str], Optional[list[str]]]:
        """
        Check for and handle prompt.txt in the files list.

        If prompt.txt is found, reads its content and removes it from the files list.
        This file is treated specially as the main prompt, not as an embedded file.

        This mechanism allows us to work around MCP's ~25K token limit by having
        Claude save large prompts to a file, effectively using the file transfer
        mechanism to bypass token constraints while preserving response capacity.

        Args:
            files: List of file paths (will be translated for current environment)

        Returns:
            tuple: (prompt_content, updated_files_list)
        """
        if not files:
            return None, files

        prompt_content = None
        updated_files = []

        for file_path in files:
            # Translate path for current environment (Docker/direct)
            translated_path = translate_path_for_environment(file_path)

            # Check if the filename is exactly "prompt.txt"
            # This ensures we don't match files like "myprompt.txt" or "prompt.txt.bak"
            if os.path.basename(translated_path) == "prompt.txt":
                try:
                    # Read prompt.txt content and extract just the text
                    content, _ = read_file_content(translated_path)
                    # Extract the content between the file markers
                    if "--- BEGIN FILE:" in content and "--- END FILE:" in content:
                        lines = content.split("\n")
                        in_content = False
                        content_lines = []
                        for line in lines:
                            if line.startswith("--- BEGIN FILE:"):
                                in_content = True
                                continue
                            elif line.startswith("--- END FILE:"):
                                break
                            elif in_content:
                                content_lines.append(line)
                        prompt_content = "\n".join(content_lines)
                    else:
                        # Fallback: if it's already raw content (from tests or direct input)
                        # and doesn't have error markers, use it directly
                        if not content.startswith("\n--- ERROR"):
                            prompt_content = content
                        else:
                            prompt_content = None
                except Exception:
                    # If we can't read the file, we'll just skip it
                    # The error will be handled elsewhere
                    pass
            else:
                # Keep the original path in the files list (will be translated later by read_files)
                updated_files.append(file_path)

        return prompt_content, updated_files if updated_files else None

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute the tool with the provided arguments.

        This is the main entry point for tool execution. It handles:
        1. Request validation using the tool's Pydantic model
        2. File path security validation
        3. Prompt preparation
        4. Model creation and configuration
        5. Response generation and formatting
        6. Error handling and recovery

        Args:
            arguments: Dictionary of arguments from the MCP client

        Returns:
            List[TextContent]: Formatted response as MCP TextContent objects
        """
        try:
            # Store arguments for access by helper methods (like _prepare_file_content_for_prompt)
            self._current_arguments = arguments

            # Set up logger for this tool execution
            logger = logging.getLogger(f"tools.{self.name}")
            logger.info(f"Starting {self.name} tool execution with arguments: {list(arguments.keys())}")

            # Validate request using the tool's Pydantic model
            # This ensures all required fields are present and properly typed
            request_model = self.get_request_model()
            request = request_model(**arguments)
            logger.debug(f"Request validation successful for {self.name}")

            # Validate file paths for security
            # This prevents path traversal attacks and ensures proper access control
            path_error = self.validate_file_paths(request)
            if path_error:
                error_output = ToolOutput(
                    status="error",
                    content=path_error,
                    content_type="text",
                )
                return [TextContent(type="text", text=error_output.model_dump_json())]

            # Check if we have continuation_id - if so, conversation history is already embedded
            continuation_id = getattr(request, "continuation_id", None)

            if continuation_id:
                # When continuation_id is present, server.py has already injected the
                # conversation history into the appropriate field. We need to check if
                # the prompt already contains conversation history marker.
                logger.debug(f"Continuing {self.name} conversation with thread {continuation_id}")

                # Store the original arguments to detect enhanced prompts
                self._has_embedded_history = False

                # Check if conversation history is already embedded in the prompt field
                field_value = getattr(request, "prompt", "")
                field_name = "prompt"

                if "=== CONVERSATION HISTORY ===" in field_value:
                    # Conversation history is already embedded, use it directly
                    prompt = field_value
                    self._has_embedded_history = True
                    logger.debug(f"{self.name}: Using pre-embedded conversation history from {field_name}")
                else:
                    # No embedded history, prepare prompt normally
                    prompt = await self.prepare_prompt(request)
                    logger.debug(f"{self.name}: No embedded history found, prepared prompt normally")
            else:
                # New conversation, prepare prompt normally
                prompt = await self.prepare_prompt(request)

                # Add follow-up instructions for new conversations
                from server import get_follow_up_instructions

                follow_up_instructions = get_follow_up_instructions(0)  # New conversation, turn 0
                prompt = f"{prompt}\n\n{follow_up_instructions}"
                logger.debug(f"Added follow-up instructions for new {self.name} conversation")

            # Extract model configuration from request or use defaults
            model_name = getattr(request, "model", None)
            if not model_name:
                model_name = DEFAULT_MODEL

            # In auto mode, model parameter is required
            from config import IS_AUTO_MODE

            if IS_AUTO_MODE and model_name.lower() == "auto":
                error_output = ToolOutput(
                    status="error",
                    content="Model parameter is required. Please specify which model to use for this task.",
                    content_type="text",
                )
                return [TextContent(type="text", text=error_output.model_dump_json())]

            # Store model name for use by helper methods like _prepare_file_content_for_prompt
            self._current_model_name = model_name

            temperature = getattr(request, "temperature", None)
            if temperature is None:
                temperature = self.get_default_temperature()
            thinking_mode = getattr(request, "thinking_mode", None)
            if thinking_mode is None:
                thinking_mode = self.get_default_thinking_mode()

            # Get the appropriate model provider
            provider = self.get_model_provider(model_name)

            # Validate and correct temperature for this model
            temperature, temp_warnings = self._validate_and_correct_temperature(model_name, temperature)

            # Log any temperature corrections
            for warning in temp_warnings:
                logger.warning(warning)

            # Get system prompt for this tool
            system_prompt = self.get_system_prompt()

            # Generate AI response using the provider
            logger.info(f"Sending request to {provider.get_provider_type().value} API for {self.name}")
            logger.info(f"Using model: {model_name} via {provider.get_provider_type().value} provider")
            logger.debug(f"Prompt length: {len(prompt)} characters")

            # Generate content with provider abstraction
            model_response = provider.generate_content(
                prompt=prompt,
                model_name=model_name,
                system_prompt=system_prompt,
                temperature=temperature,
                thinking_mode=thinking_mode if provider.supports_thinking_mode(model_name) else None,
            )

            logger.info(f"Received response from {provider.get_provider_type().value} API for {self.name}")

            # Process the model's response
            if model_response.content:
                raw_text = model_response.content

                # Parse response to check for clarification requests or format output
                # Pass model info for conversation tracking
                model_info = {"provider": provider, "model_name": model_name, "model_response": model_response}
                tool_output = self._parse_response(raw_text, request, model_info)
                logger.info(f"Successfully completed {self.name} tool execution")

            else:
                # Handle cases where the model couldn't generate a response
                # This might happen due to safety filters or other constraints
                finish_reason = model_response.metadata.get("finish_reason", "Unknown")
                logger.warning(f"Response blocked or incomplete for {self.name}. Finish reason: {finish_reason}")
                tool_output = ToolOutput(
                    status="error",
                    content=f"Response blocked or incomplete. Finish reason: {finish_reason}",
                    content_type="text",
                )

            # Return standardized JSON response for consistent client handling
            return [TextContent(type="text", text=tool_output.model_dump_json())]

        except Exception as e:
            # Catch all exceptions to prevent server crashes
            # Return error information in standardized format
            logger = logging.getLogger(f"tools.{self.name}")
            error_msg = str(e)

            # Check if this is a 500 INTERNAL error that asks for retry
            if "500 INTERNAL" in error_msg and "Please retry" in error_msg:
                logger.warning(f"500 INTERNAL error in {self.name} - attempting retry")
                try:
                    # Single retry attempt using provider
                    retry_response = provider.generate_content(
                        prompt=prompt,
                        model_name=model_name,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        thinking_mode=thinking_mode if provider.supports_thinking_mode(model_name) else None,
                    )

                    if retry_response.content:
                        # If successful, process normally
                        retry_model_info = {
                            "provider": provider,
                            "model_name": model_name,
                            "model_response": retry_response,
                        }
                        tool_output = self._parse_response(retry_response.content, request, retry_model_info)
                        return [TextContent(type="text", text=tool_output.model_dump_json())]

                except Exception as retry_e:
                    logger.error(f"Retry failed for {self.name} tool: {str(retry_e)}")
                    error_msg = f"Tool failed after retry: {str(retry_e)}"

            logger.error(f"Error in {self.name} tool execution: {error_msg}", exc_info=True)

            error_output = ToolOutput(
                status="error",
                content=f"Error in {self.name}: {error_msg}",
                content_type="text",
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]

    def _parse_response(self, raw_text: str, request, model_info: Optional[dict] = None) -> ToolOutput:
        """
        Parse the raw response and determine if it's a clarification request or follow-up.

        Some tools may return JSON indicating they need more information or want to
        continue the conversation. This method detects such responses and formats them.

        Args:
            raw_text: The raw text response from the model
            request: The original request for context

        Returns:
            ToolOutput: Standardized output object
        """
        # Check for follow-up questions in JSON blocks at the end of the response
        follow_up_question = self._extract_follow_up_question(raw_text)
        logger = logging.getLogger(f"tools.{self.name}")

        if follow_up_question:
            logger.debug(
                f"Found follow-up question in {self.name} response: {follow_up_question.get('follow_up_question', 'N/A')}"
            )
        else:
            logger.debug(f"No follow-up question found in {self.name} response")

        try:
            # Try to parse as JSON to check for clarification requests
            potential_json = json.loads(raw_text.strip())

            if isinstance(potential_json, dict) and potential_json.get("status") == "requires_clarification":
                # Validate the clarification request structure
                clarification = ClarificationRequest(**potential_json)
                return ToolOutput(
                    status="requires_clarification",
                    content=clarification.model_dump_json(),
                    content_type="json",
                    metadata={
                        "original_request": (request.model_dump() if hasattr(request, "model_dump") else str(request))
                    },
                )

        except (json.JSONDecodeError, ValueError, TypeError):
            # Not a JSON clarification request, treat as normal response
            pass

        # Normal text response - format using tool-specific formatting
        formatted_content = self.format_response(raw_text, request, model_info)

        # If we found a follow-up question, prepare the threading response
        if follow_up_question:
            return self._create_follow_up_response(formatted_content, follow_up_question, request, model_info)

        # Check if we should offer Claude a continuation opportunity
        continuation_offer = self._check_continuation_opportunity(request)

        if continuation_offer:
            logger.debug(
                f"Creating continuation offer for {self.name} with {continuation_offer['remaining_turns']} turns remaining"
            )
            return self._create_continuation_offer_response(formatted_content, continuation_offer, request, model_info)
        else:
            logger.debug(f"No continuation offer created for {self.name}")

        # If this is a threaded conversation (has continuation_id), save the response
        continuation_id = getattr(request, "continuation_id", None)
        if continuation_id:
            request_files = getattr(request, "files", []) or []
            # Extract model metadata for conversation tracking
            model_provider = None
            model_name = None
            model_metadata = None

            if model_info:
                provider = model_info.get("provider")
                if provider:
                    model_provider = provider.get_provider_type().value
                model_name = model_info.get("model_name")
                model_response = model_info.get("model_response")
                if model_response:
                    model_metadata = {"usage": model_response.usage, "metadata": model_response.metadata}

            success = add_turn(
                continuation_id,
                "assistant",
                formatted_content,
                files=request_files,
                tool_name=self.name,
                model_provider=model_provider,
                model_name=model_name,
                model_metadata=model_metadata,
            )
            if not success:
                logging.warning(f"Failed to add turn to thread {continuation_id} for {self.name}")

        # Determine content type based on the formatted content
        content_type = (
            "markdown" if any(marker in formatted_content for marker in ["##", "**", "`", "- ", "1. "]) else "text"
        )

        return ToolOutput(
            status="success",
            content=formatted_content,
            content_type=content_type,
            metadata={"tool_name": self.name},
        )

    def _extract_follow_up_question(self, text: str) -> Optional[dict]:
        """
        Extract follow-up question from JSON blocks in the response.

        Looks for JSON blocks containing follow_up_question at the end of responses.

        Args:
            text: The response text to parse

        Returns:
            Dict with follow-up data if found, None otherwise
        """
        # Look for JSON blocks that contain follow_up_question
        # Pattern handles optional leading whitespace and indentation
        json_pattern = r'```json\s*\n\s*(\{.*?"follow_up_question".*?\})\s*\n\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)

        if not matches:
            return None

        # Take the last match (most recent follow-up)
        try:
            # Clean up the JSON string - remove excess whitespace and normalize
            json_str = re.sub(r"\n\s+", "\n", matches[-1]).strip()
            follow_up_data = json.loads(json_str)
            if "follow_up_question" in follow_up_data:
                return follow_up_data
        except (json.JSONDecodeError, ValueError):
            pass

        return None

    def _create_follow_up_response(
        self, content: str, follow_up_data: dict, request, model_info: Optional[dict] = None
    ) -> ToolOutput:
        """
        Create a response with follow-up question for conversation threading.

        Args:
            content: The main response content
            follow_up_data: Dict containing follow_up_question and optional suggested_params
            request: Original request for context

        Returns:
            ToolOutput configured for conversation continuation
        """
        # Always create a new thread (with parent linkage if continuation)
        continuation_id = getattr(request, "continuation_id", None)
        request_files = getattr(request, "files", []) or []

        try:
            # Create new thread with parent linkage if continuing
            thread_id = create_thread(
                tool_name=self.name,
                initial_request=request.model_dump() if hasattr(request, "model_dump") else {},
                parent_thread_id=continuation_id,  # Link to parent thread if continuing
            )

            # Add the assistant's response with follow-up
            # Extract model metadata
            model_provider = None
            model_name = None
            model_metadata = None

            if model_info:
                provider = model_info.get("provider")
                if provider:
                    model_provider = provider.get_provider_type().value
                model_name = model_info.get("model_name")
                model_response = model_info.get("model_response")
                if model_response:
                    model_metadata = {"usage": model_response.usage, "metadata": model_response.metadata}

            add_turn(
                thread_id,  # Add to the new thread
                "assistant",
                content,
                follow_up_question=follow_up_data.get("follow_up_question"),
                files=request_files,
                tool_name=self.name,
                model_provider=model_provider,
                model_name=model_name,
                model_metadata=model_metadata,
            )
        except Exception as e:
            # Threading failed, return normal response
            logger = logging.getLogger(f"tools.{self.name}")
            logger.warning(f"Follow-up threading failed in {self.name}: {str(e)}")
            return ToolOutput(
                status="success",
                content=content,
                content_type="markdown",
                metadata={"tool_name": self.name, "follow_up_error": str(e)},
            )

        # Create follow-up request
        follow_up_request = FollowUpRequest(
            continuation_id=thread_id,
            question_to_user=follow_up_data["follow_up_question"],
            suggested_tool_params=follow_up_data.get("suggested_params"),
            ui_hint=follow_up_data.get("ui_hint"),
        )

        # Strip the JSON block from the content since it's now in the follow_up_request
        clean_content = self._remove_follow_up_json(content)

        return ToolOutput(
            status="requires_continuation",
            content=clean_content,
            content_type="markdown",
            follow_up_request=follow_up_request,
            metadata={"tool_name": self.name, "thread_id": thread_id},
        )

    def _remove_follow_up_json(self, text: str) -> str:
        """Remove follow-up JSON blocks from the response text"""
        # Remove JSON blocks containing follow_up_question
        pattern = r'```json\s*\n\s*\{.*?"follow_up_question".*?\}\s*\n\s*```'
        return re.sub(pattern, "", text, flags=re.DOTALL).strip()

    def _check_continuation_opportunity(self, request) -> Optional[dict]:
        """
        Check if we should offer Claude a continuation opportunity.

        This is called when Gemini doesn't ask a follow-up question, but we want
        to give Claude the chance to continue the conversation if needed.

        Args:
            request: The original request

        Returns:
            Dict with continuation data if opportunity should be offered, None otherwise
        """
        # Skip continuation offers in test mode
        import os

        if os.getenv("PYTEST_CURRENT_TEST"):
            return None

        continuation_id = getattr(request, "continuation_id", None)

        try:
            if continuation_id:
                # Check remaining turns in thread chain
                from utils.conversation_memory import get_thread_chain

                chain = get_thread_chain(continuation_id)
                if chain:
                    # Count total turns across all threads in chain
                    total_turns = sum(len(thread.turns) for thread in chain)
                    remaining_turns = MAX_CONVERSATION_TURNS - total_turns - 1  # -1 for this response
                else:
                    # Thread not found, don't offer continuation
                    return None
            else:
                # New conversation, we have MAX_CONVERSATION_TURNS - 1 remaining
                # (since this response will be turn 1)
                remaining_turns = MAX_CONVERSATION_TURNS - 1

            if remaining_turns <= 0:
                return None

            # Offer continuation opportunity
            return {"remaining_turns": remaining_turns, "tool_name": self.name}
        except Exception:
            # If anything fails, don't offer continuation
            return None

    def _create_continuation_offer_response(
        self, content: str, continuation_data: dict, request, model_info: Optional[dict] = None
    ) -> ToolOutput:
        """
        Create a response offering Claude the opportunity to continue conversation.

        Args:
            content: The main response content
            continuation_data: Dict containing remaining_turns and tool_name
            request: Original request for context

        Returns:
            ToolOutput configured with continuation offer
        """
        try:
            # Create new thread for potential continuation (with parent link if continuing)
            continuation_id = getattr(request, "continuation_id", None)
            thread_id = create_thread(
                tool_name=self.name,
                initial_request=request.model_dump() if hasattr(request, "model_dump") else {},
                parent_thread_id=continuation_id,  # Link to parent if this is a continuation
            )

            # Add this response as the first turn (assistant turn)
            request_files = getattr(request, "files", []) or []
            # Extract model metadata
            model_provider = None
            model_name = None
            model_metadata = None

            if model_info:
                provider = model_info.get("provider")
                if provider:
                    model_provider = provider.get_provider_type().value
                model_name = model_info.get("model_name")
                model_response = model_info.get("model_response")
                if model_response:
                    model_metadata = {"usage": model_response.usage, "metadata": model_response.metadata}

            add_turn(
                thread_id,
                "assistant",
                content,
                files=request_files,
                tool_name=self.name,
                model_provider=model_provider,
                model_name=model_name,
                model_metadata=model_metadata,
            )

            # Create continuation offer
            remaining_turns = continuation_data["remaining_turns"]
            continuation_offer = ContinuationOffer(
                continuation_id=thread_id,
                message_to_user=(
                    f"If you'd like to continue this analysis or need further details, "
                    f"you can use the continuation_id '{thread_id}' in your next {self.name} tool call. "
                    f"You have {remaining_turns} more exchange(s) available in this conversation thread."
                ),
                suggested_tool_params={
                    "continuation_id": thread_id,
                    "prompt": "[Your follow-up question or request for additional analysis]",
                },
                remaining_turns=remaining_turns,
            )

            return ToolOutput(
                status="continuation_available",
                content=content,
                content_type="markdown",
                continuation_offer=continuation_offer,
                metadata={"tool_name": self.name, "thread_id": thread_id, "remaining_turns": remaining_turns},
            )

        except Exception as e:
            # If threading fails, return normal response but log the error
            logger = logging.getLogger(f"tools.{self.name}")
            logger.warning(f"Conversation threading failed in {self.name}: {str(e)}")
            return ToolOutput(
                status="success",
                content=content,
                content_type="markdown",
                metadata={"tool_name": self.name, "threading_error": str(e)},
            )

    @abstractmethod
    async def prepare_prompt(self, request) -> str:
        """
        Prepare the complete prompt for the Gemini model.

        This method should combine the system prompt with the user's request
        and any additional context (like file contents) needed for the task.

        Args:
            request: The validated request object

        Returns:
            str: Complete prompt ready for the model
        """
        pass

    def format_response(self, response: str, request, model_info: Optional[dict] = None) -> str:
        """
        Format the model's response for display.

        Override this method to add tool-specific formatting like headers,
        summaries, or structured output. Default implementation returns
        the response unchanged.

        Args:
            response: The raw response from the model
            request: The original request for context
            model_info: Optional dict with model metadata (provider, model_name, model_response)

        Returns:
            str: Formatted response
        """
        return response

    def _validate_token_limit(self, text: str, context_type: str = "Context") -> None:
        """
        Validate token limit and raise ValueError if exceeded.

        This centralizes the token limit check that was previously duplicated
        in all prepare_prompt methods across tools.

        Args:
            text: The text to check
            context_type: Description of what's being checked (for error message)

        Raises:
            ValueError: If text exceeds MAX_CONTEXT_TOKENS
        """
        within_limit, estimated_tokens = check_token_limit(text)
        if not within_limit:
            raise ValueError(
                f"{context_type} too large (~{estimated_tokens:,} tokens). Maximum is {MAX_CONTEXT_TOKENS:,} tokens."
            )

    def _validate_and_correct_temperature(self, model_name: str, temperature: float) -> tuple[float, list[str]]:
        """
        Validate and correct temperature for the specified model.

        Args:
            model_name: Name of the model to validate temperature for
            temperature: Temperature value to validate

        Returns:
            Tuple of (corrected_temperature, warning_messages)
        """
        try:
            provider = self.get_model_provider(model_name)
            capabilities = provider.get_capabilities(model_name)
            constraint = capabilities.temperature_constraint

            warnings = []

            if not constraint.validate(temperature):
                corrected = constraint.get_corrected_value(temperature)
                warning = (
                    f"Temperature {temperature} invalid for {model_name}. "
                    f"{constraint.get_description()}. Using {corrected} instead."
                )
                warnings.append(warning)
                return corrected, warnings

            return temperature, warnings

        except Exception as e:
            # If validation fails for any reason, use the original temperature
            # and log a warning (but don't fail the request)
            logger = logging.getLogger(f"tools.{self.name}")
            logger.warning(f"Temperature validation failed for {model_name}: {e}")
            return temperature, [f"Temperature validation failed: {e}"]

    def get_model_provider(self, model_name: str) -> ModelProvider:
        """
        Get a model provider for the specified model.

        Args:
            model_name: Name of the model to use (can be provider-specific or generic)

        Returns:
            ModelProvider instance configured for the model

        Raises:
            ValueError: If no provider supports the requested model
        """
        # Get provider from registry
        provider = ModelProviderRegistry.get_provider_for_model(model_name)

        if not provider:
            # Try to determine provider from model name patterns
            if "gemini" in model_name.lower() or model_name.lower() in ["flash", "pro"]:
                # Register Gemini provider if not already registered
                from providers.base import ProviderType
                from providers.gemini import GeminiModelProvider

                ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)
                provider = ModelProviderRegistry.get_provider(ProviderType.GOOGLE)
            elif "gpt" in model_name.lower() or "o3" in model_name.lower():
                # Register OpenAI provider if not already registered
                from providers.base import ProviderType
                from providers.openai import OpenAIModelProvider

                ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)
                provider = ModelProviderRegistry.get_provider(ProviderType.OPENAI)

        if not provider:
            raise ValueError(
                f"No provider found for model '{model_name}'. "
                f"Ensure the appropriate API key is set and the model name is correct."
            )

        return provider
