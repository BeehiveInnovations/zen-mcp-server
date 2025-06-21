"""Tests for UV/UVX configuration and entry point."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestUVConfiguration:
    """Test UV/UVX configuration functionality."""

    def test_zen_mcp_server_main_entry_point(self):
        """Test that the main entry point function exists and is callable."""
        from zen_mcp_server import main
        
        # Should be a callable function
        assert callable(main)

    def test_zen_config_minimal_exists(self):
        """Test that the minimal config example exists and is valid JSON."""
        config_path = Path(__file__).parent.parent / "examples" / "zen-config-minimal.json"
        assert config_path.exists(), "zen-config-minimal.json should exist"
        
        with open(config_path) as f:
            config = json.load(f)
        
        # Should have basic required fields
        assert "GEMINI_API_KEY" in config
        assert "DEFAULT_MODEL" in config
        assert "LOG_LEVEL" in config

    def test_claude_desktop_uv_config_exists(self):
        """Test that Claude Desktop UV config examples exist and are valid JSON."""
        examples_dir = Path(__file__).parent.parent / "examples"
        
        uv_configs = [
            "claude_desktop_uv_macos.json",
        ]
        
        for config_file in uv_configs:
            config_path = examples_dir / config_file
            assert config_path.exists(), f"{config_file} should exist"
            
            with open(config_path) as f:
                config = json.load(f)
            
            # Should have MCP server configuration
            assert "mcpServers" in config
            assert "zen-mcp-server" in config["mcpServers"]
            
            server_config = config["mcpServers"]["zen-mcp-server"]
            assert "command" in server_config
            assert "args" in server_config
            assert server_config["command"] == "uvx"

    def test_pyproject_toml_has_correct_entry_point(self):
        """Test that pyproject.toml has the correct entry point configuration."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml should exist"
        
        # Read and parse pyproject.toml
        with open(pyproject_path) as f:
            content = f.read()
        
        # Check for required sections
        assert "[project]" in content
        assert "[project.scripts]" in content
        assert 'zen_mcp_server = "zen_mcp_server:main"' in content
        
        # Check project metadata
        assert 'name = "zen-mcp-server"' in content
        assert 'requires-python = ">=3.10"' in content

    def test_version_consistency(self):
        """Test that version numbers are consistent across files."""
        # Get version from zen_mcp_server/_version.py
        from zen_mcp_server._version import __version__ as package_version
        
        # Check pyproject.toml
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path) as f:
            pyproject_content = f.read()
        
        assert f'version = "{package_version}"' in pyproject_content

    @patch.dict(os.environ, {}, clear=True)
    def test_config_loading_with_minimal_config(self):
        """Test that configuration loading works with minimal UV config."""
        # Create a temporary config file
        config_data = {
            "GEMINI_API_KEY": "test-openai-key",
            "DEFAULT_MODEL": "gemini-2.0-flash-exp",
            "LOG_LEVEL": "DEBUG"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            # Test that we can load and apply the config
            # (This is a basic integration test)
            from config import load_config_file, apply_config
            
            # Load config from file
            loaded_config = load_config_file(temp_config_path)
            assert loaded_config == config_data
            
            # Apply config to environment
            apply_config(loaded_config)
            
            # Verify environment variables were set
            assert os.getenv("GEMINI_API_KEY") == "test-openai-key"
            assert os.getenv("DEFAULT_MODEL") == "gemini-2.0-flash-exp"
            assert os.getenv("LOG_LEVEL") == "DEBUG"
            
        finally:
            # Clean up
            os.unlink(temp_config_path)
            # Clear the environment variables we set
            for key in config_data.keys():
                os.environ.pop(key, None)