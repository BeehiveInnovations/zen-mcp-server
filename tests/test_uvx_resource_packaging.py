"""Tests for uvx path resolution functionality."""

from pathlib import Path
from unittest.mock import patch

from providers.openrouter_registry import OpenRouterModelRegistry


class TestUvxPathResolution:
    """Test uvx path resolution for OpenRouter model registry."""

    def test_normal_operation(self):
        """Test that normal operation works in development environment."""
        registry = OpenRouterModelRegistry()
        assert len(registry.list_models()) > 0
        assert len(registry.list_aliases()) > 0

    def test_config_path_resolution(self):
        """Test that the config path resolution finds the config file in multiple locations."""
        # Check that the config file exists in the development location
        config_file = Path(__file__).parent.parent / "conf" / "custom_models.json"
        assert config_file.exists(), "Config file should exist in conf/custom_models.json"

        # Test that a registry can find and use the config
        registry = OpenRouterModelRegistry()
        assert registry.config_path.exists(), "Registry should find existing config path"
        assert len(registry.list_models()) > 0, "Registry should load models from config"

    def test_explicit_config_path_override(self):
        """Test that explicit config path works correctly."""
        config_path = Path(__file__).parent.parent / "conf" / "custom_models.json"

        registry = OpenRouterModelRegistry(config_path=str(config_path))

        # Should use the provided file path
        assert registry.config_path == config_path
        assert len(registry.list_models()) > 0

    def test_environment_variable_override(self):
        """Test that CUSTOM_MODELS_CONFIG_PATH environment variable works."""
        config_path = Path(__file__).parent.parent / "conf" / "custom_models.json"

        with patch.dict("os.environ", {"CUSTOM_MODELS_CONFIG_PATH": str(config_path)}):
            registry = OpenRouterModelRegistry()

            # Should use environment path
            assert registry.config_path == config_path
            assert len(registry.list_models()) > 0

    def test_multiple_path_fallback(self):
        """Test that multiple path resolution works for different deployment scenarios."""
        registry = OpenRouterModelRegistry()

        # In development, should find the config
        assert registry.config_path is not None
        assert isinstance(registry.config_path, Path)

        # Should load models successfully
        assert len(registry.list_models()) > 0

    def test_missing_config_handling(self):
        """Test behavior when config file is missing."""
        # Use a non-existent path
        registry = OpenRouterModelRegistry(config_path="/nonexistent/path/config.json")

        # Should gracefully handle missing config
        assert len(registry.list_models()) == 0
        assert len(registry.list_aliases()) == 0
