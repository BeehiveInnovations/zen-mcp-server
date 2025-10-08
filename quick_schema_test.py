#!/usr/bin/env python3
"""Quick test to measure current schema size."""

import json
import subprocess
import time


def test_current_schema():
    """Test current schema size via docker exec."""

    # Use docker exec to connect to running server
    cmd = ["docker", "exec", "-i", "zen-mcp-server", "python", "server.py", "--stdio"]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        time.sleep(0.5)

        # Initialize
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

        # List tools
        tools_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

        proc.stdin.write(tools_req + "\n")
        proc.stdin.flush()

        # Read response with timeout
        import select

        ready, _, _ = select.select([proc.stdout], [], [], 10)

        if ready:
            response_line = proc.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                response_str = json.dumps(response)
                size_kb = len(response_str) / 1024

                print(f"Schema response size: {size_kb:.1f} KB")
                print(f"Character count: {len(response_str):,}")

                tools = response.get("result", {}).get("tools", [])
                print(f"Number of tools: {len(tools)}")

                # Check chat tool specifically
                chat_tool = next((t for t in tools if t["name"] == "chat"), None)
                if chat_tool:
                    model_field = chat_tool["inputSchema"]["properties"].get("model", {})
                    if "enum" in model_field:
                        print(f"Model enum entries: {len(model_field['enum'])}")
                    if "description" in model_field:
                        desc_len = len(model_field["description"])
                        print(f"Model description length: {desc_len} chars")
                        if desc_len > 500:
                            print("⚠️  Description still too long!")
                        else:
                            print("✅ Description within limits")

                return size_kb
            else:
                print("No response received")
        else:
            print("Timeout waiting for response")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    print("Testing current Zen MCP schema size...")
    test_current_schema()
