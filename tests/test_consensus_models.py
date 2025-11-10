"""
Unit tests for consensus_models.py

Tests TierManager additive architecture and BandSelector integration.
"""

import pytest
from unittest.mock import Mock, patch

from tools.custom.consensus_models import (
    TierManager,
    AvailabilityCache,
    ModelAvailability,
    get_level_description,
)


class TestAvailabilityCache:
    """Test availability cache functionality."""

    def test_cache_initialization(self):
        """Test cache initializes with correct TTL."""
        cache = AvailabilityCache(ttl_seconds=300)
        assert cache.ttl_seconds == 300
        assert len(cache._cache) == 0

    def test_cache_miss_returns_none(self):
        """Test cache returns None for unknown models."""
        cache = AvailabilityCache()
        assert cache.is_available("unknown-model") is None

    def test_cache_hit_returns_status(self):
        """Test cache returns cached availability status."""
        cache = AvailabilityCache()
        cache.set_available("test-model", True)
        assert cache.is_available("test-model") is True

        cache.set_available("unavailable-model", False, error_code=404)
        assert cache.is_available("unavailable-model") is False

    def test_cache_expiration(self):
        """Test cache expires after TTL."""
        cache = AvailabilityCache(ttl_seconds=0)  # Immediate expiration
        cache.set_available("test-model", True)

        import time
        time.sleep(0.1)  # Wait for expiration

        assert cache.is_available("test-model") is None  # Expired

    def test_cache_stats(self):
        """Test cache statistics calculation."""
        cache = AvailabilityCache()
        cache.set_available("model1", True)
        cache.set_available("model2", True)
        cache.set_available("model3", False)

        stats = cache.get_stats()
        assert stats["total_cached"] == 3
        assert stats["available"] == 2
        assert stats["unavailable"] == 1

    def test_cache_clear(self):
        """Test cache can be cleared."""
        cache = AvailabilityCache()
        cache.set_available("model1", True)
        cache.set_available("model2", False)

        cache.clear()

        assert len(cache._cache) == 0
        assert cache.is_available("model1") is None


class TestTierManager:
    """Test TierManager additive architecture."""

    def test_tier_manager_initialization(self):
        """Test TierManager initializes correctly."""
        manager = TierManager()
        assert manager.band_selector is not None
        assert manager.availability_cache is not None

    def test_invalid_level_raises_error(self):
        """Test invalid level raises ValueError."""
        manager = TierManager()

        with pytest.raises(ValueError, match="Invalid level.*Must be 1, 2, or 3"):
            manager.get_tier_models(0)

        with pytest.raises(ValueError, match="Invalid level.*Must be 1, 2, or 3"):
            manager.get_tier_models(4)

    @patch('tools.custom.consensus_models.BandSelector')
    def test_level_1_returns_free_models(self, mock_band_selector):
        """Test Level 1 returns only free models."""
        # Mock BandSelector to return specific models
        mock_selector = Mock()
        mock_selector.get_models_by_cost_tier.return_value = [
            "deepseek/deepseek-chat:free",
            "meta-llama/llama-3.3-70b:free",
            "qwen/qwen-coder:free",
        ]

        manager = TierManager(band_selector=mock_selector)
        models = manager.get_tier_models(1)

        # Should call get_models_by_cost_tier with "free"
        mock_selector.get_models_by_cost_tier.assert_called_with("free", limit=10)

        # Should return 3 free models
        assert len(models) == 3
        assert all("free" in model for model in models)

    @patch('tools.custom.consensus_models.BandSelector')
    def test_level_2_additive_architecture(self, mock_band_selector):
        """Test Level 2 includes Level 1's models (ADDITIVE)."""
        # Mock BandSelector
        mock_selector = Mock()

        def mock_get_models(tier, limit):
            if tier == "free":
                return ["free1", "free2", "free3"]
            elif tier == "economy":
                return ["economy1", "economy2", "economy3"]
            return []

        mock_selector.get_models_by_cost_tier.side_effect = mock_get_models

        manager = TierManager(band_selector=mock_selector)
        tier2_models = manager.get_tier_models(2)

        # Should have 6 models total (3 free + 3 economy)
        assert len(tier2_models) == 6

        # First 3 should be free models
        assert tier2_models[:3] == ["free1", "free2", "free3"]

        # Next 3 should be economy models
        assert tier2_models[3:] == ["economy1", "economy2", "economy3"]

    @patch('tools.custom.consensus_models.BandSelector')
    def test_level_3_additive_architecture(self, mock_band_selector):
        """Test Level 3 includes Level 1 + Level 2's models (ADDITIVE)."""
        # Mock BandSelector
        mock_selector = Mock()

        def mock_get_models(tier, limit):
            if tier == "free":
                return ["free1", "free2", "free3"]
            elif tier == "economy":
                return ["economy1", "economy2", "economy3"]
            elif tier == "premium":
                return ["premium1", "premium2"]
            return []

        mock_selector.get_models_by_cost_tier.side_effect = mock_get_models

        manager = TierManager(band_selector=mock_selector)
        tier3_models = manager.get_tier_models(3)

        # Should have 8 models total (3 free + 3 economy + 2 premium)
        assert len(tier3_models) == 8

        # First 3 should be free models
        assert tier3_models[:3] == ["free1", "free2", "free3"]

        # Next 3 should be economy models
        assert tier3_models[3:6] == ["economy1", "economy2", "economy3"]

        # Last 2 should be premium models
        assert tier3_models[6:] == ["premium1", "premium2"]

    @patch('tools.custom.consensus_models.BandSelector')
    def test_tier_costs_calculation(self, mock_band_selector):
        """Test tier cost estimation."""
        # Mock BandSelector with cost data
        mock_selector = Mock()
        mock_selector.get_models_by_cost_tier.return_value = ["model1", "model2", "model3"]

        # Mock models DataFrame
        import pandas as pd
        mock_selector.models_df = pd.DataFrame({
            'model': ['model1', 'model2', 'model3'],
            'input_cost': [1.0, 2.0, 3.0],
            'output_cost': [5.0, 10.0, 15.0],
        })

        manager = TierManager(band_selector=mock_selector)
        costs = manager.get_tier_costs(1)

        # Should calculate total costs
        assert costs['level'] == 1
        assert costs['model_count'] == 3
        assert costs['input_cost_per_million'] == 6.0  # 1+2+3
        assert costs['output_cost_per_million'] == 30.0  # 5+10+15

        # Estimated cost: (6*1000 + 30*2000) / 1M = 0.066
        assert 0.06 < costs['estimated_cost_per_call'] < 0.07

    def test_get_level_description(self):
        """Test level descriptions."""
        desc1 = get_level_description(1)
        desc2 = get_level_description(2)
        desc3 = get_level_description(3)

        assert "Foundation" in desc1
        assert "$0" in desc1

        assert "Professional" in desc2
        assert "$0.50" in desc2

        assert "Executive" in desc3
        assert "$5" in desc3

    @patch('tools.custom.consensus_models.BandSelector')
    def test_tier_summary(self, mock_band_selector):
        """Test tier summary generation."""
        # Mock BandSelector
        mock_selector = Mock()
        mock_selector.get_models_by_cost_tier.return_value = ["model1", "model2"]

        import pandas as pd
        mock_selector.models_df = pd.DataFrame({
            'model': ['model1', 'model2'],
            'input_cost': [1.0, 2.0],
            'output_cost': [5.0, 10.0],
        })

        manager = TierManager(band_selector=mock_selector)
        summary = manager.get_tier_summary(1)

        assert summary['level'] == 1
        assert summary['model_count'] == 2
        assert 'models' in summary
        assert 'costs' in summary
        assert 'cache_stats' in summary


class TestFreeModelFailover:
    """Test free model failover behavior."""

    @patch('tools.custom.consensus_models.BandSelector')
    def test_failover_tries_multiple_free_models(self, mock_band_selector):
        """Test failover tries multiple free models when some are unavailable."""
        # Mock BandSelector to return 5 candidate free models
        mock_selector = Mock()
        mock_selector.get_models_by_cost_tier.return_value = [
            "free1", "free2", "free3", "free4", "free5"
        ]

        manager = TierManager(band_selector=mock_selector)

        # Mock availability checks: first 2 fail, next 3 succeed
        with patch.object(manager, '_check_model_availability') as mock_check:
            mock_check.side_effect = [False, False, True, True, True]

            models = manager._get_available_free_models(target=3, max_attempts=10)

            # Should have tried multiple models
            assert mock_check.call_count >= 3

            # Should return 3 available models (skipped first 2)
            assert len(models) == 3
            assert models == ["free3", "free4", "free5"]

    @patch('tools.custom.consensus_models.BandSelector')
    def test_failover_respects_cache(self, mock_band_selector):
        """Test failover skips models cached as unavailable."""
        mock_selector = Mock()
        mock_selector.get_models_by_cost_tier.return_value = [
            "free1", "free2", "free3"
        ]

        manager = TierManager(band_selector=mock_selector)

        # Pre-populate cache: free1 is unavailable
        manager.availability_cache.set_available("free1", False)

        with patch.object(manager, '_check_model_availability') as mock_check:
            mock_check.return_value = True  # All checks succeed

            models = manager._get_available_free_models(target=2, max_attempts=10)

            # Should skip free1 (cached as unavailable)
            # Should only check free2 and free3
            assert mock_check.call_count == 2

            # Should return 2 models (not including free1)
            assert len(models) == 2
            assert "free1" not in models


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
