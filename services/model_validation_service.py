"""
Model Validation Service for centralized model validation logic.

This service extracts model validation logic from the monolithic request handler
to provide focused, testable model validation and resolution capabilities.
"""

import logging
from typing import Any, Optional

from services.provider_manager import ProviderManager

logger = logging.getLogger(__name__)


class ModelValidationService:
    """
    Handles model validation, resolution, and context creation.

    This service coordinates with ProviderManager to provide comprehensive
    model validation and resolution services for tool execution.
    """

    def __init__(self, provider_manager: ProviderManager):
        """
        Initialize the model validation service.

        Args:
            provider_manager: ProviderManager instance for provider operations
        """
        self.provider_manager = provider_manager

    async def resolve_and_validate_model(
        self, arguments: dict[str, Any], tool_name: str, tool, default_model: str
    ) -> tuple[Optional[dict[str, Any]], Optional[str], Optional[str]]:
        """
        Resolve and validate model for tool execution.

        This method handles the complete model resolution pipeline:
        1. Extract model from arguments or use default
        2. Parse model:option format
        3. Handle auto mode resolution
        4. Validate model availability
        5. Create model context

        Args:
            arguments: Tool arguments that may contain model specification
            tool_name: Name of the tool requesting model validation
            tool: Tool instance for category and requirements checking
            default_model: Default model to use if none specified

        Returns:
            Tuple of (error_dict, resolved_model_name, model_option)
            error_dict is None if validation successful
        """
        # Skip model resolution for tools that don't require models
        if not tool.requires_model():
            logger.debug(f"Tool {tool_name} doesn't require model resolution - skipping validation")
            return None, None, None

        # Get model from arguments or use default
        model_name = arguments.get("model") or default_model
        logger.debug(f"Initial model for {tool_name}: {model_name}")

        # Parse model:option format if present
        model_name, model_option = self.provider_manager.parse_model_option(model_name)
        if model_option:
            logger.debug(f"Parsed model format - model: '{model_name}', option: '{model_option}'")

        # Handle auto mode resolution
        if model_name.lower() == "auto":
            model_name = await self.provider_manager.resolve_model_auto(tool_name, tool)
            # Update arguments with resolved model
            arguments["model"] = model_name

        # Validate model availability
        validation_error = await self.provider_manager.validate_model_availability(model_name, tool_name, tool)
        if validation_error:
            return validation_error, None, None

        # Create model context
        model_context = await self.provider_manager.create_model_context(model_name, model_option)

        # Update arguments with model context and resolved name
        arguments["_model_context"] = model_context
        arguments["_resolved_model_name"] = model_name

        logger.debug(f"Model validation completed successfully for {tool_name} with model {model_name}")

        return None, model_name, model_option

    def requires_model_validation(self, tool) -> bool:
        """
        Check if a tool requires model validation.

        Args:
            tool: Tool instance to check

        Returns:
            True if tool requires model validation, False otherwise
        """
        return tool.requires_model()

    def update_arguments_with_model_context(self, arguments: dict[str, Any], model_context, resolved_model_name: str):
        """
        Update arguments with model context information.

        Args:
            arguments: Tool arguments to update
            model_context: ModelContext instance
            resolved_model_name: Name of the resolved model
        """
        arguments["_model_context"] = model_context
        arguments["_resolved_model_name"] = resolved_model_name

        logger.debug(f"Arguments updated with model context for {resolved_model_name}")

    def extract_model_name(self, arguments: dict[str, Any], default_model: str) -> str:
        """
        Extract model name from arguments or return default.

        Args:
            arguments: Tool arguments to extract from
            default_model: Default model to use if none specified

        Returns:
            Model name to use
        """
        return arguments.get("model") or default_model
