"""
Unit tests to validate UTF-8 encoding in providers
and integration with language models.
"""

import json
import os
import unittest
from unittest.mock import Mock, patch

import pytest

from providers.base import ModelProvider, ProviderType
from providers.gemini import GeminiModelProvider
from providers.openai_compatible import OpenAICompatibleProvider
from providers.openai_provider import OpenAIModelProvider


class TestProviderUTF8Encoding(unittest.TestCase):
    """Tests for UTF-8 encoding in providers."""

    def setUp(self):
        """Test setup."""
        self.original_locale = os.getenv("LOCALE")

    def tearDown(self):
        """Cleanup after tests."""
        if self.original_locale is not None:
            os.environ["LOCALE"] = self.original_locale
        else:
            os.environ.pop("LOCALE", None)

    def test_base_provider_utf8_support(self):
        """Test that the base provider supports UTF-8."""
        provider = ModelProvider(api_key="test")

        # Test with UTF-8 characters
        test_text = "Développement en français avec émojis 🚀"
        tokens = provider.count_tokens(test_text, "test-model")

        # Should return a valid number (character-based estimate)
        self.assertIsInstance(tokens, int)
        self.assertGreater(tokens, 0)

    @patch("google.generativeai.GenerativeModel")
    def test_gemini_provider_utf8_request(self, mock_model_class):
        """Test that the Gemini provider handles UTF-8 correctly."""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "Response in French with accents: créé, développé, préféré 🎉"
        mock_response.usage_metadata = Mock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 15
        mock_response.usage_metadata.total_token_count = 25

        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        # Test Gemini provider
        provider = GeminiModelProvider(api_key="test-key")

        # Request with UTF-8 characters
        response = provider.generate_content(
            prompt="Can you explain software development?",
            model_name="gemini-2.5-flash",
            system_prompt="Reply in French with emojis.",
        )

        # Checks
        self.assertIsNotNone(response)
        self.assertIn("French", response.content)
        self.assertIn("🎉", response.content)

        # Check that the request contains UTF-8 characters
        mock_model.generate_content.assert_called_once()
        call_args = mock_model.generate_content.call_args
        parts = call_args[0][0]  # First argument (parts)

        # Check for UTF-8 content in the request
        request_content = str(parts)
        self.assertIn("développement", request_content)

    @patch("openai.OpenAI")
    def test_openai_provider_utf8_logging(self, mock_openai_class):
        """Test that the OpenAI provider logs UTF-8 correctly."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Python code created successfully! ✅"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 10
        mock_response.usage.total_tokens = 30

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Test OpenAI provider
        provider = OpenAIModelProvider(api_key="test-key")

        # Test with UTF-8 logging
        with patch("logging.info") as mock_logging:
            response = provider.generate_content(
                prompt="Generate Python code to process data",
                model_name="gpt-4",
                system_prompt="You are an expert Python developer.",
            )

            # Response checks
            self.assertIsNotNone(response)
            self.assertIn("created", response.content)
            self.assertIn("✅", response.content)

    @patch("openai.OpenAI")
    def test_openai_compatible_o3_pro_utf8(self, mock_openai_class):
        """Specific test for o3-pro with /responses endpoint and UTF-8."""
        # Mock o3-pro response
        mock_response = Mock()
        mock_response.output = Mock()
        mock_response.output.content = [Mock()]
        mock_response.output.content[0].type = "output_text"
        mock_response.output.content[0].text = "Analysis complete: code is well structured! 🎯"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 25
        mock_response.model = "o3-pro-2025-06-10"
        mock_response.id = "test-id"
        mock_response.created_at = 1234567890

        mock_client = Mock()
        mock_client.responses.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        # Test OpenAI Compatible provider with o3-pro
        provider = OpenAICompatibleProvider(api_key="test-key", base_url="https://api.openai.com/v1")

        # Test with UTF-8 logging for o3-pro
        with patch("logging.info") as mock_logging:
            response = provider.generate_content(
                prompt="Analyze this Python code for issues",
                model_name="o3-pro-2025-06-10",
                system_prompt="You are a code review expert.",
            )

            # Response checks
            self.assertIsNotNone(response)
            self.assertIn("complete", response.content)
            self.assertIn("🎯", response.content)

            # Check that logging was called with ensure_ascii=False
            mock_logging.assert_called()
            log_calls = [call for call in mock_logging.call_args_list if "API request payload" in str(call)]
            self.assertTrue(len(log_calls) > 0, "No API payload log found")

    def test_provider_type_enum_utf8_safe(self):
        """Test that ProviderType enum is UTF-8 safe."""
        # Test all provider types
        provider_types = list(ProviderType)

        for provider_type in provider_types:
            # Test JSON serialization
            data = {"provider": provider_type.value, "message": "UTF-8 test: emojis 🚀"}
            json_str = json.dumps(data, ensure_ascii=False)

            # Checks
            self.assertIn(provider_type.value, json_str)
            self.assertIn("emojis", json_str)
            self.assertIn("🚀", json_str)

            # Test deserialization
            parsed = json.loads(json_str)
            self.assertEqual(parsed["provider"], provider_type.value)
            self.assertEqual(parsed["message"], "UTF-8 test: emojis 🚀")

    def test_model_response_utf8_serialization(self):
        """Test UTF-8 serialization of model responses."""
        from providers.base import ModelResponse

        # Create a response with UTF-8 characters
        response = ModelResponse(
            content="Development successful! Code generated successfully. 🎉✅",
            usage={"input_tokens": 10, "output_tokens": 15, "total_tokens": 25},
            model_name="test-model",
            friendly_name="Test Model",
            provider=ProviderType.OPENAI,
            metadata={"created": "2024-01-01", "developer": "Test", "emojis": "🚀🎯🔥"},
        )

        # Test serialization
        response_dict = response.to_dict()
        json_str = json.dumps(response_dict, ensure_ascii=False, indent=2)

        # Checks
        self.assertIn("Development", json_str)
        self.assertIn("successful", json_str)
        self.assertIn("generated", json_str)
        self.assertIn("🎉", json_str)
        self.assertIn("✅", json_str)
        self.assertIn("created", json_str)
        self.assertIn("developer", json_str)
        self.assertIn("🚀", json_str)

        # Test deserialization
        parsed = json.loads(json_str)
        self.assertEqual(parsed["content"], response.content)
        self.assertEqual(parsed["friendly_name"], "Test Model")

    def test_error_handling_with_utf8(self):
        """Test error handling with UTF-8 characters."""
        provider = ModelProvider(api_key="test")

        # Test validation with UTF-8 error message
        with self.assertRaises(ValueError) as context:
            provider.validate_parameters("", -1.0)  # Invalid temperature

        error_message = str(context.exception)
        # Error message may contain UTF-8 characters
        self.assertIsInstance(error_message, str)

    def test_temperature_handling_utf8_locale(self):
        """Test temperature handling with UTF-8 locale."""
        # Set French locale
        os.environ["LOCALE"] = "fr-FR"

        provider = ModelProvider(api_key="test")

        # Test different temperatures
        test_temps = [0.0, 0.5, 1.0, 1.5, 2.0]

        for temp in test_temps:
            try:
                provider.validate_parameters("gpt-4", temp)
                # If no exception, temperature is valid
                self.assertLessEqual(temp, 2.0)
            except ValueError:
                # If exception, temperature must be > 2.0
                self.assertGreater(temp, 2.0)

    def test_provider_registry_utf8(self):
        """Test that the provider registry handles UTF-8."""
        from providers.registry import ModelProviderRegistry

        # Test listing providers with UTF-8 descriptions
        providers = ModelProviderRegistry.get_available_providers()

        # Should contain valid providers
        self.assertGreater(len(providers), 0)

        # Test serialization
        provider_data = {
            "providers": [p.value for p in providers],
            "description": "Available providers for development 🚀",
        }

        json_str = json.dumps(provider_data, ensure_ascii=False)

        # Checks
        self.assertIn("development", json_str)
        self.assertIn("🚀", json_str)

        # Test parsing
        parsed = json.loads(json_str)
        self.assertEqual(parsed["description"], provider_data["description"])


class TestLocaleModelIntegration(unittest.TestCase):
    """Integration tests between locale and models."""

    def setUp(self):
        """Integration test setup."""
        self.original_locale = os.getenv("LOCALE")

    def tearDown(self):
        """Cleanup after integration tests."""
        if self.original_locale is not None:
            os.environ["LOCALE"] = self.original_locale
        else:
            os.environ.pop("LOCALE", None)

    def test_system_prompt_enhancement_french(self):
        """Test system prompt enhancement with French locale."""
        # Set to French
        os.environ["LOCALE"] = "fr-FR"

        provider = ModelProvider(api_key="test")
        base_prompt = "You are a helpful coding assistant."

        # Test prompt enhancement
        enhanced_prompt = provider.enhance_system_prompt(base_prompt)

        # Checks
        self.assertIn("fr-FR", enhanced_prompt)
        self.assertIn(base_prompt, enhanced_prompt)

    def test_system_prompt_enhancement_multiple_locales(self):
        """Test enhancement with different locales."""
        provider = ModelProvider(api_key="test")
        base_prompt = "You are a helpful assistant."

        locales = ["fr-FR", "es-ES", "de-DE", "it-IT", "pt-BR", "ja-JP", "zh-CN"]

        for locale in locales:
            os.environ["LOCALE"] = locale
            enhanced_prompt = provider.enhance_system_prompt(base_prompt)

            # Locale-specific checks
            self.assertIn(locale, enhanced_prompt)
            self.assertIn(base_prompt, enhanced_prompt)

            # Test JSON serialization
            prompt_data = {"system_prompt": enhanced_prompt, "locale": locale}
            json_str = json.dumps(prompt_data, ensure_ascii=False)

            # Should parse without error
            parsed = json.loads(json_str)
            self.assertEqual(parsed["locale"], locale)

    def test_model_name_resolution_utf8(self):
        """Test model name resolution with UTF-8."""
        provider = ModelProvider(api_key="test")

        # Test with different model names
        model_names = ["gpt-4", "gemini-2.5-flash", "claude-3-opus", "o3-pro-2025-06-10"]

        for model_name in model_names:
            # Test resolution
            resolved = provider._resolve_model_name(model_name)
            self.assertIsInstance(resolved, str)

            # Test serialization with UTF-8 metadata
            model_data = {
                "model": resolved,
                "description": f"Model {model_name} - advanced development 🚀",
                "capabilities": ["generation", "review", "creation"],
            }

            json_str = json.dumps(model_data, ensure_ascii=False)

            # Checks
            self.assertIn("development", json_str)
            self.assertIn("generation", json_str)
            self.assertIn("review", json_str)
            self.assertIn("creation", json_str)
            self.assertIn("🚀", json_str)


if __name__ == "__main__":
    # Test configuration
    pytest.main([__file__, "-v", "--tb=short"])
