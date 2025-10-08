#!/usr/bin/env python3
"""Simulate MCP handshake to debug tools/list issue."""

import json
import subprocess
import time


def send_jsonrpc(proc, request, timeout=5):
    """Send a JSON-RPC request and read response."""
    request_str = json.dumps(request)
    print(f"\n→ Sending: {request_str}")

    try:
        # Write request
        proc.stdin.write(request_str + "\n")
        proc.stdin.flush()

        # Read response with a timeout
        import select

        readable, _, _ = select.select([proc.stdout], [], [], timeout)
        if readable:
            response_line = proc.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                print(f"← Response: {json.dumps(response, indent=2)}")
                return response
        print(f"← No response received within {timeout}s")
        return None
    except Exception as e:
        print(f"← Error: {e}")
        return None


def test_mcp_handshake():
    """Test the MCP handshake sequence."""
    print("Starting MCP server in stdio mode...")

    # Start the server
    proc = subprocess.Popen(
        ["python3", "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # Check if server started
        time.sleep(0.5)
        if proc.poll() is not None:
            stderr_output = proc.stderr.read()
            print("❌ Server crashed on startup!")
            print(f"Stderr: {stderr_output}")
            return

        # Wait for server to start
        time.sleep(1)

        # Step 1: Initialize
        print("\n=== Step 1: Initialize ===")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        response = send_jsonrpc(proc, init_request)

        if not response or "error" in response:
            print("❌ Initialize failed!")
            if response and "error" in response:
                print(f"   Error: {response['error']}")
            return

        # Step 2: Send initialized notification
        print("\n=== Step 2: Initialized notification ===")
        initialized_notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        send_jsonrpc(proc, initialized_notif)

        # Step 3: List tools
        print("\n=== Step 3: List tools ===")
        list_tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        response = send_jsonrpc(proc, list_tools_request)

        if not response:
            print("❌ No response to tools/list!")
        elif "error" in response:
            print(f"❌ Error in tools/list: {response['error']}")
        elif "result" in response:
            print("✅ Tools listed successfully!")
            print(f"   Found {len(response['result'].get('tools', []))} tools")

        # Check stderr for any errors
        time.sleep(0.5)
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"\n=== Server stderr ===\n{stderr_output}")

    finally:
        # Clean up
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    test_mcp_handshake()
