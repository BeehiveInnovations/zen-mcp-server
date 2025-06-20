"""Test listmodels tool respects model restrictions."""

import os
import json
import unittest
from unittest.mock import patch, MagicMock

from tools.listmodels import ListModelsTool
from providers.base import ModelProvider, ProviderType
from providers.registry import ModelProviderRegistry


class TestListModelsRestrictions(unittest.TestCase):
    """Test that listmodels respects OPENROUTER_ALLOWED_MODELS."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing registry state
        ModelProviderRegistry.clear_cache()
        
        # Create mock OpenRouter provider
        self.mock_openrouter = MagicMock(spec=ModelProvider)
        self.mock_openrouter.provider_type = ProviderType.OPENROUTER
        
        # Create mock Gemini provider for comparison
        self.mock_gemini = MagicMock(spec=ModelProvider)
        self.mock_gemini.provider_type = ProviderType.GOOGLE
        self.mock_gemini.list_models.return_value = ["gemini-2.5-flash", "gemini-2.5-pro"]

    def tearDown(self):
        """Clean up after tests."""
        ModelProviderRegistry.clear_cache()
        # Clean up environment variables
        for key in ["OPENROUTER_ALLOWED_MODELS", "OPENROUTER_API_KEY", "GEMINI_API_KEY"]:
            os.environ.pop(key, None)

    @patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key",
        "OPENROUTER_ALLOWED_MODELS": "opus,sonnet,haiku",
        "GEMINI_API_KEY": "gemini-test-key"
    })
    def test_listmodels_respects_openrouter_restrictions(self):
        """Test that listmodels only shows allowed OpenRouter models."""
        # Set up mock to return only allowed models when restrictions are respected
        self.mock_openrouter.list_models.return_value = [
            "anthropic/claude-3-opus-20240229",
            "anthropic/claude-3-sonnet-20240229", 
            "anthropic/claude-3-haiku-20240307"
        ]
        
        # Patch the registry to return our mocks
        with patch.object(ModelProviderRegistry, 'get_provider') as mock_get_provider:
            def get_provider_side_effect(provider_type, force_new=False):
                if provider_type == ProviderType.OPENROUTER:
                    return self.mock_openrouter
                elif provider_type == ProviderType.GOOGLE:
                    return self.mock_gemini
                return None
            
            mock_get_provider.side_effect = get_provider_side_effect
            
            # Also patch get_available_models to return restricted counts
            with patch.object(ModelProviderRegistry, 'get_available_models') as mock_get_models:
                mock_get_models.return_value = {
                    "gemini-2.5-flash": ProviderType.GOOGLE,
                    "gemini-2.5-pro": ProviderType.GOOGLE,
                    "anthropic/claude-3-opus-20240229": ProviderType.OPENROUTER,
                    "anthropic/claude-3-sonnet-20240229": ProviderType.OPENROUTER,
                    "anthropic/claude-3-haiku-20240307": ProviderType.OPENROUTER
                }
                
                # Create tool and execute
                tool = ListModelsTool()
                result = tool._execute()
                
                # Parse the output
                lines = result.split('\n')
                
                # Check that OpenRouter section exists and shows restrictions
                openrouter_section_found = False
                openrouter_models = []
                in_openrouter_section = False
                
                for line in lines:
                    if "OpenRouter Models" in line:
                        openrouter_section_found = True
                        in_openrouter_section = True
                    elif in_openrouter_section and line.strip().startswith('- '):
                        # Extract model name from line like "- anthropic/claude-3-opus-20240229 (opus)"
                        model_name = line.strip()[2:].split(' ')[0]
                        openrouter_models.append(model_name)
                    elif in_openrouter_section and not line.strip():
                        # Empty line ends the section
                        in_openrouter_section = False
                
                self.assertTrue(openrouter_section_found, "OpenRouter section not found")
                self.assertEqual(len(openrouter_models), 3, f"Expected 3 models, got {len(openrouter_models)}")
                
                # Verify the models are the allowed ones
                expected_models = [
                    "anthropic/claude-3-opus-20240229",
                    "anthropic/claude-3-sonnet-20240229",
                    "anthropic/claude-3-haiku-20240307"
                ]
                for model in expected_models:
                    self.assertIn(model, openrouter_models, f"Expected model {model} not found")
                
                # Verify list_models was called with respect_restrictions=True
                self.mock_openrouter.list_models.assert_called_with(respect_restrictions=True)
                
                # Check for restriction note
                self.assertIn("restricted", result.lower(), "No restriction note found")

    @patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key",
        "GEMINI_API_KEY": "gemini-test-key"
    })
    def test_listmodels_shows_all_models_without_restrictions(self):
        """Test that listmodels shows all models when no restrictions are set."""
        # Set up mock to return many models when no restrictions
        all_models = [f"model-{i}" for i in range(50)]  # Simulate 50 models
        self.mock_openrouter.list_models.return_value = all_models
        
        # Patch the registry to return our mocks
        with patch.object(ModelProviderRegistry, 'get_provider') as mock_get_provider:
            def get_provider_side_effect(provider_type, force_new=False):
                if provider_type == ProviderType.OPENROUTER:
                    return self.mock_openrouter
                elif provider_type == ProviderType.GOOGLE:
                    return self.mock_gemini
                return None
            
            mock_get_provider.side_effect = get_provider_side_effect
            
            # Create tool and execute
            tool = ListModelsTool()
            result = tool._execute()
            
            # Should show all 50 models
            model_count = result.count("model-")
            self.assertEqual(model_count, 50, f"Expected 50 models, found {model_count}")
            
            # Verify list_models was called with respect_restrictions=True
            # (even without restrictions, we always pass True)
            self.mock_openrouter.list_models.assert_called_with(respect_restrictions=True)


if __name__ == "__main__":
    unittest.main()