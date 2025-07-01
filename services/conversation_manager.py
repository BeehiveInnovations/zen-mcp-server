"""
Conversation Manager Service for handling conversation context management.

This service extracts conversation management logic from the monolithic request handler
to provide focused, testable conversation context reconstruction and management.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Handles conversation context reconstruction and management.

    This service encapsulates the logic for managing conversation threads,
    context reconstruction, and continuation handling for stateless-to-stateful
    conversation bridges.
    """

    def __init__(self):
        """Initialize the conversation manager."""
        pass

    async def handle_continuation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Handle conversation continuation if continuation_id is present.

        This method checks for continuation_id in arguments and delegates to
        the existing reconstruct_thread_context function for backward compatibility.

        Args:
            arguments: Tool arguments that may contain continuation_id

        Returns:
            Arguments with reconstructed conversation context if continuation_id present,
            original arguments otherwise
        """
        if "continuation_id" not in arguments or not arguments["continuation_id"]:
            return arguments

        continuation_id = arguments["continuation_id"]
        logger.debug(f"Resuming conversation thread: {continuation_id}")
        logger.debug(
            f"[CONVERSATION_DEBUG] ConversationManager handling thread {continuation_id} with {len(arguments)} arguments"
        )
        logger.debug(f"[CONVERSATION_DEBUG] Original arguments keys: {list(arguments.keys())}")

        # Log to activity file for monitoring
        try:
            mcp_activity_logger = logging.getLogger("mcp_activity")
            mcp_activity_logger.info(f"CONVERSATION_RESUME: Handling thread {continuation_id}")
        except Exception:
            pass

        # Import and delegate to existing function to maintain compatibility
        # This keeps the complex conversation reconstruction logic intact
        # Use dynamic import to avoid circular imports
        import importlib

        server_module = importlib.import_module("server")
        reconstruct_thread_context = server_module.reconstruct_thread_context

        reconstructed_arguments = await reconstruct_thread_context(arguments)

        logger.debug(
            f"[CONVERSATION_DEBUG] After thread reconstruction, arguments keys: {list(reconstructed_arguments.keys())}"
        )
        if "_remaining_tokens" in reconstructed_arguments:
            logger.debug(
                f"[CONVERSATION_DEBUG] Remaining token budget: {reconstructed_arguments['_remaining_tokens']:,}"
            )

        return reconstructed_arguments

    def has_continuation(self, arguments: dict[str, Any]) -> bool:
        """
        Check if arguments contain a valid continuation_id.

        Args:
            arguments: Tool arguments to check

        Returns:
            True if continuation_id is present and not empty, False otherwise
        """
        return "continuation_id" in arguments and bool(arguments["continuation_id"])

    def get_continuation_id(self, arguments: dict[str, Any]) -> Optional[str]:
        """
        Extract continuation_id from arguments if present.

        Args:
            arguments: Tool arguments to extract from

        Returns:
            continuation_id string if present, None otherwise
        """
        if self.has_continuation(arguments):
            return arguments["continuation_id"]
        return None

    def log_conversation_activity(self, tool_name: str, continuation_id: str, activity_type: str):
        """
        Log conversation activity to the MCP activity logger.

        Args:
            tool_name: Name of the tool handling the conversation
            continuation_id: ID of the conversation thread
            activity_type: Type of activity (e.g., "RESUME", "START", "CONTINUE")
        """
        try:
            mcp_activity_logger = logging.getLogger("mcp_activity")
            mcp_activity_logger.info(f"CONVERSATION_{activity_type}: {tool_name} thread {continuation_id}")
        except Exception:
            # Silently fail if logging fails - don't break conversation flow
            pass
