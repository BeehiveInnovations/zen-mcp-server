#!/usr/bin/env python3
"""
Simple test to verify zen_select_mode and zen_execute are available.
"""

import json
import subprocess


def send_mcp_commands(commands):
    """Send multiple commands to MCP server via stdio."""
    cmd = ["docker", "exec", "-i", "zen-mcp-server", "python", "server.py", "--stdio"]

    input_data = "\n".join(json.dumps(cmd) for cmd in commands) + "\n"

    result = subprocess.run(cmd, input=input_data, capture_output=True, text=True)

    responses = []
    for line in result.stdout.strip().split("\n"):
        if line and line.startswith("{"):
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Failed to parse: {line}")
                print(f"Error: {e}")

    return responses


def main():
    print("=" * 60)
    print("TESTING ZEN MCP TOKEN OPTIMIZATION")
    print("=" * 60)

    # Commands to send
    commands = [
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
    ]

    print("\n📤 Sending initialization and tools/list request...")
    responses = send_mcp_commands(commands)

    # Check responses
    if len(responses) >= 2:
        # Check initialization
        init_response = responses[0]
        print(f"\n✅ Initialization successful: {init_response.get('result', {}).get('serverInfo', {})}")

        # Check tools list
        tools_response = responses[1]
        if "result" in tools_response:
            tools = tools_response["result"]
            tool_names = [tool["name"] for tool in tools]

            print(f"\n📋 Available tools ({len(tool_names)}):")
            for name in tool_names:
                marker = "✅" if name in ["zen_select_mode", "zen_execute"] else "  "
                print(f"  {marker} {name}")

            # Check for optimized tools
            has_select = "zen_select_mode" in tool_names
            has_execute = "zen_execute" in tool_names

            if has_select and has_execute:
                print("\n🎉 SUCCESS: Two-stage token optimization tools are available!")

                # Find and display schema sizes
                for tool in tools:
                    if tool["name"] in ["zen_select_mode", "zen_execute"]:
                        schema_size = len(json.dumps(tool.get("inputSchema", {})))
                        print(f"\n📊 {tool['name']} schema size: {schema_size} chars (~{schema_size//4} tokens)")
            else:
                print("\n❌ ERROR: Token optimization tools not found!")
                print(f"  - zen_select_mode: {'Found' if has_select else 'Missing'}")
                print(f"  - zen_execute: {'Found' if has_execute else 'Missing'}")
        else:
            print(f"\n❌ Error in tools response: {tools_response.get('error', 'Unknown error')}")
    else:
        print(f"\n❌ Incomplete responses received: {len(responses)} responses")
        for i, resp in enumerate(responses):
            print(f"  Response {i+1}: {resp}")

    # Now test calling zen_select_mode
    print("\n" + "=" * 60)
    print("TESTING STAGE 1: zen_select_mode")
    print("=" * 60)

    stage1_commands = [
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
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "zen_select_mode",
                "arguments": {
                    "task_description": "Debug why OAuth tokens aren't persisting",
                    "confidence_level": "exploring",
                },
            },
        },
    ]

    print("\n📤 Calling zen_select_mode...")
    responses = send_mcp_commands(stage1_commands)

    if len(responses) >= 2:
        tool_response = responses[1]
        if "result" in tool_response:
            result = tool_response["result"]
            if result and isinstance(result, list) and len(result) > 0:
                content = json.loads(result[0]["text"])
                print(f"\n✅ Mode selected: {content.get('selected_mode', 'unknown')}")
                print(f"   Complexity: {content.get('complexity', 'unknown')}")
                print(f"   Token savings: {content.get('token_savings', 'unknown')}")

                # Calculate actual token usage
                request_size = len(json.dumps(stage1_commands[1]))
                response_size = len(json.dumps(tool_response))
                total_size = request_size + response_size
                print("\n📊 Actual Stage 1 usage:")
                print(f"   Request: {request_size} chars (~{request_size//4} tokens)")
                print(f"   Response: {response_size} chars (~{response_size//4} tokens)")
                print(f"   Total: {total_size} chars (~{total_size//4} tokens)")
            else:
                print(f"\n❌ Unexpected result format: {result}")
        else:
            print(f"\n❌ Error calling zen_select_mode: {tool_response.get('error', 'Unknown error')}")

    print("\n" + "=" * 60)
    print("✨ Test complete!")


if __name__ == "__main__":
    main()
