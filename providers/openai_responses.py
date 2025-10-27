"""OpenAI Responses API provider (/v1/responses endpoint).

This provider handles OpenAI's Responses API which is used for reasoning models
like o3, o3-pro, and GPT-5-Pro. It's separate from the Chat Completions API.
"""

import logging
from typing import Optional

from openai import OpenAI

from utils.env import get_env

from .base import ModelProvider
from .shared import ModelCapabilities, ModelResponse, ProviderType


class OpenAIResponsesProvider(ModelProvider):
    """Provider for OpenAI's Responses API (/v1/responses endpoint).

    This is a completely different API from Chat Completions, designed for
    reasoning models that support extended thinking and stateful context.
    """

    PROVIDER_TYPE = ProviderType.OPENAI
    FRIENDLY_NAME = "OpenAI Responses API"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI Responses API provider.

        Args:
            api_key: OpenAI API key. If not provided, reads from environment.
        """
        api_key = api_key or get_env("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required for Responses API")

        super().__init__(api_key=api_key)
        self.client = OpenAI(api_key=self.api_key)

    def get_provider_type(self) -> ProviderType:
        """Return the provider type."""
        return self.PROVIDER_TYPE

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
        images: Optional[list[str]] = None,
        files: Optional[list[str]] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate content using the Responses API.

        Args:
            prompt: User prompt
            model_name: Model name (e.g., "o3", "gpt-5-pro")
            system_prompt: System instructions
            temperature: Not used for reasoning models
            max_output_tokens: Maximum tokens to generate
            images: Images to include (if model supports vision)
            files: Document files to include (PDF, docs, etc.)
                   Files will be uploaded and processed using file_search tool
            **kwargs: Additional parameters

        Returns:
            ModelResponse with generated content
        """
        # Prepare input messages for responses endpoint
        input_messages = []

        # Add system prompt if provided
        if system_prompt:
            input_messages.append({"role": "user", "content": [{"type": "input_text", "text": system_prompt}]})

        # Add user prompt with optional images
        user_content = [{"type": "input_text", "text": prompt}]

        # Add images if provided and model supports them
        if images:
            for image_path in images:
                try:
                    # Process image (base64 encode or URL)
                    image_content = self._process_image(image_path)
                    if image_content:
                        user_content.append(image_content)
                except Exception as e:
                    logging.warning(f"Failed to process image {image_path}: {e}")

        input_messages.append({"role": "user", "content": user_content})

        # Handle file attachments if provided
        file_ids = []
        if files:
            logging.info(f"Processing {len(files)} file attachment(s) for Responses API")
            for file_path in files:
                try:
                    file_id = self._upload_file(file_path)
                    if file_id:
                        file_ids.append(file_id)
                        logging.info(f"Uploaded file {file_path} with ID: {file_id}")
                except Exception as e:
                    logging.error(f"Failed to upload file {file_path}: {e}")
                    raise ValueError(
                        f"Failed to upload file {file_path}: {e}. " "Please check the file path and permissions."
                    )

        # Get reasoning effort level
        reasoning_effort = kwargs.get("reasoning_effort", "medium")
        if reasoning_effort not in ["low", "medium", "high"]:
            reasoning_effort = "medium"

        # Prepare request parameters
        request_params = {
            "model": model_name,
            "input": input_messages,
            "reasoning": {"effort": reasoning_effort},
            "store": kwargs.get("store", True),
        }

        # Add file_search tool if files were provided
        if file_ids:
            request_params["tools"] = [{"type": "file_search"}]
            request_params["file_ids"] = file_ids
            logging.info(f"Enabled file_search tool with {len(file_ids)} file(s)")

        if max_output_tokens:
            request_params["max_completion_tokens"] = max_output_tokens

        # Log sanitized request
        logging.info(f"Responses API request to {model_name} with effort={reasoning_effort}")

        try:
            # Call the Responses API
            response = self.client.responses.create(**request_params)

            # Extract content from response
            content = self._extract_content(response)

            # Extract usage information
            usage = self._extract_usage(response)

            return ModelResponse(
                content=content,
                usage=usage,
                model_name=model_name,
                friendly_name=self.FRIENDLY_NAME,
                provider=self.PROVIDER_TYPE,
                metadata={
                    "model": getattr(response, "model", model_name),
                    "id": getattr(response, "id", ""),
                    "created": getattr(response, "created_at", 0),
                    "endpoint": "responses",
                    "reasoning_effort": reasoning_effort,
                },
            )

        except Exception as exc:
            error_msg = f"Responses API error for {model_name}: {exc}"
            logging.error(error_msg)
            raise RuntimeError(error_msg) from exc

    def _upload_file(self, file_path: str) -> Optional[str]:
        """Upload a file to OpenAI for use with file_search tool.

        Args:
            file_path: Path to the file to upload

        Returns:
            File ID if successful, None otherwise

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file type is not supported
        """
        import os

        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size (OpenAI limit is typically 512MB)
        file_size = os.path.getsize(file_path)
        max_size = 512 * 1024 * 1024  # 512MB
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes. Maximum size is {max_size} bytes (512MB)")

        try:
            # Upload file using OpenAI Files API
            with open(file_path, "rb") as f:
                file_response = self.client.files.create(file=f, purpose="assistants")  # Required for file_search

            return file_response.id

        except Exception as e:
            logging.error(f"Failed to upload file {file_path}: {e}")
            raise

    def _process_image(self, image_path: str) -> Optional[dict]:
        """Process image for inclusion in request.

        Args:
            image_path: Path to image or data URL

        Returns:
            Image content dict for API request
        """
        # This should be implemented based on OpenAI's image format requirements
        # For now, return a placeholder
        return {"type": "input_image", "image_url": image_path}

    def _extract_content(self, response) -> str:
        """Extract content from Responses API response.

        Args:
            response: API response object

        Returns:
            Extracted text content
        """
        # Try different response formats
        if hasattr(response, "output_text"):
            return response.output_text
        elif hasattr(response, "output") and hasattr(response.output, "text"):
            return response.output.text
        elif hasattr(response, "content"):
            return response.content
        else:
            # Fallback to string representation
            return str(response)

    def _extract_usage(self, response) -> Optional[dict]:
        """Extract usage information from response.

        Args:
            response: API response object

        Returns:
            Usage dict with token counts
        """
        usage = {}

        if hasattr(response, "input_tokens"):
            usage["input_tokens"] = response.input_tokens

        if hasattr(response, "output_tokens"):
            usage["output_tokens"] = response.output_tokens

        if "input_tokens" in usage and "output_tokens" in usage:
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]

        return usage if usage else None

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a model.

        All Responses API models have similar capabilities focused on reasoning.

        Args:
            model_name: Model name

        Returns:
            ModelCapabilities for the model
        """
        # Base capabilities for all reasoning models
        return ModelCapabilities(
            model_name=model_name,
            friendly_name=f"OpenAI {model_name} (Responses API)",
            context_window=200000,  # Most reasoning models have large context
            max_output_tokens=32000,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=False,  # Responses API doesn't stream
            supports_function_calling=True,
            supports_json_mode=True,
            supports_images="vision" in model_name.lower() or "o" in model_name.lower(),
            supports_temperature=False,  # Reasoning models use effort instead
            use_openai_response_api=True,  # Always true for this provider
            default_reasoning_effort="medium",
        )

    def validate_model_name(self, model_name: str) -> bool:
        """Check if model is supported by Responses API.

        Args:
            model_name: Model name to validate

        Returns:
            True if model is supported
        """
        # Models that require Responses API
        responses_models = {
            "o3",
            "o3-mini",
            "o3-pro",
            "o4",
            "o4-mini",
            "gpt-5-pro",
            "gpt-5",
            "gpt-5-mini",
            "gpt-5-nano",
        }

        # Check if model is in the list (case-insensitive)
        model_lower = model_name.lower()
        return any(m in model_lower for m in responses_models)

    def test_connection(self) -> bool:
        """Test if the API connection works.

        Returns:
            True if connection successful
        """
        try:
            # Try a minimal request
            response = self.client.responses.create(
                model="o3-mini",
                input=[{"role": "user", "content": [{"type": "input_text", "text": "Hi"}]}],
                reasoning={"effort": "low"},
                max_completion_tokens=10,
            )
            return bool(response)
        except Exception as e:
            logging.error(f"Responses API connection test failed: {e}")
            return False
