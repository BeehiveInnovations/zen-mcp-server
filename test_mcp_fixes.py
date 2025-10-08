#!/usr/bin/env python3
"""
Test script to verify MCP fixes.
"""

import json
import subprocess
import time


def test_minimal_server():
    """Test the minimal server with simple requests."""
    print("=" * 60)
    print("Testing Minimal MCP Server")
    print("=" * 60)

    # Start the minimal server in background
    proc = subprocess.Popen(
        ["python3", "minimal_mcp_test.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    time.sleep(1)  # Let it start

    # Test initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "1.0.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    }

    # Test tools/list
    list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    # Test tool call
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "test_tool", "arguments": {"message": "Hello MCP!"}},
    }

    # Send all requests
    requests = json.dumps(init_req) + "\n" + json.dumps(list_req) + "\n" + json.dumps(call_req) + "\n"

    stdout, stderr = proc.communicate(input=requests, timeout=5)

    print("STDOUT:")
    for line in stdout.strip().split("\n"):
        if line:
            try:
                resp = json.loads(line)
                if "result" in resp:
                    print(f"  ✅ Request {resp['id']}: Success")
                elif "error" in resp:
                    print(f"  ❌ Request {resp['id']}: {resp['error']}")
            except:
                pass

    if stderr:
        print("\nSTDERR (first 5 lines):")
        for line in stderr.split("\n")[:5]:
            if line:
                print(f"  {line}")


def test_production_server():
    """Test the production server with optimized tools."""
    print("\n" + "=" * 60)
    print("Testing Production Server with Optimized Tools")
    print("=" * 60)

    cmd = ["docker", "exec", "-i", "zen-mcp-server", "python", "server.py", "--stdio"]

    # Prepare requests
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0.0",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "zen_select_mode", "arguments": {"task_description": "Debug test"}},
        },
    ]

    input_data = "\n".join(json.dumps(r) for r in requests) + "\n"

    result = subprocess.run(cmd, input=input_data, capture_output=True, text=True, timeout=10)

    print("Results:")
    for line in result.stdout.strip().split("\n"):
        if line:
            try:
                resp = json.loads(line)
                if "result" in resp:
                    if resp["id"] == 2:
                        tools = resp.get("result", {}).get("tools", [])
                        print(f"  ✅ tools/list: Found {len(tools)} tools")
                        if tools:
                            zen_tools = [t["name"] for t in tools if "zen_" in t["name"]]
                            print(f"     Zen tools: {zen_tools}")
                    elif resp["id"] == 3:
                        print("  ✅ zen_select_mode: Executed successfully")
                elif "error" in resp:
                    print(f"  ❌ Request {resp['id']}: {resp['error']}")
            except:
                pass

    # Check logs for validation report
    logs = subprocess.run(["docker-compose", "logs", "zen-mcp", "--tail=50"], capture_output=True, text=True)

    if "MCP TOOL VALIDATION REPORT" in logs.stdout:
        print("\n✅ Validation report generated (check logs for details)")

    validation_errors = []
    for line in logs.stdout.split("\n"):
        if "⚠️" in line or "❌" in line:
            validation_errors.append(line.strip())

    if validation_errors:
        print("\nValidation Issues Found:")
        for error in validation_errors[:5]:
            print(f"  {error}")


if __name__ == "__main__":
    # Test minimal server first
    try:
        test_minimal_server()
    except Exception as e:
        print(f"Minimal server test failed: {e}")

    # Test production server
    try:
        test_production_server()
    except Exception as e:
        print(f"Production server test failed: {e}")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
