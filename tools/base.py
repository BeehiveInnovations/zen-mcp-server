"""
Base class for all Gemini MCP tools
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from mcp.types import TextContent
from pydantic import BaseModel, Field

class ToolRequest(BaseModel):
    """Base request model for all tools"""

    model: Optional[str] = Field(
        None, description="Model to use (defaults to Gemini 2.5 Pro)"
    )
    temperature: Optional[float] = Field(
        None, description="Temperature for response (tool-specific defaults)"
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

    @abstractmethod
    def get_request_model(self):
        """Return the Pydantic model for request validation"""
        pass

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute the tool with given arguments"""
        try:
            # Validate request
            request_model = self.get_request_model()
            request = request_model(**arguments)

            # Prepare the prompt
            prompt = await self.prepare_prompt(request)

            # Get model configuration
            from config import DEFAULT_MODEL

            model_name = getattr(request, "model", None) or DEFAULT_MODEL
            temperature = getattr(request, "temperature", None)
            if temperature is None:
                temperature = self.get_default_temperature()

            # Create and configure model
            model = self.create_model(model_name, temperature)

            # Generate response
            response = model.generate_content(prompt)

            # Handle response
            if response.candidates and response.candidates[0].content.parts:
                text = response.candidates[0].content.parts[0].text
            else:
                finish_reason = (
                    response.candidates[0].finish_reason
                    if response.candidates
                    else "Unknown"
                )
                text = f"Response blocked or incomplete. Finish reason: {finish_reason}"

            # Format response
            formatted_response = self.format_response(text, request)

            return [TextContent(type="text", text=formatted_response)]

        except Exception as e:
            error_msg = f"Error in {self.name}: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    @abstractmethod
    async def prepare_prompt(self, request) -> str:
        """Prepare the full prompt for Gemini"""
        pass

    def format_response(self, response: str, request) -> str:
        """Format the response for display (can be overridden)"""
        return response

    def create_model(
        self, model_name: str, temperature: float
    ) -> genai.GenerativeModel:
        """Create a configured Gemini model"""
        return genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": temperature,
                "candidate_count": 1,
            },
        )
