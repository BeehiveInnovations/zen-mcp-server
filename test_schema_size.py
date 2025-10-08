#!/usr/bin/env python3
"""Test that the schema fix reduced the size."""

import json
import subprocess
import time


def test_schema_size():
    """Test the size of the tools/list response."""
    print("Starting server to test schema size...")

    # Start the server
    proc = subprocess.Popen(
        ["python3", "server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    try:
        time.sleep(1)

        # Send initialize
        init_req = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
            }
        )
        proc.stdin.write(init_req + "\n")
        proc.stdin.flush()
        proc.stdout.readline()  # Read response

        # Send tools/list
        tools_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        proc.stdin.write(tools_req + "\n")
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline()
        response = json.loads(response_line)

        # Check size
        response_str = json.dumps(response)
        size_kb = len(response_str) / 1024

        print(f"\n✅ Schema size: {size_kb:.1f} KB")

        if size_kb > 50:
            print("⚠️  Schema is still large! Target is < 10 KB")
        else:
            print("✅ Schema size is reasonable")

        # Count tools
        tools = response.get("result", {}).get("tools", [])
        print(f"✅ Found {len(tools)} tools")

        # Check chat tool specifically
        chat_tool = next((t for t in tools if t["name"] == "chat"), None)
        if chat_tool:
            chat_schema_str = json.dumps(chat_tool["inputSchema"])
            print(f"✅ Chat tool schema: {len(chat_schema_str) / 1024:.1f} KB")

            # Check model field
            model_field = chat_tool["inputSchema"]["properties"].get("model", {})
            if "enum" in model_field:
                print(f"   Model enum has {len(model_field['enum'])} entries")
            if "description" in model_field:
                print(f"   Model description: {len(model_field['description'])} chars")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    test_schema_size()
