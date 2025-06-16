"""
Integration tests for internal application configuration file access.

These tests verify that:
1. Specific internal config files are accessible (exact path matching)
2. Path variations and traversal attempts are blocked (security)
3. The OpenRouter model configuration loads properly
4. Normal workspace file operations continue to work

This follows the established testing patterns from test_docker_path_integration.py
by using actual file operations and module reloading instead of mocks.
"""

import importlib
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.file_utils import translate_path_for_environment


class TestInternalConfigFileAccess:
    """Test access to internal application configuration files."""

    def test_allowed_internal_config_file_access(self):
        """Test that the specific internal config file is accessible."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up Docker-like environment
            host_workspace = Path(tmpdir) / "host_workspace"
            host_workspace.mkdir()
            container_workspace = Path(tmpdir) / "container_workspace"
            container_workspace.mkdir()

            original_env = os.environ.copy()
            try:
                os.environ["WORKSPACE_ROOT"] = str(host_workspace)

                # Reload modules to pick up environment
                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

                # Test with Docker environment simulation
                with patch("utils.file_utils.CONTAINER_WORKSPACE", container_workspace):
                    # The exact allowed path should pass through unchanged
                    result = translate_path_for_environment("/app/conf/custom_models.json")
                    assert result == "/app/conf/custom_models.json"

            finally:
                # Restore environment
                os.environ.clear()
                os.environ.update(original_env)
                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

    def test_blocked_config_file_variations(self):
        """Test that variations of the config file path are blocked."""

        with tempfile.TemporaryDirectory() as tmpdir:
            host_workspace = Path(tmpdir) / "host_workspace"
            host_workspace.mkdir()
            container_workspace = Path(tmpdir) / "container_workspace"
            container_workspace.mkdir()

            original_env = os.environ.copy()
            try:
                os.environ["WORKSPACE_ROOT"] = str(host_workspace)

                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

                with patch("utils.file_utils.CONTAINER_WORKSPACE", container_workspace):
                    # Test blocked variations - these should return inaccessible paths
                    blocked_paths = [
                        "/app/conf/",  # Directory
                        "/app/conf/other_file.json",  # Different file
                        "/app/conf/custom_models.json.backup",  # Extra extension
                        "/app/conf/custom_models.txt",  # Different extension
                        "/app/conf/../server.py",  # Path traversal
                        "/app/server.py",  # Application code
                        "/etc/passwd",  # System file
                    ]

                    for path in blocked_paths:
                        result = translate_path_for_environment(path)
                        assert result.startswith("/inaccessible/"), f"Path {path} should be blocked but got: {result}"

            finally:
                os.environ.clear()
                os.environ.update(original_env)
                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

    def test_workspace_files_continue_to_work(self):
        """Test that normal workspace file operations are unaffected."""

        with tempfile.TemporaryDirectory() as tmpdir:
            host_workspace = Path(tmpdir) / "host_workspace"
            host_workspace.mkdir()
            container_workspace = Path(tmpdir) / "container_workspace"
            container_workspace.mkdir()

            # Create a test file in the workspace
            test_file = host_workspace / "src" / "test.py"
            test_file.parent.mkdir(parents=True)
            test_file.write_text("# test file")

            original_env = os.environ.copy()
            try:
                os.environ["WORKSPACE_ROOT"] = str(host_workspace)

                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

                with patch("utils.file_utils.CONTAINER_WORKSPACE", container_workspace):
                    # Normal workspace file should translate correctly
                    result = translate_path_for_environment(str(test_file))
                    expected = str(container_workspace / "src" / "test.py")
                    assert result == expected

            finally:
                os.environ.clear()
                os.environ.update(original_env)
                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

    def test_openrouter_config_loading_real_world(self):
        """Test that OpenRouter configuration loading works in real container environment."""

        # This test validates that our fix works in the actual Docker environment
        # by checking that the translate_path_for_environment function handles
        # the exact internal config path correctly

        with tempfile.TemporaryDirectory() as tmpdir:
            host_workspace = Path(tmpdir) / "host_workspace"
            host_workspace.mkdir()
            container_workspace = Path(tmpdir) / "container_workspace"
            container_workspace.mkdir()

            original_env = os.environ.copy()
            try:
                os.environ["WORKSPACE_ROOT"] = str(host_workspace)

                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

                with patch("utils.file_utils.CONTAINER_WORKSPACE", container_workspace):
                    # Test that the function correctly handles the config path
                    result = translate_path_for_environment("/app/conf/custom_models.json")

                    # The path should pass through unchanged (not be blocked)
                    assert result == "/app/conf/custom_models.json"

                    # Verify it's not marked as inaccessible
                    assert not result.startswith("/inaccessible/")

            finally:
                os.environ.clear()
                os.environ.update(original_env)
                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

    def test_security_boundary_comprehensive(self):
        """Comprehensive test of all security boundaries in Docker environment."""

        with tempfile.TemporaryDirectory() as tmpdir:
            host_workspace = Path(tmpdir) / "host_workspace"
            host_workspace.mkdir()
            container_workspace = Path(tmpdir) / "container_workspace"
            container_workspace.mkdir()

            # Create a workspace file for testing
            workspace_file = host_workspace / "project" / "main.py"
            workspace_file.parent.mkdir(parents=True)
            workspace_file.write_text("# workspace file")

            original_env = os.environ.copy()
            try:
                os.environ["WORKSPACE_ROOT"] = str(host_workspace)

                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

                with patch("utils.file_utils.CONTAINER_WORKSPACE", container_workspace):
                    # Test cases: (path, should_be_allowed, description)
                    test_cases = [
                        # Allowed cases
                        ("/app/conf/custom_models.json", True, "Exact allowed internal config"),
                        (str(workspace_file), True, "Workspace file"),
                        (str(container_workspace / "existing.py"), True, "Container path"),
                        # Blocked cases
                        ("/app/conf/", False, "Directory access"),
                        ("/app/conf/other.json", False, "Different config file"),
                        ("/app/conf/custom_models.json.backup", False, "Config with extra extension"),
                        ("/app/server.py", False, "Application source"),
                        ("/etc/passwd", False, "System file"),
                        ("../../../etc/passwd", False, "Relative path traversal"),
                        ("/app/conf/../server.py", False, "Path traversal through config dir"),
                    ]

                    for path, should_be_allowed, description in test_cases:
                        result = translate_path_for_environment(path)

                        if should_be_allowed:
                            # Should either pass through unchanged or translate to container path
                            assert not result.startswith(
                                "/inaccessible/"
                            ), f"{description}: {path} should be allowed but was blocked"
                        else:
                            # Should be blocked with inaccessible path
                            assert result.startswith(
                                "/inaccessible/"
                            ), f"{description}: {path} should be blocked but got: {result}"

            finally:
                os.environ.clear()
                os.environ.update(original_env)
                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

    def test_exact_path_matching_prevents_wildcards(self):
        """Test that using exact path matching prevents any wildcard-like behavior."""

        with tempfile.TemporaryDirectory() as tmpdir:
            host_workspace = Path(tmpdir) / "host_workspace"
            host_workspace.mkdir()
            container_workspace = Path(tmpdir) / "container_workspace"
            container_workspace.mkdir()

            original_env = os.environ.copy()
            try:
                os.environ["WORKSPACE_ROOT"] = str(host_workspace)

                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)

                with patch("utils.file_utils.CONTAINER_WORKSPACE", container_workspace):
                    # Even subtle variations should be blocked
                    subtle_variations = [
                        "/app/conf/custom_models.jsonx",  # Extra char
                        "/app/conf/custom_models.jso",  # Missing char
                        "/app/conf/custom_models.JSON",  # Different case
                        "/app/conf/custom_models.json ",  # Trailing space
                        " /app/conf/custom_models.json",  # Leading space
                        "/app/conf/./custom_models.json",  # Current dir reference
                        "/app/conf/subdir/../custom_models.json",  # Up and down
                    ]

                    for variation in subtle_variations:
                        result = translate_path_for_environment(variation)
                        assert result.startswith(
                            "/inaccessible/"
                        ), f"Variation {variation} should be blocked but got: {result}"

            finally:
                os.environ.clear()
                os.environ.update(original_env)
                import utils.security_config

                importlib.reload(utils.security_config)
                importlib.reload(utils.file_utils)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
