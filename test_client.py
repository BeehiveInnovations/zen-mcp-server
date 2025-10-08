#!/usr/bin/env python3
"""
Test client to generate Zen MCP tool requests for A/B testing
"""

import json
import random
import sys
import time
from typing import Any, Dict

# Test scenarios for different tools
TEST_SCENARIOS = [
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "zen_select_mode",
            "arguments": {
                "task_description": "Debug a React component that renders twice",
                "context_size": "standard",
                "confidence_level": "medium",
            },
        },
    },
    {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "chat",
            "arguments": {"prompt": "Explain the difference between async and await in Python", "model": "auto"},
        },
    },
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "debug",
            "arguments": {"problem": "My API returns 404 but the endpoint exists", "confidence": "exploring"},
        },
    },
    {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "zen_select_mode",
            "arguments": {
                "task_description": "Review security vulnerabilities in authentication code",
                "context_size": "comprehensive",
                "confidence_level": "high",
            },
        },
    },
]


def send_request(request: Dict[str, Any]) -> None:
    """Send a JSON-RPC request to the MCP server via stdin"""
    print(f"Sending request: {request['params']['name']}")

    # Write to stdin (this simulates what Claude would send)
    json_str = json.dumps(request)
    sys.stdout.write(json_str + "\n")
    sys.stdout.flush()

    # Wait a bit to simulate processing
    time.sleep(random.uniform(2, 5))


def main():
    """Run test scenarios"""
    print("Starting Zen MCP test client...")
    print(f"Will send {len(TEST_SCENARIOS)} test requests")
    print("-" * 50)

    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"\nTest {i}/{len(TEST_SCENARIOS)}:")
        send_request(scenario)

        # Wait between requests
        if i < len(TEST_SCENARIOS):
            wait_time = random.uniform(3, 8)
            print(f"Waiting {wait_time:.1f} seconds before next request...")
            time.sleep(wait_time)

    print("\n" + "-" * 50)
    print("Test sequence complete!")
    print("\nTo check telemetry:")
    print("  cat logs/token_telemetry.jsonl | python3 -m json.tool")


if __name__ == "__main__":
    main()
