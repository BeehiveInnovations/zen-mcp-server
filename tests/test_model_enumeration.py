"""
Integration tests for model enumeration across all provider combinations.

These tests ensure that the _get_available_models() method correctly returns
all expected models based on which providers are configured via environment variables.
"""

import importlib
import os

import pytest

from providers.registry import ModelProviderRegistry
from tools.analyze import AnalyzeTool


@pytest.mark.no_mock_provider
class TestModelEnumeration:
    """Test model enumeration with various provider configurations"""

    def setup_method(self):
        """Set up clean state before each test."""
        # Save original environment state
        self._original_env = {
            "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL", ""),
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
            "XAI_API_KEY": os.environ.get("XAI_API_KEY", ""),
            "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
            "CUSTOM_API_URL": os.environ.get("CUSTOM_API_URL", ""),
        }

        # Clear provider registry
        ModelProviderRegistry._instance = None

    def teardown_method(self):
        """Clean up after each test."""
        # Restore original environment
        for key, value in self._original_env.items():
            if value:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]

        # Reload config
        import config

        importlib.reload(config)

        # Clear provider registry
        ModelProviderRegistry._instance = None

    def _setup_environment(self, provider_config):
        """Helper to set up environment variables for testing."""
        # Clear all provider-related env vars first
        for key in ["GEMINI_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY", "CUSTOM_API_URL"]:
            if key in os.environ:
                del os.environ[key]

        # Set new values
        for key, value in provider_config.items():
            if value is not None:
                os.environ[key] = value

        # Set auto mode only if not explicitly set in provider_config
        if "DEFAULT_MODEL" not in provider_config:
            os.environ["DEFAULT_MODEL"] = "auto"

        # Reload config to pick up changes
        import config

        importlib.reload(config)

        # Reload tools.base to ensure fresh state
        import tools.base

        importlib.reload(tools.base)

    def test_native_models_always_included(self):
        """Test that native models from MODEL_CAPABILITIES_DESC are always included."""
        self._setup_environment({})  # No providers configured

        tool = AnalyzeTool()
        models = tool._get_available_models()

        # All native models should be present
        native_models = [
            "flash",
            "pro",  # Gemini aliases
            "o3",
            "o3-mini",
            "o3-pro",
            "o4-mini",
            "o4-mini-high",  # OpenAI models
            "grok",
            "grok-3",
            "grok-3-fast",
            "grok3",
            "grokfast",  # X.AI models
            "gemini-2.5-flash",
            "gemini-2.5-pro",  # Full Gemini names
        ]

        for model in native_models:
            assert model in models, f"Native model {model} should always be in enum"

    @pytest.mark.skip(reason="Complex integration test - rely on simulator tests for provider testing")
    def test_openrouter_models_with_api_key(self):
        """Test that OpenRouter models are included when API key is configured."""
        pass

    def test_openrouter_models_without_api_key(self):
        """Test that OpenRouter models are NOT included when API key is not configured."""
        self._setup_environment({})  # No OpenRouter key

        tool = AnalyzeTool()
        models = tool._get_available_models()

        # OpenRouter-specific models should NOT be present
        openrouter_only_models = ["opus", "sonnet", "haiku"]
        found_count = sum(1 for m in openrouter_only_models if m in models)

        assert found_count == 0, "OpenRouter models should not be included without API key"

    @pytest.mark.skip(reason="Integration test - rely on simulator tests for API testing")
    def test_custom_models_with_custom_url(self):
        """Test that custom models are included when CUSTOM_API_URL is configured."""
        pass

    def test_custom_models_without_custom_url(self):
        """Test that custom models are NOT included when CUSTOM_API_URL is not configured."""
        self._setup_environment({})  # No custom URL

        tool = AnalyzeTool()
        models = tool._get_available_models()

        # Custom-only models should NOT be present
        custom_only_models = ["local-llama", "llama3.2"]
        found_count = sum(1 for m in custom_only_models if m in models)

        assert found_count == 0, "Custom models should not be included without CUSTOM_API_URL"

    @pytest.mark.skip(reason="Integration test - rely on simulator tests for API testing")
    def test_all_providers_combined(self):
        """Test that all models are included when all providers are configured."""
        pass

    @pytest.mark.skip(reason="Integration test - rely on simulator tests for API testing")
    def test_mixed_provider_combinations(self):
        """Test various mixed provider configurations."""
        pass

    def test_no_duplicates_with_overlapping_providers(self):
        """Test that models aren't duplicated when multiple providers offer the same model."""
        self._setup_environment(
            {
                "OPENAI_API_KEY": "test",
                "OPENROUTER_API_KEY": "test",  # OpenRouter also offers OpenAI models
            }
        )

        tool = AnalyzeTool()
        models = tool._get_available_models()

        # Count occurrences of each model
        model_counts = {}
        for model in models:
            model_counts[model] = model_counts.get(model, 0) + 1

        # Check no duplicates
        duplicates = {m: count for m, count in model_counts.items() if count > 1}
        assert len(duplicates) == 0, f"Found duplicate models: {duplicates}"

    @pytest.mark.skip(reason="Integration test - rely on simulator tests for API testing")
    def test_schema_enum_matches_get_available_models(self):
        """Test that the schema enum matches what _get_available_models returns."""
        pass

    @pytest.mark.parametrize(
        "model_name,should_exist",
        [
            ("flash", True),  # Native Gemini
            ("o3", True),  # Native OpenAI
            ("grok", True),  # Native X.AI
            ("gemini-2.5-flash", True),  # Full native name
            ("o4-mini-high", True),  # Native OpenAI variant
            ("grok-3-fast", True),  # Native X.AI variant
        ],
    )
    def test_specific_native_models_always_present(self, model_name, should_exist):
        """Test that specific native models are always present regardless of configuration."""
        self._setup_environment({})  # No providers

        tool = AnalyzeTool()
        models = tool._get_available_models()

        if should_exist:
            assert model_name in models, f"Native model {model_name} should always be present"
        else:
            assert model_name not in models, f"Model {model_name} should not be present"

    def test_auto_mode_behavior_with_environment_variables(self):
        """Test auto mode behavior with various environment variable combinations."""

        # Test different environment scenarios for auto mode
        test_scenarios = [
            {"name": "no_providers", "env": {}, "expected_behavior": "should_include_native_only"},
            {
                "name": "gemini_only",
                "env": {"GEMINI_API_KEY": "test-key"},
                "expected_behavior": "should_include_gemini_models",
            },
            {
                "name": "openai_only",
                "env": {"OPENAI_API_KEY": "test-key"},
                "expected_behavior": "should_include_openai_models",
            },
            {"name": "xai_only", "env": {"XAI_API_KEY": "test-key"}, "expected_behavior": "should_include_xai_models"},
            {
                "name": "multiple_providers",
                "env": {"GEMINI_API_KEY": "test-key", "OPENAI_API_KEY": "test-key", "XAI_API_KEY": "test-key"},
                "expected_behavior": "should_include_all_native_models",
            },
        ]

        for scenario in test_scenarios:
            # Test each scenario independently
            self._setup_environment(scenario["env"])

            tool = AnalyzeTool()
            models = tool._get_available_models()

            # Always expect native models regardless of configuration
            native_models = ["flash", "pro", "o3", "o3-mini", "grok"]
            for model in native_models:
                assert model in models, f"Native model {model} missing in {scenario['name']} scenario"

            # Verify auto mode detection
            assert tool.is_effective_auto_mode(), f"Auto mode should be active in {scenario['name']} scenario"

            # Verify model schema includes model field in auto mode
            schema = tool.get_input_schema()
            assert "model" in schema["required"], f"Model field should be required in auto mode for {scenario['name']}"
            assert "model" in schema["properties"], f"Model field should be in properties for {scenario['name']}"

            # Verify enum contains expected models
            model_enum = schema["properties"]["model"]["enum"]
            for model in native_models:
                assert model in model_enum, f"Native model {model} should be in enum for {scenario['name']}"

    def test_auto_mode_model_selection_validation(self):
        """Test that auto mode properly validates model selection."""
        self._setup_environment({"DEFAULT_MODEL": "auto", "GEMINI_API_KEY": "test-key"})

        tool = AnalyzeTool()

        # Verify auto mode is active
        assert tool.is_effective_auto_mode()

        # Test valid model selection
        available_models = tool._get_available_models()
        assert len(available_models) > 0, "Should have available models in auto mode"

        # Test that model validation works
        schema = tool.get_input_schema()
        model_enum = schema["properties"]["model"]["enum"]

        # All enum models should be in available models
        for enum_model in model_enum:
            assert enum_model in available_models, f"Enum model {enum_model} should be available"

        # All available models should be in enum
        for available_model in available_models:
            assert available_model in model_enum, f"Available model {available_model} should be in enum"

    def test_environment_variable_precedence(self):
        """Test that environment variables are properly handled for model availability."""
        # Test that setting DEFAULT_MODEL to auto enables auto mode
        self._setup_environment({"DEFAULT_MODEL": "auto"})
        tool = AnalyzeTool()
        assert tool.is_effective_auto_mode(), "DEFAULT_MODEL=auto should enable auto mode"

        # Test environment variable combinations with auto mode
        self._setup_environment({"DEFAULT_MODEL": "auto", "GEMINI_API_KEY": "test-key", "OPENAI_API_KEY": "test-key"})
        tool = AnalyzeTool()
        models = tool._get_available_models()

        # Should include native models from providers that are theoretically configured
        native_models = ["flash", "pro", "o3", "o3-mini", "grok"]
        for model in native_models:
            assert model in models, f"Native model {model} should be available in auto mode"

        # Verify auto mode is still active
        assert tool.is_effective_auto_mode(), "Auto mode should remain active with multiple providers"
