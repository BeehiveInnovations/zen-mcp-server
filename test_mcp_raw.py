#!/usr/bin/env python3
"""
Test raw MCP protocol to debug parameter validation.
"""

import json
import subprocess


def test_request(request_dict, description):
    """Send a single request and check response."""
    print(f"\n=== Testing: {description} ===")
    print(f"Request: {json.dumps(request_dict)}")

    input_data = json.dumps(request_dict) + "\n"

    result = subprocess.run(
        ["docker", "exec", "-i", "zen-mcp-server", "python", "server.py", "--stdio"],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Parse first JSON response
    for line in result.stdout.strip().split("\n"):
        if line and line.startswith("{"):
            try:
                resp = json.loads(line)
                if "result" in resp:
                    print(f"✅ Success: {resp.get('result', {})}")
                elif "error" in resp:
                    print(f"❌ Error: {resp['error']}")
                return resp
            except json.JSONDecodeError:
                pass

    print("❌ No valid response")
    return None


# Test different parameter variations
print("=" * 60)
print("MCP Protocol Parameter Testing")
print("=" * 60)

# Standard initialization
test_request(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "1.0.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    },
    "Standard initialization",
)

# Try tools/list with empty params
test_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, "tools/list with empty params {}")

# Try tools/list with null params
test_request({"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": None}, "tools/list with null params")

# Try tools/list without params field
test_request({"jsonrpc": "2.0", "id": 4, "method": "tools/list"}, "tools/list without params field")

# Try with different protocol version
test_request(
    {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"},
        },
    },
    "Initialize with protocol 2025-06-18",
)

# Then try tools/list again
test_request({"jsonrpc": "2.0", "id": 6, "method": "tools/list", "params": {}}, "tools/list after newer protocol init")
