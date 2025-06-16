"""
Test /app/ to ./ path translation for standalone mode.

Tests that internal application paths work in both Docker and standalone modes.
"""

import os
import tempfile
from unittest.mock import patch

from utils.file_utils import translate_path_for_environment


class TestAppPathTranslation:
    """Test translation of /app/ paths for different environments."""

    def test_app_path_translation_in_standalone_mode(self):
        """Test that /app/ paths are translated to ./ in standalone mode."""

        # Mock standalone environment (no Docker)
        with patch("utils.file_utils.CONTAINER_WORKSPACE") as mock_container_workspace:
            mock_container_workspace.exists.return_value = False

            # Clear WORKSPACE_ROOT to simulate standalone mode
            with patch.dict(os.environ, {}, clear=True):

                # Test translation of internal app paths
                test_cases = [
                    ("/app/conf/custom_models.json", "./conf/custom_models.json"),
                    ("/app/conf/other_config.json", "./conf/other_config.json"),
                    ("/app/logs/app.log", "./logs/app.log"),
                    ("/app/data/file.txt", "./data/file.txt"),
                ]

                for input_path, expected_output in test_cases:
                    result = translate_path_for_environment(input_path)
                    assert result == expected_output, f"Expected {expected_output}, got {result}"

    def test_allowed_app_path_unchanged_in_docker_mode(self):
        """Test that allowed /app/ paths remain unchanged in Docker mode."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock Docker environment
            with patch("utils.file_utils.CONTAINER_WORKSPACE") as mock_container_workspace:
                mock_container_workspace.exists.return_value = True
                mock_container_workspace.__str__.return_value = "/workspace"

                # Set WORKSPACE_ROOT to simulate Docker environment
                with patch.dict(os.environ, {"WORKSPACE_ROOT": tmpdir}):

                    # Only specifically allowed internal app paths should remain unchanged in Docker
                    allowed_path = "/app/conf/custom_models.json"
                    result = translate_path_for_environment(allowed_path)
                    assert (
                        result == allowed_path
                    ), f"Docker mode should preserve allowed path {allowed_path}, got {result}"

    def test_non_allowed_app_paths_blocked_in_docker_mode(self):
        """Test that non-allowed /app/ paths are blocked in Docker mode."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock Docker environment
            with patch("utils.file_utils.CONTAINER_WORKSPACE") as mock_container_workspace:
                mock_container_workspace.exists.return_value = True
                mock_container_workspace.__str__.return_value = "/workspace"

                # Set WORKSPACE_ROOT to simulate Docker environment
                with patch.dict(os.environ, {"WORKSPACE_ROOT": tmpdir}):

                    # Non-allowed internal app paths should be blocked in Docker for security
                    blocked_paths = [
                        "/app/conf/other_config.json",
                        "/app/logs/app.log",
                        "/app/server.py",
                    ]

                    for blocked_path in blocked_paths:
                        result = translate_path_for_environment(blocked_path)
                        assert result.startswith(
                            "/inaccessible/"
                        ), f"Docker mode should block non-allowed path {blocked_path}, got {result}"

    def test_non_app_paths_unchanged_in_standalone(self):
        """Test that non-/app/ paths are unchanged in standalone mode."""

        # Mock standalone environment
        with patch("utils.file_utils.CONTAINER_WORKSPACE") as mock_container_workspace:
            mock_container_workspace.exists.return_value = False

            with patch.dict(os.environ, {}, clear=True):

                # Non-app paths should be unchanged
                test_cases = [
                    "/home/user/file.py",
                    "/etc/config.conf",
                    "./local/file.txt",
                    "relative/path.py",
                    "/workspace/file.py",
                ]

                for input_path in test_cases:
                    result = translate_path_for_environment(input_path)
                    assert result == input_path, f"Non-app path {input_path} should be unchanged, got {result}"

    def test_edge_cases_in_app_translation(self):
        """Test edge cases in /app/ path translation."""

        # Mock standalone environment
        with patch("utils.file_utils.CONTAINER_WORKSPACE") as mock_container_workspace:
            mock_container_workspace.exists.return_value = False

            with patch.dict(os.environ, {}, clear=True):

                # Test edge cases
                test_cases = [
                    ("/app/", "./"),  # Root app directory
                    ("/app", "/app"),  # Exact match without trailing slash - not translated
                    ("/app/file", "./file"),  # File directly in app
                    ("/app//double/slash", "./double/slash"),  # Handle double slashes
                ]

                for input_path, expected_output in test_cases:
                    result = translate_path_for_environment(input_path)
                    assert (
                        result == expected_output
                    ), f"Edge case {input_path}: expected {expected_output}, got {result}"
