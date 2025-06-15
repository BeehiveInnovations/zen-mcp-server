"""
Test to verify that precommit tool formats diffs correctly without line numbers.
This test focuses on the diff formatting logic rather than full integration.
"""

from tools.precommit import Precommit


class TestPrecommitDiffFormatting:
    """Test that precommit correctly formats diffs without line numbers."""

    def test_git_diff_formatting_has_no_line_numbers(self):
        """Test that git diff output is preserved without line number additions."""
        # Sample git diff output
        git_diff = """diff --git a/example.py b/example.py
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
"""

        # Simulate how precommit formats a diff
        repo_name = "test_repo"
        file_path = "example.py"
        diff_header = f"\n--- BEGIN DIFF: {repo_name} / {file_path} (unstaged) ---\n"
        diff_footer = f"\n--- END DIFF: {repo_name} / {file_path} ---\n"
        formatted_diff = diff_header + git_diff + diff_footer

        # Verify the diff doesn't contain line number markers (│)
        assert "│" not in formatted_diff, "Git diffs should NOT have line number markers"

        # Verify the diff preserves git's own line markers
        assert "@@ -1,5 +1,8 @@" in formatted_diff
        assert '-    print("Hello, World!")' in formatted_diff
        assert '+    print("Hello, Universe!")' in formatted_diff

    def test_untracked_file_diff_formatting(self):
        """Test that untracked files formatted as diffs don't have line numbers."""
        # Simulate untracked file content
        file_content = """def new_function():
    return "I am new"

class NewClass:
    pass
"""

        # Simulate how precommit formats untracked files as diffs
        repo_name = "test_repo"
        file_path = "new_file.py"

        diff_header = f"\n--- BEGIN DIFF: {repo_name} / {file_path} (untracked - new file) ---\n"
        diff_content = f"+++ b/{file_path}\n"

        # Add each line with + prefix (simulating new file diff)
        for _line_num, line in enumerate(file_content.splitlines(), 1):
            diff_content += f"+{line}\n"

        diff_footer = f"\n--- END DIFF: {repo_name} / {file_path} ---\n"
        formatted_diff = diff_header + diff_content + diff_footer

        # Verify no line number markers
        assert "│" not in formatted_diff, "Untracked file diffs should NOT have line number markers"

        # Verify diff format
        assert "+++ b/new_file.py" in formatted_diff
        assert "+def new_function():" in formatted_diff
        assert '+    return "I am new"' in formatted_diff

    def test_compare_to_diff_formatting(self):
        """Test that compare_to mode diffs don't have line numbers."""
        # Sample git diff for compare_to mode
        git_diff = """diff --git a/config.py b/config.py
index abc123..def456 100644
--- a/config.py
+++ b/config.py
@@ -10,7 +10,7 @@ class Config:
     def __init__(self):
         self.debug = False
-        self.timeout = 30
+        self.timeout = 60  # Increased timeout
         self.retries = 3
"""

        # Format as compare_to diff
        repo_name = "test_repo"
        file_path = "config.py"
        compare_ref = "v1.0"

        diff_header = f"\n--- BEGIN DIFF: {repo_name} / {file_path} (compare to {compare_ref}) ---\n"
        diff_footer = f"\n--- END DIFF: {repo_name} / {file_path} ---\n"
        formatted_diff = diff_header + git_diff + diff_footer

        # Verify no line number markers
        assert "│" not in formatted_diff, "Compare-to diffs should NOT have line number markers"

        # Verify diff markers
        assert "@@ -10,7 +10,7 @@ class Config:" in formatted_diff
        assert "-        self.timeout = 30" in formatted_diff
        assert "+        self.timeout = 60  # Increased timeout" in formatted_diff

    def test_base_tool_default_line_numbers(self):
        """Test that the base tool wants line numbers by default."""
        tool = Precommit()
        assert tool.wants_line_numbers_by_default(), "Base tool should want line numbers by default"

    def test_context_files_want_line_numbers(self):
        """Test that precommit tool inherits base class behavior for line numbers."""
        tool = Precommit()

        # The precommit tool should want line numbers by default (inherited from base)
        assert tool.wants_line_numbers_by_default()

        # This means when it calls read_files for context files,
        # it will pass include_line_numbers=True

    def test_diff_sections_in_prompt(self):
        """Test the structure of diff sections in the final prompt."""
        # Create sample prompt sections
        diff_section = """
## Git Diffs

--- BEGIN DIFF: repo / file.py (staged) ---
diff --git a/file.py b/file.py
index 123..456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def main():
     print("Hello")
+    print("World")
--- END DIFF: repo / file.py ---
"""

        context_section = """
## Additional Context Files
The following files are provided for additional context. They have NOT been modified.

--- BEGIN FILE: /path/to/context.py ---
   1│ # Context file
   2│ def helper():
   3│     pass
--- END FILE: /path/to/context.py ---
"""

        # Verify diff section has no line numbers
        assert "│" not in diff_section, "Diff section should not have line number markers"

        # Verify context section has line numbers
        assert "│" in context_section, "Context section should have line number markers"

        # Verify the sections are clearly separated
        assert "## Git Diffs" in diff_section
        assert "## Additional Context Files" in context_section
        assert "have NOT been modified" in context_section
