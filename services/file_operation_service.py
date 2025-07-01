"""
File Operation Service for handling file validation and operations.

This service extracts file operation logic from the monolithic request handler
to provide focused, testable file validation and processing capabilities.
"""

import logging
from typing import Any, Optional

from utils.file_utils import check_total_file_size_async

logger = logging.getLogger(__name__)


class FileOperationService:
    """
    Handles file validation and operations for tool execution.

    This service encapsulates file-related operations including size validation,
    existence checks, and preparation for tool processing.
    """

    def __init__(self):
        """Initialize the file operation service."""
        pass

    async def validate_file_sizes(self, files: list[str], model_name: str) -> Optional[dict[str, Any]]:
        """
        Validate file sizes against model context limits using async I/O.

        This method checks if the total size of files is within the context window
        limits of the specified model, providing early validation at the MCP boundary.

        Args:
            files: List of file paths to validate
            model_name: Name of the model to validate against

        Returns:
            None if files are valid, error dict if validation fails
        """
        if not files:
            return None

        logger.debug(f"Async checking file sizes for {len(files)} files with model {model_name}")

        # Use existing file size validation with async I/O
        file_size_check = await check_total_file_size_async(files, model_name)

        if file_size_check:
            logger.warning(f"Async file size check failed for model {model_name}")
            return file_size_check

        logger.debug(f"File size validation passed for {len(files)} files with model {model_name}")
        return None

    def has_files(self, arguments: dict[str, Any]) -> bool:
        """
        Check if arguments contain files for processing.

        Args:
            arguments: Tool arguments to check

        Returns:
            True if files are present and not empty, False otherwise
        """
        return "files" in arguments and bool(arguments["files"])

    def get_files(self, arguments: dict[str, Any]) -> list[str]:
        """
        Extract files list from arguments.

        Args:
            arguments: Tool arguments to extract from

        Returns:
            List of file paths, empty list if no files present
        """
        if self.has_files(arguments):
            return arguments["files"]
        return []

    def count_files(self, arguments: dict[str, Any]) -> int:
        """
        Count the number of files in arguments.

        Args:
            arguments: Tool arguments to count files from

        Returns:
            Number of files present
        """
        files = self.get_files(arguments)
        return len(files)

    async def prepare_files_for_tool(self, arguments: dict[str, Any], model_name: str) -> Optional[dict[str, Any]]:
        """
        Prepare and validate files for tool execution.

        This method performs comprehensive file preparation including size validation
        and any other file-related checks needed before tool execution.

        Args:
            arguments: Tool arguments containing files
            model_name: Model name for validation context

        Returns:
            None if preparation successful, error dict if preparation fails
        """
        if not self.has_files(arguments):
            return None

        files = self.get_files(arguments)

        # Validate file sizes
        validation_result = await self.validate_file_sizes(files, model_name)
        if validation_result:
            return validation_result

        logger.debug(f"Files prepared successfully for tool execution: {len(files)} files")
        return None
