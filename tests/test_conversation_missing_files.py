"""
Test conversation memory handling of missing files.

Following existing test patterns to ensure conversation memory gracefully
handles missing files without crashing.
"""

from unittest.mock import Mock

from utils.conversation_memory import (
    ConversationTurn,
    ThreadContext,
    build_conversation_history,
)


class TestConversationMissingFiles:
    """Test handling of missing files during conversation memory reconstruction."""

    def test_build_conversation_history_handles_missing_files(self):
        """Test that conversation history building handles missing files gracefully."""

        # Create conversation context with missing file reference (following existing test patterns)
        context = ThreadContext(
            thread_id="test-thread",
            created_at="2024-01-01T00:00:00Z",
            last_updated_at="2024-01-01T00:05:00Z",
            tool_name="analyze",
            turns=[
                ConversationTurn(
                    role="user",
                    content="Please analyze this file",
                    timestamp="2024-01-01T00:01:00Z",
                    files=["/nonexistent/missing_file.py"],  # File that doesn't exist
                    tool_name="analyze",
                ),
                ConversationTurn(
                    role="assistant",
                    content="Here's my analysis...",
                    timestamp="2024-01-01T00:02:00Z",
                    tool_name="analyze",
                ),
            ],
            initial_context={"path": "/nonexistent/missing_file.py"},
        )

        # Mock model context (following existing test patterns)
        mock_model_context = Mock()
        mock_model_context.calculate_token_allocation.return_value = Mock(file_tokens=50000, history_tokens=50000)
        mock_model_context.estimate_tokens.return_value = 100
        mock_model_context.model_name = "test-model"

        # Should not crash, should handle missing file gracefully
        history, tokens = build_conversation_history(context, mock_model_context)

        # Should return valid history despite missing file
        assert isinstance(history, str)
        assert isinstance(tokens, int)
        assert len(history) > 0

        # Should contain conversation content
        assert "CONVERSATION HISTORY" in history
        assert "Please analyze this file" in history
        assert "Here's my analysis" in history
