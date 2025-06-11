"""
Test suite for conversation history bug fix

This test verifies that the critical bug where conversation history
(including file context) was not included when using continuation_id
has been properly fixed.

The bug was that tools with continuation_id would not see previous
conversation turns, causing issues like Gemini not seeing files that
Claude had shared in earlier turns.
"""

import json
from unittest.mock import Mock, patch

import pytest
from pydantic import Field

from tools.base import BaseTool, ToolRequest
from utils.conversation_memory import ConversationTurn, ThreadContext


class FileContextRequest(ToolRequest):
    """Test request with file support"""

    prompt: str = Field(..., description="Test prompt")
    files: list[str] = Field(default_factory=list, description="Optional files")


class FileContextTool(BaseTool):
    """Test tool for file context verification"""

    def get_name(self) -> str:
        return "test_file_context"

    def get_description(self) -> str:
        return "Test tool for file context"

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "continuation_id": {"type": "string", "required": False},
            },
        }

    def get_system_prompt(self) -> str:
        return "Test system prompt for file context"

    def get_request_model(self):
        return FileContextRequest

    async def prepare_prompt(self, request) -> str:
        # Simple prompt preparation that would normally read files
        # For this test, we're focusing on whether conversation history is included
        files_context = ""
        if request.files:
            files_context = f"\nFiles in current request: {', '.join(request.files)}"

        return f"System: {self.get_system_prompt()}\nUser: {request.prompt}{files_context}"


class TestConversationHistoryBugFix:
    """Test that conversation history is properly included with continuation_id"""

    def setup_method(self):
        self.tool = FileContextTool()

    @patch("tools.base.get_thread")
    @patch("tools.base.add_turn")
    async def test_conversation_history_included_with_continuation_id(self, mock_add_turn, mock_get_thread):
        """Test that conversation history (including file context) is included when using continuation_id"""

        # Create a thread context with previous turns including files
        thread_context = ThreadContext(
            thread_id="test-history-id",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:02:00Z",
            tool_name="analyze",  # Started with analyze tool
            turns=[
                ConversationTurn(
                    role="assistant",
                    content="I've analyzed the authentication module and found several security issues.",
                    timestamp="2023-01-01T00:01:00Z",
                    tool_name="analyze",
                    files=["/src/auth.py", "/src/security.py"],  # Files from analyze tool
                ),
                ConversationTurn(
                    role="assistant",
                    content="The code review shows these files have critical vulnerabilities.",
                    timestamp="2023-01-01T00:02:00Z",
                    tool_name="codereview",
                    files=["/src/auth.py", "/tests/test_auth.py"],  # Files from codereview tool
                ),
            ],
            initial_context={"question": "Analyze authentication security"},
        )

        # Mock get_thread to return our test context
        mock_get_thread.return_value = thread_context
        # Mock add_turn to return success
        mock_add_turn.return_value = True

        # Mock the model to capture what prompt it receives
        captured_prompt = None

        with patch.object(self.tool, "create_model") as mock_create_model:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = [
                Mock(
                    content=Mock(parts=[Mock(text="Response with conversation context")]),
                    finish_reason="STOP",
                )
            ]

            def capture_prompt(prompt):
                nonlocal captured_prompt
                captured_prompt = prompt
                return mock_response

            mock_model.generate_content.side_effect = capture_prompt
            mock_create_model.return_value = mock_model

            # Execute tool with continuation_id
            arguments = {
                "prompt": "What should we fix first?",
                "continuation_id": "test-history-id",
                "files": ["/src/utils.py"],  # New file for this turn
            }
            response = await self.tool.execute(arguments)

            # Verify response succeeded
            response_data = json.loads(response[0].text)
            assert response_data["status"] == "success"

            # Verify get_thread was called for history reconstruction
            mock_get_thread.assert_called_with("test-history-id")

            # Verify the prompt includes conversation history
            assert captured_prompt is not None

            # Check that conversation history is included
            assert "=== CONVERSATION HISTORY ===" in captured_prompt
            assert "Turn 1 (Gemini using analyze)" in captured_prompt
            assert "Turn 2 (Gemini using codereview)" in captured_prompt

            # Check that file context from previous turns is included
            assert "📁 Files referenced: /src/auth.py, /src/security.py" in captured_prompt
            assert "📁 Files referenced: /src/auth.py, /tests/test_auth.py" in captured_prompt

            # Check that previous turn content is included
            assert "I've analyzed the authentication module and found several security issues." in captured_prompt
            assert "The code review shows these files have critical vulnerabilities." in captured_prompt

            # Check that continuation instruction is included
            assert "Continue this conversation by building on the previous context." in captured_prompt

            # Check that current request is still included
            assert "What should we fix first?" in captured_prompt
            assert "Files in current request: /src/utils.py" in captured_prompt

    @patch("tools.base.get_thread")
    async def test_no_history_when_thread_not_found(self, mock_get_thread):
        """Test graceful handling when thread is not found"""

        # Mock get_thread to return None (thread not found)
        mock_get_thread.return_value = None

        captured_prompt = None

        with patch.object(self.tool, "create_model") as mock_create_model:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = [
                Mock(
                    content=Mock(parts=[Mock(text="Response without history")]),
                    finish_reason="STOP",
                )
            ]

            def capture_prompt(prompt):
                nonlocal captured_prompt
                captured_prompt = prompt
                return mock_response

            mock_model.generate_content.side_effect = capture_prompt
            mock_create_model.return_value = mock_model

            # Execute tool with continuation_id for non-existent thread
            arguments = {"prompt": "Test without history", "continuation_id": "non-existent-thread-id"}
            response = await self.tool.execute(arguments)

            # Should still succeed but without history
            response_data = json.loads(response[0].text)
            assert response_data["status"] == "success"

            # Verify get_thread was called for non-existent thread
            mock_get_thread.assert_called_with("non-existent-thread-id")

            # Verify the prompt does NOT include conversation history
            assert captured_prompt is not None
            assert "=== CONVERSATION HISTORY ===" not in captured_prompt
            assert "Test without history" in captured_prompt

    async def test_no_history_for_new_conversations(self):
        """Test that new conversations (no continuation_id) don't get history"""

        captured_prompt = None

        with patch.object(self.tool, "create_model") as mock_create_model:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = [
                Mock(
                    content=Mock(parts=[Mock(text="New conversation response")]),
                    finish_reason="STOP",
                )
            ]

            def capture_prompt(prompt):
                nonlocal captured_prompt
                captured_prompt = prompt
                return mock_response

            mock_model.generate_content.side_effect = capture_prompt
            mock_create_model.return_value = mock_model

            # Execute tool without continuation_id (new conversation)
            arguments = {"prompt": "Start new conversation", "files": ["/src/new_file.py"]}
            response = await self.tool.execute(arguments)

            # Should succeed (may offer continuation for new conversations)
            response_data = json.loads(response[0].text)
            assert response_data["status"] in ["success", "continuation_available"]

            # Verify the prompt does NOT include conversation history
            assert captured_prompt is not None
            assert "=== CONVERSATION HISTORY ===" not in captured_prompt
            assert "Start new conversation" in captured_prompt
            assert "Files in current request: /src/new_file.py" in captured_prompt

            # Should include follow-up instructions for new conversation
            # (This is the existing behavior for new conversations)
            assert "If you'd like to ask a follow-up question" in captured_prompt


if __name__ == "__main__":
    pytest.main([__file__])
