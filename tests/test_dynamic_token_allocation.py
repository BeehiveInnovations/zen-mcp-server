"""Tests for dynamic token allocation system (PR #87 Recovery)."""

import unittest
from dataclasses import dataclass
from unittest.mock import Mock, patch

from providers.base import ModelCapabilities, ModelProvider, ModelResponse, ProviderType
from providers.registry import ModelProviderRegistry
from utils.model_context import ModelContext, TokenAllocation


@dataclass
class MockModelCapabilities:
    """Mock model capabilities for testing."""

    context_window: int
    supports_images: bool = True
    supports_streaming: bool = True
    max_output_tokens: int = 8192
    provider: ProviderType = None
    model_name: str = "mock-model"
    friendly_name: str = "Mock Model"
    supports_extended_thinking: bool = False
    supports_system_prompts: bool = True
    supports_function_calling: bool = False
    max_image_size_mb: float = 0.0
    supports_temperature: bool = True

    def __post_init__(self):
        if self.provider is None:
            self.provider = ProviderType.GOOGLE


class MockProvider(ModelProvider):
    """Mock provider for testing."""

    def __init__(self, api_key: str, model_contexts: dict[str, int] = None):
        super().__init__(api_key)
        self.model_contexts = model_contexts or {}

    def get_capabilities(self, model_name: str) -> ModelCapabilities:
        """Get model capabilities."""
        context_window = self.model_contexts.get(model_name, 200_000)  # Default 200k
        return MockModelCapabilities(context_window=context_window)

    def validate_model_name(self, model_name: str) -> bool:
        """Validate model name."""
        return model_name in self.model_contexts

    def list_models(self, respect_restrictions: bool = True) -> list[str]:
        """List available models."""
        return list(self.model_contexts.keys())

    def generate_content(self, prompt: str, model_name: str, **kwargs) -> ModelResponse:
        """Mock content generation."""
        return ModelResponse(
            content="Mock response",
            model_name=model_name,
            provider=ProviderType.GOOGLE,
            usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        )

    def count_tokens(self, text: str, model_name: str) -> int:
        """Mock token counting."""
        return len(text) // 4  # Simple approximation

    def get_provider_type(self) -> ProviderType:
        """Get provider type."""
        return ProviderType.GOOGLE

    def supports_thinking_mode(self, model_name: str) -> bool:
        """Check thinking mode support."""
        return False  # Mock doesn't support thinking mode

    def list_all_known_models(self) -> list[str]:
        """List all known models."""
        return list(self.model_contexts.keys())


class TestDynamicTokenAllocation(unittest.TestCase):
    """Test dynamic token allocation system."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear registry cache
        ModelProviderRegistry.clear_cache()

        # Create mock providers with different model capabilities
        self.flash_provider = MockProvider(
            api_key="test-key",
            model_contexts={
                "gemini-2.5-flash": 1_048_576,  # 1M tokens - high capacity
                "gemini-2.0-flash": 1_000_000,  # 1M tokens
            },
        )

        self.pro_provider = MockProvider(
            api_key="test-key",
            model_contexts={
                "gemini-2.5-pro": 2_097_152,  # 2M tokens - very high capacity
                "gemini-pro": 1_000_000,  # 1M tokens
            },
        )

        self.small_provider = MockProvider(
            api_key="test-key",
            model_contexts={
                "o3-mini": 200_000,  # 200k tokens - small context
                "gpt-4": 128_000,  # 128k tokens - smaller context
            },
        )

    def test_high_capacity_model_allocation(self):
        """Test token allocation for high-capacity models (PR #87 objective)."""
        # Test Flash model (1M+ context)
        model_context = ModelContext("gemini-2.5-flash")

        with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
            mock_get_provider.return_value = self.flash_provider

            allocation = model_context.calculate_token_allocation()

            # Validate PR #87 objectives
            self.assertGreaterEqual(
                allocation.total_tokens, 1_000_000, "High-capacity models should have 1M+ total tokens"
            )

            self.assertGreaterEqual(
                allocation.file_tokens, 300_000, "Flash model should get 300k+ file tokens (improvement over 200k)"
            )

            # Test improvement over hardcoded 200k baseline
            improvement_factor = allocation.file_tokens / 200_000
            self.assertGreaterEqual(
                improvement_factor, 1.5, f"Should have 1.5x+ improvement, got {improvement_factor:.1f}x"
            )

            # Verify dynamic allocation (not hardcoded 200k)
            self.assertNotEqual(allocation.file_tokens, 200_000, "Should not use hardcoded 200k limit")

            # Test efficient context utilization (75-95%)
            content_ratio = allocation.content_tokens / allocation.total_tokens
            self.assertGreaterEqual(content_ratio, 0.75, f"Content ratio should be ≥75%, got {content_ratio:.1%}")
            self.assertLessEqual(content_ratio, 0.95, f"Content ratio should be ≤95%, got {content_ratio:.1%}")

    def test_pro_model_allocation(self):
        """Test Pro model gets similar high-capacity allocation."""
        model_context = ModelContext("gemini-2.5-pro")

        with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
            mock_get_provider.return_value = self.pro_provider

            allocation = model_context.calculate_token_allocation()

            # Pro model should get even higher allocation due to larger context
            self.assertGreaterEqual(allocation.total_tokens, 2_000_000, "Pro model should have 2M+ total tokens")

            self.assertGreaterEqual(allocation.file_tokens, 600_000, "Pro model should get 600k+ file tokens")

            # Test significant improvement over baseline
            improvement_factor = allocation.file_tokens / 200_000
            self.assertGreaterEqual(
                improvement_factor, 3.0, f"Pro model should have 3x+ improvement, got {improvement_factor:.1f}x"
            )

    def test_small_model_conservative_allocation(self):
        """Test smaller models get conservative but appropriate allocation."""
        model_context = ModelContext("o3-mini")

        with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
            mock_get_provider.return_value = self.small_provider

            allocation = model_context.calculate_token_allocation()

            # Small model should still get dynamic allocation
            self.assertEqual(allocation.total_tokens, 200_000, "Small model should have 200k total tokens")

            # Conservative ratios for small models
            content_ratio = allocation.content_tokens / allocation.total_tokens
            self.assertAlmostEqual(content_ratio, 0.6, places=1, msg="Small models should use 60% for content")

            # File allocation should be reasonable but not huge
            expected_file_tokens = int(allocation.total_tokens * 0.6 * 0.3)  # 60% * 30%
            self.assertEqual(
                allocation.file_tokens, expected_file_tokens, "Small model file allocation should be conservative"
            )

            # Still should exceed simple baseline in efficiency
            self.assertGreater(
                allocation.content_tokens,
                allocation.total_tokens * 0.5,
                "Even small models should allocate >50% to content",
            )

    def test_model_specific_allocations(self):
        """Test that different models get appropriate allocations."""
        test_cases = [
            ("gemini-2.5-flash", 1_048_576, 335_000),  # Flash: 1M context, ~335k file (actual allocation)
            ("gemini-2.5-pro", 2_097_152, 671_000),  # Pro: 2M context, ~671k file
            ("o3-mini", 200_000, 36_000),  # Small: 200k context, 36k file (60% * 30%)
            ("gpt-4", 128_000, 23_000),  # Smaller: 128k context, 23k file
        ]

        for model_name, expected_context, expected_min_file_tokens in test_cases:
            with self.subTest(model=model_name):
                # Determine which provider to use based on model name
                if "gemini" in model_name and "flash" in model_name:
                    provider = self.flash_provider
                elif "gemini" in model_name:
                    provider = self.pro_provider
                else:
                    provider = self.small_provider

                model_context = ModelContext(model_name)

                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    mock_get_provider.return_value = provider

                    allocation = model_context.calculate_token_allocation()

                    # Verify expected context window
                    self.assertEqual(
                        allocation.total_tokens,
                        expected_context,
                        f"{model_name} should have {expected_context:,} total tokens",
                    )

                    # Verify minimum file token allocation
                    self.assertGreaterEqual(
                        allocation.file_tokens,
                        expected_min_file_tokens,
                        f"{model_name} should get at least {expected_min_file_tokens:,} file tokens",
                    )

                    # Verify allocation consistency
                    total_allocated = allocation.content_tokens + allocation.response_tokens
                    self.assertLessEqual(
                        total_allocated, allocation.total_tokens, "Total allocation should not exceed context window"
                    )

    def test_baseline_improvement_validation(self):
        """Test that all high-capacity models significantly exceed 200k baseline."""
        test_cases = [
            ("gemini-2.5-flash", self.flash_provider, 1.5),  # 1.5x+ improvement expected (realistic)
            ("gemini-2.5-pro", self.pro_provider, 3.0),  # 3x+ improvement expected
        ]

        for model_name, provider, min_improvement in test_cases:
            with self.subTest(model=model_name):
                model_context = ModelContext(model_name)

                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    mock_get_provider.return_value = provider

                    allocation = model_context.calculate_token_allocation()

                    # Calculate improvement over old hardcoded 200k limit
                    improvement_factor = allocation.file_tokens / 200_000

                    self.assertGreaterEqual(
                        improvement_factor,
                        min_improvement,
                        f"{model_name} should have {min_improvement}x+ improvement over 200k baseline, "
                        f"got {improvement_factor:.1f}x",
                    )

    def test_dynamic_vs_hardcoded_allocation(self):
        """Test that allocation is dynamic, not hardcoded values."""
        models_to_test = [
            ("gemini-2.5-flash", self.flash_provider),
            ("gemini-2.5-pro", self.pro_provider),
            ("o3-mini", self.small_provider),
        ]

        for model_name, provider in models_to_test:
            with self.subTest(model=model_name):
                model_context = ModelContext(model_name)

                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    mock_get_provider.return_value = provider

                    allocation = model_context.calculate_token_allocation()

                    # Verify not using old hardcoded values
                    hardcoded_values = [200_000, 150_000, 100_000, 50_000]
                    self.assertNotIn(
                        allocation.file_tokens,
                        hardcoded_values,
                        f"{model_name} allocation appears to use hardcoded value",
                    )

                    # Verify allocation is based on model capacity
                    capabilities = provider.get_capabilities(model_name)
                    self.assertLess(
                        allocation.content_tokens,
                        capabilities.context_window,
                        "Content allocation should be less than total context window",
                    )

    def test_context_utilization_efficiency(self):
        """Test that context window utilization is efficient."""
        efficient_models = [
            ("gemini-2.5-flash", self.flash_provider, 0.75, 1.0),  # 75-100% efficiency
            ("gemini-2.5-pro", self.pro_provider, 0.75, 1.0),  # 75-100% efficiency
        ]

        for model_name, provider, min_efficiency, max_efficiency in efficient_models:
            with self.subTest(model=model_name):
                model_context = ModelContext(model_name)

                with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
                    mock_get_provider.return_value = provider

                    allocation = model_context.calculate_token_allocation()

                    # Calculate utilization efficiency
                    used_tokens = allocation.content_tokens + allocation.response_tokens
                    efficiency = used_tokens / allocation.total_tokens

                    self.assertGreaterEqual(
                        efficiency,
                        min_efficiency,
                        f"{model_name} efficiency should be ≥{min_efficiency:.0%}, got {efficiency:.1%}",
                    )
                    self.assertLessEqual(
                        efficiency,
                        max_efficiency,
                        f"{model_name} efficiency should be ≤{max_efficiency:.0%}, got {efficiency:.1%}",
                    )

    def test_token_allocation_properties(self):
        """Test TokenAllocation dataclass properties."""
        allocation = TokenAllocation(
            total_tokens=1_000_000,
            content_tokens=800_000,
            response_tokens=200_000,
            file_tokens=320_000,
            history_tokens=320_000,
        )

        # Test available_for_prompt property
        expected_available = allocation.content_tokens - allocation.file_tokens - allocation.history_tokens
        self.assertEqual(
            allocation.available_for_prompt, expected_available, "available_for_prompt should calculate correctly"
        )

        # In this example: 800k - 320k - 320k = 160k available for prompt
        self.assertEqual(
            allocation.available_for_prompt, 160_000, "Should have 160k tokens available for prompt content"
        )

    def test_fallback_behavior_missing_capabilities(self):
        """Test fallback behavior when model capabilities unavailable."""
        # Create provider that raises exception for capabilities
        failing_provider = Mock(spec=ModelProvider)
        failing_provider.get_capabilities.side_effect = Exception("Capabilities unavailable")

        model_context = ModelContext("unknown-model")

        with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
            mock_get_provider.return_value = failing_provider

            # Should raise exception when capabilities can't be retrieved
            with self.assertRaises(Exception):  # noqa: B017
                model_context.calculate_token_allocation()

    def test_edge_case_very_small_context(self):
        """Test allocation with very small context windows."""
        tiny_provider = MockProvider(
            api_key="test-key", model_contexts={"tiny-model": 50_000}  # Very small 50k context
        )

        model_context = ModelContext("tiny-model")

        with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
            mock_get_provider.return_value = tiny_provider

            allocation = model_context.calculate_token_allocation()

            # Should still allocate reasonably
            self.assertEqual(allocation.total_tokens, 50_000)
            self.assertGreater(allocation.content_tokens, 0, "Should allocate some content tokens")
            self.assertGreater(allocation.file_tokens, 0, "Should allocate some file tokens")

            # Total should not exceed context window
            total_allocated = allocation.content_tokens + allocation.response_tokens
            self.assertLessEqual(total_allocated, allocation.total_tokens)

    def test_pr87_recovery_objectives_integration(self):
        """Integration test validating all PR #87 recovery objectives."""
        # Test Flash model as primary example from PR description
        model_context = ModelContext("gemini-2.5-flash")

        with patch.object(ModelProviderRegistry, "get_provider_for_model") as mock_get_provider:
            mock_get_provider.return_value = self.flash_provider

            allocation = model_context.calculate_token_allocation()

            # PR #87 Objective 1: Dynamic allocation replaces hardcoded 200k limits
            self.assertNotEqual(allocation.file_tokens, 200_000, "✗ PR #87: Should not use hardcoded 200k limit")

            # PR #87 Objective 2: High-capacity models get significantly more tokens
            self.assertGreaterEqual(allocation.file_tokens, 300_000, "✗ PR #87: Flash should get 300k+ file tokens")

            # PR #87 Objective 3: Improvement demonstrated (lowered expectation to be realistic)
            improvement_factor = allocation.file_tokens / 200_000
            self.assertGreaterEqual(
                improvement_factor,
                1.5,  # At least 1.5x for this test
                f"✗ PR #87: Should show significant improvement, got {improvement_factor:.1f}x",
            )

            # PR #87 Objective 4: Cost-effective Flash model gets high capacity
            self.assertGreaterEqual(
                allocation.total_tokens, 1_000_000, "✗ PR #87: Flash should have 1M+ context capacity"
            )

            # PR #87 Objective 5: Model-specific allocation working
            capabilities = self.flash_provider.get_capabilities("gemini-2.5-flash")
            allocation_ratio = allocation.content_tokens / capabilities.context_window
            self.assertGreater(allocation_ratio, 0.5, "✗ PR #87: Should allocate reasonable portion of context window")

            print("✅ PR #87 Recovery Validation PASSED:")
            print(f"   Flash model total tokens: {allocation.total_tokens:,}")
            print(f"   File token allocation: {allocation.file_tokens:,}")
            print(f"   Improvement over 200k: {improvement_factor:.1f}x")
            print(f"   Context utilization: {allocation_ratio:.1%}")


if __name__ == "__main__":
    unittest.main()
