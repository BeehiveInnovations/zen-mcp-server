"""
Regression tests to ensure normal prompt handling still works after large prompt changes.

This test module verifies that all tools continue to work correctly with
normal-sized prompts after implementing the large prompt handling feature.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.analyze import AnalyzeTool
from tools.chat import ChatTool
from tools.debug_issue import DebugIssueTool
from tools.review_changes import ReviewChanges
from tools.review_code import ReviewCodeTool
from tools.think_deeper import ThinkDeeperTool


class TestPromptRegression:
    """Regression test suite for normal prompt handling."""

    @pytest.fixture
    def mock_model_response(self):
        """Create a mock model response."""

        def _create_response(text="Test response"):
            mock_response = MagicMock()
            mock_response.candidates = [
                MagicMock(
                    content=MagicMock(parts=[MagicMock(text=text)]),
                    finish_reason="STOP",
                )
            ]
            return mock_response

        return _create_response

    @pytest.mark.asyncio
    async def test_chat_normal_prompt(self, mock_model_response):
        """Test chat tool with normal prompt."""
        tool = ChatTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response("This is a helpful response about Python.")
            mock_create_model.return_value = mock_model

            result = await tool.execute({"prompt": "Explain Python decorators"})

            assert len(result) == 1
            output = json.loads(result[0].text)
            assert output["status"] == "success"
            assert "helpful response about Python" in output["content"]

            # Verify model was called
            mock_model.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_with_files(self, mock_model_response):
        """Test chat tool with files parameter."""
        tool = ChatTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response()
            mock_create_model.return_value = mock_model

            # Mock file reading
            with patch("tools.chat.read_files") as mock_read_files:
                mock_read_files.return_value = "File content here"

                result = await tool.execute({"prompt": "Analyze this code", "files": ["/path/to/file.py"]})

                assert len(result) == 1
                output = json.loads(result[0].text)
                assert output["status"] == "success"
                mock_read_files.assert_called_once_with(["/path/to/file.py"])

    @pytest.mark.asyncio
    async def test_think_deeper_normal_analysis(self, mock_model_response):
        """Test think_deeper tool with normal analysis."""
        tool = ThinkDeeperTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response(
                "Here's a deeper analysis with edge cases..."
            )
            mock_create_model.return_value = mock_model

            result = await tool.execute(
                {
                    "current_analysis": "I think we should use a cache for performance",
                    "problem_context": "Building a high-traffic API",
                    "focus_areas": ["scalability", "reliability"],
                }
            )

            assert len(result) == 1
            output = json.loads(result[0].text)
            assert output["status"] == "success"
            assert "Extended Analysis by Gemini" in output["content"]
            assert "deeper analysis" in output["content"]

    @pytest.mark.asyncio
    async def test_review_code_normal_review(self, mock_model_response):
        """Test review_code tool with normal inputs."""
        tool = ReviewCodeTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response(
                "Found 3 issues: 1) Missing error handling..."
            )
            mock_create_model.return_value = mock_model

            # Mock file reading
            with patch("tools.review_code.read_files") as mock_read_files:
                mock_read_files.return_value = "def main(): pass"

                result = await tool.execute(
                    {
                        "files": ["/path/to/code.py"],
                        "review_type": "security",
                        "focus_on": "Look for SQL injection vulnerabilities",
                        "context": "Test code review for validation purposes",
                    }
                )

                assert len(result) == 1
                output = json.loads(result[0].text)
                assert output["status"] == "success"
                assert "Found 3 issues" in output["content"]

    @pytest.mark.asyncio
    async def test_review_changes_normal_request(self, mock_model_response):
        """Test review_changes tool with normal original_request."""
        tool = ReviewChanges()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response(
                "Changes look good, implementing feature as requested..."
            )
            mock_create_model.return_value = mock_model

            # Mock git operations
            with patch("tools.review_changes.find_git_repositories") as mock_find_repos:
                with patch("tools.review_changes.get_git_status") as mock_git_status:
                    mock_find_repos.return_value = ["/path/to/repo"]
                    mock_git_status.return_value = {
                        "modified": ["file.py"],
                        "untracked": [],
                    }

                    result = await tool.execute(
                        {
                            "path": "/path/to/repo",
                            "original_request": "Add user authentication feature with JWT tokens",
                        }
                    )

                    assert len(result) == 1
                    output = json.loads(result[0].text)
                    assert output["status"] == "success"

    @pytest.mark.asyncio
    async def test_debug_issue_normal_error(self, mock_model_response):
        """Test debug_issue tool with normal error description."""
        tool = DebugIssueTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response(
                "Root cause: The variable is undefined. Fix: Initialize it..."
            )
            mock_create_model.return_value = mock_model

            result = await tool.execute(
                {
                    "error_description": "TypeError: Cannot read property 'name' of undefined",
                    "error_context": "at line 42 in user.js\n  console.log(user.name)",
                    "runtime_info": "Node.js v16.14.0",
                }
            )

            assert len(result) == 1
            output = json.loads(result[0].text)
            assert output["status"] == "success"
            assert "Debug Analysis" in output["content"]
            assert "Root cause" in output["content"]

    @pytest.mark.asyncio
    async def test_analyze_normal_question(self, mock_model_response):
        """Test analyze tool with normal question."""
        tool = AnalyzeTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response(
                "The code follows MVC pattern with clear separation..."
            )
            mock_create_model.return_value = mock_model

            # Mock file reading
            with patch("tools.analyze.read_files") as mock_read_files:
                mock_read_files.return_value = "class UserController: ..."

                result = await tool.execute(
                    {
                        "files": ["/path/to/project"],
                        "question": "What design patterns are used in this codebase?",
                        "analysis_type": "architecture",
                    }
                )

                assert len(result) == 1
                output = json.loads(result[0].text)
                assert output["status"] == "success"
                assert "MVC pattern" in output["content"]

    @pytest.mark.asyncio
    async def test_empty_optional_fields(self, mock_model_response):
        """Test tools work with empty optional fields."""
        tool = ChatTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response()
            mock_create_model.return_value = mock_model

            # Test with no files parameter
            result = await tool.execute({"prompt": "Hello"})

            assert len(result) == 1
            output = json.loads(result[0].text)
            assert output["status"] == "success"

    @pytest.mark.asyncio
    async def test_thinking_modes_work(self, mock_model_response):
        """Test that thinking modes are properly passed through."""
        tool = ChatTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response()
            mock_create_model.return_value = mock_model

            result = await tool.execute({"prompt": "Test", "thinking_mode": "high", "temperature": 0.8})

            assert len(result) == 1
            output = json.loads(result[0].text)
            assert output["status"] == "success"

            # Verify create_model was called with correct parameters
            mock_create_model.assert_called_once()
            call_args = mock_create_model.call_args
            assert call_args[0][2] == "high"  # thinking_mode
            assert call_args[0][1] == 0.8  # temperature

    @pytest.mark.asyncio
    async def test_special_characters_in_prompts(self, mock_model_response):
        """Test prompts with special characters work correctly."""
        tool = ChatTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response()
            mock_create_model.return_value = mock_model

            special_prompt = 'Test with "quotes" and\nnewlines\tand tabs'
            result = await tool.execute({"prompt": special_prompt})

            assert len(result) == 1
            output = json.loads(result[0].text)
            assert output["status"] == "success"

    @pytest.mark.asyncio
    async def test_mixed_file_paths(self, mock_model_response):
        """Test handling of various file path formats."""
        tool = AnalyzeTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response()
            mock_create_model.return_value = mock_model

            with patch("tools.analyze.read_files") as mock_read_files:
                mock_read_files.return_value = "Content"

                result = await tool.execute(
                    {
                        "files": [
                            "/absolute/path/file.py",
                            "/Users/name/project/src/",
                            "/home/user/code.js",
                        ],
                        "question": "Analyze these files",
                    }
                )

                assert len(result) == 1
                output = json.loads(result[0].text)
                assert output["status"] == "success"
                mock_read_files.assert_called_once()

    @pytest.mark.asyncio
    async def test_unicode_content(self, mock_model_response):
        """Test handling of unicode content in prompts."""
        tool = ChatTool()

        with patch.object(tool, "create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_model_response()
            mock_create_model.return_value = mock_model

            unicode_prompt = "Explain this: 你好世界 مرحبا بالعالم"
            result = await tool.execute({"prompt": unicode_prompt})

            assert len(result) == 1
            output = json.loads(result[0].text)
            assert output["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
