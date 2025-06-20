"""Test listmodels tool respects model restrictions."""

import os
import unittest
import asyncio
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
        "OPENROUTER_ALLOWED_MODELS": "opus,sonnet,deepseek/deepseek-r1-0528:free,qwen/qwen3-235b-a22b-04-28:free",
        "GEMINI_API_KEY": "gemini-test-key"
    })
    @patch('utils.model_restrictions.get_restriction_service')
    @patch('providers.openrouter_registry.OpenRouterModelRegistry')
    @patch.object(ModelProviderRegistry, 'get_available_models')
    @patch.object(ModelProviderRegistry, 'get_provider')
    def test_listmodels_respects_openrouter_restrictions(self, mock_get_provider, mock_get_models, 
                                                        mock_registry_class, mock_get_restriction):
        """Test that listmodels only shows allowed OpenRouter models."""
        # Set up mock to return only allowed models when restrictions are respected
        # Include both aliased models and full model names without aliases
        self.mock_openrouter.list_models.return_value = [
            "anthropic/claude-3-opus-20240229",  # Has alias "opus"
            "anthropic/claude-3-sonnet-20240229",  # Has alias "sonnet" 
            "deepseek/deepseek-r1-0528:free",  # No alias, full name
            "qwen/qwen3-235b-a22b-04-28:free"  # No alias, full name
        ]
        
        # Mock registry instance
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        
        # Mock resolve method - return config for aliased models, None for others
        def resolve_side_effect(model_name):
            if "opus" in model_name.lower():
                config = MagicMock()
                config.model_name = "anthropic/claude-3-opus-20240229"
                config.context_window = 200000
                return config
            elif "sonnet" in model_name.lower():
                config = MagicMock()
                config.model_name = "anthropic/claude-3-sonnet-20240229"
                config.context_window = 200000
                return config
            return None  # No config for models without aliases
        
        mock_registry.resolve.side_effect = resolve_side_effect
        
        # Mock provider registry
        def get_provider_side_effect(provider_type, force_new=False):
            if provider_type == ProviderType.OPENROUTER:
                return self.mock_openrouter
            elif provider_type == ProviderType.GOOGLE:
                return self.mock_gemini
            return None
        
        mock_get_provider.side_effect = get_provider_side_effect
        
        # Mock available models
        mock_get_models.return_value = {
            "gemini-2.5-flash": ProviderType.GOOGLE,
            "gemini-2.5-pro": ProviderType.GOOGLE,
            "anthropic/claude-3-opus-20240229": ProviderType.OPENROUTER,
            "anthropic/claude-3-sonnet-20240229": ProviderType.OPENROUTER,
            "deepseek/deepseek-r1-0528:free": ProviderType.OPENROUTER,
            "qwen/qwen3-235b-a22b-04-28:free": ProviderType.OPENROUTER
        }
        
        # Mock restriction service
        mock_restriction_service = MagicMock()
        mock_restriction_service.has_restrictions.return_value = True
        mock_restriction_service.get_allowed_models.return_value = {
            "opus", "sonnet", "deepseek/deepseek-r1-0528:free", "qwen/qwen3-235b-a22b-04-28:free"
        }
        mock_get_restriction.return_value = mock_restriction_service
        
        # Create tool and execute
        tool = ListModelsTool()
        # Execute asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result_contents = loop.run_until_complete(tool.execute({}))
        loop.close()
        
        # Extract text content from result
        result_text = result_contents[0].text
        
        # Parse JSON response
        import json
        result_json = json.loads(result_text)
        result = result_json['content']
        
        # Parse the output
        lines = result.split('\n')
        
        # Check that OpenRouter section exists
        openrouter_section_found = False
        openrouter_models = []
        in_openrouter_section = False
        
        for line in lines:
            if "OpenRouter" in line and "✅" in line:
                openrouter_section_found = True
            elif "Available Models" in line and openrouter_section_found:
                in_openrouter_section = True
            elif in_openrouter_section and line.strip().startswith('- '):
                # Extract model name from various line formats:
                # - `model-name` → `full-name` (context)
                # - `model-name`
                line_content = line.strip()[2:]  # Remove "- "
                if '`' in line_content:
                    # Extract content between first pair of backticks
                    model_name = line_content.split('`')[1]
                    openrouter_models.append(model_name)
        
        self.assertTrue(openrouter_section_found, "OpenRouter section not found")
        self.assertEqual(len(openrouter_models), 4, f"Expected 4 models, got {len(openrouter_models)}: {openrouter_models}")
        
        # Verify list_models was called with respect_restrictions=True
        self.mock_openrouter.list_models.assert_called_with(respect_restrictions=True)
        
        # Check for restriction note
        self.assertIn("Restricted to models matching:", result)

    @patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key",
        "GEMINI_API_KEY": "gemini-test-key"
    })
    @patch('providers.openrouter_registry.OpenRouterModelRegistry')
    @patch.object(ModelProviderRegistry, 'get_provider')
    def test_listmodels_shows_all_models_without_restrictions(self, mock_get_provider, mock_registry_class):
        """Test that listmodels shows all models when no restrictions are set."""
        # Set up mock to return many models when no restrictions
        all_models = [f"provider{i//10}/model-{i}" for i in range(50)]  # Simulate 50 models from different providers
        self.mock_openrouter.list_models.return_value = all_models
        
        # Mock registry instance
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry
        mock_registry.resolve.return_value = None  # No configs for simplicity
        
        # Mock provider registry
        def get_provider_side_effect(provider_type, force_new=False):
            if provider_type == ProviderType.OPENROUTER:
                return self.mock_openrouter
            elif provider_type == ProviderType.GOOGLE:
                return self.mock_gemini
            return None
        
        mock_get_provider.side_effect = get_provider_side_effect
        
        # Create tool and execute
        tool = ListModelsTool()
        # Execute asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result_contents = loop.run_until_complete(tool.execute({}))
        loop.close()
        
        # Extract text content from result
        result_text = result_contents[0].text
        
        # Parse JSON response
        import json
        result_json = json.loads(result_text)
        result = result_json['content']
        
        # Should show first 20 models (as per the code limit)
        model_count = 0
        for line in result.split('\n'):
            if line.strip().startswith('- ') and '`' in line:
                model_count += 1
        
        # The tool shows max 20 models in the output
        self.assertGreaterEqual(model_count, 15, f"Expected at least 15 models shown, found {model_count}")
        self.assertLessEqual(model_count, 20, f"Expected at most 20 models shown, found {model_count}")
        
        # Should show "and X more models available" message
        self.assertIn("more models available", result)
        
        # Verify list_models was called with respect_restrictions=True
        # (even without restrictions, we always pass True)
        self.mock_openrouter.list_models.assert_called_with(respect_restrictions=True)
        
        # Should NOT have restriction note when no restrictions are set
        self.assertNotIn("Restricted to models matching:", result)


if __name__ == "__main__":
    unittest.main()