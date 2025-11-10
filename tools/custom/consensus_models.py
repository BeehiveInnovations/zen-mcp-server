"""
Consensus Model Selection and Tier Management.

Implements additive tier architecture with BandSelector integration,
free model failover, and paid model deprecation alerts.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from tools.custom.band_selector import BandSelector

logger = logging.getLogger(__name__)


@dataclass
class ModelAvailability:
    """Track model availability status."""

    model: str
    is_available: bool
    last_checked: float
    error_code: Optional[int] = None
    error_message: Optional[str] = None


class AvailabilityCache:
    """
    Cache model availability to avoid repeated health checks.

    Implements 5-minute TTL for transient free model availability.
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize availability cache.

        Args:
            ttl_seconds: Time-to-live for cached availability (default: 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, ModelAvailability] = {}

    def is_available(self, model: str) -> Optional[bool]:
        """
        Check if model is available from cache.

        Args:
            model: Model name

        Returns:
            True if available, False if unavailable, None if not cached or expired
        """
        if model not in self._cache:
            return None

        cached = self._cache[model]
        age = time.time() - cached.last_checked

        if age > self.ttl_seconds:
            # Cache expired
            del self._cache[model]
            return None

        return cached.is_available

    def set_available(self, model: str, is_available: bool, error_code: Optional[int] = None, error_message: Optional[str] = None):
        """
        Update model availability in cache.

        Args:
            model: Model name
            is_available: Whether model is currently available
            error_code: HTTP error code if unavailable
            error_message: Error message if unavailable
        """
        self._cache[model] = ModelAvailability(
            model=model,
            is_available=is_available,
            last_checked=time.time(),
            error_code=error_code,
            error_message=error_message,
        )

    def clear(self):
        """Clear all cached availability data."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = len(self._cache)
        available = sum(1 for v in self._cache.values() if v.is_available)
        unavailable = total - available

        return {
            "total_cached": total,
            "available": available,
            "unavailable": unavailable,
        }


class TierManager:
    """
    Manages model selection across organizational tiers with additive architecture.

    Implements:
    - Additive tier architecture (Level 2 includes Level 1's models)
    - BandSelector integration (no hardcoded model lists)
    - Free model failover (from dynamic-model-availability.md ADR)
    - Paid model deprecation alerts
    """

    def __init__(self, band_selector: Optional[BandSelector] = None):
        """
        Initialize tier manager.

        Args:
            band_selector: BandSelector instance (creates new if None)
        """
        self.band_selector = band_selector or BandSelector()
        self.availability_cache = AvailabilityCache(ttl_seconds=300)  # 5-minute TTL

    def get_tier_models(self, level: int, max_attempts: int = 10) -> List[str]:
        """
        Get models for specified tier with additive architecture.

        Level 1: 3 free models
        Level 2: Level 1's models + 3 economy models (6 total)
        Level 3: Level 2's models + 2 premium models (8 total)

        Args:
            level: Organizational level (1, 2, or 3)
            max_attempts: Maximum models to try for failover

        Returns:
            List of model names (additive - higher levels include all lower level models)

        Raises:
            ValueError: If level is invalid
        """
        if level not in [1, 2, 3]:
            raise ValueError(f"Invalid level: {level}. Must be 1, 2, or 3")

        if level == 1:
            # Level 1: 3 free models with failover
            return self._get_available_free_models(target=3, max_attempts=max_attempts)

        elif level == 2:
            # Level 2: Level 1's models + 3 economy models (ADDITIVE)
            tier1_models = self._get_available_free_models(target=3, max_attempts=max_attempts)
            economy_models = self._get_economy_models(target=3)
            return tier1_models + economy_models

        else:  # level == 3
            # Level 3: Level 2's models + 2 premium models (ADDITIVE)
            tier1_models = self._get_available_free_models(target=3, max_attempts=max_attempts)
            economy_models = self._get_economy_models(target=3)
            premium_models = self._get_premium_models(target=2)
            return tier1_models + economy_models + premium_models

    def _get_available_free_models(self, target: int, max_attempts: int) -> List[str]:
        """
        Get available free models with failover for transient availability.

        Tries multiple free models until we get the target number or exhaust attempts.

        Args:
            target: Target number of free models
            max_attempts: Maximum models to try

        Returns:
            List of available free model names
        """
        # Get candidate free models from BandSelector
        candidates = self.band_selector.get_models_by_cost_tier("free", limit=max_attempts)

        available = []
        attempts = 0

        for model in candidates:
            if len(available) >= target:
                break

            attempts += 1
            if attempts > max_attempts:
                break

            # Check cache first
            cached_status = self.availability_cache.is_available(model)
            if cached_status is False:
                logger.debug(f"Skipping {model} (cached as unavailable)")
                continue

            # Health check (simulated for now - actual implementation would call model)
            is_available = self._check_model_availability(model)

            if is_available:
                available.append(model)
                logger.debug(f"Free model {model} is available")
            else:
                logger.debug(f"Free model {model} temporarily unavailable (transient)")

        if len(available) < target:
            logger.warning(
                f"Only found {len(available)} available free models "
                f"(target: {target}, attempts: {attempts})"
            )

        return available

    def _get_economy_models(self, target: int) -> List[str]:
        """
        Get economy tier models (should be stable, no failover).

        Args:
            target: Target number of economy models

        Returns:
            List of economy model names
        """
        models = self.band_selector.get_models_by_cost_tier("economy", limit=target)

        # Economy models should be stable (paid tier)
        # If they fail, it's a permanent issue requiring manual intervention
        for model in models:
            is_available = self._check_model_availability(model)
            if not is_available:
                logger.error(
                    f"Economy model {model} is unavailable. "
                    f"This is a paid model - failure indicates deprecation needed."
                )

        return models

    def _get_premium_models(self, target: int) -> List[str]:
        """
        Get premium tier models (should be stable, alert if fail).

        Args:
            target: Target number of premium models

        Returns:
            List of premium model names
        """
        models = self.band_selector.get_models_by_cost_tier("premium", limit=target)

        # Premium models should have 99.9%+ uptime
        # Failures indicate serious issues requiring removal
        for model in models:
            is_available = self._check_model_availability(model)
            if not is_available:
                logger.critical(
                    f"CRITICAL: Premium model {model} is unavailable. "
                    f"This is a paid flagship model - failure indicates deprecation needed."
                )
                self._alert_paid_model_failure(model, tier="premium")

        return models

    def _check_model_availability(self, model: str) -> bool:
        """
        Check if model is currently available.

        This is a placeholder for actual model health check.
        Real implementation would make a lightweight test request.

        Args:
            model: Model name

        Returns:
            True if available, False otherwise
        """
        # Check cache first
        cached_status = self.availability_cache.is_available(model)
        if cached_status is not None:
            return cached_status

        # TODO: Real implementation would call the model with minimal prompt
        # For now, assume all models are available
        # Actual implementation:
        # try:
        #     response = call_model(model=model, prompt="test", max_tokens=1, timeout=5)
        #     is_available = response.status_code == 200
        # except HTTPError as e:
        #     is_available = False
        #     self._handle_model_error(model, e.status_code)

        is_available = True  # Placeholder
        self.availability_cache.set_available(model, is_available)
        return is_available

    def _handle_model_error(self, model: str, error_code: int):
        """
        Handle model availability error based on tier and error code.

        Args:
            model: Model name
            error_code: HTTP error code
        """
        is_paid = self._is_paid_model(model)

        if is_paid and error_code in [404, 429]:
            # Paid models shouldn't fail with these codes
            logger.error(
                f"CRITICAL: Paid model {model} returned {error_code}. "
                f"This indicates the model should be removed from registry."
            )
            self._alert_paid_model_failure(model, error_code=error_code)
        elif error_code == 503:
            # Temporary capacity issue - retry
            logger.warning(f"Model {model} returned 503 (temporary capacity issue)")
        elif error_code == 401:
            # API key issue - don't failover
            logger.error(f"Model {model} returned 401 (API key issue - check configuration)")
        else:
            logger.debug(f"Model {model} unavailable: error {error_code}")

    def _is_paid_model(self, model: str) -> bool:
        """
        Check if model is in paid tier (not free).

        Args:
            model: Model name

        Returns:
            True if paid model, False if free
        """
        # Check models.csv for model status
        model_data = self.band_selector.models_df[self.band_selector.models_df['model'] == model]

        if model_data.empty:
            logger.warning(f"Model {model} not found in registry")
            return False

        status = model_data.iloc[0]['status']
        return status != 'free'

    def _alert_paid_model_failure(self, model: str, tier: str = "unknown", error_code: Optional[int] = None):
        """
        Alert about paid model failure requiring manual intervention.

        Args:
            model: Model name
            tier: Model tier (economy, premium, etc.)
            error_code: HTTP error code if available
        """
        alert_message = {
            "severity": "CRITICAL",
            "model": model,
            "tier": tier,
            "error_code": error_code,
            "action_required": "Update models.csv status to 'deprecated'",
            "timestamp": time.time(),
        }

        # Log to dedicated alert channel
        logger.critical(f"Paid model failure alert: {alert_message}")

        # TODO: Could also send to monitoring service, Slack, PagerDuty, etc.

    def get_tier_costs(self, level: int) -> Dict[str, float]:
        """
        Get estimated costs for specified tier.

        Args:
            level: Organizational level (1, 2, or 3)

        Returns:
            Dictionary with cost estimates
        """
        models = self.get_tier_models(level)

        total_input_cost = 0.0
        total_output_cost = 0.0

        for model in models:
            model_data = self.band_selector.models_df[self.band_selector.models_df['model'] == model]

            if not model_data.empty:
                total_input_cost += model_data.iloc[0]['input_cost']
                total_output_cost += model_data.iloc[0]['output_cost']

        # Rough estimate: 1K input tokens, 2K output tokens per model
        input_tokens = 1000
        output_tokens = 2000

        estimated_cost = (total_input_cost * input_tokens + total_output_cost * output_tokens) / 1_000_000

        return {
            "level": level,
            "model_count": len(models),
            "estimated_cost_per_call": round(estimated_cost, 4),
            "input_cost_per_million": round(total_input_cost, 2),
            "output_cost_per_million": round(total_output_cost, 2),
        }

    def get_tier_summary(self, level: int) -> Dict[str, any]:
        """
        Get comprehensive summary for specified tier.

        Args:
            level: Organizational level (1, 2, or 3)

        Returns:
            Dictionary with tier summary
        """
        models = self.get_tier_models(level)
        costs = self.get_tier_costs(level)

        return {
            "level": level,
            "models": models,
            "model_count": len(models),
            "costs": costs,
            "cache_stats": self.availability_cache.get_stats(),
        }


def get_level_description(level: int) -> str:
    """
    Get human-readable description of tier level.

    Args:
        level: Organizational level (1, 2, or 3)

    Returns:
        Description string
    """
    descriptions = {
        1: "Foundation (3 free models, $0 cost) - Quick validation and initial review",
        2: "Professional (6 models: 3 free + 3 economy, ~$0.50 cost) - Standard development decisions",
        3: "Executive (8 models: 3 free + 3 economy + 2 premium, ~$5 cost) - Critical architectural decisions",
    }

    return descriptions.get(level, f"Unknown level: {level}")
