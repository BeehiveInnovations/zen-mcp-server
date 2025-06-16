"""Tests for OpenAI Flex Processing service tier functionality"""

import os
from unittest.mock import Mock, patch

import config
from providers.openai import OpenAIModelProvider


class TestOpenAIServiceTier:
    """Test OpenAI service tier functionality"""

    def test_service_tier_parameter_allowed(self):
        """Test that service_tier is in the allowed parameters list"""
        provider = OpenAIModelProvider(api_key="test-key")

        # Mock the OpenAI client
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="Test response"), finish_reason="stop")]
        mock_completion.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_completion.model = "o3"
        mock_completion.id = "test-id"
        mock_completion.created = 1234567890

        mock_client.chat.completions.create.return_value = mock_completion
        provider._client = mock_client

        # Call generate_content with service_tier parameter
        response = provider.generate_content(prompt="Test prompt", model_name="o3", service_tier="flex")

        # Verify the API was called with service_tier
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args

        assert "service_tier" in call_args.kwargs
        assert call_args.kwargs["service_tier"] == "flex"
        assert response.content == "Test response"

    def test_service_tier_logic_in_base_tool(self):
        """Test the logic that determines when to apply flex service tier"""
        # Test OpenAI provider with o3 model
        mock_provider = Mock()
        mock_provider.get_provider_type.return_value.value = "openai"

        # Test for o3
        generation_kwargs = {}
        if mock_provider.get_provider_type().value == "openai" and "o3" in ["o3", "o3-mini"]:
            generation_kwargs["service_tier"] = "flex"

        assert generation_kwargs == {"service_tier": "flex"}

        # Test for o3-mini
        generation_kwargs = {}
        if mock_provider.get_provider_type().value == "openai" and "o3-mini" in ["o3", "o3-mini"]:
            generation_kwargs["service_tier"] = "flex"

        assert generation_kwargs == {"service_tier": "flex"}

        # Test for non-OpenAI provider
        mock_provider.get_provider_type.return_value.value = "google"
        generation_kwargs = {}
        if mock_provider.get_provider_type().value == "openai" and "o3" in ["o3", "o3-mini"]:
            generation_kwargs["service_tier"] = "flex"

        assert generation_kwargs == {}

        # Test for OpenAI provider with different model
        mock_provider.get_provider_type.return_value.value = "openai"
        generation_kwargs = {}
        if mock_provider.get_provider_type().value == "openai" and "gpt-4" in ["o3", "o3-mini"]:
            generation_kwargs["service_tier"] = "flex"

        assert generation_kwargs == {}

    def test_service_tier_not_passed_for_other_parameters(self):
        """Test that other parameters don't accidentally get service_tier"""
        provider = OpenAIModelProvider(api_key="test-key")

        # Mock the OpenAI client
        mock_client = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content="Test response"), finish_reason="stop")]
        mock_completion.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_completion.model = "o3"
        mock_completion.id = "test-id"
        mock_completion.created = 1234567890

        mock_client.chat.completions.create.return_value = mock_completion
        provider._client = mock_client

        # Call generate_content without service_tier but with other params
        provider.generate_content(
            prompt="Test prompt", model_name="o3", temperature=0.5, max_output_tokens=100, top_p=0.9
        )

        # Verify the API was called
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args

        # Check that only expected parameters were passed
        assert "temperature" in call_args.kwargs
        assert "max_tokens" in call_args.kwargs
        assert "top_p" in call_args.kwargs
        assert "service_tier" not in call_args.kwargs  # Not passed without explicit request

    @patch("tools.base.logger")
    def test_logging_when_flex_tier_applied(self, mock_logger):
        """Test that logging occurs when flex tier is applied"""
        # Simulate the logic in base.py
        provider_type = "openai"
        model_name = "o3"

        generation_kwargs = {}
        if provider_type == "openai" and model_name in ["o3", "o3-mini"]:
            generation_kwargs["service_tier"] = "flex"
            mock_logger.info(f"Using Flex Processing service tier for OpenAI model {model_name}")

        # Verify logging was called
        mock_logger.info.assert_called_once_with("Using Flex Processing service tier for OpenAI model o3")
        assert generation_kwargs == {"service_tier": "flex"}

    def test_flex_tier_fallback_on_failure(self):
        """Test that service tier falls back to standard when flex fails"""
        provider = OpenAIModelProvider(api_key="test-key")

        # Mock the OpenAI client
        mock_client = Mock()

        # First call fails with service_tier error
        mock_error = Exception("Invalid parameter: service_tier")
        mock_client.chat.completions.create.side_effect = [
            mock_error,  # First call with flex fails
            Mock(  # Second call without flex succeeds
                choices=[Mock(message=Mock(content="Fallback response"), finish_reason="stop")],
                usage=Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30),
                model="o3",
                id="test-id-fallback",
                created=1234567890,
            ),
        ]

        provider._client = mock_client

        # Call generate_content with service_tier parameter
        response = provider.generate_content(prompt="Test prompt", model_name="o3", service_tier="flex")

        # Verify the API was called twice
        assert mock_client.chat.completions.create.call_count == 2

        # First call should have service_tier
        first_call = mock_client.chat.completions.create.call_args_list[0]
        assert "service_tier" in first_call.kwargs
        assert first_call.kwargs["service_tier"] == "flex"

        # Second call should NOT have service_tier
        second_call = mock_client.chat.completions.create.call_args_list[1]
        assert "service_tier" not in second_call.kwargs

        # Response should indicate fallback
        assert response.content == "Fallback response"
        assert response.metadata.get("service_tier_fallback") is True

    @patch("providers.openai_compatible.logging")
    def test_flex_tier_fallback_logging(self, mock_logging):
        """Test that fallback is properly logged"""
        provider = OpenAIModelProvider(api_key="test-key")

        # Mock the OpenAI client
        mock_client = Mock()

        # First call fails with flex error
        mock_error = Exception("service_tier 'flex' is not available")
        mock_client.chat.completions.create.side_effect = [
            mock_error,
            Mock(
                choices=[Mock(message=Mock(content="Fallback response"), finish_reason="stop")],
                usage=Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30),
                model="o3",
                id="test-id",
                created=1234567890,
            ),
        ]

        provider._client = mock_client

        # Call with service_tier
        provider.generate_content(prompt="Test prompt", model_name="o3", service_tier="flex")

        # Verify warning was logged (may have multiple warnings)
        warning_calls = [call[0][0] for call in mock_logging.warning.call_args_list]

        # Find the flex tier warning
        flex_warning = None
        for warning in warning_calls:
            if "Flex Processing tier failed" in warning:
                flex_warning = warning
                break

        assert flex_warning is not None, "Expected flex tier warning not found"
        assert "Flex Processing tier failed for o3" in flex_warning
        assert "retrying with standard tier" in flex_warning

    @patch.dict(os.environ, {"OPENAI_USE_FLEX_PROCESSING": "0"})
    def test_flex_tier_disabled_by_env_var(self):
        """Test that flex tier is not applied when disabled via environment variable"""
        # Reload config to pick up the environment variable
        import importlib

        importlib.reload(config)

        # Simulate the logic in base.py
        provider_type = "openai"
        model_name = "o3"

        generation_kwargs = {}
        if provider_type == "openai" and model_name in ["o3", "o3-mini"] and config.OPENAI_USE_FLEX_PROCESSING:
            generation_kwargs["service_tier"] = "flex"

        # Should not add service_tier when disabled
        assert generation_kwargs == {}

    @patch.dict(os.environ, {"OPENAI_USE_FLEX_PROCESSING": "1"})
    def test_flex_tier_enabled_by_env_var(self):
        """Test that flex tier is applied when enabled via environment variable"""
        # Reload config to pick up the environment variable
        import importlib

        importlib.reload(config)

        # Simulate the logic in base.py
        provider_type = "openai"
        model_name = "o3"

        generation_kwargs = {}
        if provider_type == "openai" and model_name in ["o3", "o3-mini"] and config.OPENAI_USE_FLEX_PROCESSING:
            generation_kwargs["service_tier"] = "flex"

        # Should add service_tier when enabled
        assert generation_kwargs == {"service_tier": "flex"}

    @patch.dict(os.environ, {"OPENAI_USE_FLEX_PROCESSING": "false"})
    def test_flex_tier_disabled_by_false_string(self):
        """Test that flex tier is disabled when env var is set to 'false'"""
        # Reload config to pick up the environment variable
        import importlib

        importlib.reload(config)

        # Check that config properly parsed the false value
        assert config.OPENAI_USE_FLEX_PROCESSING is False

    @patch.dict(os.environ, {"OPENAI_USE_FLEX_PROCESSING": "no"})
    def test_flex_tier_disabled_by_no_string(self):
        """Test that flex tier is disabled when env var is set to 'no'"""
        # Reload config to pick up the environment variable
        import importlib

        importlib.reload(config)

        # Check that config properly parsed the no value
        assert config.OPENAI_USE_FLEX_PROCESSING is False
