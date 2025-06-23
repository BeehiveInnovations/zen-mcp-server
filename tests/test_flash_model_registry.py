"""Tests for Flash model registry functionality and regression prevention.

This test file ensures that the Flash model registry fix continues to work correctly
and prevents regression of the alias handling bug that prevented Flash model access.
"""

import os
from unittest.mock import patch

from providers.base import ProviderType
from providers.gemini import GeminiModelProvider
from providers.registry import ModelProviderRegistry
from utils.model_context import ModelContext
from utils.model_restrictions import ModelRestrictionService


class TestFlashModelRegistry:
    """Test Flash model availability and registry functionality."""

    def setup_method(self):
        """Set up clean state before each test."""
        # Clear restriction service cache before each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        # Clear registry cache to ensure clean state
        ModelProviderRegistry.clear_cache()

    def teardown_method(self):
        """Clean up after each test to avoid singleton issues."""
        # Clear restriction service cache after each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

        # Clear registry cache
        ModelProviderRegistry.clear_cache()

    def test_flash_models_available_without_restrictions(self):
        """Test that Flash models are available when no restrictions are set."""
        with patch.dict(os.environ, {}, clear=True):
            # Create provider instance directly
            provider = GeminiModelProvider(api_key="test-key")

            # Get all models without restrictions
            available_models = provider.list_models(respect_restrictions=True)
            flash_models = [m for m in available_models if "flash" in m.lower()]

            # Should have Flash models available
            assert len(flash_models) > 0, "Flash models should be available without restrictions"

            # Should include key Flash model variants (both canonical and aliases)
            expected_flash_models = ["gemini-2.5-flash", "gemini-2.0-flash", "flash"]
            for expected_model in expected_flash_models:
                assert expected_model in available_models, f"{expected_model} should be available"

    def test_flash_models_filtered_with_pro_restriction(self):
        """Test that Flash models are filtered out when GOOGLE_ALLOWED_MODELS=pro."""
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "pro"}):
            provider = GeminiModelProvider(api_key="test-key")

            # Get models with restrictions
            available_models = provider.list_models(respect_restrictions=True)
            flash_models = [m for m in available_models if "flash" in m.lower()]

            # Flash models should be filtered out
            assert len(flash_models) == 0, "Flash models should be filtered out with pro restriction"

            # Pro model should be available (alias form)
            assert "pro" in available_models, "Pro alias should be available"

    def test_flash_models_included_with_flash_restriction(self):
        """Test that Flash models are included when GOOGLE_ALLOWED_MODELS includes flash."""
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash,pro"}):
            provider = GeminiModelProvider(api_key="test-key")

            # Get models with restrictions
            available_models = provider.list_models(respect_restrictions=True)
            flash_models = [m for m in available_models if "flash" in m.lower()]

            # Flash models should be available
            assert len(flash_models) > 0, "Flash models should be available with flash restriction"

            # Should include the flash alias
            assert "flash" in available_models, "Flash alias should be available"

            # Pro alias should also be available
            assert "pro" in available_models, "Pro alias should also be available"

    def test_alias_resolution_flash_to_canonical(self):
        """Test that 'flash' alias correctly resolves to canonical model name."""
        with patch.dict(os.environ, {}):
            provider = GeminiModelProvider(api_key="test-key")

            # Test alias resolution
            resolved = provider._resolve_model_name("flash")
            assert resolved == "gemini-2.5-flash", "Flash alias should resolve to gemini-2.5-flash"

            # Test flash-2.0 alias resolution
            resolved_2 = provider._resolve_model_name("flash-2.0")
            assert resolved_2 == "gemini-2.0-flash", "flash-2.0 alias should resolve to gemini-2.0-flash"

    def test_flash_model_validation_with_restrictions(self):
        """Test Flash model validation respects restrictions correctly."""
        # Test with flash allowed
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash"}):
            # Clear cached restriction service
            import utils.model_restrictions

            utils.model_restrictions._restriction_service = None

            provider = GeminiModelProvider(api_key="test-key")

            # Flash alias should be valid
            assert provider.validate_model_name("flash"), "Flash alias should be valid when allowed"

            # Canonical name should NOT be valid when only alias is allowed
            # This is the correct behavior - restrictions are exact matches
            assert not provider.validate_model_name(
                "gemini-2.5-flash"
            ), "Canonical name should not be valid when only alias is allowed"

            # Pro should not be valid
            assert not provider.validate_model_name("pro"), "Pro should not be valid when not in restrictions"

    def test_regression_prevention_parameter_order_bug(self):
        """Test that prevents regression of parameter order bug in restriction validation.

        This test specifically catches the bug where parameters were incorrectly
        passed to is_allowed() method, causing Flash models to be incorrectly filtered.
        """
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash"}):
            # Clear cached restriction service
            import utils.model_restrictions

            utils.model_restrictions._restriction_service = None

            provider = GeminiModelProvider(api_key="test-key")

            # Test the exact scenario that was failing before the fix
            # Only "flash" alias is allowed, test that provider correctly validates it
            assert provider.validate_model_name("flash"), "Flash alias validation should work correctly"

            # Test getting capabilities works
            capabilities = provider.get_capabilities("flash")
            assert capabilities.model_name == "gemini-2.5-flash", "Capabilities should return canonical name"

            # Test that the restriction service is called with correct parameters
            restriction_service = utils.model_restrictions.get_restriction_service()

            # Manually test the parameter order that caused the bug
            # This call should succeed (flash is allowed)
            assert restriction_service.is_allowed(ProviderType.GOOGLE, "gemini-2.5-flash", "flash")

            # This call should fail (only alias is allowed, not full name)
            assert not restriction_service.is_allowed(ProviderType.GOOGLE, "gemini-2.5-flash")

    def test_model_context_creation_for_flash_models(self):
        """Test that ModelContext can be created for Flash models."""
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash,pro", "GOOGLE_API_KEY": "test-key"}):
            # Clear and reinitialize registry with proper API key
            ModelProviderRegistry._instance = None
            ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)

            # Test ModelContext creation with Flash alias
            ctx = ModelContext("flash")
            assert ctx is not None, "ModelContext should be created for 'flash' alias"
            assert isinstance(ctx.provider, GeminiModelProvider), "Provider should be GeminiModelProvider"

    def test_flash_models_in_registry_get_available_models(self):
        """Test that registry's get_available_models includes Flash models correctly."""
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash,pro", "GOOGLE_API_KEY": "test-key"}):
            # Clear and reinitialize registry
            ModelProviderRegistry._instance = None
            ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)

            # Get available models from registry
            available_models = ModelProviderRegistry.get_available_models(respect_restrictions=True)

            # Should include Flash models
            flash_models = [m for m in available_models if "flash" in m.lower()]
            assert len(flash_models) > 0, "Registry should include Flash models"

            # Should include specific Flash alias
            assert "flash" in available_models, "Registry should include flash alias"

    def test_multiple_flash_aliases_all_work(self):
        """Test that all Flash aliases resolve and work correctly when no restrictions are set."""
        with patch.dict(os.environ, {}, clear=True):
            provider = GeminiModelProvider(api_key="test-key")

            # Test all flash aliases
            flash_aliases = ["flash", "flash-2.0", "flash2", "flash-lite", "flashlite"]

            for alias in flash_aliases:
                # Should validate when no restrictions
                assert provider.validate_model_name(alias), f"Alias '{alias}' should validate without restrictions"

                # Should resolve to a canonical model name
                resolved = provider._resolve_model_name(alias)
                assert resolved.startswith("gemini-"), f"Alias '{alias}' should resolve to gemini-* model"

                # Should be able to get capabilities
                capabilities = provider.get_capabilities(alias)
                assert capabilities is not None, f"Should get capabilities for alias '{alias}'"


class TestFlashModelRestrictionService:
    """Test ModelRestrictionService behavior with Flash models."""

    def setup_method(self):
        """Set up clean state before each test."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    def teardown_method(self):
        """Clean up after each test."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    def test_restriction_service_flash_alias_handling(self):
        """Test that restriction service correctly handles Flash aliases."""
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash,pro"}):
            service = ModelRestrictionService()

            # Test that both alias and canonical name are allowed through alias resolution
            assert service.is_allowed(ProviderType.GOOGLE, "gemini-2.5-flash", "flash")
            assert service.is_allowed(ProviderType.GOOGLE, "flash")

            # Test that disallowed models are rejected
            assert not service.is_allowed(ProviderType.GOOGLE, "gemini-2.0-flash")

    def test_restriction_service_filter_models_with_flash(self):
        """Test that filter_models correctly handles Flash models."""
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash,flash-2.0,pro"}):
            service = ModelRestrictionService()

            test_models = [
                "flash",  # Use aliases for filtering since that's what list_models returns
                "flash-2.0",
                "flash-lite",
                "pro",
            ]

            # Filter models - should keep flash and pro variants
            filtered = service.filter_models(ProviderType.GOOGLE, test_models)

            # Should include Flash aliases and Pro
            assert "flash" in filtered
            assert "flash-2.0" in filtered
            assert "pro" in filtered

            # Should exclude flash-lite (not explicitly allowed)
            assert "flash-lite" not in filtered

    def test_case_insensitive_flash_restrictions(self):
        """Test that Flash restrictions are case insensitive."""
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "FLASH,Pro"}):
            service = ModelRestrictionService()

            # Should work with any case
            assert service.is_allowed(ProviderType.GOOGLE, "gemini-2.5-flash", "flash")
            assert service.is_allowed(ProviderType.GOOGLE, "gemini-2.5-flash", "Flash")
            assert service.is_allowed(ProviderType.GOOGLE, "gemini-2.5-flash", "FLASH")

            # Pro should also work
            assert service.is_allowed(ProviderType.GOOGLE, "gemini-2.5-pro", "pro")
            assert service.is_allowed(ProviderType.GOOGLE, "gemini-2.5-pro", "Pro")


class TestFlashModelRegressionPrevention:
    """Comprehensive regression prevention tests for Flash model issues."""

    def setup_method(self):
        """Set up clean state before each test."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None
        ModelProviderRegistry.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None
        ModelProviderRegistry.clear_cache()

    def test_end_to_end_flash_model_access(self):
        """End-to-end test of Flash model access through the complete stack."""
        with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": "flash,pro", "GOOGLE_API_KEY": "test-key"}):
            # Clear and reinitialize everything
            ModelProviderRegistry._instance = None
            ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)

            # Test 1: Registry shows Flash models
            available_models = ModelProviderRegistry.get_available_models(respect_restrictions=True)
            assert "flash" in available_models, "Flash alias should be in registry"

            # Test 2: Can create ModelContext
            ctx = ModelContext("flash")
            assert ctx is not None, "Should create ModelContext for Flash"
            assert isinstance(ctx.provider, GeminiModelProvider), "Should use Gemini provider"

            # Test 3: Provider validates correctly
            provider = ctx.provider
            assert provider.validate_model_name("flash"), "Provider should validate Flash alias"

            # Test 4: Can get capabilities
            capabilities = provider.get_capabilities("flash")
            assert capabilities.model_name == "gemini-2.5-flash", "Should return canonical model name"
            assert capabilities.provider == ProviderType.GOOGLE, "Should have correct provider type"

    def test_alias_parameter_order_regression_comprehensive(self):
        """Comprehensive test to prevent parameter order regression in all cases."""
        test_cases = [
            # (allowed_models, test_alias, expected_result, description)
            ("flash", "flash", True, "Flash alias allowed directly"),
            ("gemini-2.5-flash", "flash", True, "Flash alias resolves to allowed canonical name"),
            ("flash", "gemini-2.5-flash", False, "Canonical name NOT allowed when only alias is allowed"),
            ("pro", "flash", False, "Flash alias not allowed when only pro allowed"),
            ("flash,pro", "flash", True, "Flash alias allowed in multi-model restriction"),
            ("flash,pro", "pro", True, "Pro alias allowed in multi-model restriction"),
        ]

        for allowed_models, test_alias, expected, description in test_cases:
            with patch.dict(os.environ, {"GOOGLE_ALLOWED_MODELS": allowed_models}):
                # Clear state
                import utils.model_restrictions

                utils.model_restrictions._restriction_service = None

                provider = GeminiModelProvider(api_key="test-key")

                # Test validation
                result = provider.validate_model_name(test_alias)
                assert result == expected, f"Case: {description} - Expected {expected}, got {result}"

    def test_comprehensive_flash_scenarios(self):
        """Test various Flash model scenarios comprehensively."""
        scenarios = [
            # (restriction, should_have_flash, description)
            (None, True, "No restrictions"),
            ("", True, "Empty restrictions"),
            ("pro", False, "Pro only"),
            ("flash", True, "Flash only"),
            ("flash,pro", True, "Flash and Pro"),
        ]

        for restriction, should_have_flash, description in scenarios:
            env_dict = {}
            if restriction is not None:
                env_dict["GOOGLE_ALLOWED_MODELS"] = restriction

            with patch.dict(os.environ, env_dict, clear=True):
                # Clear state
                import utils.model_restrictions

                utils.model_restrictions._restriction_service = None

                provider = GeminiModelProvider(api_key="test-key")
                available_models = provider.list_models(respect_restrictions=True)
                flash_models = [m for m in available_models if "flash" in m.lower()]
                has_flash = len(flash_models) > 0

                assert (
                    has_flash == should_have_flash
                ), f"Scenario '{description}': Expected flash={should_have_flash}, got {has_flash}. Models: {available_models}"
