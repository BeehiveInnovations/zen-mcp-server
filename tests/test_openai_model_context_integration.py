"""Tests for OpenAI ModelContext token estimation integration."""

import unittest
from unittest.mock import Mock, patch

from utils.model_context import ModelContext


class TestOpenAIModelContextIntegration(unittest.TestCase):
    """Test OpenAI token estimation integration with ModelContext."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_openai_provider = Mock()
        self.mock_openai_provider.get_capabilities.return_value = Mock(
            context_window=200_000,
            max_output_tokens=16_000,
        )

    def test_estimate_tokens_with_openai_provider(self):
        """Test estimate_tokens calls OpenAI provider's text tokenization."""
        # Setup mock provider with _calculate_text_tokens method
        self.mock_openai_provider._calculate_text_tokens.return_value = 15

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            model_context = ModelContext("gpt-4o")

            tokens = model_context.estimate_tokens("Hello, world!")

            # Should call provider's text token calculation
            self.assertEqual(tokens, 15)
            self.mock_openai_provider._calculate_text_tokens.assert_called_once_with("gpt-4o", "Hello, world!")

    def test_estimate_tokens_fallback_when_provider_lacks_method(self):
        """Test estimate_tokens falls back when provider doesn't have _calculate_text_tokens."""
        # Mock provider without _calculate_text_tokens attribute
        mock_provider_no_calc = Mock(spec=["get_capabilities", "generate_content"])
        mock_provider_no_calc.get_capabilities.return_value = Mock(
            context_window=200_000,
            max_output_tokens=4096,
        )

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=mock_provider_no_calc
        ):
            model_context = ModelContext("unknown-model")

            tokens = model_context.estimate_tokens("Hello, world!")

            # Should use fallback: len(text) // 4
            self.assertEqual(tokens, len("Hello, world!") // 4)

    def test_estimate_tokens_fallback_on_provider_exception(self):
        """Test estimate_tokens falls back when provider raises exception."""
        self.mock_openai_provider._calculate_text_tokens.side_effect = Exception("Tokenizer error")

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            model_context = ModelContext("gpt-4o")

            tokens = model_context.estimate_tokens("Test text")

            # Should fall back to conservative estimation (1 token ≈ 4 chars)
            self.assertEqual(tokens, len("Test text") // 4)

    def test_estimate_file_tokens_with_openai_provider_image(self):
        """Test estimate_file_tokens calls OpenAI provider for image files."""
        # Setup mock provider with estimate_tokens_for_files method
        self.mock_openai_provider.estimate_tokens_for_files.return_value = 255

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            model_context = ModelContext("gpt-4o")

            tokens = model_context.estimate_file_tokens("/path/to/image.jpg")

            # Should call provider's file estimation
            self.assertEqual(tokens, 255)
            self.mock_openai_provider.estimate_tokens_for_files.assert_called_once()

            # Verify the call arguments
            call_args = self.mock_openai_provider.estimate_tokens_for_files.call_args
            model_name, files = call_args[0]
            self.assertEqual(model_name, "gpt-4o")
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["path"], "/path/to/image.jpg")
            self.assertEqual(files[0]["mime_type"], "image/jpeg")

    def test_estimate_file_tokens_with_openai_provider_audio(self):
        """Test estimate_file_tokens calls OpenAI provider for audio files (GPT-4o)."""
        # Setup mock provider for GPT-4o with audio support
        self.mock_openai_provider.estimate_tokens_for_files.return_value = 100

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            model_context = ModelContext("gpt-4o")

            tokens = model_context.estimate_file_tokens("/path/to/audio.mp3")

            # Should call provider's estimation
            self.assertEqual(tokens, 100)
            call_args = self.mock_openai_provider.estimate_tokens_for_files.call_args
            files = call_args[0][1]
            self.assertEqual(files[0]["mime_type"], "audio/mpeg")

    def test_estimate_file_tokens_fallback_when_provider_lacks_method(self):
        """Test estimate_file_tokens falls back when provider doesn't have estimation method."""
        # Mock provider without estimate_tokens_for_files attribute
        mock_provider_no_estimation = Mock(spec=["get_capabilities", "generate_content"])
        mock_provider_no_estimation.get_capabilities.return_value = Mock(
            context_window=200_000,
            max_output_tokens=4096,
        )

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=mock_provider_no_estimation
        ):
            with patch("utils.file_utils.estimate_file_tokens", return_value=100) as mock_fallback:
                model_context = ModelContext("gpt-5")

                tokens = model_context.estimate_file_tokens("/path/to/file.txt")

                # Should use fallback
                self.assertEqual(tokens, 100)
                mock_fallback.assert_called_once_with("/path/to/file.txt")

    def test_estimate_file_tokens_fallback_on_provider_exception(self):
        """Test estimate_file_tokens falls back when provider raises exception."""
        self.mock_openai_provider.estimate_tokens_for_files.side_effect = ValueError("Unsupported file type")

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            with patch("utils.file_utils.estimate_file_tokens", return_value=150) as mock_fallback:
                model_context = ModelContext("gpt-4o")

                tokens = model_context.estimate_file_tokens("/path/to/video.mp4")

                # Should fall back to file_utils estimation
                self.assertEqual(tokens, 150)
                mock_fallback.assert_called_once_with("/path/to/video.mp4")

    def test_estimate_file_tokens_fallback_when_provider_returns_none(self):
        """Test estimate_file_tokens falls back when provider returns None."""
        self.mock_openai_provider.estimate_tokens_for_files.return_value = None

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            with patch("utils.file_utils.estimate_file_tokens", return_value=200) as mock_fallback:
                model_context = ModelContext("gpt-4o")

                tokens = model_context.estimate_file_tokens("/path/to/unknown.xyz")

                # Should fall back when provider returns None
                self.assertEqual(tokens, 200)
                mock_fallback.assert_called_once_with("/path/to/unknown.xyz")

    def test_estimate_file_tokens_fallback_for_unknown_mime_type(self):
        """Test estimate_file_tokens uses fallback for files without detectable mime type."""
        # Mock provider to return None for unknown mime types (triggers fallback)
        self.mock_openai_provider.estimate_tokens_for_files.return_value = None

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            with patch("utils.file_utils.estimate_file_tokens", return_value=300) as mock_fallback:
                model_context = ModelContext("gpt-4o")

                # File without extension will get "text/plain" mime type, provider returns None
                tokens = model_context.estimate_file_tokens("/path/to/noext")

                # Should use fallback when provider returns None
                self.assertEqual(tokens, 300)
                mock_fallback.assert_called_once_with("/path/to/noext")

    def test_openai_text_tokens_more_accurate_than_fallback(self):
        """Test that OpenAI provider tokenization is more accurate than simple fallback."""
        # This is a conceptual test - actual token counts depend on tiktoken
        text = "The quick brown fox jumps over the lazy dog."

        # Mock OpenAI provider with realistic token count (using tiktoken logic)
        self.mock_openai_provider._calculate_text_tokens.return_value = 10

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            model_context = ModelContext("gpt-4o")

            tokens = model_context.estimate_tokens(text)

            # Provider tokenization (10) should be different from fallback (len//4 = 11)
            self.assertEqual(tokens, 10)
            self.assertNotEqual(tokens, len(text) // 4)

    def test_unsupported_content_type_propagates_error(self):
        """Test that UnsupportedContentTypeError is propagated, not caught for fallback."""
        from utils.openai_token_estimator import UnsupportedContentTypeError

        # Setup OpenAI provider that raises UnsupportedContentTypeError for audio on GPT-5
        self.mock_openai_provider.estimate_tokens_for_files.side_effect = UnsupportedContentTypeError(
            "gpt-5", "audio files", "/path/to/audio.mp3"
        )

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            with patch("utils.file_utils.estimate_file_tokens") as mock_fallback:
                model_context = ModelContext("gpt-5")

                # Should raise UnsupportedContentTypeError, NOT use fallback
                with self.assertRaises(UnsupportedContentTypeError) as context:
                    model_context.estimate_file_tokens("/path/to/audio.mp3")

                # Verify the error message
                self.assertIn("gpt-5", str(context.exception))
                self.assertIn("audio files", str(context.exception))

                # Verify fallback was NOT called
                mock_fallback.assert_not_called()

    def test_regular_errors_still_use_fallback(self):
        """Test that regular errors (not UnsupportedContentTypeError) still use fallback."""
        # Setup provider to raise a regular ValueError
        self.mock_openai_provider.estimate_tokens_for_files.side_effect = ValueError("Some other error")

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model", return_value=self.mock_openai_provider
        ):
            with patch("utils.file_utils.estimate_file_tokens", return_value=200) as mock_fallback:
                model_context = ModelContext("gpt-4o")

                # Regular errors should still use fallback
                tokens = model_context.estimate_file_tokens("/path/to/file.txt")

                # Should use fallback
                self.assertEqual(tokens, 200)
                mock_fallback.assert_called_once_with("/path/to/file.txt")


class TestOpenRouterIntegration(unittest.TestCase):
    """Test OpenRouter's multi-provider routing for OpenAI models."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_openrouter_provider = Mock()
        self.mock_openrouter_provider.get_capabilities.return_value = Mock(
            context_window=200_000,
            max_output_tokens=16_000,
        )

    def test_openrouter_routes_openai_models_correctly(self):
        """Test that OpenRouter routes OpenAI models to OpenAI estimator."""
        # Setup OpenRouter provider with routing logic
        self.mock_openrouter_provider._calculate_text_tokens.return_value = 25

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model",
            return_value=self.mock_openrouter_provider,
        ):
            model_context = ModelContext("openai/gpt-4o")

            tokens = model_context.estimate_tokens("OpenRouter test text")

            # Should call OpenRouter's routing implementation
            self.assertEqual(tokens, 25)
            self.mock_openrouter_provider._calculate_text_tokens.assert_called_once_with(
                "openai/gpt-4o", "OpenRouter test text"
            )

    def test_openrouter_image_estimation_for_openai_models(self):
        """Test OpenRouter routes image estimation for OpenAI models."""
        self.mock_openrouter_provider.estimate_tokens_for_files.return_value = 340

        with patch(
            "utils.model_context.ModelProviderRegistry.get_provider_for_model",
            return_value=self.mock_openrouter_provider,
        ):
            model_context = ModelContext("openai/gpt-5")

            tokens = model_context.estimate_file_tokens("/path/to/large_image.png")

            # Should use OpenRouter's routing to OpenAI estimator
            self.assertEqual(tokens, 340)
            call_args = self.mock_openrouter_provider.estimate_tokens_for_files.call_args
            model_name, files = call_args[0]
            self.assertEqual(model_name, "openai/gpt-5")
            self.assertEqual(files[0]["mime_type"], "image/png")
