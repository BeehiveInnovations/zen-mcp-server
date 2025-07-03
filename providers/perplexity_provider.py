"""Perplexity AI model provider for Sonar models."""

import logging
import re
from typing import Optional

from utils.model_restrictions import get_restriction_service

from .base import (
    ModelCapabilities,
    ModelResponse,
    ProviderType,
    RangeTemperatureConstraint,
)
from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class PerplexityProvider(OpenAICompatibleProvider):
    """Provider for Perplexity AI Sonar models.
    - sonar: Fast search-augmented model
    - sonar-pro: High-quality search-augmented model
    - sonar-reasoning: Reasoning with search
    - sonar-reasoning-pro: Advanced reasoning with search
    - sonar-deep-research: Deep research model
    - r1-1776: Offline reasoning model (no search)
    """

    FRIENDLY_NAME = "Perplexity"
    DEFAULT_HEADERS = {}

    # Supported models based on Perplexity API documentation
    SUPPORTED_MODELS = {
        "sonar": ModelCapabilities(
            provider=ProviderType.PERPLEXITY,
            model_name="sonar",
            friendly_name="Perplexity Sonar",
            context_window=127072,  # ~127K context
            max_output_tokens=4096,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            description="Fast search-augmented model with real-time search",
            aliases=["perplexity"],
            supports_json_mode=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.2),
        ),
        "sonar-pro": ModelCapabilities(
            provider=ProviderType.PERPLEXITY,
            model_name="sonar-pro",
            friendly_name="Perplexity Sonar Pro",
            context_window=127072,  # ~127K context
            max_output_tokens=4096,
            supports_extended_thinking=False,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            description="High-quality search-augmented model",
            aliases=["perplexity-pro"],
            supports_json_mode=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.2),
        ),
        "sonar-reasoning": ModelCapabilities(
            provider=ProviderType.PERPLEXITY,
            model_name="sonar-reasoning",
            friendly_name="Perplexity Sonar Reasoning",
            context_window=127072,  # ~127K context
            max_output_tokens=4096,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            description="Reasoning model with search capabilities",
            aliases=["perplexity-reasoning"],
            supports_json_mode=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.2),
        ),
        "sonar-reasoning-pro": ModelCapabilities(
            provider=ProviderType.PERPLEXITY,
            model_name="sonar-reasoning-pro",
            friendly_name="Perplexity Sonar Reasoning Pro",
            context_window=127072,  # ~127K context
            max_output_tokens=4096,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            description="Advanced reasoning with search - enterprise grade",
            aliases=["perplexity-reasoning-pro"],
            supports_json_mode=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.2),
        ),
        "sonar-deep-research": ModelCapabilities(
            provider=ProviderType.PERPLEXITY,
            model_name="sonar-deep-research",
            friendly_name="Perplexity Sonar Deep Research",
            context_window=127072,  # ~127K context
            max_output_tokens=4096,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            description="Deep research model for comprehensive analysis",
            aliases=["deep-research"],
            supports_json_mode=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.2),
        ),
        "r1-1776": ModelCapabilities(
            provider=ProviderType.PERPLEXITY,
            model_name="r1-1776",
            friendly_name="Perplexity R1-1776",
            context_window=127072,  # ~127K context
            max_output_tokens=4096,
            supports_extended_thinking=True,
            supports_system_prompts=True,
            supports_streaming=True,
            supports_function_calling=True,
            supports_images=False,
            description="DeepSeek R1 post-trained for factual info (offline)",
            aliases=["r1"],
            supports_json_mode=True,
            temperature_constraint=RangeTemperatureConstraint(0.0, 2.0, 0.2),
        ),
    }

    FRIENDLY_NAME = "Perplexity"
    DEFAULT_HEADERS = {}

    def __init__(self, api_key: str, **kwargs):
        """Initialize Perplexity provider.

        Args:
            api_key: Perplexity API key
            **kwargs: Additional configuration options
        """
        # Initialize with Perplexity API base URL
        super().__init__(
            api_key=api_key,
            base_url="https://api.perplexity.ai",
            **kwargs,
        )
        logger.info("Initialized Perplexity provider")

    def get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        return ProviderType.PERPLEXITY

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get capabilities for a specific Perplexity model."""
        # Resolve model name through aliases
        resolved_name = self._resolve_model_name(model_name)

        if resolved_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")

        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.PERPLEXITY, resolved_name, model_name):
            raise ValueError(f"Model '{model_name}' is not allowed.")

        return self.SUPPORTED_MODELS[resolved_name]

    def validate_model_name(self, model_name: str) -> bool:
        """Validate if the model name is supported by Perplexity."""
        resolved_name = self._resolve_model_name(model_name)

        # First check if model is supported
        if resolved_name not in self.SUPPORTED_MODELS:
            return False

        # Then check if model is allowed by restrictions
        restriction_service = get_restriction_service()
        if not restriction_service.is_allowed(ProviderType.PERPLEXITY, resolved_name, model_name):
            return False

        return True

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check if the model supports extended thinking mode."""
        try:
            capabilities = self.get_capabilities(model_name)
            return capabilities.supports_extended_thinking
        except (ValueError, KeyError):
            return False

    def generate_content(
        self,
        prompt: str,
        model_name: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        images: Optional[list[str]] = None,
        **kwargs,
    ) -> "ModelResponse":
        """Generate content using Perplexity API with special parameters.

        Perplexity-specific parameters:
        - search_domain_filter: List of domains to include/exclude
        - search_recency_filter: Time filter (hour, day, week, month, year)
        - reasoning_effort: For reasoning models (low, medium, high)
        - max_tokens: Maximum tokens in response
        - search_mode: Search mode (web, high, medium, low)
        - search_after_date_filter: Search after this date (YYYY-MM-DD)
        - search_before_date_filter: Search before this date (YYYY-MM-DD)
        - return_images: Include images in response
        - image_domain_filter: Filter image sources
        - image_format_filter: Filter image formats
        - return_related_questions: Include related question suggestions

        Returns:
            ModelResponse with Perplexity metadata (citations, etc.)
        """
        # Extract and validate Perplexity-specific parameters
        perplexity_params = self._extract_perplexity_params(model_name, kwargs)

        # Add Perplexity parameters to the kwargs that will be passed to parent
        cleaned_kwargs = {k: v for k, v in kwargs.items() if k not in perplexity_params}
        cleaned_kwargs.update(perplexity_params)

        # Handle max_tokens parameter specifically
        if max_output_tokens is None and "max_tokens" in perplexity_params:
            max_output_tokens = perplexity_params.pop("max_tokens")

        # Resolve aliases before API call
        resolved_model_name = self._resolve_model_name(model_name)

        # Call parent's generate_content method
        model_response = super().generate_content(
            prompt=prompt,
            model_name=resolved_model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            images=images,
            **cleaned_kwargs,
        )

        # Enhance with Perplexity-specific metadata if available
        raw_response = None
        if hasattr(model_response, "metadata") and isinstance(model_response.metadata, dict):
            raw_response = model_response.metadata.get("raw_response")
        return self._enhance_model_response_with_perplexity_metadata(
            response=raw_response,
            model_response=model_response,
        )

    def _extract_perplexity_params(self, model_name: str, kwargs: dict) -> dict:
        """Extract and validate Perplexity-specific parameters.

        Args:
            model_name: Name of the model being used
            kwargs: Keyword arguments containing potential Perplexity
                parameters

        Returns:
            dict: Validated Perplexity-specific parameters
        """
        params = {}

        # max_tokens support
        if "max_tokens" in kwargs:
            params["max_tokens"] = kwargs["max_tokens"]

        # reasoning_effort support
        if "reasoning_effort" in kwargs:
            if self.supports_thinking_mode(model_name):
                self._validate_reasoning_effort(kwargs["reasoning_effort"])
                params["reasoning_effort"] = kwargs["reasoning_effort"]
            else:
                logger.warning(
                    "reasoning_effort ignored for non-reasoning model: %s",
                    model_name,
                )

        # search_domain_filter support
        if "search_domain_filter" in kwargs:
            self._validate_search_domain_filter(kwargs["search_domain_filter"])
            params["search_domain_filter"] = kwargs["search_domain_filter"]

        # search_recency_filter support
        if "search_recency_filter" in kwargs:
            recency_filter = kwargs["search_recency_filter"]
            self._validate_search_recency_filter(recency_filter)
            params["search_recency_filter"] = recency_filter

        # search_mode support
        if "search_mode" in kwargs:
            self._validate_search_mode(kwargs["search_mode"])
            params["search_mode"] = kwargs["search_mode"]

        # Date filters support
        date_params = ["search_after_date_filter", "search_before_date_filter"]
        for date_param in date_params:
            if date_param in kwargs:
                self._validate_date_filter(kwargs[date_param])
                params[date_param] = kwargs[date_param]

        # Image parameters support
        image_params = [
            "return_images",
            "image_domain_filter",
            "image_format_filter",
        ]
        for image_param in image_params:
            if image_param in kwargs:
                if image_param == "return_images":
                    params[image_param] = bool(kwargs[image_param])
                else:
                    params[image_param] = kwargs[image_param]

        # Related questions support
        if "return_related_questions" in kwargs:
            value = bool(kwargs["return_related_questions"])
            params["return_related_questions"] = value

        return params

    def _validate_reasoning_effort(self, effort: str) -> None:
        """Validate reasoning_effort parameter."""
        valid_efforts = ["low", "medium", "high"]
        if effort not in valid_efforts:
            raise ValueError(f"reasoning_effort must be one of {valid_efforts}, " f"got: {effort}")

    def _validate_search_domain_filter(self, domains: list) -> None:
        """Validate search_domain_filter parameter."""
        if not isinstance(domains, list):
            raise ValueError("search_domain_filter must be a list of domain strings")

        for domain in domains:
            if not isinstance(domain, str):
                raise ValueError("search_domain_filter items must be strings")

            # Validate domain format (basic check)
            domain_clean = domain.lstrip("-")  # Remove exclusion prefix
            if not domain_clean or "." not in domain_clean:
                raise ValueError(f"Invalid domain format: {domain}")

    def _validate_search_recency_filter(self, recency: str) -> None:
        """Validate search_recency_filter parameter."""
        valid_recencies = ["hour", "day", "week", "month", "year"]
        if recency not in valid_recencies:
            raise ValueError("search_recency_filter must be one of " f"{valid_recencies}, got: {recency}")

    def _validate_search_mode(self, mode: str) -> None:
        """Validate search_mode parameter."""
        valid_modes = ["web", "high", "medium", "low"]
        if mode not in valid_modes:
            raise ValueError(f"search_mode must be one of {valid_modes}, got: {mode}")

    def _validate_date_filter(self, date_str: str) -> None:
        """Validate date filter format (YYYY-MM-DD)."""
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(date_pattern, date_str):
            raise ValueError(f"Date filter must be in YYYY-MM-DD format, got: {date_str}")

        # Additional validation: check if it's a valid date
        try:
            from datetime import datetime

            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date: {date_str} - {e}")

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve model name through aliases."""
        # Direct mapping for aliases
        alias_map = {
            "perplexity": "sonar",
            "perplexity-pro": "sonar-pro",
            "perplexity-reasoning": "sonar-reasoning",
            "perplexity-reasoning-pro": "sonar-reasoning-pro",
            "deep-research": "sonar-deep-research",
            "r1": "r1-1776",
        }

        return alias_map.get(model_name, model_name)

    def _enhance_model_response_with_perplexity_metadata(
        self, response, model_response: ModelResponse
    ) -> ModelResponse:
        """Enhance ModelResponse with Perplexity-specific metadata.

        This method extracts and integrates Perplexity-specific metadata
        including:
        - Response ID for conversation continuity
        - Usage tokens breakdown (prompt, completion, citation, reasoning)
        - Citations and search results
        - Search queries count for metrics

        Args:
            response: Raw response object from Perplexity API (can be None)
            model_response: The ModelResponse object to enhance

        Returns:
            ModelResponse: Enhanced response with Perplexity metadata
                integrated
        """
        # Extract Perplexity-specific metadata
        # If no response provided, try to get it from model_response metadata
        actual_response = response
        if actual_response is None:
            if hasattr(model_response, "metadata") and isinstance(model_response.metadata, dict):
                actual_response = model_response.metadata.get("raw_response")

        perplexity_metadata = self._extract_perplexity_metadata(actual_response)

        # Safely merge with existing metadata
        existing_metadata = {}
        if hasattr(model_response, "metadata") and isinstance(model_response.metadata, dict):
            existing_metadata = model_response.metadata
        enhanced_metadata = {**existing_metadata, **perplexity_metadata}

        # Create enhanced ModelResponse
        return ModelResponse(
            content=model_response.content,
            usage=model_response.usage,
            model_name=model_response.model_name,
            friendly_name=model_response.friendly_name,
            provider=model_response.provider,
            metadata=enhanced_metadata,
        )

    def _extract_perplexity_metadata(self, response) -> dict:
        """Extract Perplexity-specific metadata from API response.

        Returns:
            dict: Perplexity metadata including citations, search_results, etc.
        """
        metadata = {}

        # Response ID for conversation continuity
        if hasattr(response, "id") and response.id:
            metadata["perplexity_response_id"] = response.id
            metadata["conversation_id"] = response.id  # For continuity

        # Enhanced usage tokens
        if hasattr(response, "usage") and response.usage:
            usage_data = response.usage
            enhanced_usage = {}

            # Standard tokens
            if hasattr(usage_data, "prompt_tokens"):
                enhanced_usage["prompt_tokens"] = usage_data.prompt_tokens
            if hasattr(usage_data, "completion_tokens"):
                enhanced_usage["completion_tokens"] = usage_data.completion_tokens
            if hasattr(usage_data, "total_tokens"):
                enhanced_usage["total_tokens"] = usage_data.total_tokens

            # Perplexity-specific tokens
            if hasattr(usage_data, "citation_tokens"):
                enhanced_usage["citation_tokens"] = usage_data.citation_tokens
            if hasattr(usage_data, "reasoning_tokens"):
                enhanced_usage["reasoning_tokens"] = usage_data.reasoning_tokens

            # Search queries metrics
            if hasattr(usage_data, "num_search_queries"):
                enhanced_usage["num_search_queries"] = usage_data.num_search_queries
                metadata["search_queries_count"] = usage_data.num_search_queries

            # Calculate search efficiency if possible
            citation_tokens = enhanced_usage.get("citation_tokens", 0)
            num_queries = enhanced_usage.get("num_search_queries", 0)
            if citation_tokens and num_queries > 0:
                efficiency = citation_tokens / num_queries
                metadata["search_efficiency"] = efficiency

            metadata["perplexity_usage"] = enhanced_usage

        # Citations (URLs) - Legacy support
        if hasattr(response, "citations") and response.citations:
            metadata["citations"] = response.citations
            metadata["citation_urls"] = response.citations  # Alternative name

        # Search results with title, url, date
        if hasattr(response, "search_results") and response.search_results:
            search_results = []
            for result in response.search_results:
                result_data = {}

                if hasattr(result, "title") and result.title:
                    result_data["title"] = result.title
                if hasattr(result, "url") and result.url:
                    result_data["url"] = result.url
                if hasattr(result, "date") and result.date:
                    result_data["date"] = result.date

                if result_data:  # Only add if we got at least some data
                    search_results.append(result_data)

            if search_results:
                metadata["search_results"] = search_results
                # Alternative name for zen tools
                metadata["sources"] = search_results

                # Extract just URLs for backward compatibility
                urls = [r.get("url") for r in search_results if r.get("url")]
                if urls:
                    metadata["source_urls"] = urls

        # Additional Perplexity metadata
        if hasattr(response, "model") and response.model:
            metadata["actual_model_used"] = response.model

        if hasattr(response, "created") and response.created:
            metadata["response_created_at"] = response.created

        return metadata

    def _calculate_perplexity_cost(self, usage_data: dict, model_name: str) -> dict:
        """Calculate detailed cost breakdown for Perplexity usage.

        Returns:
            dict: Cost breakdown by token type
        """
        # Model prices in USD per million tokens
        # https://docs.perplexity.ai/models/model-cards
        model_prices = {
            "sonar": {"input": 0.001, "output": 0.001},
            "sonar-pro": {"input": 0.003, "output": 0.015},
            "sonar-reasoning": {"input": 0.001, "output": 0.005},
            "sonar-reasoning-pro": {"input": 0.002, "output": 0.008},
            "sonar-deep-research": {
                "input": 0.002,
                "output": 0.008,
                "citation": 0.002,
                "reasoning": 0.003,
            },
            "r1-1776": {"input": 0.002, "output": 0.008},
        }
        resolved_name = self._resolve_model_name(model_name)
        prices = model_prices.get(resolved_name, {"input": 0.003, "output": 0.015})

        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        citation_tokens = usage_data.get("citation_tokens", 0)
        reasoning_tokens = usage_data.get("reasoning_tokens", 0)

        prompt_cost = (prompt_tokens / 1_000_000) * prices["input"]
        completion_cost = (completion_tokens / 1_000_000) * prices["output"]
        citation_cost = (citation_tokens / 1_000_000) * prices.get("citation", 0.0)
        reasoning_cost = (reasoning_tokens / 1_000_000) * prices.get("reasoning", 0.0)
        total_cost = prompt_cost + completion_cost + citation_cost + reasoning_cost

        cost_breakdown = {
            "total_cost": round(total_cost, 8),
            "prompt_cost": round(prompt_cost, 8),
            "completion_cost": round(completion_cost, 8),
            "citation_cost": round(citation_cost, 8),
            "reasoning_cost": round(reasoning_cost, 8),
            "currency": "USD",
        }
        return cost_breakdown

    def _safe_get_from_kwargs(self, kwargs: dict, key: str, default=None):
        """Safely get a value from kwargs with proper error handling.

        Args:
            kwargs: Keyword arguments dictionary
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Value from kwargs or default
        """
        return kwargs.get(key, default)

    def _validate_perplexity_param(self, param_name: str, value, validator_func):
        """Validate a single Perplexity parameter using provided validator.

        Args:
            param_name: Name of the parameter for error messages
            value: Value to validate
            validator_func: Function to validate the value

        Raises:
            ValueError: If validation fails
        """
        try:
            validator_func(value)
        except ValueError as e:
            logger.error(f"Invalid {param_name}: {e}")
            raise
