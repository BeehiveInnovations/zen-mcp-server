"""
Test to verify that precommit tool handles line numbers correctly:
- Diffs should NOT have line numbers (they have their own diff markers)
- Additional context files SHOULD have line numbers
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.precommit import Precommit, PrecommitRequest


class TestPrecommitLineNumbers:
    """Test that precommit correctly handles line numbers for diffs vs context files."""

    @pytest.fixture
    def tool(self):
        """Create a Precommit tool instance."""
        return Precommit()

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider."""
        provider = MagicMock()
        provider.get_provider_type.return_value.value = "test"

        # Mock the model response
        model_response = MagicMock()
        model_response.content = "Test review response"
        model_response.usage = {"total_tokens": 100}
        model_response.metadata = {"finish_reason": "stop"}
        model_response.friendly_name = "test-model"

        provider.generate_content = AsyncMock(return_value=model_response)
        provider.get_capabilities.return_value = MagicMock(
            context_window=200000,
            temperature_constraint=MagicMock(
                validate=lambda x: True, get_corrected_value=lambda x: x, get_description=lambda: "0.0 to 1.0"
            ),
        )
        provider.supports_thinking_mode.return_value = False

        return provider

    @pytest.mark.asyncio
    async def test_diffs_have_no_line_numbers_but_context_files_do(self, tool, mock_provider, tmp_path):
        """Test that git diffs don't have line numbers but context files do."""
        # Use the workspace root for test files
        import tempfile

        test_workspace = tempfile.mkdtemp(prefix="test_precommit_")

        # Create a context file in the workspace
        context_file = os.path.join(test_workspace, "context.py")
        with open(context_file, "w") as f:
            f.write(
                """# This is a context file
def context_function():
    return "This should have line numbers"
"""
            )

        # Mock git commands to return predictable output
        def mock_run_git_command(repo_path, command):
            if command == ["status", "--porcelain"]:
                return True, " M example.py"
            elif command == ["diff", "--name-only"]:
                return True, "example.py"
            elif command == ["diff", "--", "example.py"]:
                # Return a sample diff - this should NOT have line numbers added
                return (
                    True,
                    """diff --git a/example.py b/example.py
index 1234567..abcdefg 100644
--- a/example.py
+++ b/example.py
@@ -1,5 +1,8 @@
 def hello():
-    print("Hello, World!")
+    print("Hello, Universe!")  # Changed this line

 def goodbye():
     print("Goodbye!")
+
+def new_function():
+    print("This is new")
""",
                )
            else:
                return True, ""

        # Create request with context file
        request = PrecommitRequest(
            path=test_workspace,
            prompt="Review my changes",
            files=[context_file],  # This should get line numbers
            include_staged=False,
            include_unstaged=True,
        )

        # Mock the tool's provider and git functions
        with (
            patch.object(tool, "get_model_provider", return_value=mock_provider),
            patch("tools.precommit.run_git_command", side_effect=mock_run_git_command),
            patch("tools.precommit.find_git_repositories", return_value=[test_workspace]),
            patch(
                "tools.precommit.get_git_status",
                return_value={
                    "branch": "main",
                    "ahead": 0,
                    "behind": 0,
                    "staged_files": [],
                    "unstaged_files": ["example.py"],
                    "untracked_files": [],
                },
            ),
        ):

            # Prepare the prompt
            prompt = await tool.prepare_prompt(request)

            # Print prompt sections for debugging if test fails
            # print("\n=== PROMPT OUTPUT ===")
            # print(prompt)
            # print("=== END PROMPT ===\n")

            # Verify that diffs don't have line numbers
            assert "--- BEGIN DIFF:" in prompt
            assert "--- END DIFF:" in prompt

            # Check that the diff content doesn't have line number markers (│)
            # Find diff section
            diff_start = prompt.find("--- BEGIN DIFF:")
            diff_end = prompt.find("--- END DIFF:", diff_start) + len("--- END DIFF:")
            if diff_start != -1 and diff_end > diff_start:
                diff_section = prompt[diff_start:diff_end]
                assert "│" not in diff_section, "Diff section should NOT have line number markers"

                # Verify the diff has its own line markers
                assert "@@ -1,5 +1,8 @@" in diff_section
                assert '-    print("Hello, World!")' in diff_section
                assert '+    print("Hello, Universe!")  # Changed this line' in diff_section

            # Verify that context files DO have line numbers
            if "--- BEGIN FILE:" in prompt:
                # Extract context file section
                file_start = prompt.find("--- BEGIN FILE:")
                file_end = prompt.find("--- END FILE:", file_start) + len("--- END FILE:")
                if file_start != -1 and file_end > file_start:
                    context_section = prompt[file_start:file_end]

                    # Context files should have line number markers
                    assert "│" in context_section, "Context file section SHOULD have line number markers"

                    # Verify specific line numbers in context file
                    assert "1│ # This is a context file" in context_section
                    assert "2│ def context_function():" in context_section
                    assert '3│     return "This should have line numbers"' in context_section

    def test_base_tool_wants_line_numbers_by_default(self, tool):
        """Verify that the base tool configuration wants line numbers by default."""
        # The precommit tool should inherit the base behavior
        assert tool.wants_line_numbers_by_default(), "Base tool should want line numbers by default"
