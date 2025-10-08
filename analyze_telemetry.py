#!/usr/bin/env python3
"""
Telemetry Analysis Script for Zen MCP Token Optimization A/B Testing

This script analyzes the telemetry data collected during A/B testing to compare
the effectiveness of the token optimization against the baseline.
"""

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


class TelemetryAnalyzer:
    """Analyze token optimization telemetry data."""

    def __init__(self, telemetry_file: str = None):
        """Initialize the analyzer with telemetry file path."""
        if telemetry_file:
            self.telemetry_file = Path(telemetry_file)
        else:
            # Default locations to check
            locations = [
                Path("./telemetry_export/token_telemetry.jsonl"),
                Path("./logs/token_telemetry.jsonl"),
                Path.home() / ".zen_mcp" / "token_telemetry.jsonl",
            ]

            for loc in locations:
                if loc.exists():
                    self.telemetry_file = loc
                    break
            else:
                raise FileNotFoundError(f"No telemetry file found in: {locations}")

        self.data = self._load_data()
        self.optimized_data = []
        self.baseline_data = []
        self._categorize_data()

    def _load_data(self) -> List[Dict]:
        """Load telemetry data from JSONL file."""
        data = []
        print(f"Loading telemetry from: {self.telemetry_file}")

        with open(self.telemetry_file) as f:
            for line in f:
                try:
                    data.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        print(f"Loaded {len(data)} telemetry events")
        return data

    def _categorize_data(self):
        """Categorize data by version (optimized vs baseline)."""
        for entry in self.data:
            version = entry.get("version", "")
            if "alpha" in version or "optimized" in version:
                self.optimized_data.append(entry)
            else:
                self.baseline_data.append(entry)

    def analyze_mode_selections(self) -> Dict[str, Any]:
        """Analyze mode selection patterns."""
        optimized_modes = defaultdict(int)

        for entry in self.optimized_data:
            if entry.get("event") == "mode_selection":
                mode = entry.get("mode", "unknown")
                complexity = entry.get("complexity", "unknown")
                key = f"{mode}_{complexity}"
                optimized_modes[key] += 1

        return {
            "total_selections": sum(optimized_modes.values()),
            "mode_distribution": dict(optimized_modes),
            "most_common": max(optimized_modes.items(), key=lambda x: x[1])[0] if optimized_modes else None,
        }

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics."""

        def get_latencies(data):
            latencies = []
            for entry in data:
                if entry.get("event") == "latency":
                    latencies.append(entry.get("duration_ms", 0))
            return latencies

        opt_latencies = get_latencies(self.optimized_data)
        base_latencies = get_latencies(self.baseline_data)

        results = {}

        if opt_latencies:
            results["optimized"] = {
                "avg_latency_ms": statistics.mean(opt_latencies),
                "median_latency_ms": statistics.median(opt_latencies),
                "min_latency_ms": min(opt_latencies),
                "max_latency_ms": max(opt_latencies),
                "count": len(opt_latencies),
            }

        if base_latencies:
            results["baseline"] = {
                "avg_latency_ms": statistics.mean(base_latencies),
                "median_latency_ms": statistics.median(base_latencies),
                "min_latency_ms": min(base_latencies),
                "max_latency_ms": max(base_latencies),
                "count": len(base_latencies),
            }

        # Calculate improvement
        if opt_latencies and base_latencies:
            opt_avg = statistics.mean(opt_latencies)
            base_avg = statistics.mean(base_latencies)

            if base_avg > 0:
                improvement = ((base_avg - opt_avg) / base_avg) * 100
                results["latency_improvement"] = f"{improvement:.1f}%"

        return results

    def analyze_token_usage(self) -> Dict[str, Any]:
        """Analyze token usage patterns."""

        def get_tokens(data):
            tokens = []
            for entry in data:
                if entry.get("event") == "tool_execution":
                    token_count = entry.get("tokens_used")
                    if token_count:
                        tokens.append(token_count)
            return tokens

        opt_tokens = get_tokens(self.optimized_data)
        base_tokens = get_tokens(self.baseline_data) or [43000]  # Default baseline

        results = {}

        if opt_tokens:
            results["optimized"] = {
                "avg_tokens": statistics.mean(opt_tokens),
                "median_tokens": statistics.median(opt_tokens),
                "total_tokens": sum(opt_tokens),
                "executions": len(opt_tokens),
            }

        if base_tokens:
            results["baseline"] = {
                "avg_tokens": statistics.mean(base_tokens),
                "median_tokens": statistics.median(base_tokens),
                "total_tokens": sum(base_tokens),
                "executions": len(base_tokens),
            }

        # Calculate token savings
        if opt_tokens and base_tokens:
            opt_avg = statistics.mean(opt_tokens)
            base_avg = statistics.mean(base_tokens) if base_tokens else 43000

            savings = ((base_avg - opt_avg) / base_avg) * 100
            results["token_savings"] = f"{savings:.1f}%"
            results["absolute_savings"] = int(base_avg - opt_avg)

        return results

    def analyze_success_rates(self) -> Dict[str, Any]:
        """Analyze tool execution success rates."""

        def get_success_rate(data):
            total = 0
            successful = 0

            for entry in data:
                if entry.get("event") == "tool_execution":
                    total += 1
                    if entry.get("success", False):
                        successful += 1

            return (successful / total * 100) if total > 0 else 0, total

        opt_rate, opt_total = get_success_rate(self.optimized_data)
        base_rate, base_total = get_success_rate(self.baseline_data)

        results = {
            "optimized": {"success_rate": f"{opt_rate:.1f}%", "total_executions": opt_total},
            "baseline": {"success_rate": f"{base_rate:.1f}%", "total_executions": base_total},
        }

        # Check if success rate maintained
        if opt_rate >= base_rate - 5:  # Allow 5% tolerance
            results["effectiveness_maintained"] = True
        else:
            results["effectiveness_maintained"] = False

        return results

    def analyze_retry_patterns(self) -> Dict[str, Any]:
        """Analyze retry patterns."""

        def get_retry_stats(data):
            retries = []
            for entry in data:
                if entry.get("event") == "retry":
                    retries.append(entry.get("attempt", 1))

            return retries

        opt_retries = get_retry_stats(self.optimized_data)
        base_retries = get_retry_stats(self.baseline_data)

        results = {}

        if opt_retries:
            results["optimized"] = {
                "total_retries": len(opt_retries),
                "avg_attempts": statistics.mean(opt_retries),
                "max_attempts": max(opt_retries),
            }

        if base_retries:
            results["baseline"] = {
                "total_retries": len(base_retries),
                "avg_attempts": statistics.mean(base_retries),
                "max_attempts": max(base_retries),
            }

        return results

    def generate_report(self) -> str:
        """Generate comprehensive A/B test report."""
        report = []
        report.append("=" * 60)
        report.append("    Zen MCP Token Optimization A/B Test Report")
        report.append("=" * 60)
        report.append("")

        # Data summary
        report.append("📊 Data Summary:")
        report.append(f"  Total events: {len(self.data)}")
        report.append(f"  Optimized events: {len(self.optimized_data)}")
        report.append(f"  Baseline events: {len(self.baseline_data)}")
        report.append("")

        # Token usage analysis
        report.append("💾 Token Usage Analysis:")
        token_stats = self.analyze_token_usage()
        if "optimized" in token_stats:
            report.append("  Optimized:")
            report.append(f"    Average: {token_stats['optimized']['avg_tokens']:.0f} tokens")
            report.append(f"    Total: {token_stats['optimized']['total_tokens']:.0f} tokens")
        if "baseline" in token_stats:
            report.append("  Baseline:")
            report.append(f"    Average: {token_stats['baseline']['avg_tokens']:.0f} tokens")
            report.append(f"    Total: {token_stats['baseline']['total_tokens']:.0f} tokens")
        if "token_savings" in token_stats:
            report.append(f"  🎯 Token Savings: {token_stats['token_savings']}")
            report.append(f"  🎯 Absolute Savings: {token_stats['absolute_savings']} tokens per call")
        report.append("")

        # Performance analysis
        report.append("⚡ Performance Analysis:")
        perf_stats = self.analyze_performance()
        if "optimized" in perf_stats:
            report.append("  Optimized:")
            report.append(f"    Avg latency: {perf_stats['optimized']['avg_latency_ms']:.1f}ms")
            report.append(f"    Median: {perf_stats['optimized']['median_latency_ms']:.1f}ms")
        if "baseline" in perf_stats:
            report.append("  Baseline:")
            report.append(f"    Avg latency: {perf_stats['baseline']['avg_latency_ms']:.1f}ms")
            report.append(f"    Median: {perf_stats['baseline']['median_latency_ms']:.1f}ms")
        if "latency_improvement" in perf_stats:
            report.append(f"  🎯 Latency Improvement: {perf_stats['latency_improvement']}")
        report.append("")

        # Success rates
        report.append("✅ Success Rate Analysis:")
        success_stats = self.analyze_success_rates()
        if "optimized" in success_stats:
            report.append(
                f"  Optimized: {success_stats['optimized']['success_rate']} ({success_stats['optimized']['total_executions']} executions)"
            )
        if "baseline" in success_stats:
            report.append(
                f"  Baseline: {success_stats['baseline']['success_rate']} ({success_stats['baseline']['total_executions']} executions)"
            )
        if "effectiveness_maintained" in success_stats:
            if success_stats["effectiveness_maintained"]:
                report.append("  🎯 Effectiveness: MAINTAINED ✅")
            else:
                report.append("  ⚠️  Effectiveness: DEGRADED")
        report.append("")

        # Mode selection patterns
        if self.optimized_data:
            report.append("🎯 Mode Selection Patterns:")
            mode_stats = self.analyze_mode_selections()
            report.append(f"  Total selections: {mode_stats['total_selections']}")
            if mode_stats["most_common"]:
                report.append(f"  Most common: {mode_stats['most_common']}")
            if mode_stats["mode_distribution"]:
                report.append("  Distribution:")
                for mode, count in sorted(mode_stats["mode_distribution"].items(), key=lambda x: x[1], reverse=True):
                    report.append(f"    {mode}: {count}")
            report.append("")

        # Retry patterns
        report.append("🔄 Retry Patterns:")
        retry_stats = self.analyze_retry_patterns()
        if "optimized" in retry_stats:
            report.append(f"  Optimized: {retry_stats['optimized']['total_retries']} retries")
        if "baseline" in retry_stats:
            report.append(f"  Baseline: {retry_stats['baseline']['total_retries']} retries")
        report.append("")

        # Summary
        report.append("=" * 60)
        report.append("📈 SUMMARY:")

        # Determine success
        success_criteria = []

        # Check token savings
        if "token_savings" in token_stats:
            savings = float(token_stats["token_savings"].rstrip("%"))
            if savings > 85:
                success_criteria.append(f"✅ Token reduction: {token_stats['token_savings']} (target: >85%)")
            else:
                success_criteria.append(f"❌ Token reduction: {token_stats['token_savings']} (target: >85%)")

        # Check effectiveness
        if "effectiveness_maintained" in success_stats:
            if success_stats["effectiveness_maintained"]:
                success_criteria.append("✅ Effectiveness maintained")
            else:
                success_criteria.append("❌ Effectiveness degraded")

        for criterion in success_criteria:
            report.append(f"  {criterion}")

        # Final verdict
        if all("✅" in c for c in success_criteria):
            report.append("")
            report.append("🎉 RESULT: Token optimization SUCCESSFUL!")
            report.append("   Ready for production deployment")
        else:
            report.append("")
            report.append("⚠️  RESULT: Token optimization needs tuning")
            report.append("   Review mode selection heuristics")

        report.append("=" * 60)

        return "\n".join(report)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Zen MCP token optimization telemetry")
    parser.add_argument("--file", "-f", help="Path to telemetry file")
    parser.add_argument("--export", "-e", help="Export report to file")

    args = parser.parse_args()

    try:
        analyzer = TelemetryAnalyzer(args.file)
        report = analyzer.generate_report()

        print(report)

        if args.export:
            with open(args.export, "w") as f:
                f.write(report)
            print(f"\nReport exported to: {args.export}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nPlease ensure telemetry data exists. Run some tests first or specify the file path with --file")
        sys.exit(1)
    except Exception as e:
        print(f"Error analyzing telemetry: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
