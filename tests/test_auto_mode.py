"""Tests for auto mode functionality"""

import importlib
import os
from unittest.mock import patch

import pytest

from tools.analyze import AnalyzeTool


class TestAutoMode:
    """Test auto mode configuration and behavior"""

    def test_auto_mode_detection(self):
        """Test that auto mode is detected correctly"""
        # Save original
        original = os.environ.get("DEFAULT_MODEL", "")

        try:
            # Test auto mode
            os.environ["DEFAULT_MODEL"] = "auto"
            import config

            importlib.reload(config)

            assert config.DEFAULT_MODEL == "auto"
            assert config.IS_AUTO_MODE is True

            # Test non-auto mode
            os.environ["DEFAULT_MODEL"] = "pro"
            importlib.reload(config)

            assert config.DEFAULT_MODEL == "pro"
            assert config.IS_AUTO_MODE is False

        finally:
            # Restore
            if original:
                os.environ["DEFAULT_MODEL"] = original
            else:
                os.environ.pop("DEFAULT_MODEL", None)
            importlib.reload(config)

    def test_model_capabilities_descriptions(self):
        """Test that model capabilities are properly defined"""
        from config import MODEL_CAPABILITIES_DESC

        # Check all expected models are present
        expected_models = ["flash", "pro", "o3", "o3-mini", "o3-pro", "o4-mini", "o4-mini-high"]
        for model in expected_models:
            assert model in MODEL_CAPABILITIES_DESC
            assert isinstance(MODEL_CAPABILITIES_DESC[model], str)
            assert len(MODEL_CAPABILITIES_DESC[model]) > 50  # Meaningful description

    def test_tool_schema_in_auto_mode(self):
        """Test that tool schemas require model in auto mode"""
        # Save original
        original = os.environ.get("DEFAULT_MODEL", "")

        try:
            # Enable auto mode
            os.environ["DEFAULT_MODEL"] = "auto"
            import config

            importlib.reload(config)

            tool = AnalyzeTool()
            schema = tool.get_input_schema()

            # Model should be required
            assert "model" in schema["required"]

            # Model field should have detailed descriptions
            model_schema = schema["properties"]["model"]
            assert "enum" in model_schema
            assert "flash" in model_schema["enum"]
            assert "select the most suitable model" in model_schema["description"]

        finally:
            # Restore
            if original:
                os.environ["DEFAULT_MODEL"] = original
            else:
                os.environ.pop("DEFAULT_MODEL", None)
            importlib.reload(config)

    def test_tool_schema_in_normal_mode(self):
        """Test that tool schemas don't require model in normal mode"""
        # This test uses the default from conftest.py which sets non-auto mode
        # The conftest.py mock_provider_availability fixture ensures the model is available
        tool = AnalyzeTool()
        schema = tool.get_input_schema()

        # Model should not be required
        assert "model" not in schema["required"]

        # Model field should have simpler description
        model_schema = schema["properties"]["model"]
        assert "enum" not in model_schema
        assert "Native models:" in model_schema["description"]
        assert "Defaults to" in model_schema["description"]

    @pytest.mark.asyncio
    async def test_auto_mode_requires_model_parameter(self):
        """Test that auto mode enforces model parameter"""
        # Save original
        original = os.environ.get("DEFAULT_MODEL", "")

        try:
            # Enable auto mode
            os.environ["DEFAULT_MODEL"] = "auto"
            import config

            importlib.reload(config)

            tool = AnalyzeTool()

            # Mock the provider to avoid real API calls
            with patch.object(tool, "get_model_provider"):
                # Execute without model parameter
                result = await tool.execute({"files": ["/tmp/test.py"], "prompt": "Analyze this"})

            # Should get error
            assert len(result) == 1
            response = result[0].text
            assert "error" in response
            assert "Model parameter is required" in response

        finally:
            # Restore
            if original:
                os.environ["DEFAULT_MODEL"] = original
            else:
                os.environ.pop("DEFAULT_MODEL", None)
            importlib.reload(config)

    @pytest.mark.asyncio
    async def test_unavailable_model_error_message(self):
        """Test that unavailable model shows helpful error with available models"""
        # Save original
        original = os.environ.get("DEFAULT_MODEL", "")

        try:
            # Enable auto mode
            os.environ["DEFAULT_MODEL"] = "auto"
            import config

            importlib.reload(config)

            tool = AnalyzeTool()

            # Get currently available models to use in the test
            from providers.registry import ModelProviderRegistry

            available_models = ModelProviderRegistry.get_available_model_names()

            # Mock the provider to simulate o3 not being available but keep actual available models
            with (
                patch("providers.registry.ModelProviderRegistry.get_provider_for_model") as mock_provider,
                patch("providers.registry.ModelProviderRegistry.get_available_models") as mock_available,
                patch.object(tool, "_get_available_models") as mock_tool_available,
            ):

                # Mock that o3 is not available but actual available models are
                def mock_get_provider(model_name):
                    if model_name == "o3":
                        # o3 is specifically not available
                        return None
                    elif model_name in available_models:
                        # Return a mock provider for actually available models
                        from unittest.mock import MagicMock

                        from providers.base import ModelCapabilities

                        mock_provider = MagicMock()
                        # Set up proper capabilities to avoid MagicMock comparison errors
                        from providers.base import ProviderType

                        mock_capabilities = ModelCapabilities(
                            provider=ProviderType.GOOGLE,
                            model_name=model_name,
                            friendly_name="Test Model",
                            context_window=1048576,  # 1M tokens
                            supports_function_calling=True,
                        )
                        mock_provider.get_capabilities.return_value = mock_capabilities
                        return mock_provider
                    else:
                        # Other unknown models are not available
                        return None

                mock_provider.side_effect = mock_get_provider

                # Mock available models to return the actual available models
                mock_available.return_value = dict.fromkeys(available_models, "test")

                # Mock the tool's available models method to return the actual available models
                mock_tool_available.return_value = available_models

                # Execute with unavailable model
                result = await tool.execute(
                    {"files": ["/tmp/test.py"], "prompt": "Analyze this", "model": "o3"}  # This model is not available
                )

            # Should get error with helpful message
            assert len(result) == 1
            response = result[0].text
            assert "error" in response
            assert "Model 'o3' is not available" in response
            assert "Available models:" in response

            # Should list at least one of the actually available models
            has_available_model = any(model in response for model in available_models)
            assert has_available_model, f"Expected one of {available_models} to be in response: {response}"

        finally:
            # Restore
            if original:
                os.environ["DEFAULT_MODEL"] = original
            else:
                os.environ.pop("DEFAULT_MODEL", None)
            importlib.reload(config)

    def test_model_field_schema_generation(self):
        """Test the get_model_field_schema method"""
        from tools.base import BaseTool

        # Create a minimal concrete tool for testing
        class TestTool(BaseTool):
            def get_name(self):
                return "test"

            def get_description(self):
                return "test"

            def get_input_schema(self):
                return {}

            def get_system_prompt(self):
                return ""

            def get_request_model(self):
                return None

            async def prepare_prompt(self, request):
                return ""

        tool = TestTool()

        # Save original
        original = os.environ.get("DEFAULT_MODEL", "")

        try:
            # Test auto mode
            os.environ["DEFAULT_MODEL"] = "auto"
            import config

            importlib.reload(config)

            schema = tool.get_model_field_schema()
            assert "enum" in schema
            assert all(
                model in schema["enum"]
                for model in ["flash", "pro", "o3", "o3-mini", "o3-pro", "o4-mini", "o4-mini-high"]
            )
            assert "select the most suitable model" in schema["description"]

            # Test normal mode
            os.environ["DEFAULT_MODEL"] = "pro"
            importlib.reload(config)

            schema = tool.get_model_field_schema()
            assert "enum" not in schema
            assert "Native models:" in schema["description"]
            assert "'pro'" in schema["description"]
            assert "Defaults to" in schema["description"]

        finally:
            # Restore
            if original:
                os.environ["DEFAULT_MODEL"] = original
            else:
                os.environ.pop("DEFAULT_MODEL", None)
            importlib.reload(config)
