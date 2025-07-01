"""
Cache Monitoring Tool for Zen MCP Server

This tool provides comprehensive monitoring and management capabilities
for the caching infrastructure, including statistics, health status,
and maintenance operations.
"""

import logging
from typing import List, Optional

from mcp.types import TextContent
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.simple.base import SimpleTool

logger = logging.getLogger(__name__)


class CacheMonitorRequest(ToolRequest):
    """Request model for Cache Monitor tool"""

    action: str = Field(
        ...,
        description=(
            "Action to perform: 'stats' (get statistics), 'health' (check health), "
            "'report' (detailed report), 'cleanup' (run maintenance), "
            "'invalidate' (clear caches), 'warm' (warm caches)"
        ),
    )

    target: Optional[str] = Field(
        default=None,
        description=(
            "Target for action: 'all' (all caches), 'token' (token cache), "
            "'schema' (schema cache), 'model' (model validation cache), "
            "or specific model name for invalidation"
        ),
    )


class CacheMonitorTool(SimpleTool):
    """
    Cache monitoring and management tool.

    Provides comprehensive monitoring capabilities for the caching infrastructure,
    including real-time statistics, health monitoring, maintenance operations,
    and performance analytics.
    """

    def get_name(self) -> str:
        return "cache_monitor"

    def get_description(self) -> str:
        return (
            "CACHE MONITORING & MANAGEMENT - Monitor and manage the caching infrastructure. "
            "Get real-time statistics, health status, detailed performance reports, "
            "and perform maintenance operations. Use this to optimize cache performance, "
            "identify bottlenecks, and maintain cache health."
        )

    def requires_model(self) -> bool:
        """Cache monitor doesn't require AI model execution."""
        return False

    def get_system_prompt(self) -> str:
        """Cache monitor doesn't use AI, so no system prompt needed."""
        return ""

    def get_tool_fields(self) -> dict:
        """Return tool-specific field schemas."""
        return {
            "action": {
                "type": "string",
                "description": (
                    "Action to perform: 'stats' (get statistics), 'health' (check health), "
                    "'report' (detailed report), 'cleanup' (run maintenance), "
                    "'invalidate' (clear caches), 'warm' (warm caches)"
                ),
            },
            "target": {
                "type": "string",
                "description": (
                    "Target for action: 'all' (all caches), 'token' (token cache), "
                    "'schema' (schema cache), 'model' (model validation cache), "
                    "or specific model name for invalidation"
                ),
            },
        }

    def prepare_prompt(self, request: CacheMonitorRequest) -> str:
        """Cache monitor doesn't use AI, so no prompt needed."""
        return ""

    async def execute(self, request: CacheMonitorRequest) -> List[TextContent]:
        """
        Execute cache monitoring operation.

        Args:
            request: CacheMonitorRequest with action and optional target

        Returns:
            List of TextContent objects with formatted responses
        """
        try:
            action = request.action.lower()
            target = request.target.lower() if request.target else "all"

            if action == "stats":
                response_lines = await self._get_statistics(target)
            elif action == "health":
                response_lines = await self._check_health()
            elif action == "report":
                response_lines = await self._generate_report()
            elif action == "cleanup":
                response_lines = await self._run_cleanup(target)
            elif action == "invalidate":
                response_lines = await self._invalidate_caches(target)
            elif action == "warm":
                response_lines = await self._warm_caches()
            else:
                response_lines = [
                    f"Unknown action: {action}. Valid actions: stats, health, report, cleanup, invalidate, warm"
                ]

            # Convert to TextContent objects
            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            logger.error(f"Cache monitor error: {e}")
            return [TextContent(type="text", text=f"Cache monitor error: {str(e)}")]

    async def _get_statistics(self, target: str) -> List[str]:
        """Get cache statistics for specified target."""
        try:
            if target == "all":
                from utils.cache_manager import get_cache_manager

                manager = get_cache_manager()
                stats = manager.get_global_stats()

                response = [
                    "🔧 **CACHE STATISTICS - ALL CACHES**",
                    "",
                    "**Overall Performance:**",
                    f"• Hit Rate: {stats['overall_hit_rate_percent']:.1f}%",
                    f"• Total Requests: {stats['total_requests']:,}",
                    f"• Memory Usage: {stats['total_memory_usage_mb']:.1f}MB / {stats['memory_limit_mb']:.0f}MB",
                    f"• Memory Utilization: {stats['memory_utilization_percent']:.1f}%",
                    "",
                    "**Cache Breakdown:**",
                ]

                for cache_name, cache_stats in stats["cache_breakdown"].items():
                    response.extend(
                        [
                            "",
                            f"**{cache_name.replace('_', ' ').title()}:**",
                            f"• Hit Rate: {cache_stats['hit_rate_percent']:.1f}%",
                            f"• Entries: {cache_stats.get('current_size', cache_stats.get('total_entries', 0))}",
                            f"• Hits: {cache_stats['hits']:,}",
                            f"• Misses: {cache_stats['misses']:,}",
                        ]
                    )

                return response

            elif target == "token":
                from utils.token_cache import get_token_cache_stats

                stats = get_token_cache_stats()

                return [
                    "🔢 **TOKEN CACHE STATISTICS**",
                    "",
                    f"• Hit Rate: {stats['hit_rate_percent']:.1f}%",
                    f"• Cache Size: {stats['current_size']} / {stats['capacity']} entries",
                    f"• Total Requests: {stats['total_requests']:,}",
                    f"• Hits: {stats['hits']:,}",
                    f"• Misses: {stats['misses']:,}",
                    f"• Evictions: {stats['evictions']:,}",
                    f"• Memory Usage: ~{stats['memory_usage_estimate']:,} bytes",
                ]

            elif target == "schema":
                from tools.shared.schema_cache import get_schema_cache_stats

                stats = get_schema_cache_stats()

                response = [
                    "📋 **SCHEMA CACHE STATISTICS**",
                    "",
                    f"• Hit Rate: {stats['hit_rate_percent']:.1f}%",
                    f"• Cache Size: {stats['current_size']} / {stats['capacity']} entries",
                    f"• Total Requests: {stats['total_requests']:,}",
                    f"• Hits: {stats['hits']:,}",
                    f"• Misses: {stats['misses']:,}",
                    f"• Invalidations: {stats['invalidations']:,}",
                    f"• Schema Size: {stats['total_schema_size_bytes']:,} bytes",
                    f"• Tracked Tool Versions: {stats['tracked_tool_versions']}",
                ]

                if stats["tool_counts"]:
                    response.extend(["", "**Schemas by Tool:**"])
                    for tool, count in stats["tool_counts"].items():
                        response.append(f"• {tool}: {count} schemas")

                return response

            elif target == "model":
                from utils.model_validation_cache import get_model_validation_cache_stats

                stats = get_model_validation_cache_stats()

                return [
                    "🤖 **MODEL VALIDATION CACHE STATISTICS**",
                    "",
                    f"• Hit Rate: {stats['hit_rate_percent']:.1f}%",
                    f"• Total Entries: {stats['total_entries']}",
                    f"• Availability Cache: {stats['availability_cache_size']} entries",
                    f"• Capability Cache: {stats['capability_cache_size']} entries",
                    f"• Resolution Cache: {stats['resolution_cache_size']} entries",
                    f"• Total Requests: {stats['total_requests']:,}",
                    f"• Hits: {stats['hits']:,}",
                    f"• Misses: {stats['misses']:,}",
                    f"• Invalidations: {stats['invalidations']:,}",
                ]

            else:
                return [f"Unknown target: {target}. Valid targets: all, token, schema, model"]

        except ImportError as e:
            return [f"Cache system not available: {e}"]
        except Exception as e:
            return [f"Error getting statistics: {e}"]

    async def _check_health(self) -> List[str]:
        """Check cache system health status."""
        try:
            from utils.cache_manager import get_cache_manager

            manager = get_cache_manager()

            health = manager.get_health_status()
            memory_check = manager.check_memory_usage()

            status_emoji = "✅" if health["overall_healthy"] else "⚠️"

            response = [
                f"{status_emoji} **CACHE SYSTEM HEALTH STATUS**",
                "",
                f"**Overall Status:** {'HEALTHY' if health['overall_healthy'] else 'UNHEALTHY'}",
                "",
                "**Health Indicators:**",
            ]

            for indicator, status in health["indicators"].items():
                status_icon = "✅" if status else "❌"
                response.append(f"• {indicator.replace('_', ' ').title()}: {status_icon}")

            response.extend(
                [
                    "",
                    "**Memory Status:**",
                    f"• Usage: {memory_check['total_memory_mb']:.1f}MB",
                    f"• Utilization: {memory_check['utilization_percent']:.1f}%",
                    f"• Status: {'HEALTHY' if memory_check['is_healthy'] else 'WARNING'}",
                ]
            )

            if health["warnings"]:
                response.extend(["", "**⚠️ Warnings:**"])
                for warning in health["warnings"]:
                    response.append(f"• {warning}")

            if health["recommendations"]:
                response.extend(["", "**💡 Recommendations:**"])
                for rec in health["recommendations"]:
                    response.append(f"• {rec}")

            return response

        except ImportError as e:
            return [f"Cache system not available: {e}"]
        except Exception as e:
            return [f"Error checking health: {e}"]

    async def _generate_report(self) -> List[str]:
        """Generate detailed performance report."""
        try:
            from utils.cache_manager import get_cache_manager

            manager = get_cache_manager()

            report = manager.get_detailed_report()

            return ["📊 **DETAILED CACHE PERFORMANCE REPORT**", "", "```", report, "```"]

        except ImportError as e:
            return [f"Cache system not available: {e}"]
        except Exception as e:
            return [f"Error generating report: {e}"]

    async def _run_cleanup(self, target: str) -> List[str]:
        """Run cache cleanup/maintenance."""
        try:
            if target == "all":
                from utils.cache_manager import get_cache_manager

                manager = get_cache_manager()
                manager.cleanup_all_caches()

                return [
                    "🧹 **CACHE CLEANUP COMPLETED**",
                    "",
                    "• All caches cleaned up successfully",
                    "• Expired entries removed",
                    "• Memory optimized",
                ]

            else:
                # Target-specific cleanup
                if target == "token":
                    from utils.token_cache import get_token_cache

                    cache = get_token_cache()
                    cache.cleanup()
                    cache_type = "Token cache"
                elif target == "schema":
                    from tools.shared.schema_cache import get_schema_cache

                    cache = get_schema_cache()
                    cache.cleanup()
                    cache_type = "Schema cache"
                elif target == "model":
                    from utils.model_validation_cache import get_model_validation_cache

                    cache = get_model_validation_cache()
                    cache.cleanup_all()
                    cache_type = "Model validation cache"
                else:
                    return [f"Unknown cleanup target: {target}"]

                return [
                    f"🧹 **{cache_type.upper()} CLEANUP COMPLETED**",
                    "",
                    f"• {cache_type} cleaned up successfully",
                    "• Expired entries removed",
                ]

        except ImportError as e:
            return [f"Cache system not available: {e}"]
        except Exception as e:
            return [f"Error during cleanup: {e}"]

    async def _invalidate_caches(self, target: str) -> List[str]:
        """Invalidate caches or specific models."""
        try:
            if target == "all":
                from utils.cache_manager import get_cache_manager

                manager = get_cache_manager()
                manager.invalidate_all_caches()

                return [
                    "🗑️ **ALL CACHES INVALIDATED**",
                    "",
                    "• All cache entries cleared",
                    "• Fresh cache state restored",
                    "⚠️ **Warning:** Cache performance will be temporarily reduced",
                ]

            elif target in ["token", "schema", "model"]:
                if target == "token":
                    from utils.token_cache import clear_token_cache

                    clear_token_cache()
                    cache_type = "Token cache"
                elif target == "schema":
                    from tools.shared.schema_cache import clear_schema_cache

                    clear_schema_cache()
                    cache_type = "Schema cache"
                elif target == "model":
                    from utils.model_validation_cache import get_model_validation_cache

                    cache = get_model_validation_cache()
                    # Model cache doesn't have a global clear, so we'll skip
                    cache_type = "Model validation cache"
                    return ["Model validation cache doesn't support global invalidation"]

                return [
                    f"🗑️ **{cache_type.upper()} INVALIDATED**",
                    "",
                    f"• {cache_type} cleared successfully",
                    "⚠️ **Warning:** Cache performance will be temporarily reduced",
                ]

            else:
                # Assume it's a model name
                from utils.cache_manager import get_cache_manager

                manager = get_cache_manager()
                manager.invalidate_model_caches(target)

                return [
                    f"🗑️ **MODEL CACHES INVALIDATED: {target}**",
                    "",
                    f"• All cache entries for model '{target}' cleared",
                    "• Token estimation cache cleared for model",
                    "• Model validation cache cleared for model",
                ]

        except ImportError as e:
            return [f"Cache system not available: {e}"]
        except Exception as e:
            return [f"Error during invalidation: {e}"]

    async def _warm_caches(self) -> List[str]:
        """Warm caches with common data."""
        try:
            from utils.cache_manager import get_cache_manager

            manager = get_cache_manager()
            manager.warm_all_caches()

            return [
                "🔥 **CACHE WARMING COMPLETED**",
                "",
                "• Caches warmed with common data",
                "• Token cache warmed with standard prompts",
                "• Performance should be improved for common operations",
                "",
                "💡 **Tip:** Run cache warming after server startup for best performance",
            ]

        except ImportError as e:
            return [f"Cache system not available: {e}"]
        except Exception as e:
            return [f"Error during cache warming: {e}"]
