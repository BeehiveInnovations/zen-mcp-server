"""
Integration tests for Docker path translation

These tests verify the actual behavior when running in a Docker-like environment
by creating temporary directories and testing the path translation logic.
"""

import importlib
import os
import tempfile
from pathlib import Path

import pytest

# We'll reload the module to test different environment configurations
import utils.file_utils


def test_docker_path_translation_integration():
    """Test path translation in a simulated Docker environment"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up directories
        host_workspace = Path(tmpdir) / "host_workspace"
        host_workspace.mkdir()
        container_workspace = Path(tmpdir) / "container_workspace"
        container_workspace.mkdir()

        # Create a test file structure
        (host_workspace / "src").mkdir()
        test_file = host_workspace / "src" / "test.py"
        test_file.write_text("# test file")

        # Set environment variables and reload the module
        original_env = os.environ.copy()
        try:
            os.environ["WORKSPACE_ROOT"] = str(host_workspace)

            # Reload the module to pick up new environment variables
            importlib.reload(utils.file_utils)

            # Mock the CONTAINER_WORKSPACE to point to our test directory
            utils.file_utils.CONTAINER_WORKSPACE = container_workspace

            # Test the translation
            from utils.file_utils import translate_path_for_environment

            # This should translate the host path to container path
            host_path = str(test_file)
            result = translate_path_for_environment(host_path)

            # Verify the translation worked
            expected = str(container_workspace / "src" / "test.py")
            assert result == expected

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
            importlib.reload(utils.file_utils)


def test_docker_security_validation():
    """Test that path traversal attempts are properly blocked"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up directories
        host_workspace = Path(tmpdir) / "workspace"
        host_workspace.mkdir()
        secret_dir = Path(tmpdir) / "secret"
        secret_dir.mkdir()
        secret_file = secret_dir / "password.txt"
        secret_file.write_text("secret")

        # Create a symlink inside workspace pointing to secret
        symlink = host_workspace / "link_to_secret"
        symlink.symlink_to(secret_file)

        original_env = os.environ.copy()
        try:
            os.environ["WORKSPACE_ROOT"] = str(host_workspace)

            # Reload the module
            importlib.reload(utils.file_utils)
            utils.file_utils.CONTAINER_WORKSPACE = Path("/workspace")

            from utils.file_utils import resolve_and_validate_path

            # Trying to access the symlink should fail
            with pytest.raises(PermissionError):
                resolve_and_validate_path(str(symlink))

        finally:
            os.environ.clear()
            os.environ.update(original_env)
            importlib.reload(utils.file_utils)


def test_no_docker_environment():
    """Test that paths are unchanged when Docker environment is not set"""

    original_env = os.environ.copy()
    try:
        # Clear Docker-related environment variables
        os.environ.pop("WORKSPACE_ROOT", None)

        # Reload the module
        importlib.reload(utils.file_utils)

        from utils.file_utils import translate_path_for_environment

        # Path should remain unchanged
        test_path = "/some/random/path.py"
        assert translate_path_for_environment(test_path) == test_path

    finally:
        os.environ.clear()
        os.environ.update(original_env)
        importlib.reload(utils.file_utils)


def test_review_changes_docker_path_translation():
    """Test that review_changes tool properly translates Docker paths"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up directories to simulate Docker mount
        host_workspace = Path(tmpdir) / "host_workspace"
        host_workspace.mkdir()
        container_workspace = Path(tmpdir) / "container_workspace"
        container_workspace.mkdir()

        # Create a git repository in the container workspace
        project_dir = container_workspace / "project"
        project_dir.mkdir()

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)

        # Create a test file
        test_file = project_dir / "test.py"
        test_file.write_text("print('hello')")

        # Stage the file
        subprocess.run(["git", "add", "test.py"], cwd=project_dir, capture_output=True)

        original_env = os.environ.copy()
        try:
            # Simulate Docker environment
            os.environ["WORKSPACE_ROOT"] = str(host_workspace)

            # Reload the module
            importlib.reload(utils.file_utils)
            utils.file_utils.CONTAINER_WORKSPACE = container_workspace

            # Import after reloading to get updated environment
            from tools.precommit import Precommit

            # Create tool instance
            tool = Precommit()

            # Test path translation in prepare_prompt
            request = tool.get_request_model()(
                path=str(host_workspace / "project"),  # Host path that needs translation
                review_type="quick",
                severity_filter="all",
            )

            # This should translate the path and find the git repository
            import asyncio

            result = asyncio.run(tool.prepare_prompt(request))

            # Should find the repository (not raise an error about inaccessible path)
            # If we get here without exception, the path was successfully translated
            assert isinstance(result, str)
            # The result should contain git diff information or indicate no changes
            assert "No git repositories found" not in result or "changes" in result.lower()

        finally:
            os.environ.clear()
            os.environ.update(original_env)
            importlib.reload(utils.file_utils)


def test_review_changes_docker_path_error():
    """Test that review_changes tool raises error for inaccessible paths"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up directories to simulate Docker mount
        host_workspace = Path(tmpdir) / "host_workspace"
        host_workspace.mkdir()
        container_workspace = Path(tmpdir) / "container_workspace"
        container_workspace.mkdir()

        # Create a path outside the mounted workspace
        outside_path = Path(tmpdir) / "outside_workspace"
        outside_path.mkdir()

        original_env = os.environ.copy()
        try:
            # Simulate Docker environment
            os.environ["WORKSPACE_ROOT"] = str(host_workspace)

            # Reload the module
            importlib.reload(utils.file_utils)
            utils.file_utils.CONTAINER_WORKSPACE = container_workspace

            # Import after reloading to get updated environment
            from tools.precommit import Precommit

            # Create tool instance
            tool = Precommit()

            # Test path translation with an inaccessible path
            request = tool.get_request_model()(
                path=str(outside_path),  # Path outside the mounted workspace
                review_type="quick",
                severity_filter="all",
            )

            # This should raise a ValueError
            import asyncio

            with pytest.raises(ValueError) as exc_info:
                asyncio.run(tool.prepare_prompt(request))

            # Check the error message
            assert "not accessible from within the Docker container" in str(exc_info.value)
            assert "mounted workspace" in str(exc_info.value)

        finally:
            os.environ.clear()
            os.environ.update(original_env)
            importlib.reload(utils.file_utils)


def test_double_translation_prevention():
    """Test that already-translated paths are not double-translated"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up directories
        host_workspace = Path(tmpdir) / "host_workspace"
        host_workspace.mkdir()
        container_workspace = Path(tmpdir) / "container_workspace"
        container_workspace.mkdir()

        original_env = os.environ.copy()
        try:
            os.environ["WORKSPACE_ROOT"] = str(host_workspace)

            # Reload the module
            importlib.reload(utils.file_utils)
            utils.file_utils.CONTAINER_WORKSPACE = container_workspace

            from utils.file_utils import translate_path_for_environment

            # Test 1: Normal translation
            host_path = str(host_workspace / "src" / "main.py")
            translated_once = translate_path_for_environment(host_path)
            expected = str(container_workspace / "src" / "main.py")
            assert translated_once == expected

            # Test 2: Double translation should return the same path
            translated_twice = translate_path_for_environment(translated_once)
            assert translated_twice == translated_once
            assert translated_twice == expected

            # Test 3: Container workspace root should not be double-translated
            root_path = str(container_workspace)
            translated_root = translate_path_for_environment(root_path)
            assert translated_root == root_path

        finally:
            os.environ.clear()
            os.environ.update(original_env)
            importlib.reload(utils.file_utils)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
