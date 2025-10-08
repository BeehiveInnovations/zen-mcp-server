#!/usr/bin/env python3
"""
Simple test to verify MCP protocol works with original tools.
"""

import json
import subprocess

# Test requests
requests = [
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "1.0.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
    },
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "version", "arguments": {}}},
]

# Send to server
input_data = "\n".join(json.dumps(r) for r in requests) + "\n"

result = subprocess.run(
    ["docker", "exec", "-i", "zen-mcp-server", "python", "server.py", "--stdio"],
    input=input_data,
    capture_output=True,
    text=True,
    timeout=10,
)

print("STDOUT:")
for line in result.stdout.strip().split("\n"):
    if line and line.startswith("{"):
        try:
            resp = json.loads(line)
            if "result" in resp:
                if resp["id"] == 1:
                    print("✅ Initialize: Success")
                elif resp["id"] == 2:
                    tools = resp.get("result", {}).get("tools", [])
                    print(f"✅ tools/list: Found {len(tools)} tools")
                    if tools:
                        print(f"   First 3 tools: {[t['name'] for t in tools[:3]]}")
                elif resp["id"] == 3:
                    print("✅ tools/call: Success")
            elif "error" in resp:
                print(f"❌ Request {resp['id']}: {resp['error']}")
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error parsing: {e}")

if result.stderr:
    print("\nSTDERR (first 10 lines):")
    for line in result.stderr.split("\n")[:10]:
        if line and not line.startswith("202"):
            print(f"  {line}")
