"""
Base class for all Gemini MCP tools

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

from google import genai
from google.genai import types
from mcp.types import TextContent
from pydantic import BaseModel, Field

from config import DEFAULT_MODEL, MAX_CONTEXT_TOKENS, MCP_PROMPT_SIZE_LIMIT
from utils import check_token_limit
from utils.conversation_memory import (
    MAX_CONVERSATION_TURNS,
    add_turn,
    create_thread,
    get_conversation_file_list,
    get_thread,
)
from utils.file_utils import read_file_content, read_files, translate_path_for_environment

from .models import ClarificationRequest, ContinuationOffer, FollowUpRequest, ToolOutput, TokenUsage

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
        description=f"Model to use: 'pro' (Gemini 2.5 Pro with extended thinking) or 'flash' (Gemini 2.0 Flash - faster). Defaults to '{DEFAULT_MODEL}' if not specified.",
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
                logger.debug(
                    f"📁 {self.name} tool: No files found in conversation history for thread {continuation_id}"
                )
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
                    f"📁 {self.name} tool: Filtering {len(skipped)} files already in conversation history: {', '.join(skipped)}"
                )
                logger.debug(f"[FILES] {self.name}: Skipped (already embedded): {skipped}")

            return new_files

        except Exception as e:
            # If there's any issue with conversation history lookup, be conservative
            # and include all files rather than risk losing access to needed files
            logger.warning(f"📁 {self.name} tool: Error checking conversation history for {continuation_id}: {e}")
            logger.warning(f"📁 {self.name} tool: Including all requested files as fallback")
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

        # Extract remaining budget from arguments if available
        if remaining_budget is None:
            # Use provided arguments or fall back to stored arguments from execute()
            args_to_use = arguments or getattr(self, "_current_arguments", {})
            remaining_budget = args_to_use.get("_remaining_tokens")

        # Use remaining budget if provided, otherwise fall back to max_tokens or default
        if remaining_budget is not None:
            effective_max_tokens = remaining_budget - reserve_tokens
        elif max_tokens is not None:
            effective_max_tokens = max_tokens - reserve_tokens
        else:
            from config import MAX_CONTENT_TOKENS

            effective_max_tokens = MAX_CONTENT_TOKENS - reserve_tokens

        # Ensure we have a reasonable minimum budget
        effective_max_tokens = max(1000, effective_max_tokens)

        files_to_embed = self.filter_new_files(request_files, continuation_id)
        logger.debug(f"[FILES] {self.name}: Will embed {len(files_to_embed)} files after filtering")

        content_parts = []

        # Read content of new files only
        if files_to_embed:
            logger.debug(f"📁 {self.name} tool embedding {len(files_to_embed)} new files: {', '.join(files_to_embed)}")
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
                    f"📁 {self.name} tool successfully embedded {len(files_to_embed)} files ({content_tokens:,} tokens)"
                )
                logger.debug(f"[FILES] {self.name}: Successfully embedded files - {content_tokens:,} tokens used")
            except Exception as e:
                logger.error(f"📁 {self.name} tool failed to embed files {files_to_embed}: {type(e).__name__}: {e}")
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
                    f"📁 {self.name} tool skipping {len(skipped_files)} files already in conversation history: {', '.join(skipped_files)}"
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

            # Prepare the full prompt by combining system prompt with user request
            # This is delegated to the tool implementation for customization
            prompt = await self.prepare_prompt(request)

            # Add follow-up instructions for new conversations (not threaded)
            continuation_id = getattr(request, "continuation_id", None)
            if not continuation_id:
                # Import here to avoid circular imports
                from server import get_follow_up_instructions

                follow_up_instructions = get_follow_up_instructions(0)  # New conversation, turn 0
                prompt = f"{prompt}\n\n{follow_up_instructions}"

                logger.debug(f"Added follow-up instructions for new {self.name} conversation")

                # Also log to file for debugging MCP issues
                try:
                    with open("/tmp/gemini_debug.log", "a") as f:
                        f.write(f"[{self.name}] Added follow-up instructions for new conversation\n")
                except Exception:
                    pass
            else:
                logger.debug(f"Continuing {self.name} conversation with thread {continuation_id}")
                # History reconstruction is handled by server.py:reconstruct_thread_context
                # No need to rebuild it here - prompt already contains conversation history

            # Extract model configuration from request or use defaults
            model_name = getattr(request, "model", None) or DEFAULT_MODEL
            temperature = getattr(request, "temperature", None)
            if temperature is None:
                temperature = self.get_default_temperature()
            thinking_mode = getattr(request, "thinking_mode", None)
            if thinking_mode is None:
                thinking_mode = self.get_default_thinking_mode()

            # Create model instance with appropriate configuration
            # This handles both regular models and thinking-enabled models
            model = self.create_model(model_name, temperature, thinking_mode)

            # Track prompt tokens
            from utils.token_utils import estimate_tokens
            prompt_tokens = estimate_tokens(prompt)
            
            # Generate AI response using the configured model
            logger.info(f"Sending request to Gemini API for {self.name}")
            logger.debug(f"Prompt length: {len(prompt)} characters (~{prompt_tokens:,} tokens)")
            response = model.generate_content(prompt)
            logger.info(f"Received response from Gemini API for {self.name}")

            # Extract token usage from response if available
            token_usage = None
            try:
                # Try to get usage metadata from response
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = response.usage_metadata
                    # Safely extract attributes with defaults
                    token_usage = TokenUsage(
                        prompt_tokens=getattr(usage, 'prompt_token_count', prompt_tokens),
                        completion_tokens=getattr(usage, 'candidates_token_count', 0),
                        total_tokens=getattr(usage, 'total_token_count', prompt_tokens),
                        cached_tokens=getattr(usage, 'cached_content_token_count', None)
                    )
                    logger.debug(f"[TOKENS] API reported usage for {self.name}: {token_usage.total_tokens:,} total tokens")
                else:
                    # Fallback: estimate tokens if API doesn't provide usage
                    completion_text = ""
                    if response.candidates and response.candidates[0].content.parts:
                        completion_text = response.candidates[0].content.parts[0].text
                    completion_tokens = estimate_tokens(completion_text) if completion_text else 0
                    
                    token_usage = TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens
                    )
                    logger.debug(f"[TOKENS] Estimated usage for {self.name}: {token_usage.total_tokens:,} total tokens")
            except Exception as e:
                # Final fallback: provide basic token usage even on error
                logger.warning(f"[TOKENS] Failed to extract token usage for {self.name}: {type(e).__name__}")
                token_usage = TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=0,
                    total_tokens=prompt_tokens
                )

            # Process the model's response
            if response.candidates and response.candidates[0].content.parts:
                raw_text = response.candidates[0].content.parts[0].text

                # Parse response to check for clarification requests or format output
                tool_output = self._parse_response(raw_text, request, token_usage)
                logger.info(f"Successfully completed {self.name} tool execution")

            else:
                # Handle cases where the model couldn't generate a response
                # This might happen due to safety filters or other constraints
                finish_reason = response.candidates[0].finish_reason if response.candidates else "Unknown"
                logger.warning(f"Response blocked or incomplete for {self.name}. Finish reason: {finish_reason}")
                tool_output = ToolOutput(
                    status="error",
                    content=f"Response blocked or incomplete. Finish reason: {finish_reason}",
                    content_type="text",
                    token_usage=token_usage
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
                    # Single retry attempt
                    model = self._get_model_wrapper(request)
                    raw_response = await model.generate_content(prompt)
                    response = raw_response.text

                    # If successful, process normally
                    return [TextContent(type="text", text=self._process_response(response, request).model_dump_json())]

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

    def _parse_response(self, raw_text: str, request, token_usage: Optional[TokenUsage] = None) -> ToolOutput:
        """
        Parse the raw response and determine if it's a clarification request or follow-up.

        Some tools may return JSON indicating they need more information or want to
        continue the conversation. This method detects such responses and formats them.

        Args:
            raw_text: The raw text response from the model
            request: The original request for context
            token_usage: Optional token usage information from the API

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
                    token_usage=token_usage
                )

        except (json.JSONDecodeError, ValueError, TypeError):
            # Not a JSON clarification request, treat as normal response
            pass

        # Normal text response - format using tool-specific formatting
        formatted_content = self.format_response(raw_text, request)

        # If we found a follow-up question, prepare the threading response
        if follow_up_question:
            return self._create_follow_up_response(formatted_content, follow_up_question, request, token_usage)

        # Check if we should offer Claude a continuation opportunity
        continuation_offer = self._check_continuation_opportunity(request)

        if continuation_offer:
            logger.debug(
                f"Creating continuation offer for {self.name} with {continuation_offer['remaining_turns']} turns remaining"
            )
            return self._create_continuation_offer_response(formatted_content, continuation_offer, request, token_usage)
        else:
            logger.debug(f"No continuation offer created for {self.name}")

        # If this is a threaded conversation (has continuation_id), save the response
        continuation_id = getattr(request, "continuation_id", None)
        if continuation_id:
            request_files = getattr(request, "files", []) or []
            success = add_turn(
                continuation_id,
                "assistant",
                formatted_content,
                files=request_files,
                tool_name=self.name,
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
            token_usage=token_usage
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

    def _create_follow_up_response(self, content: str, follow_up_data: dict, request, token_usage: Optional[TokenUsage] = None) -> ToolOutput:
        """
        Create a response with follow-up question for conversation threading.

        Args:
            content: The main response content
            follow_up_data: Dict containing follow_up_question and optional suggested_params
            request: Original request for context
            token_usage: Optional token usage information

        Returns:
            ToolOutput configured for conversation continuation
        """
        # Create or get thread ID
        continuation_id = getattr(request, "continuation_id", None)

        if continuation_id:
            # This is a continuation - add this turn to existing thread
            request_files = getattr(request, "files", []) or []
            success = add_turn(
                continuation_id,
                "assistant",
                content,
                follow_up_question=follow_up_data.get("follow_up_question"),
                files=request_files,
                tool_name=self.name,
            )
            if not success:
                # Thread not found or at limit, return normal response
                return ToolOutput(
                    status="success",
                    content=content,
                    content_type="markdown",
                    metadata={"tool_name": self.name},
                    token_usage=token_usage
                )
            thread_id = continuation_id
        else:
            # Create new thread
            try:
                thread_id = create_thread(
                    tool_name=self.name, initial_request=request.model_dump() if hasattr(request, "model_dump") else {}
                )

                # Add the assistant's response with follow-up
                request_files = getattr(request, "files", []) or []
                add_turn(
                    thread_id,
                    "assistant",
                    content,
                    follow_up_question=follow_up_data.get("follow_up_question"),
                    files=request_files,
                    tool_name=self.name,
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
                    token_usage=token_usage
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
            token_usage=token_usage
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
        continuation_id = getattr(request, "continuation_id", None)

        try:
            if continuation_id:
                # Check remaining turns in existing thread
                from utils.conversation_memory import get_thread

                context = get_thread(continuation_id)
                if context:
                    current_turns = len(context.turns)
                    remaining_turns = MAX_CONVERSATION_TURNS - current_turns - 1  # -1 for this response
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

    def _create_continuation_offer_response(self, content: str, continuation_data: dict, request, token_usage: Optional[TokenUsage] = None) -> ToolOutput:
        """
        Create a response offering Claude the opportunity to continue conversation.

        Args:
            content: The main response content
            continuation_data: Dict containing remaining_turns and tool_name
            request: Original request for context
            token_usage: Optional token usage information

        Returns:
            ToolOutput configured with continuation offer
        """
        try:
            # Create new thread for potential continuation
            thread_id = create_thread(
                tool_name=self.name, initial_request=request.model_dump() if hasattr(request, "model_dump") else {}
            )

            # Add this response as the first turn (assistant turn)
            request_files = getattr(request, "files", []) or []
            add_turn(thread_id, "assistant", content, files=request_files, tool_name=self.name)

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
                token_usage=token_usage
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
                token_usage=token_usage
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

    def format_response(self, response: str, request) -> str:
        """
        Format the model's response for display.

        Override this method to add tool-specific formatting like headers,
        summaries, or structured output. Default implementation returns
        the response unchanged.

        Args:
            response: The raw response from the model
            request: The original request for context

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

    def create_model(self, model_name: str, temperature: float, thinking_mode: str = "medium"):
        """
        Create a configured Gemini model instance.

        This method handles model creation with appropriate settings including
        temperature and thinking budget configuration for models that support it.

        Args:
            model_name: Name of the Gemini model to use (or shorthand like 'flash', 'pro')
            temperature: Temperature setting for response generation
            thinking_mode: Thinking depth mode (affects computational budget)

        Returns:
            Model instance configured and ready for generation
        """
        # Define model shorthands for user convenience
        model_shorthands = {
            "pro": "gemini-2.5-pro-preview-06-05",
            "flash": "gemini-2.0-flash-exp",
        }

        # Resolve shorthand to full model name
        resolved_model_name = model_shorthands.get(model_name.lower(), model_name)

        # Map thinking modes to computational budget values
        # Higher budgets allow for more complex reasoning but increase latency
        thinking_budgets = {
            "minimal": 128,  # Minimum for 2.5 Pro - fast responses
            "low": 2048,  # Light reasoning tasks
            "medium": 8192,  # Balanced reasoning (default)
            "high": 16384,  # Complex analysis
            "max": 32768,  # Maximum reasoning depth
        }

        thinking_budget = thinking_budgets.get(thinking_mode, 8192)

        # Gemini 2.5 models support thinking configuration for enhanced reasoning
        # Skip special handling in test environment to allow mocking
        if "2.5" in resolved_model_name and not os.environ.get("PYTEST_CURRENT_TEST"):
            try:
                # Retrieve API key for Gemini client creation
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY environment variable is required")

                client = genai.Client(api_key=api_key)

                # Create a wrapper class to provide a consistent interface
                # This abstracts the differences between API versions
                class ModelWrapper:
                    def __init__(self, client, model_name, temperature, thinking_budget):
                        self.client = client
                        self.model_name = model_name
                        self.temperature = temperature
                        self.thinking_budget = thinking_budget

                    def generate_content(self, prompt):
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                temperature=self.temperature,
                                candidate_count=1,
                                thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget),
                            ),
                        )

                        # Wrap the response to match the expected format
                        # This ensures compatibility across different API versions
                        class ResponseWrapper:
                            def __init__(self, text):
                                self.text = text
                                self.candidates = [
                                    type(
                                        "obj",
                                        (object,),
                                        {
                                            "content": type(
                                                "obj",
                                                (object,),
                                                {
                                                    "parts": [
                                                        type(
                                                            "obj",
                                                            (object,),
                                                            {"text": text},
                                                        )
                                                    ]
                                                },
                                            )(),
                                            "finish_reason": "STOP",
                                        },
                                    )
                                ]

                        return ResponseWrapper(response.text)

                return ModelWrapper(client, resolved_model_name, temperature, thinking_budget)

            except Exception:
                # Fall back to regular API if thinking configuration fails
                # This ensures the tool remains functional even with API changes
                pass

        # For models that don't support thinking configuration, use standard API
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        client = genai.Client(api_key=api_key)

        # Create a simple wrapper for models without thinking configuration
        # This provides the same interface as the thinking-enabled wrapper
        class SimpleModelWrapper:
            def __init__(self, client, model_name, temperature):
                self.client = client
                self.model_name = model_name
                self.temperature = temperature

            def generate_content(self, prompt):
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        candidate_count=1,
                    ),
                )

                # Convert to match expected format
                class ResponseWrapper:
                    def __init__(self, text):
                        self.text = text
                        self.candidates = [
                            type(
                                "obj",
                                (object,),
                                {
                                    "content": type(
                                        "obj",
                                        (object,),
                                        {"parts": [type("obj", (object,), {"text": text})]},
                                    )(),
                                    "finish_reason": "STOP",
                                },
                            )
                        ]

                return ResponseWrapper(response.text)

        return SimpleModelWrapper(client, resolved_model_name, temperature)
