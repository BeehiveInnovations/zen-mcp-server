"""
Token Optimization Configuration

This module manages the configuration for the two-stage token optimization architecture.
It provides feature flags for A/B testing and controls the behavior of the optimized
tool loading system.

Environment Variables:
- ZEN_TOKEN_OPTIMIZATION: Enable token optimization ("enabled", "disabled", "auto")
- ZEN_OPTIMIZATION_MODE: Optimization strategy ("two_stage", "single_orchestrator")
- ZEN_TOKEN_TELEMETRY: Enable telemetry for A/B testing ("true", "false")
- ZEN_OPTIMIZATION_VERSION: Version for A/B testing tracking
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Feature flags from environment
TOKEN_OPTIMIZATION_ENABLED = os.getenv("ZEN_TOKEN_OPTIMIZATION", "enabled").lower()
OPTIMIZATION_MODE = os.getenv("ZEN_OPTIMIZATION_MODE", "two_stage").lower()
TELEMETRY_ENABLED = os.getenv("ZEN_TOKEN_TELEMETRY", "true").lower() == "true"
OPTIMIZATION_VERSION = os.getenv("ZEN_OPTIMIZATION_VERSION", "v5.12.0")

# Telemetry file path
# In Docker, use the logs directory which is writable
if os.path.exists("/app/logs"):
    TELEMETRY_FILE = Path("/app/logs") / "token_telemetry.jsonl"
else:
    TELEMETRY_FILE = Path.home() / ".zen_mcp" / "token_telemetry.jsonl"


class TokenOptimizationConfig:
    """
    Configuration manager for token optimization features.

    This class handles feature flags, telemetry, and A/B testing configuration
    for the two-stage token optimization architecture.
    """

    def __init__(self):
        self.enabled = TOKEN_OPTIMIZATION_ENABLED in ["enabled", "auto"]
        self.mode = OPTIMIZATION_MODE
        self.telemetry_enabled = TELEMETRY_ENABLED
        self.version = OPTIMIZATION_VERSION

        # Statistics for A/B testing
        self.stats = {
            "mode_selections": {},
            "tool_executions": {},
            "token_savings": [],
            "retry_counts": {},
            "latency_measurements": [],
            "session_start": time.time(),
        }

        # Ensure telemetry directory exists
        if self.telemetry_enabled:
            # In Docker, /app/logs already exists; only create for local dev
            if not os.path.exists("/app/logs"):
                TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)

    def is_enabled(self) -> bool:
        """Check if token optimization is enabled"""
        return self.enabled

    def is_two_stage(self) -> bool:
        """Check if using two-stage architecture"""
        return self.mode == "two_stage" and self.enabled

    def should_use_original_tools(self) -> bool:
        """
        Determine if we should use original tool registration.

        Returns True if optimization is disabled or in fallback mode.
        """
        return not self.enabled or TOKEN_OPTIMIZATION_ENABLED == "disabled"

    def record_mode_selection(self, mode: str, complexity: str, confidence: str):
        """Record a mode selection event for telemetry"""
        if not self.telemetry_enabled:
            return

        key = f"{mode}_{complexity}"
        self.stats["mode_selections"][key] = self.stats["mode_selections"].get(key, 0) + 1

        self._append_telemetry(
            {
                "event": "mode_selection",
                "mode": mode,
                "complexity": complexity,
                "confidence": confidence,
                "timestamp": time.time(),
                "version": self.version,
            }
        )

    def record_tool_execution(self, tool: str, success: bool, tokens_used: Optional[int] = None):
        """Record a tool execution event"""
        if not self.telemetry_enabled:
            return

        self.stats["tool_executions"][tool] = self.stats["tool_executions"].get(tool, 0) + 1

        if tokens_used:
            self.stats["token_savings"].append(tokens_used)

        self._append_telemetry(
            {
                "event": "tool_execution",
                "tool": tool,
                "success": success,
                "tokens_used": tokens_used,
                "timestamp": time.time(),
                "version": self.version,
            }
        )

    def record_retry(self, tool: str, attempt: int):
        """Record a retry attempt"""
        if not self.telemetry_enabled:
            return

        self.stats["retry_counts"][tool] = self.stats["retry_counts"].get(tool, [])
        self.stats["retry_counts"][tool].append(attempt)

        self._append_telemetry(
            {"event": "retry", "tool": tool, "attempt": attempt, "timestamp": time.time(), "version": self.version}
        )

    def record_latency(self, operation: str, duration_ms: float):
        """Record operation latency"""
        if not self.telemetry_enabled:
            return

        self.stats["latency_measurements"].append({"operation": operation, "duration_ms": duration_ms})

        self._append_telemetry(
            {
                "event": "latency",
                "operation": operation,
                "duration_ms": duration_ms,
                "timestamp": time.time(),
                "version": self.version,
            }
        )

    def get_stats_summary(self) -> Dict:
        """Get summary statistics for the current session"""
        session_duration = time.time() - self.stats["session_start"]

        total_executions = sum(self.stats["tool_executions"].values())
        avg_tokens = (
            sum(self.stats["token_savings"]) / len(self.stats["token_savings"]) if self.stats["token_savings"] else 0
        )

        retry_rates = {}
        for tool, retries in self.stats["retry_counts"].items():
            retry_rates[tool] = sum(retries) / len(retries) if retries else 0

        return {
            "version": self.version,
            "optimization_enabled": self.enabled,
            "mode": self.mode,
            "session_duration_seconds": session_duration,
            "total_tool_executions": total_executions,
            "mode_selections": self.stats["mode_selections"],
            "average_tokens_per_call": avg_tokens,
            "retry_rates": retry_rates,
            "telemetry_file": str(TELEMETRY_FILE) if self.telemetry_enabled else None,
        }

    def _append_telemetry(self, data: Dict):
        """Append telemetry data to file"""
        try:
            with open(TELEMETRY_FILE, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.debug(f"Failed to write telemetry: {e}")

    def log_configuration(self):
        """Log the current configuration for debugging"""
        logger.info("Token Optimization Configuration:")
        logger.info(f"  - Enabled: {self.enabled}")
        logger.info(f"  - Mode: {self.mode}")
        logger.info(f"  - Version: {self.version}")
        logger.info(f"  - Telemetry: {self.telemetry_enabled}")

        if self.enabled:
            if self.mode == "two_stage":
                logger.info("  - Using two-stage architecture for 82% token reduction")
            else:
                logger.info(f"  - Using {self.mode} mode")
        else:
            logger.info("  - Using original tool registration (no optimization)")


# Global configuration instance
token_config = TokenOptimizationConfig()


def estimate_token_savings(original_schema_size: int, optimized_schema_size: int) -> float:
    """
    Estimate the token savings percentage.

    Args:
        original_schema_size: Size of original schema in characters
        optimized_schema_size: Size of optimized schema in characters

    Returns:
        Percentage of tokens saved (0-100)
    """
    if original_schema_size == 0:
        return 0.0

    savings = ((original_schema_size - optimized_schema_size) / original_schema_size) * 100
    return max(0.0, min(100.0, savings))


def should_use_mode_selector() -> bool:
    """
    Determine if the mode selector should be used for the current request.

    This allows for gradual rollout or A/B testing.
    """
    if not token_config.is_enabled():
        return False

    if TOKEN_OPTIMIZATION_ENABLED == "auto":
        # In auto mode, we could use random selection for A/B testing
        # For now, always use optimization in auto mode
        return True

    return token_config.is_two_stage()
