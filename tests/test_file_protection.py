"""
Test file protection mechanisms to ensure MCP doesn't scan:
1. Its own directory
2. User's home directory root
3. Excluded directories
"""

import os
from pathlib import Path
from unittest.mock import patch

from utils.file_utils import (
    MCP_SIGNATURE_FILES,
    expand_paths,
    get_user_home_directory,
    is_home_directory_root,
    is_mcp_directory,
)


class TestMCPDirectoryDetection:
    """Test MCP self-detection to prevent scanning its own code."""

    def test_detect_mcp_directory_with_all_signatures(self, tmp_path):
        """Test detection when all signature files are present."""
        # Create a fake MCP directory with signature files
        for sig_file in list(MCP_SIGNATURE_FILES)[:4]:  # Use 4 files
            if "/" in sig_file:
                (tmp_path / sig_file).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / sig_file).touch()

        assert is_mcp_directory(tmp_path) is True

    def test_no_detection_with_few_signatures(self, tmp_path):
        """Test no detection with only 1-2 signature files."""
        # Create only 2 signature files (less than threshold)
        for sig_file in list(MCP_SIGNATURE_FILES)[:2]:
            if "/" in sig_file:
                (tmp_path / sig_file).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / sig_file).touch()

        assert is_mcp_directory(tmp_path) is False

    def test_no_detection_on_regular_directory(self, tmp_path):
        """Test no detection on regular project directories."""
        # Create some random Python files
        (tmp_path / "app.py").touch()
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()

        assert is_mcp_directory(tmp_path) is False

    def test_no_detection_on_file(self, tmp_path):
        """Test no detection when path is a file, not directory."""
        file_path = tmp_path / "test.py"
        file_path.touch()

        assert is_mcp_directory(file_path) is False

    def test_mcp_directory_excluded_from_scan(self, tmp_path):
        """Test that MCP directories are excluded during path expansion."""
        # Create a project with MCP as subdirectory
        project_root = tmp_path / "my_project"
        project_root.mkdir()

        # Add some project files
        (project_root / "app.py").write_text("# My app")
        (project_root / "config.py").write_text("# Config")

        # Create MCP subdirectory
        mcp_dir = project_root / "gemini-mcp-server"
        mcp_dir.mkdir()
        for sig_file in list(MCP_SIGNATURE_FILES)[:4]:
            if "/" in sig_file:
                (mcp_dir / sig_file).parent.mkdir(parents=True, exist_ok=True)
            (mcp_dir / sig_file).write_text("# MCP file")

        # Also add a regular file to MCP dir
        (mcp_dir / "test.py").write_text("# Should not be included")

        # Scan the project - use parent as SECURITY_ROOT to avoid workspace root check
        with patch("utils.file_utils.SECURITY_ROOT", tmp_path):
            files = expand_paths([str(project_root)])

        # Verify project files are included but MCP files are not
        file_names = [Path(f).name for f in files]
        assert "app.py" in file_names
        assert "config.py" in file_names
        assert "test.py" not in file_names  # From MCP dir
        assert "server.py" not in file_names  # From MCP dir


class TestHomeDirectoryProtection:
    """Test protection against scanning user's home directory root."""

    def test_detect_exact_home_directory(self):
        """Test detection of exact home directory path."""
        with patch("utils.file_utils.get_user_home_directory") as mock_home:
            mock_home.return_value = Path("/Users/testuser")

            assert is_home_directory_root(Path("/Users/testuser")) is True
            assert is_home_directory_root(Path("/Users/testuser/")) is True

    def test_allow_home_subdirectories(self):
        """Test that subdirectories of home are allowed."""
        with patch("utils.file_utils.get_user_home_directory") as mock_home:
            mock_home.return_value = Path("/Users/testuser")

            assert is_home_directory_root(Path("/Users/testuser/projects")) is False
            assert is_home_directory_root(Path("/Users/testuser/Documents/code")) is False

    def test_detect_home_patterns_macos(self):
        """Test detection of macOS home directory patterns."""
        # Test various macOS home patterns
        assert is_home_directory_root(Path("/Users/john")) is True
        assert is_home_directory_root(Path("/Users/jane")) is True
        # But subdirectories should be allowed
        assert is_home_directory_root(Path("/Users/john/projects")) is False

    def test_detect_home_patterns_linux(self):
        """Test detection of Linux home directory patterns."""
        assert is_home_directory_root(Path("/home/ubuntu")) is True
        assert is_home_directory_root(Path("/home/user")) is True
        # But subdirectories should be allowed
        assert is_home_directory_root(Path("/home/ubuntu/code")) is False

    def test_detect_home_patterns_windows(self):
        """Test detection of Windows home directory patterns."""
        assert is_home_directory_root(Path("C:\\Users\\John")) is True
        assert is_home_directory_root(Path("C:/Users/Jane")) is True
        # But subdirectories should be allowed
        assert is_home_directory_root(Path("C:\\Users\\John\\Documents")) is False

    def test_home_directory_excluded_from_scan(self, tmp_path):
        """Test that home directory root is excluded during path expansion."""
        with patch("utils.file_utils.get_user_home_directory") as mock_home:
            mock_home.return_value = tmp_path
            with patch("utils.file_utils.SECURITY_ROOT", tmp_path):
                # Try to scan home directory
                files = expand_paths([str(tmp_path)])
                # Should return empty as home root is skipped
                assert files == []


class TestUserHomeEnvironmentVariable:
    """Test USER_HOME environment variable handling."""

    def test_user_home_from_env(self):
        """Test USER_HOME is used when set."""
        test_home = "/Users/dockeruser"
        with patch.dict(os.environ, {"USER_HOME": test_home}):
            home = get_user_home_directory()
            assert home == Path(test_home).resolve()

    def test_fallback_to_workspace_root_in_docker(self):
        """Test fallback to WORKSPACE_ROOT in Docker when USER_HOME not set."""
        with patch("utils.file_utils.WORKSPACE_ROOT", "/Users/realuser"):
            with patch("utils.file_utils.CONTAINER_WORKSPACE") as mock_container:
                mock_container.exists.return_value = True
                # Clear USER_HOME to test fallback
                with patch.dict(os.environ, {"USER_HOME": ""}, clear=False):
                    home = get_user_home_directory()
                    assert str(home) == "/Users/realuser"

    def test_fallback_to_system_home(self):
        """Test fallback to system home when not in Docker."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("utils.file_utils.CONTAINER_WORKSPACE") as mock_container:
                mock_container.exists.return_value = False
                with patch("pathlib.Path.home") as mock_home:
                    mock_home.return_value = Path("/home/user")
                    home = get_user_home_directory()
                    assert home == Path("/home/user")


class TestExcludedDirectories:
    """Test that excluded directories are properly filtered."""

    def test_excluded_dirs_not_scanned(self, tmp_path):
        """Test that directories in EXCLUDED_DIRS are skipped."""
        # Create a project with various directories
        project = tmp_path / "project"
        project.mkdir()

        # Create some allowed files
        (project / "main.py").write_text("# Main")
        (project / "app.py").write_text("# App")

        # Create excluded directories with files
        for excluded in ["node_modules", ".git", "build", "__pycache__", ".venv"]:
            excluded_dir = project / excluded
            excluded_dir.mkdir()
            (excluded_dir / "test.py").write_text("# Should not be included")
            (excluded_dir / "data.json").write_text("{}")

        # Create a nested allowed directory
        src = project / "src"
        src.mkdir()
        (src / "utils.py").write_text("# Utils")

        with patch("utils.file_utils.SECURITY_ROOT", tmp_path):
            files = expand_paths([str(project)])

        file_names = [Path(f).name for f in files]

        # Check allowed files are included
        assert "main.py" in file_names
        assert "app.py" in file_names
        assert "utils.py" in file_names

        # Check excluded files are not included
        assert "test.py" not in file_names
        assert "data.json" not in file_names

    def test_new_excluded_directories(self, tmp_path):
        """Test newly added excluded directories like .next, .nuxt, etc."""
        project = tmp_path / "webapp"
        project.mkdir()

        # Create files in new excluded directories
        for excluded in [".next", ".nuxt", "bower_components", ".expo"]:
            excluded_dir = project / excluded
            excluded_dir.mkdir()
            (excluded_dir / "generated.js").write_text("// Generated")

        # Create an allowed file
        (project / "index.js").write_text("// Index")

        with patch("utils.file_utils.SECURITY_ROOT", tmp_path):
            files = expand_paths([str(project)])

        file_names = [Path(f).name for f in files]

        assert "index.js" in file_names
        assert "generated.js" not in file_names


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_project_with_mcp_clone_inside(self, tmp_path):
        """Test scanning a project that has MCP cloned inside it."""
        # Setup: User project with MCP cloned as a tool
        user_project = tmp_path / "my-awesome-project"
        user_project.mkdir()

        # User's project files
        (user_project / "README.md").write_text("# My Project")
        (user_project / "main.py").write_text("print('Hello')")
        src = user_project / "src"
        src.mkdir()
        (src / "app.py").write_text("# App code")

        # MCP cloned inside the project
        mcp = user_project / "tools" / "gemini-mcp-server"
        mcp.mkdir(parents=True)
        for sig_file in list(MCP_SIGNATURE_FILES)[:4]:
            if "/" in sig_file:
                (mcp / sig_file).parent.mkdir(parents=True, exist_ok=True)
            (mcp / sig_file).write_text("# MCP code")
        (mcp / "LICENSE").write_text("MIT License")
        (mcp / "README.md").write_text("# Gemini MCP")

        # Also add node_modules (should be excluded)
        node_modules = user_project / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.json").write_text("{}")

        with patch("utils.file_utils.SECURITY_ROOT", tmp_path):
            files = expand_paths([str(user_project)])

        file_paths = [str(f) for f in files]

        # User files should be included
        assert any("my-awesome-project/README.md" in p for p in file_paths)
        assert any("my-awesome-project/main.py" in p for p in file_paths)
        assert any("src/app.py" in p for p in file_paths)

        # MCP files should NOT be included
        assert not any("gemini-mcp-server" in p for p in file_paths)
        assert not any("zen_server.py" in p for p in file_paths)

        # node_modules should NOT be included
        assert not any("node_modules" in p for p in file_paths)

    def test_cannot_scan_above_workspace_root(self, tmp_path):
        """Test that we cannot scan outside the workspace root."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create a file in workspace
        (workspace / "allowed.py").write_text("# Allowed")

        # Create a file outside workspace
        (tmp_path / "outside.py").write_text("# Outside")

        with patch("utils.file_utils.SECURITY_ROOT", workspace):
            # Try to expand paths outside workspace - should return empty list
            files = expand_paths([str(tmp_path)])
            assert files == []  # Path outside workspace is skipped silently
