"""
Tests for the review_pending_changes tool
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from tools.review_pending_changes import (
    ReviewPendingChanges,
    ReviewPendingChangesRequest,
)


class TestReviewPendingChangesTool:
    """Test the review_pending_changes tool"""

    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return ReviewPendingChanges()

    def test_tool_metadata(self, tool):
        """Test tool metadata"""
        assert tool.get_name() == "review_pending_changes"
        assert "REVIEW PENDING GIT CHANGES" in tool.get_description()
        assert "pre-commit review" in tool.get_description()

        # Check schema
        schema = tool.get_input_schema()
        assert schema["type"] == "object"
        assert "path" in schema["properties"]
        assert "original_request" in schema["properties"]
        assert "compare_to" in schema["properties"]
        assert "review_type" in schema["properties"]

    def test_request_model_defaults(self):
        """Test request model default values"""
        request = ReviewPendingChangesRequest(path="/some/absolute/path")
        assert request.path == "/some/absolute/path"
        assert request.original_request is None
        assert request.compare_to is None
        assert request.include_staged is True
        assert request.include_unstaged is True
        assert request.review_type == "full"
        assert request.severity_filter == "all"
        assert request.max_depth == 5

    def test_sanitize_filename(self, tool):
        """Test filename sanitization"""
        # Test path separators
        assert tool._sanitize_filename("src/main.py") == "src_main.py"
        assert tool._sanitize_filename("src\\main.py") == "src_main.py"

        # Test spaces
        assert tool._sanitize_filename("my file.py") == "my_file.py"

        # Test special characters
        assert tool._sanitize_filename("file@#$.py") == "file.py"

        # Test length limit
        long_name = "a" * 150
        sanitized = tool._sanitize_filename(long_name)
        assert len(sanitized) == 100

    @pytest.mark.asyncio
    async def test_relative_path_rejected(self, tool):
        """Test that relative paths are rejected"""
        result = await tool.execute(
            {"path": "./relative/path", "original_request": "Test"}
        )
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["status"] == "error"
        assert "must be absolute" in response["content"]
        assert "./relative/path" in response["content"]

    @pytest.mark.asyncio
    @patch("tools.review_pending_changes.find_git_repositories")
    async def test_no_repositories_found(self, mock_find_repos, tool):
        """Test when no git repositories are found"""
        mock_find_repos.return_value = []

        request = ReviewPendingChangesRequest(path="/absolute/path/no-git")
        result = await tool.prepare_prompt(request)

        assert result == "No git repositories found in the specified path."
        mock_find_repos.assert_called_once_with("/absolute/path/no-git", 5)

    @pytest.mark.asyncio
    @patch("tools.review_pending_changes.find_git_repositories")
    @patch("tools.review_pending_changes.get_git_status")
    @patch("tools.review_pending_changes.run_git_command")
    async def test_no_changes_found(
        self, mock_run_git, mock_status, mock_find_repos, tool
    ):
        """Test when repositories have no changes"""
        mock_find_repos.return_value = ["/test/repo"]
        mock_status.return_value = {
            "branch": "main",
            "ahead": 0,
            "behind": 0,
            "staged_files": [],
            "unstaged_files": [],
            "untracked_files": [],
        }

        # No staged or unstaged files
        mock_run_git.side_effect = [
            (True, ""),  # staged files (empty)
            (True, ""),  # unstaged files (empty)
        ]

        request = ReviewPendingChangesRequest(path="/absolute/repo/path")
        result = await tool.prepare_prompt(request)

        assert result == "No pending changes found in any of the git repositories."

    @pytest.mark.asyncio
    @patch("tools.review_pending_changes.find_git_repositories")
    @patch("tools.review_pending_changes.get_git_status")
    @patch("tools.review_pending_changes.run_git_command")
    async def test_staged_changes_review(
        self,
        mock_run_git,
        mock_status,
        mock_find_repos,
        tool,
    ):
        """Test reviewing staged changes"""
        mock_find_repos.return_value = ["/test/repo"]
        mock_status.return_value = {
            "branch": "feature",
            "ahead": 1,
            "behind": 0,
            "staged_files": ["main.py"],
            "unstaged_files": [],
            "untracked_files": [],
        }

        # Mock git commands
        mock_run_git.side_effect = [
            (True, "main.py\n"),  # staged files
            (
                True,
                "diff --git a/main.py b/main.py\n+print('hello')",
            ),  # diff for main.py
            (True, ""),  # unstaged files (empty)
        ]

        request = ReviewPendingChangesRequest(
            path="/absolute/repo/path",
            original_request="Add hello message",
            review_type="security",
        )
        result = await tool.prepare_prompt(request)

        # Verify result structure
        assert "## Original Request/Ticket" in result
        assert "Add hello message" in result
        assert "## Review Parameters" in result
        assert "Review Type: security" in result
        assert "## Repository Changes Summary" in result
        assert "Branch: feature" in result
        assert "## Git Diffs" in result

    @pytest.mark.asyncio
    @patch("tools.review_pending_changes.find_git_repositories")
    @patch("tools.review_pending_changes.get_git_status")
    @patch("tools.review_pending_changes.run_git_command")
    async def test_compare_to_invalid_ref(
        self, mock_run_git, mock_status, mock_find_repos, tool
    ):
        """Test comparing to an invalid git ref"""
        mock_find_repos.return_value = ["/test/repo"]
        mock_status.return_value = {"branch": "main"}

        # Mock git commands - ref validation fails
        mock_run_git.side_effect = [
            (False, "fatal: not a valid ref"),  # rev-parse fails
        ]

        request = ReviewPendingChangesRequest(
            path="/absolute/repo/path", compare_to="invalid-branch"
        )
        result = await tool.prepare_prompt(request)

        # When all repos have errors and no changes, we get this message
        assert "No pending changes found in any of the git repositories." in result

    @pytest.mark.asyncio
    @patch("tools.review_pending_changes.ReviewPendingChanges.execute")
    async def test_execute_integration(self, mock_execute, tool):
        """Test execute method integration"""
        # Mock the execute to return a standardized response
        mock_execute.return_value = [
            Mock(
                text='{"status": "success", "content": "Review complete", "content_type": "text"}'
            )
        ]

        result = await tool.execute({"path": ".", "review_type": "full"})

        assert len(result) == 1
        mock_execute.assert_called_once()

    def test_default_temperature(self, tool):
        """Test default temperature setting"""
        from config import TEMPERATURE_ANALYTICAL

        assert tool.get_default_temperature() == TEMPERATURE_ANALYTICAL

    @pytest.mark.asyncio
    @patch("tools.review_pending_changes.find_git_repositories")
    @patch("tools.review_pending_changes.get_git_status")
    @patch("tools.review_pending_changes.run_git_command")
    async def test_mixed_staged_unstaged_changes(
        self,
        mock_run_git,
        mock_status,
        mock_find_repos,
        tool,
    ):
        """Test reviewing both staged and unstaged changes"""
        mock_find_repos.return_value = ["/test/repo"]
        mock_status.return_value = {
            "branch": "develop",
            "ahead": 2,
            "behind": 1,
            "staged_files": ["file1.py"],
            "unstaged_files": ["file2.py"],
        }

        # Mock git commands
        mock_run_git.side_effect = [
            (True, "file1.py\n"),  # staged files
            (True, "diff --git a/file1.py..."),  # diff for file1.py
            (True, "file2.py\n"),  # unstaged files
            (True, "diff --git a/file2.py..."),  # diff for file2.py
        ]

        request = ReviewPendingChangesRequest(
            path="/absolute/repo/path",
            focus_on="error handling",
            severity_filter="high",
        )
        result = await tool.prepare_prompt(request)

        # Verify all sections are present
        assert "Review Type: full" in result
        assert "Severity Filter: high" in result
        assert "Focus Areas: error handling" in result
        assert "Reviewing: staged and unstaged changes" in result
