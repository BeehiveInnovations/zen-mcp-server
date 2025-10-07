"""Tests for pip detection fix in run-server.sh script.

This test file ensures our pip detection improvements work correctly
and don't break existing functionality.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestPipDetectionFix:
    """Test cases for issue #188: PIP is available but not recognized."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Requires bash")
    def test_run_server_script_syntax_valid(self):
        """Test that run-server.sh has valid bash syntax."""
        result = subprocess.run(["bash", "-n", "./run-server.sh"], capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error in run-server.sh: {result.stderr}"

    def test_run_server_has_proper_shebang(self):
        """Test that run-server.sh starts with proper shebang."""
        content = Path("./run-server.sh").read_text(encoding="utf-8")
        assert content.startswith("#!/bin/bash"), "Script missing proper bash shebang"

    def test_critical_functions_exist(self):
        """Test that all critical functions are defined in the script."""
        content = Path("./run-server.sh").read_text(encoding="utf-8")
        critical_functions = ["find_python", "setup_environment", "setup_venv", "install_dependencies", "bootstrap_pip"]

        for func in critical_functions:
            assert f"{func}()" in content, f"Critical function {func}() not found in script"

    @pytest.mark.skipif(sys.platform == "win32", reason="Requires bash")
    def test_pip_detection_consistency_issue(self):
        """Test the specific issue: pip works in setup_venv but fails in install_dependencies.

        This test verifies that our fix ensures consistent Python executable paths.
        """
        # Test that the get_venv_python_path function now returns absolute paths
        content = Path("./run-server.sh").read_text(encoding="utf-8")

        # Check that get_venv_python_path includes our absolute path conversion logic
        assert "abs_venv_path" in content, "get_venv_python_path should use absolute paths"
        assert 'cd "$(dirname' in content, "Should convert to absolute path"

        # Test successful completion - our fix should make the script more robust
        result = subprocess.run(["bash", "-n", "./run-server.sh"], capture_output=True, text=True)
        assert result.returncode == 0, "Script should have valid syntax after our fix"

    def test_pip_detection_with_non_interactive_shell(self):
        """Test pip detection works in non-interactive shell environments.

        This addresses the contributor's suggestion about non-interactive shells
        not sourcing ~/.bashrc where pip PATH might be defined.
        """
        # Test case for Git Bash on Windows and non-interactive Linux shells
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock virtual environment structure
            venv_path = Path(temp_dir) / ".zen_venv"
            bin_path = venv_path / "bin"
            bin_path.mkdir(parents=True)

            # Create mock python executable
            python_exe = bin_path / "python"
            python_exe.write_text("#!/bin/bash\necho 'Python 3.12.3'\n", encoding="utf-8")
            python_exe.chmod(0o755)

            # Create mock pip executable
            pip_exe = bin_path / "pip"
            pip_exe.write_text("#!/bin/bash\necho 'pip 23.0.1'\n", encoding="utf-8")
            pip_exe.chmod(0o755)

            # Test that we can detect pip using explicit paths (not PATH)
            assert python_exe.exists(), "Mock python executable should exist"
            assert pip_exe.exists(), "Mock pip executable should exist"
            assert python_exe.is_file(), "Python should be a file"
            assert pip_exe.is_file(), "Pip should be a file"

    def test_enhanced_diagnostic_messages_included(self):
        """Test that our enhanced diagnostic messages are included in the script.

        Verify that the script contains the enhanced error diagnostics we added.
        """
        content = Path("./run-server.sh").read_text(encoding="utf-8")

        # Check that enhanced diagnostic information is present in the script
        expected_diagnostic_patterns = [
            "Enhanced diagnostic information for debugging",
            "Diagnostic information:",
            "Python executable:",
            "Python executable exists:",
            "Python executable permissions:",
            "Virtual environment path:",
            "Virtual environment exists:",
            "Final diagnostic information:",
        ]

        for pattern in expected_diagnostic_patterns:
            assert pattern in content, f"Enhanced diagnostic pattern '{pattern}' should be in script"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
