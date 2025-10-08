#!/usr/bin/env python3
"""Quick test to generate telemetry data"""

import os
import sys

sys.path.insert(0, "/app")
os.chdir("/app")

import time

from token_optimization_config import token_config

# Simulate some tool executions to generate telemetry
print("Generating test telemetry...")

# Test 1: Mode selection
token_config.log_mode_selection("debug", "simple", "high")
print("✓ Logged mode selection: debug")

time.sleep(1)

# Test 2: Tool execution
token_config.log_tool_execution(
    tool_name="zen_select_mode",
    success=True,
    tokens_used=187,  # Simulated token count for optimized mode
    latency_ms=250,
    mode="debug",
)
print("✓ Logged tool execution: zen_select_mode (187 tokens)")

time.sleep(1)

# Test 3: Another execution
token_config.log_tool_execution(
    tool_name="debug", success=True, tokens_used=650, latency_ms=1200, mode="debug"  # Typical for stage 2
)
print("✓ Logged tool execution: debug (650 tokens)")

time.sleep(1)

# Test 4: Chat execution
token_config.log_tool_execution(tool_name="chat", success=True, tokens_used=450, latency_ms=800, mode="chat")
print("✓ Logged tool execution: chat (450 tokens)")

print("\nTotal simulated tokens: ~1487 (optimized mode)")
print("Check telemetry at: /app/logs/token_telemetry.jsonl")
