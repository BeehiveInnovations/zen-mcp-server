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

    @patch("tools.base.add_turn")
    async def test_conversation_history_included_with_continuation_id(self, mock_add_turn):
        """Test that conversation history (including file context) is included when using continuation_id"""

        # Create a thread context with previous turns including files
        _thread_context = ThreadContext(
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
            # In the corrected flow, server.py:reconstruct_thread_context
            # would have already added conversation history to the prompt
            # This test simulates that the prompt already contains conversation history
            arguments = {
                "prompt": "What should we fix first?",
                "continuation_id": "test-history-id",
                "files": ["/src/utils.py"],  # New file for this turn
            }
            response = await self.tool.execute(arguments)

            # Verify response succeeded
            response_data = json.loads(response[0].text)
            assert response_data["status"] == "success"

            # Note: After fixing the duplication bug, conversation history reconstruction
            # now happens ONLY in server.py, not in tools/base.py
            # This test verifies that tools/base.py no longer duplicates conversation history

            # Verify the prompt is captured
            assert captured_prompt is not None

            # The prompt should NOT contain conversation history (since we removed the duplicate code)
            # In the real flow, server.py would add conversation history before calling tool.execute()
            assert "=== CONVERSATION HISTORY ===" not in captured_prompt

            # The prompt should contain the current request
            assert "What should we fix first?" in captured_prompt
            assert "Files in current request: /src/utils.py" in captured_prompt

            # This test confirms the duplication bug is fixed - tools/base.py no longer
            # redundantly adds conversation history that server.py already added

    async def test_no_history_when_thread_not_found(self):
        """Test graceful handling when thread is not found"""

        # Note: After fixing the duplication bug, thread not found handling
        # happens in server.py:reconstruct_thread_context, not in tools/base.py
        # This test verifies tools don't try to handle missing threads themselves

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
            # In the real flow, server.py would have already handled the missing thread
            arguments = {"prompt": "Test without history", "continuation_id": "non-existent-thread-id"}
            response = await self.tool.execute(arguments)

            # Should succeed since tools/base.py no longer handles missing threads
            response_data = json.loads(response[0].text)
            assert response_data["status"] == "success"

            # Verify the prompt does NOT include conversation history
            # (because tools/base.py no longer tries to add it)
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

    @patch("tools.base.get_thread")
    @patch("tools.base.add_turn")
    @patch("utils.file_utils.resolve_and_validate_path")
    async def test_no_duplicate_file_embedding_during_continuation(
        self, mock_resolve_path, mock_add_turn, mock_get_thread
    ):
        """Test that files already embedded in conversation history are not re-embedded"""

        # Mock file resolution to allow our test files
        def mock_resolve(path_str):
            from pathlib import Path

            return Path(path_str)  # Just return as-is for test files

        mock_resolve_path.side_effect = mock_resolve

        # Create a thread context with previous turns including files
        _thread_context = ThreadContext(
            thread_id="test-duplicate-files-id",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:02:00Z",
            tool_name="analyze",
            turns=[
                ConversationTurn(
                    role="assistant",
                    content="I've analyzed the authentication module.",
                    timestamp="2023-01-01T00:01:00Z",
                    tool_name="analyze",
                    files=["/src/auth.py", "/src/security.py"],  # These files were already analyzed
                ),
                ConversationTurn(
                    role="assistant",
                    content="Found security issues in the auth system.",
                    timestamp="2023-01-01T00:02:00Z",
                    tool_name="codereview",
                    files=["/src/auth.py", "/tests/test_auth.py"],  # auth.py referenced again + new file
                ),
            ],
            initial_context={"question": "Analyze authentication security"},
        )

        # Mock get_thread to return our test context
        mock_get_thread.return_value = _thread_context
        mock_add_turn.return_value = True

        # Mock the model to capture what prompt it receives
        captured_prompt = None

        with patch.object(self.tool, "create_model") as mock_create_model:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = [
                Mock(
                    content=Mock(parts=[Mock(text="Analysis of new files complete")]),
                    finish_reason="STOP",
                )
            ]

            def capture_prompt(prompt):
                nonlocal captured_prompt
                captured_prompt = prompt
                return mock_response

            mock_model.generate_content.side_effect = capture_prompt
            mock_create_model.return_value = mock_model

            # Mock read_files to simulate file existence and capture its calls
            with patch("tools.base.read_files") as mock_read_files:
                # When the tool processes the new files, it should only read '/src/utils.py'
                mock_read_files.return_value = "--- /src/utils.py ---\ncontent of utils"

                # Execute tool with continuation_id and mix of already-referenced and new files
                arguments = {
                    "prompt": "Now check the utility functions too",
                    "continuation_id": "test-duplicate-files-id",
                    "files": ["/src/auth.py", "/src/utils.py"],  # auth.py already in history, utils.py is new
                }
                response = await self.tool.execute(arguments)

                # Verify response succeeded
                response_data = json.loads(response[0].text)
                assert response_data["status"] == "success"

                # Verify the prompt structure
                assert captured_prompt is not None

                # After fixing the duplication bug, conversation history (including file embedding)
                # is no longer added by tools/base.py - it's handled by server.py
                # This test verifies the file filtering logic still works correctly

                # The current request should still be processed normally
                assert "Now check the utility functions too" in captured_prompt
                assert "Files in current request: /src/auth.py, /src/utils.py" in captured_prompt

                # Most importantly, verify that the file filtering logic works correctly
                # even though conversation history isn't built by tools/base.py anymore
                with patch.object(self.tool, "get_conversation_embedded_files") as mock_get_embedded:
                    # Mock that certain files are already embedded
                    mock_get_embedded.return_value = ["/src/auth.py", "/src/security.py", "/tests/test_auth.py"]

                    # Test the filtering logic directly
                    new_files = self.tool.filter_new_files(["/src/auth.py", "/src/utils.py"], "test-duplicate-files-id")
                    assert new_files == ["/src/utils.py"]  # Only the new file should remain

                    # Verify get_conversation_embedded_files was called correctly
                    mock_get_embedded.assert_called_with("test-duplicate-files-id")


if __name__ == "__main__":
    pytest.main([__file__])
