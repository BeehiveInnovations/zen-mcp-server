"""
Tests for large prompt handling functionality.

This test module verifies that the MCP server correctly handles
prompts that exceed the 50,000 character limit by requesting
Claude to save them to a file and resend.
"""

import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from mcp.types import TextContent

from config import MCP_PROMPT_SIZE_LIMIT
from tools.analyze import AnalyzeTool
from tools.chat import ChatTool
from tools.codereview import CodeReviewTool
from tools.debug import DebugIssueTool
from tools.precommit import Precommit
from tools.thinkdeep import ThinkDeepTool


class TestLargePromptHandling:
    """Test suite for large prompt handling across all tools."""

    @pytest.fixture
    def large_prompt(self):
        """Create a prompt larger than MCP_PROMPT_SIZE_LIMIT characters."""
        return "x" * (MCP_PROMPT_SIZE_LIMIT + 1000)

    @pytest.fixture
    def normal_prompt(self):
        """Create a normal-sized prompt."""
        return "This is a normal prompt that should work fine."

    @pytest.fixture
    def temp_prompt_file(self, large_prompt):
        """Create a temporary prompt.txt file with large content."""
        # Create temp file with exact name "prompt.txt"
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "prompt.txt")
        with open(file_path, "w") as f:
            f.write(large_prompt)
        return file_path

    @pytest.mark.asyncio
    async def test_chat_large_prompt_detection(self, large_prompt):
        """Test that chat tool detects large prompts."""
        tool = ChatTool()
        result = await tool.execute({"prompt": large_prompt})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

        output = json.loads(result[0].text)
        assert output["status"] == "requires_file_prompt"
        assert f"{MCP_PROMPT_SIZE_LIMIT:,} characters" in output["content"]
        assert output["metadata"]["prompt_size"] == len(large_prompt)
        assert output["metadata"]["limit"] == MCP_PROMPT_SIZE_LIMIT

    @pytest.mark.asyncio
    async def test_chat_normal_prompt_works(self, normal_prompt):
        """Test that chat tool works normally with regular prompts."""
        tool = ChatTool()

        # Mock the model to avoid actual API calls
        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.candidates = [
                MagicMock(
                    content=MagicMock(parts=[MagicMock(text="This is a test response")]),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            result = await tool.execute({"prompt": normal_prompt})

            assert len(result) == 1
            output = json.loads(result[0].text)
            assert output["status"] == "success"
            assert "This is a test response" in output["content"]

    @pytest.mark.asyncio
    async def test_chat_prompt_file_handling(self, temp_prompt_file, large_prompt):
        """Test that chat tool correctly handles prompt.txt files."""
        tool = ChatTool()

        # Mock the model
        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.candidates = [
                MagicMock(
                    content=MagicMock(parts=[MagicMock(text="Processed large prompt")]),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            # Mock read_file_content to avoid security checks
            with patch("tools.base.read_file_content") as mock_read_file:
                mock_read_file.return_value = (
                    large_prompt,
                    1000,
                )  # Return tuple like real function

                # Execute with empty prompt and prompt.txt file
                result = await tool.execute({"prompt": "", "files": [temp_prompt_file]})

                assert len(result) == 1
                output = json.loads(result[0].text)
                assert output["status"] == "success"

                # Verify read_file_content was called with the prompt file
                mock_read_file.assert_called_once_with(temp_prompt_file)

                # Verify the large content was used
                call_args = mock_model.generate_content.call_args[0][0]
                assert large_prompt in call_args

        # Cleanup
        temp_dir = os.path.dirname(temp_prompt_file)
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_thinkdeep_large_analysis(self, large_prompt):
        """Test that thinkdeep tool detects large current_analysis."""
        tool = ThinkDeepTool()
        result = await tool.execute({"current_analysis": large_prompt})

        assert len(result) == 1
        output = json.loads(result[0].text)
        assert output["status"] == "requires_file_prompt"

    @pytest.mark.asyncio
    async def test_codereview_large_focus(self, large_prompt):
        """Test that codereview tool detects large focus_on field."""
        tool = CodeReviewTool()
        result = await tool.execute(
            {
                "files": ["/some/file.py"],
                "focus_on": large_prompt,
                "context": "Test code review for validation purposes",
            }
        )

        assert len(result) == 1
        output = json.loads(result[0].text)
        assert output["status"] == "requires_file_prompt"

    @pytest.mark.asyncio
    async def test_review_changes_large_original_request(self, large_prompt):
        """Test that review_changes tool detects large original_request."""
        tool = Precommit()
        result = await tool.execute({"path": "/some/path", "original_request": large_prompt})

        assert len(result) == 1
        output = json.loads(result[0].text)
        assert output["status"] == "requires_file_prompt"

    @pytest.mark.asyncio
    async def test_debug_large_error_description(self, large_prompt):
        """Test that debug tool detects large error_description."""
        tool = DebugIssueTool()
        result = await tool.execute({"error_description": large_prompt})

        assert len(result) == 1
        output = json.loads(result[0].text)
        assert output["status"] == "requires_file_prompt"

    @pytest.mark.asyncio
    async def test_debug_large_error_context(self, large_prompt, normal_prompt):
        """Test that debug tool detects large error_context."""
        tool = DebugIssueTool()
        result = await tool.execute({"error_description": normal_prompt, "error_context": large_prompt})

        assert len(result) == 1
        output = json.loads(result[0].text)
        assert output["status"] == "requires_file_prompt"

    @pytest.mark.asyncio
    async def test_analyze_large_question(self, large_prompt):
        """Test that analyze tool detects large question."""
        tool = AnalyzeTool()
        result = await tool.execute({"files": ["/some/file.py"], "question": large_prompt})

        assert len(result) == 1
        output = json.loads(result[0].text)
        assert output["status"] == "requires_file_prompt"

    @pytest.mark.asyncio
    async def test_multiple_files_with_prompt_txt(self, temp_prompt_file):
        """Test handling of prompt.txt alongside other files."""
        tool = ChatTool()
        other_file = "/some/other/file.py"

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.candidates = [
                MagicMock(
                    content=MagicMock(parts=[MagicMock(text="Success")]),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            # Mock the centralized file preparation method to avoid file system access
            with patch.object(tool, "_prepare_file_content_for_prompt") as mock_prepare_files:
                mock_prepare_files.return_value = "File content"

                await tool.execute({"prompt": "", "files": [temp_prompt_file, other_file]})

                # Verify prompt.txt was removed from files list
                mock_prepare_files.assert_called_once()
                files_arg = mock_prepare_files.call_args[0][0]
                assert len(files_arg) == 1
                assert files_arg[0] == other_file

        temp_dir = os.path.dirname(temp_prompt_file)
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_boundary_case_exactly_at_limit(self):
        """Test prompt exactly at MCP_PROMPT_SIZE_LIMIT characters (should pass)."""
        tool = ChatTool()
        exact_prompt = "x" * MCP_PROMPT_SIZE_LIMIT

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.candidates = [
                MagicMock(
                    content=MagicMock(parts=[MagicMock(text="Success")]),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            result = await tool.execute({"prompt": exact_prompt})
            output = json.loads(result[0].text)
            assert output["status"] == "success"

    @pytest.mark.asyncio
    async def test_boundary_case_just_over_limit(self):
        """Test prompt just over MCP_PROMPT_SIZE_LIMIT characters (should trigger file request)."""
        tool = ChatTool()
        over_prompt = "x" * (MCP_PROMPT_SIZE_LIMIT + 1)

        result = await tool.execute({"prompt": over_prompt})
        output = json.loads(result[0].text)
        assert output["status"] == "requires_file_prompt"

    @pytest.mark.asyncio
    async def test_empty_prompt_no_file(self):
        """Test empty prompt without prompt.txt file."""
        tool = ChatTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.candidates = [
                MagicMock(
                    content=MagicMock(parts=[MagicMock(text="Success")]),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            result = await tool.execute({"prompt": ""})
            output = json.loads(result[0].text)
            assert output["status"] == "success"

    @pytest.mark.asyncio
    async def test_prompt_file_read_error(self):
        """Test handling when prompt.txt can't be read."""
        tool = ChatTool()
        bad_file = "/nonexistent/prompt.txt"

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.candidates = [
                MagicMock(
                    content=MagicMock(parts=[MagicMock(text="Success")]),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            # Should continue with empty prompt when file can't be read
            result = await tool.execute({"prompt": "", "files": [bad_file]})
            output = json.loads(result[0].text)
            assert output["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
