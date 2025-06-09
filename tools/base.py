"""
Base class for all Gemini MCP tools
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Literal
import os
import json

from google import genai
from google.genai import types
from mcp.types import TextContent
from pydantic import BaseModel, Field

from .models import ToolOutput, ClarificationRequest


class ToolRequest(BaseModel):
    """Base request model for all tools"""

    model: Optional[str] = Field(
        None, description="Model to use (defaults to Gemini 2.5 Pro)"
    )
    temperature: Optional[float] = Field(
        None, description="Temperature for response (tool-specific defaults)"
    )
    thinking_mode: Optional[Literal["minimal", "low", "medium", "high", "max"]] = Field(
        None,
        description="Thinking depth: minimal (128), low (2048), medium (8192), high (16384), max (32768)",
    )


class BaseTool(ABC):
    """Base class for all Gemini tools"""

    def __init__(self):
        self.name = self.get_name()
        self.description = self.get_description()
        self.default_temperature = self.get_default_temperature()

    @abstractmethod
    def get_name(self) -> str:
        """Return the tool name"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return the verbose tool description for Claude"""
        pass

    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for tool inputs"""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this tool"""
        pass

    def get_default_temperature(self) -> float:
        """Return default temperature for this tool"""
        return 0.5

    def get_default_thinking_mode(self) -> str:
        """Return default thinking_mode for this tool"""
        return "medium"  # Default to medium thinking for better reasoning

    @abstractmethod
    def get_request_model(self):
        """Return the Pydantic model for request validation"""
        pass

    def validate_file_paths(self, request) -> Optional[str]:
        """
        Validate that all file paths in the request are absolute.
        Returns error message if validation fails, None if all paths are valid.
        """
        # Check if request has 'files' attribute
        if hasattr(request, "files") and request.files:
            for file_path in request.files:
                if not os.path.isabs(file_path):
                    return (
                        f"Error: All file paths must be absolute. "
                        f"Received relative path: {file_path}\n"
                        f"Please provide the full absolute path starting with '/'"
                    )

        # Check if request has 'path' attribute (for review_pending_changes)
        if hasattr(request, "path") and request.path:
            if not os.path.isabs(request.path):
                return (
                    f"Error: Path must be absolute. "
                    f"Received relative path: {request.path}\n"
                    f"Please provide the full absolute path starting with '/'"
                )

        return None

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute the tool with given arguments"""
        try:
            # Validate request
            request_model = self.get_request_model()
            request = request_model(**arguments)

            # Validate file paths
            path_error = self.validate_file_paths(request)
            if path_error:
                error_output = ToolOutput(
                    status="error",
                    content=path_error,
                    content_type="text",
                )
                return [TextContent(type="text", text=error_output.model_dump_json())]

            # Prepare the prompt
            prompt = await self.prepare_prompt(request)

            # Get model configuration
            from config import DEFAULT_MODEL

            model_name = getattr(request, "model", None) or DEFAULT_MODEL
            temperature = getattr(request, "temperature", None)
            if temperature is None:
                temperature = self.get_default_temperature()
            thinking_mode = getattr(request, "thinking_mode", None)
            if thinking_mode is None:
                thinking_mode = self.get_default_thinking_mode()

            # Create and configure model
            model = self.create_model(model_name, temperature, thinking_mode)

            # Generate response
            response = model.generate_content(prompt)

            # Handle response and create standardized output
            if response.candidates and response.candidates[0].content.parts:
                raw_text = response.candidates[0].content.parts[0].text

                # Check if this is a clarification request
                tool_output = self._parse_response(raw_text, request)

            else:
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

            # Serialize the standardized output as JSON
            return [TextContent(type="text", text=tool_output.model_dump_json())]

        except Exception as e:
            error_output = ToolOutput(
                status="error",
                content=f"Error in {self.name}: {str(e)}",
                content_type="text",
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]

    def _parse_response(self, raw_text: str, request) -> ToolOutput:
        """Parse the raw response and determine if it's a clarification request"""
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
        """Prepare the full prompt for Gemini"""
        pass

    def format_response(self, response: str, request) -> str:
        """Format the response for display (can be overridden)"""
        return response

    def create_model(
        self, model_name: str, temperature: float, thinking_mode: str = "medium"
    ):
        """Create a configured Gemini model with thinking configuration"""
        # Map thinking modes to budget values
        thinking_budgets = {
            "minimal": 128,  # Minimum for 2.5 Pro
            "low": 2048,
            "medium": 8192,
            "high": 16384,
            "max": 32768,
        }

        thinking_budget = thinking_budgets.get(thinking_mode, 8192)

        # For models supporting thinking config, use the new API
        # Skip in test environment to allow mocking
        if "2.5" in model_name and not os.environ.get("PYTEST_CURRENT_TEST"):
            try:
                # Get API key
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY environment variable is required")

                client = genai.Client(api_key=api_key)

                # Create a wrapper to match the expected interface
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
                # Fall back to regular genai model if new API fails
                pass

        # For non-2.5 models or if thinking not needed, use regular API
        # Get API key
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        client = genai.Client(api_key=api_key)

        # Create wrapper for consistency
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
