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
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional

from google import genai
from google.genai import types
from mcp.types import TextContent
from pydantic import BaseModel, Field

from config import MCP_PROMPT_SIZE_LIMIT
from utils.file_utils import read_file_content

from .models import ClarificationRequest, ToolOutput


class ToolRequest(BaseModel):
    """
    Base request model for all tools.

    This Pydantic model defines common parameters that can be used by any tool.
    Tools can extend this model to add their specific parameters while inheriting
    these common fields.
    """

    model: Optional[str] = Field(
        None, description="Model to use (defaults to Gemini 2.5 Pro)"
    )
    temperature: Optional[float] = Field(
        None, description="Temperature for response (tool-specific defaults)"
    )
    # Thinking mode controls how much computational budget the model uses for reasoning
    # Higher values allow for more complex reasoning but increase latency and cost
    thinking_mode: Optional[Literal["minimal", "low", "medium", "high", "max"]] = Field(
        None,
        description="Thinking depth: minimal (128), low (2048), medium (8192), high (16384), max (32768)",
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
    def get_input_schema(self) -> Dict[str, Any]:
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

    def check_prompt_size(self, text: str) -> Optional[Dict[str, Any]]:
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

    def handle_prompt_file(
        self, files: Optional[List[str]]
    ) -> tuple[Optional[str], Optional[List[str]]]:
        """
        Check for and handle prompt.txt in the files list.

        If prompt.txt is found, reads its content and removes it from the files list.
        This file is treated specially as the main prompt, not as an embedded file.

        This mechanism allows us to work around MCP's ~25K token limit by having
        Claude save large prompts to a file, effectively using the file transfer
        mechanism to bypass token constraints while preserving response capacity.

        Args:
            files: List of file paths

        Returns:
            tuple: (prompt_content, updated_files_list)
        """
        if not files:
            return None, files

        prompt_content = None
        updated_files = []

        for file_path in files:
            # Check if the filename is exactly "prompt.txt"
            # This ensures we don't match files like "myprompt.txt" or "prompt.txt.bak"
            if os.path.basename(file_path) == "prompt.txt":
                try:
                    prompt_content = read_file_content(file_path)
                except Exception:
                    # If we can't read the file, we'll just skip it
                    # The error will be handled elsewhere
                    pass
            else:
                updated_files.append(file_path)

        return prompt_content, updated_files if updated_files else None

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
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
            # Validate request using the tool's Pydantic model
            # This ensures all required fields are present and properly typed
            request_model = self.get_request_model()
            request = request_model(**arguments)

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

            # Extract model configuration from request or use defaults
            from config import GEMINI_MODEL

            model_name = getattr(request, "model", None) or GEMINI_MODEL
            temperature = getattr(request, "temperature", None)
            if temperature is None:
                temperature = self.get_default_temperature()
            thinking_mode = getattr(request, "thinking_mode", None)
            if thinking_mode is None:
                thinking_mode = self.get_default_thinking_mode()

            # Create model instance with appropriate configuration
            # This handles both regular models and thinking-enabled models
            model = self.create_model(model_name, temperature, thinking_mode)

            # Generate AI response using the configured model
            response = model.generate_content(prompt)

            # Process the model's response
            if response.candidates and response.candidates[0].content.parts:
                raw_text = response.candidates[0].content.parts[0].text

                # Parse response to check for clarification requests or format output
                tool_output = self._parse_response(raw_text, request)

            else:
                # Handle cases where the model couldn't generate a response
                # This might happen due to safety filters or other constraints
                finish_reason = (
                    response.candidates[0].finish_reason
                    if response.candidates
                    else "Unknown"
                )
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
            error_output = ToolOutput(
                status="error",
                content=f"Error in {self.name}: {str(e)}",
                content_type="text",
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]

    def _parse_response(self, raw_text: str, request) -> ToolOutput:
        """
        Parse the raw response and determine if it's a clarification request.

        Some tools may return JSON indicating they need more information.
        This method detects such responses and formats them appropriately.

        Args:
            raw_text: The raw text response from the model
            request: The original request for context

        Returns:
            ToolOutput: Standardized output object
        """
        try:
            # Try to parse as JSON to check for clarification requests
            potential_json = json.loads(raw_text.strip())

            if (
                isinstance(potential_json, dict)
                and potential_json.get("status") == "requires_clarification"
            ):
                # Validate the clarification request structure
                clarification = ClarificationRequest(**potential_json)
                return ToolOutput(
                    status="requires_clarification",
                    content=clarification.model_dump_json(),
                    content_type="json",
                    metadata={
                        "original_request": (
                            request.model_dump()
                            if hasattr(request, "model_dump")
                            else str(request)
                        )
                    },
                )

        except (json.JSONDecodeError, ValueError, TypeError):
            # Not a JSON clarification request, treat as normal response
            pass

        # Normal text response - format using tool-specific formatting
        formatted_content = self.format_response(raw_text, request)

        # Determine content type based on the formatted content
        content_type = (
            "markdown"
            if any(
                marker in formatted_content for marker in ["##", "**", "`", "- ", "1. "]
            )
            else "text"
        )

        return ToolOutput(
            status="success",
            content=formatted_content,
            content_type=content_type,
            metadata={"tool_name": self.name},
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
        from config import MAX_CONTEXT_TOKENS
        from utils import check_token_limit

        within_limit, estimated_tokens = check_token_limit(text)
        if not within_limit:
            raise ValueError(
                f"{context_type} too large (~{estimated_tokens:,} tokens). "
                f"Maximum is {MAX_CONTEXT_TOKENS:,} tokens."
            )

    def create_model(
        self, model_name: str, temperature: float, thinking_mode: str = "medium"
    ):
        """
        Create a configured Gemini model instance.

        This method handles model creation with appropriate settings including
        temperature and thinking budget configuration for models that support it.

        Args:
            model_name: Name of the Gemini model to use
            temperature: Temperature setting for response generation
            thinking_mode: Thinking depth mode (affects computational budget)

        Returns:
            Model instance configured and ready for generation
        """
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
        if "2.5" in model_name and not os.environ.get("PYTEST_CURRENT_TEST"):
            try:
                # Retrieve API key for Gemini client creation
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY environment variable is required")

                client = genai.Client(api_key=api_key)

                # Create a wrapper class to provide a consistent interface
                # This abstracts the differences between API versions
                class ModelWrapper:
                    def __init__(
                        self, client, model_name, temperature, thinking_budget
                    ):
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
                                thinking_config=types.ThinkingConfig(
                                    thinking_budget=self.thinking_budget
                                ),
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

                return ModelWrapper(client, model_name, temperature, thinking_budget)

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
                                        {
                                            "parts": [
                                                type("obj", (object,), {"text": text})
                                            ]
                                        },
                                    )(),
                                    "finish_reason": "STOP",
                                },
                            )
                        ]

                return ResponseWrapper(response.text)

        return SimpleModelWrapper(client, model_name, temperature)
