"""Tests for Perplexity provider implementation."""

import os
from unittest.mock import patch

import pytest

from providers.base import ProviderType
from providers.perplexity_provider import PerplexityProvider


class TestPerplexityProvider:
    """Test Perplexity provider functionality."""

    def setup_method(self):
        """Set up clean state before each test."""
        # Clear restriction service cache before each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    def teardown_method(self):
        """Clean up after each test to avoid singleton issues."""
        # Clear restriction service cache after each test
        import utils.model_restrictions

        utils.model_restrictions._restriction_service = None

    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"})
    def test_initialization(self):
        """Test provider initialization."""
        provider = PerplexityProvider("test-key")
        assert provider.api_key == "test-key"
        assert provider.get_provider_type() == ProviderType.PERPLEXITY
        expected_url = "https://api.perplexity.ai"
        assert provider.base_url == expected_url

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        provider = PerplexityProvider("pplx-test-key-123")
        assert provider.api_key == "pplx-test-key-123"
        assert provider.get_provider_type() == ProviderType.PERPLEXITY

    def test_provider_type(self):
        """Test provider type is correct."""
        provider = PerplexityProvider("test-key")
        assert provider.get_provider_type() == ProviderType.PERPLEXITY

    def test_base_url_correct(self):
        """Test that base URL is set correctly for Perplexity API."""
        provider = PerplexityProvider("test-key")
        expected_url = "https://api.perplexity.ai"
        assert provider.base_url == expected_url

    def test_friendly_name(self):
        """Test provider friendly name."""
        provider = PerplexityProvider("test-key")
        assert provider.FRIENDLY_NAME == "Perplexity"

    @patch.dict(os.environ, {}, clear=True)
    def test_model_validation_implemented(self):
        """Test that model validation is now implemented."""
        provider = PerplexityProvider("test-key")

        # Should return True for valid models
        assert provider.validate_model_name("sonar") is True
        assert provider.validate_model_name("sonar-pro") is True
        assert provider.validate_model_name("sonar-reasoning") is True
        assert provider.validate_model_name("r1-1776") is True

        # Should work with aliases
        assert provider.validate_model_name("perplexity") is True

        # Should return False for invalid models
        assert provider.validate_model_name("invalid-model") is False
        assert provider.validate_model_name("gpt-4") is False

    def test_get_capabilities_implemented(self):
        """Test that get_capabilities is now implemented."""
        provider = PerplexityProvider("test-key")

        # Should work for valid models
        caps = provider.get_capabilities("sonar")
        assert caps.model_name == "sonar"
        assert caps.provider == ProviderType.PERPLEXITY
        assert caps.supports_streaming is True
        assert caps.supports_function_calling is True

        # Should work with aliases
        caps_alias = provider.get_capabilities("perplexity")
        assert caps_alias.model_name == "sonar"

        # Should raise ValueError for invalid models
        with pytest.raises(ValueError):
            provider.get_capabilities("invalid-model")

    def test_supports_thinking_mode_implemented(self):
        """Test that supports_thinking_mode is now implemented."""
        provider = PerplexityProvider("test-key")

        # Reasoning models should support thinking
        assert provider.supports_thinking_mode("sonar-reasoning") is True
        assert provider.supports_thinking_mode("sonar-reasoning-pro") is True
        assert provider.supports_thinking_mode("sonar-deep-research") is True
        assert provider.supports_thinking_mode("r1-1776") is True

        # Regular models should not support thinking
        assert provider.supports_thinking_mode("sonar") is False
        assert provider.supports_thinking_mode("sonar-pro") is False

        # Invalid models should return False
        assert provider.supports_thinking_mode("invalid-model") is False


class TestPerplexityExtensions:
    """Test Perplexity-specific extensions and parameters."""

    @pytest.fixture
    def provider(self):
        """Create a test PerplexityProvider instance."""
        return PerplexityProvider(api_key="test-key")

    def test_extract_perplexity_params_max_tokens(self, provider):
        """Test max_tokens extraction."""
        kwargs = {"max_tokens": 500}
        params = provider._extract_perplexity_params("sonar", kwargs)

        assert "max_tokens" in params
        assert params["max_tokens"] == 500

    def test_extract_perplexity_params_reasoning_effort_valid(self, provider):
        """Test reasoning effort extraction for reasoning models."""
        kwargs = {"reasoning_effort": "medium"}
        params = provider._extract_perplexity_params("sonar-reasoning", kwargs)

        assert "reasoning_effort" in params
        assert params["reasoning_effort"] == "medium"

    def test_extract_perplexity_params_reasoning_effort_ignored(self, provider):
        """Test reasoning effort is ignored for non-reasoning models."""
        kwargs = {"reasoning_effort": "medium"}
        with patch("providers.perplexity_provider.logger") as mock_logger:
            params = provider._extract_perplexity_params("sonar", kwargs)

        assert "reasoning_effort" not in params
        mock_logger.warning.assert_called_once()

    def test_extract_perplexity_params_search_domain_filter(self, provider):
        """Test search domain filter extraction."""
        kwargs = {"search_domain_filter": ["wikipedia.org", "-reddit.com"]}
        params = provider._extract_perplexity_params("sonar", kwargs)

        assert "search_domain_filter" in params
        assert params["search_domain_filter"] == ["wikipedia.org", "-reddit.com"]

    def test_extract_perplexity_params_search_recency_filter(self, provider):
        """Test search recency filter extraction."""
        kwargs = {"search_recency_filter": "week"}
        params = provider._extract_perplexity_params("sonar", kwargs)

        assert "search_recency_filter" in params
        assert params["search_recency_filter"] == "week"

    def test_extract_perplexity_params_search_mode(self, provider):
        """Test search mode extraction."""
        kwargs = {"search_mode": "high"}
        params = provider._extract_perplexity_params("sonar", kwargs)

        assert "search_mode" in params
        assert params["search_mode"] == "high"

    def test_extract_perplexity_params_date_filters(self, provider):
        """Test date filters extraction."""
        kwargs = {"search_after_date_filter": "2025-01-01", "search_before_date_filter": "2025-12-31"}
        params = provider._extract_perplexity_params("sonar", kwargs)

        assert "search_after_date_filter" in params
        assert "search_before_date_filter" in params
        assert params["search_after_date_filter"] == "2025-01-01"
        assert params["search_before_date_filter"] == "2025-12-31"

    def test_extract_perplexity_params_image_params(self, provider):
        """Test image parameters extraction."""
        kwargs = {"return_images": True, "image_domain_filter": ["unsplash.com"], "image_format_filter": ["jpg", "png"]}
        params = provider._extract_perplexity_params("sonar", kwargs)

        assert "return_images" in params
        assert "image_domain_filter" in params
        assert "image_format_filter" in params
        assert params["return_images"] is True

    def test_extract_perplexity_params_related_questions(self, provider):
        """Test related questions parameter."""
        kwargs = {"return_related_questions": True}
        params = provider._extract_perplexity_params("sonar", kwargs)

        assert "return_related_questions" in params
        assert params["return_related_questions"] is True

    def test_validate_reasoning_effort_valid(self, provider):
        """Test reasoning effort validation with valid values."""
        valid_efforts = ["low", "medium", "high"]
        for effort in valid_efforts:
            provider._validate_reasoning_effort(effort)

    def test_validate_reasoning_effort_invalid(self, provider):
        """Test reasoning effort validation with invalid values."""
        with pytest.raises(ValueError, match="reasoning_effort must be one of"):
            provider._validate_reasoning_effort("invalid")

    def test_validate_search_domain_filter_valid(self, provider):
        """Test search domain filter validation with valid domains."""
        valid_domains = ["wikipedia.org", "-reddit.com", "github.com"]
        provider._validate_search_domain_filter(valid_domains)

    def test_validate_search_domain_filter_invalid(self, provider):
        """Test search domain filter validation with invalid inputs."""
        with pytest.raises(ValueError, match="must be a list"):
            provider._validate_search_domain_filter("not_a_list")

        with pytest.raises(ValueError, match="items must be strings"):
            provider._validate_search_domain_filter([123])

        with pytest.raises(ValueError, match="Invalid domain format"):
            provider._validate_search_domain_filter(["invalid_domain"])

    def test_validate_search_recency_filter_valid(self, provider):
        """Test search recency filter validation with valid values."""
        valid_recencies = ["hour", "day", "week", "month", "year"]
        for recency in valid_recencies:
            provider._validate_search_recency_filter(recency)

    def test_validate_search_recency_filter_invalid(self, provider):
        """Test search recency filter validation with invalid values."""
        with pytest.raises(ValueError, match="search_recency_filter must be one of"):
            provider._validate_search_recency_filter("invalid")

    def test_validate_search_mode_valid(self, provider):
        """Test search mode validation with valid values."""
        valid_modes = ["web", "high", "medium", "low"]
        for mode in valid_modes:
            provider._validate_search_mode(mode)

    def test_validate_search_mode_invalid(self, provider):
        """Test search mode validation with invalid values."""
        with pytest.raises(ValueError, match="search_mode must be one of"):
            provider._validate_search_mode("invalid")

    def test_validate_date_filter_valid(self, provider):
        """Test date filter validation with valid dates."""
        valid_dates = ["2025-01-01", "2025-12-31", "2024-02-29"]
        for date in valid_dates:
            provider._validate_date_filter(date)

    def test_validate_date_filter_invalid_format(self, provider):
        """Test date filter validation with invalid formats."""
        invalid_formats = ["2025-1-1", "25-01-01", "2025/01/01", "invalid"]
        for invalid_date in invalid_formats:
            with pytest.raises(ValueError, match="Date filter must be in YYYY-MM-DD format"):
                provider._validate_date_filter(invalid_date)

    def test_validate_date_filter_invalid_date(self, provider):
        """Test date filter validation with invalid dates."""
        invalid_dates = ["2025-13-01", "2025-02-30", "2023-02-29"]
        for invalid_date in invalid_dates:
            with pytest.raises(ValueError, match="Invalid date"):
                provider._validate_date_filter(invalid_date)

    def test_resolve_model_name_aliases(self, provider):
        """Test model name alias resolution."""
        alias_tests = [
            ("perplexity", "sonar"),
            ("perplexity-pro", "sonar-pro"),
            ("perplexity-reasoning", "sonar-reasoning"),
            ("perplexity-reasoning-pro", "sonar-reasoning-pro"),
            ("deep-research", "sonar-deep-research"),
            ("r1", "r1-1776"),
        ]

        for alias, expected in alias_tests:
            assert provider._resolve_model_name(alias) == expected

    def test_calculate_perplexity_cost(self, provider):
        """Test cost calculation with official Perplexity pricing."""
        usage_data = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "citation_tokens": 100,
            "reasoning_tokens": 200,
        }

        # Test sonar model cost
        cost = provider._calculate_perplexity_cost(usage_data, "sonar")
        assert cost["currency"] == "USD"
        assert cost["prompt_cost"] == 0.000001
        assert cost["completion_cost"] == 0.0000005
        assert cost["citation_cost"] == 0.0
        assert cost["reasoning_cost"] == 0.0

        # Test sonar-deep-research model cost (has citation/reasoning charges)
        cost_deep = provider._calculate_perplexity_cost(usage_data, "sonar-deep-research")
        assert cost_deep["citation_cost"] == 0.0000002
        assert cost_deep["reasoning_cost"] == 0.0000006


class TestPerplexityProviderEdgeCases:
    """Test edge cases and error handling for Perplexity provider."""

    @pytest.fixture
    def provider(self):
        """Create a test provider instance."""
        return PerplexityProvider("test-key")

    @pytest.fixture
    def mock_model_response(self):
        """Create a mock ModelResponse for testing."""
        from providers.base import ModelResponse, ProviderType

        return ModelResponse(
            content="Test response",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            model_name="sonar",
            friendly_name="Perplexity Sonar",
            provider=ProviderType.PERPLEXITY,
            metadata={},
        )

    def test_generate_content_max_tokens_present(self, provider, mock_model_response):
        """Test generate_content with max_tokens in kwargs."""
        with (
            patch.object(provider, "validate_model_name", return_value=True),
            patch.object(provider, "_extract_perplexity_params") as extract,
            patch.object(provider, "_resolve_model_name", return_value="sonar"),
            patch.object(
                provider, "_enhance_model_response_with_perplexity_metadata", return_value=mock_model_response
            ),
        ):

            # Mock the parent class generate_content method
            parent_path = "providers.openai_compatible." "OpenAICompatibleProvider.generate_content"
            with patch(parent_path, return_value=mock_model_response) as parent:

                # Setup mock extract to return max_tokens
                extract.return_value = {"max_tokens": 500}

                provider.generate_content(prompt="Test prompt", model_name="sonar", max_tokens=500)

                # Verify max_tokens was handled correctly
                extract.assert_called_once()
                parent.assert_called_once()

                # Check that max_output_tokens was set from max_tokens
                call_args = parent.call_args[1]
                assert call_args["max_output_tokens"] == 500

    def test_generate_content_max_tokens_absent(self, provider, mock_model_response):
        """Test generate_content without max_tokens in kwargs."""
        with (
            patch.object(provider, "validate_model_name", return_value=True),
            patch.object(provider, "_extract_perplexity_params") as extract,
            patch.object(provider, "_resolve_model_name", return_value="sonar"),
            patch.object(
                provider, "_enhance_model_response_with_perplexity_metadata", return_value=mock_model_response
            ),
        ):

            parent_path = "providers.openai_compatible." "OpenAICompatibleProvider.generate_content"
            with patch(parent_path, return_value=mock_model_response) as parent:

                # Setup mock extract to return empty params
                extract.return_value = {}

                provider.generate_content(prompt="Test prompt", model_name="sonar")

                # Check that max_output_tokens was None
                call_args = parent.call_args[1]
                assert call_args["max_output_tokens"] is None

    def test_enhance_model_response_metadata_missing(self, provider):
        """Test enhance when metadata attribute is missing."""
        from providers.base import ModelResponse, ProviderType

        # Create response without metadata attribute
        response_without_metadata = ModelResponse(
            content="Test response", usage={"prompt_tokens": 100}, model_name="sonar", provider=ProviderType.PERPLEXITY
        )
        # Remove metadata to test missing case
        delattr(response_without_metadata, "metadata")

        with patch.object(provider, "_extract_perplexity_metadata", return_value={}) as mock_extract:
            result = provider._enhance_model_response_with_perplexity_metadata(
                response=None, model_response=response_without_metadata
            )

            # Should handle missing metadata gracefully
            assert result.content == "Test response"
            mock_extract.assert_called_once_with(None)

    def test_enhance_model_response_metadata_not_dict(self, provider):
        """Test enhance when metadata is not a dict."""
        from providers.base import ModelResponse, ProviderType

        response_bad_metadata = ModelResponse(
            content="Test response",
            usage={"prompt_tokens": 100},
            model_name="sonar",
            provider=ProviderType.PERPLEXITY,
            metadata="not_a_dict",  # Invalid metadata type
        )

        with patch.object(provider, "_extract_perplexity_metadata", return_value={}) as mock_extract:
            result = provider._enhance_model_response_with_perplexity_metadata(
                response=None, model_response=response_bad_metadata
            )

            # Should handle invalid metadata type gracefully
            assert result.content == "Test response"
            mock_extract.assert_called_once_with(None)

    def test_enhance_model_response_with_raw_response(self, provider):
        """Test enhance with valid raw_response."""
        from providers.base import ModelResponse, ProviderType

        response_with_metadata = ModelResponse(
            content="Test response",
            usage={"prompt_tokens": 100},
            model_name="sonar",
            provider=ProviderType.PERPLEXITY,
            metadata={"raw_response": {"id": "test_id"}},
        )

        with patch.object(
            provider, "_extract_perplexity_metadata", return_value={"test_meta": "value"}
        ) as mock_extract:
            result = provider._enhance_model_response_with_perplexity_metadata(
                response=None, model_response=response_with_metadata
            )

            # Should extract metadata from raw_response
            mock_extract.assert_called_once_with({"id": "test_id"})
            assert result.metadata["test_meta"] == "value"

    def test_extract_perplexity_params_pop_behavior(self, provider):
        """Test that max_tokens is properly handled in parameters."""
        kwargs = {"max_tokens": 1000, "temperature": 0.7, "other_param": "value"}

        # Call the method
        params = provider._extract_perplexity_params("sonar", kwargs)

        # Verify max_tokens is in returned params
        assert "max_tokens" in params
        assert params["max_tokens"] == 1000

        # Verify original kwargs still contains max_tokens (not popped yet)
        assert "max_tokens" in kwargs

    def test_extract_perplexity_metadata_no_response(self, provider):
        """Test _extract_perplexity_metadata with None response."""
        result = provider._extract_perplexity_metadata(None)

        # Should return empty dict when response is None
        assert result == {}

    def test_extract_perplexity_metadata_empty_response(self, provider):
        """Test _extract_perplexity_metadata with empty response object."""

        class EmptyResponse:
            pass

        result = provider._extract_perplexity_metadata(EmptyResponse())

        # Should return empty dict when response has no attributes
        assert result == {}

    def test_extract_perplexity_metadata_partial_response(self, provider):
        """Test _extract_perplexity_metadata with partial response data."""

        class PartialResponse:
            def __init__(self):
                self.id = "test_id_123"
                # Missing usage and other attributes

        result = provider._extract_perplexity_metadata(PartialResponse())

        # Should extract available data and ignore missing
        assert result["perplexity_response_id"] == "test_id_123"
        assert result["conversation_id"] == "test_id_123"
        assert "perplexity_usage" not in result

    def test_safe_get_from_kwargs_key_exists(self, provider):
        """Test _safe_get_from_kwargs when key exists."""
        kwargs = {"test_key": "test_value", "other": 123}

        result = provider._safe_get_from_kwargs(kwargs, "test_key")
        assert result == "test_value"

    def test_safe_get_from_kwargs_key_missing(self, provider):
        """Test _safe_get_from_kwargs when key is missing."""
        kwargs = {"other": 123}

        result = provider._safe_get_from_kwargs(kwargs, "missing_key")
        assert result is None

        # Test with custom default
        result = provider._safe_get_from_kwargs(kwargs, "missing_key", "default")
        assert result == "default"

    def test_validate_perplexity_param_success(self, provider):
        """Test _validate_perplexity_param with successful validation."""

        def mock_validator(value):
            if value != "valid":
                raise ValueError("Invalid value")

        # Should not raise when validation passes
        provider._validate_perplexity_param("test_param", "valid", mock_validator)

    def test_validate_perplexity_param_failure(self, provider):
        """Test _validate_perplexity_param with failed validation."""

        def mock_validator(value):
            raise ValueError("Always fails")

        with patch("providers.perplexity_provider.logger") as mock_logger:
            with pytest.raises(ValueError, match="Always fails"):
                provider._validate_perplexity_param("test_param", "any_value", mock_validator)

            # Should log the error
            mock_logger.error.assert_called_once()

    def test_restriction_service_integration(self, provider):
        """Test integration with restriction service."""
        service_path = "providers.perplexity_provider.get_restriction_service"
        with patch(service_path) as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.is_allowed.return_value = False

            # Should raise ValueError when model is not allowed
            with pytest.raises(ValueError, match="is not allowed"):
                provider.get_capabilities("sonar")

            # Should return False for validate_model_name when not allowed
            assert provider.validate_model_name("sonar") is False

    def test_generate_content_error_handling(self, provider):
        """Test error handling in generate_content method."""
        with patch.object(provider, "_extract_perplexity_params", side_effect=ValueError("Invalid param")):
            with pytest.raises(ValueError, match="Invalid param"):
                provider.generate_content(prompt="Test prompt", model_name="sonar", invalid_param="bad_value")

    def test_metadata_merge_behavior(self, provider):
        """Test metadata merge in _enhance_model_response_with_perplexity_metadata."""
        from providers.base import ModelResponse, ProviderType

        existing_metadata = {"existing_key": "existing_value", "shared_key": "original"}
        new_metadata = {"new_key": "new_value", "shared_key": "overwritten"}

        response = ModelResponse(
            content="Test", model_name="sonar", provider=ProviderType.PERPLEXITY, metadata=existing_metadata
        )

        with patch.object(provider, "_extract_perplexity_metadata", return_value=new_metadata):
            result = provider._enhance_model_response_with_perplexity_metadata(None, response)

            # Should merge metadata with new values taking precedence
            assert result.metadata["existing_key"] == "existing_value"
            assert result.metadata["new_key"] == "new_value"
            assert result.metadata["shared_key"] == "overwritten"


class TestPerplexityProviderValidation:
    """Test validation scenarios for Perplexity provider."""

    @pytest.fixture
    def provider(self):
        """Create a test provider instance."""
        return PerplexityProvider("test-key")

    def test_max_tokens_parameter_handling(self, provider):
        """Test max_tokens parameter is handled correctly."""
        kwargs_with_max_tokens = {"max_tokens": 1000, "temperature": 0.7}
        kwargs_without_max_tokens = {"temperature": 0.7}

        # Test with max_tokens present
        params = provider._extract_perplexity_params("sonar", kwargs_with_max_tokens)
        assert "max_tokens" in params
        assert params["max_tokens"] == 1000

        # Test without max_tokens
        params = provider._extract_perplexity_params("sonar", kwargs_without_max_tokens)
        assert "max_tokens" not in params

    def test_metadata_graceful_handling(self, provider):
        """Test graceful handling of missing or invalid metadata."""
        # Test with None response
        result = provider._extract_perplexity_metadata(None)
        assert isinstance(result, dict)
        assert len(result) == 0

        # Test with response missing attributes
        class MockResponse:
            pass

        result = provider._extract_perplexity_metadata(MockResponse())
        assert isinstance(result, dict)

    def test_enhance_metadata_existence_validation(self, provider):
        """Test that _enhance_model_response_with_perplexity_metadata exists and works."""
        from providers.base import ModelResponse, ProviderType

        # Verify the method exists
        assert hasattr(provider, "_enhance_model_response_with_perplexity_metadata")

        # Test it can be called with proper arguments
        mock_response = ModelResponse(content="Test", model_name="sonar", provider=ProviderType.PERPLEXITY, metadata={})

        result = provider._enhance_model_response_with_perplexity_metadata(None, mock_response)

        # Should return a ModelResponse
        assert isinstance(result, ModelResponse)
        assert result.content == "Test"

    def test_parameter_validation_coverage(self, provider):
        """Test that all parameter validation methods work correctly."""
        # Test reasoning effort validation
        provider._validate_reasoning_effort("low")
        provider._validate_reasoning_effort("medium")
        provider._validate_reasoning_effort("high")

        with pytest.raises(ValueError):
            provider._validate_reasoning_effort("invalid")

        # Test search domain filter validation
        provider._validate_search_domain_filter(["example.com", "-spam.com"])

        with pytest.raises(ValueError):
            provider._validate_search_domain_filter("not_a_list")

        # Test search recency filter validation
        for recency in ["hour", "day", "week", "month", "year"]:
            provider._validate_search_recency_filter(recency)

        with pytest.raises(ValueError):
            provider._validate_search_recency_filter("invalid")

        # Test search mode validation
        for mode in ["web", "high", "medium", "low"]:
            provider._validate_search_mode(mode)

        with pytest.raises(ValueError):
            provider._validate_search_mode("invalid")

        # Test date filter validation
        provider._validate_date_filter("2025-01-01")

        with pytest.raises(ValueError):
            provider._validate_date_filter("invalid-date")

    def test_helper_methods_exist_and_work(self, provider):
        """Test that helper methods exist and function correctly."""
        # Test _safe_get_from_kwargs
        assert hasattr(provider, "_safe_get_from_kwargs")

        kwargs = {"key1": "value1", "key2": "value2"}
        assert provider._safe_get_from_kwargs(kwargs, "key1") == "value1"
        assert provider._safe_get_from_kwargs(kwargs, "missing") is None
        assert provider._safe_get_from_kwargs(kwargs, "missing", "default") == "default"

        # Test _validate_perplexity_param
        assert hasattr(provider, "_validate_perplexity_param")

        def valid_validator(value):
            if value != "valid":
                raise ValueError("Invalid")

        # Should not raise for valid input
        provider._validate_perplexity_param("test", "valid", valid_validator)

        # Should raise and log for invalid input
        with patch("providers.perplexity_provider.logger") as mock_logger:
            with pytest.raises(ValueError):
                provider._validate_perplexity_param("test", "invalid", valid_validator)
            mock_logger.error.assert_called_once()

    def test_error_propagation_in_generate_content(self, provider):
        """Test that errors in generate_content are properly propagated."""
        # Test validation error propagation
        with patch.object(provider, "_extract_perplexity_params", side_effect=ValueError("Validation failed")):
            with pytest.raises(ValueError, match="Validation failed"):
                provider.generate_content("prompt", "sonar")

        # Test model name resolution error
        with patch.object(provider, "validate_model_name", return_value=False):
            # This should be handled by the parent class, but we test the flow
            pass

    def test_comprehensive_metadata_extraction(self, provider):
        """Test comprehensive metadata extraction scenarios."""

        # Test with complete response
        class CompleteResponse:
            def __init__(self):
                self.id = "response_123"
                self.model = "sonar-pro"
                self.created = 1234567890
                self.usage = MockUsage()
                self.citations = ["http://example.com"]
                self.search_results = [MockSearchResult()]

        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 100
                self.completion_tokens = 50
                self.total_tokens = 150
                self.citation_tokens = 10
                self.reasoning_tokens = 20
                self.num_search_queries = 3

        class MockSearchResult:
            def __init__(self):
                self.title = "Example Title"
                self.url = "http://example.com"
                self.date = "2025-01-01"

        result = provider._extract_perplexity_metadata(CompleteResponse())

        # Verify all metadata is extracted
        assert "perplexity_response_id" in result
        assert "conversation_id" in result
        assert "perplexity_usage" in result
        assert "citations" in result
        assert "search_results" in result
        assert "actual_model_used" in result
        assert "response_created_at" in result
        assert "search_queries_count" in result
        assert "search_efficiency" in result
