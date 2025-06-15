#!/usr/bin/env python3
"""
Test script to verify line number accuracy in the MCP server
"""

import asyncio
import json

from tools.analyze import AnalyzeTool
from tools.chat import ChatTool


async def test_line_number_reporting():
    """Test if tools report accurate line numbers when analyzing code"""

    print("=== Testing Line Number Accuracy ===\n")

    # Test 1: Analyze tool with line numbers
    analyze_tool = AnalyzeTool()

    # Create a request that asks about specific line numbers
    analyze_request = {
        "files": ["/Users/fahad/Developer/gemini-mcp-server/test_line_numbers.py"],
        "prompt": "Find all the lines where 'ignore_patterns' is assigned a list value. Report the exact line numbers.",
        "model": "flash",  # Use a real model
    }

    print("1. Testing Analyze tool:")
    print(f"   Prompt: {analyze_request['prompt']}")

    try:
        response = await analyze_tool.execute(analyze_request)
        result = json.loads(response[0].text)

        if result["status"] == "success":
            print(f"   Response excerpt: {result['content'][:200]}...")
        else:
            print(f"   Error: {result}")
    except Exception as e:
        print(f"   Exception: {e}")

    print("\n" + "=" * 50 + "\n")

    # Test 2: Chat tool to simulate the user's scenario
    chat_tool = ChatTool()

    chat_request = {
        "files": ["/Users/fahad/Developer/loganalyzer/main.py"],
        "prompt": "Tell me the exact line number where 'ignore_patterns' is assigned a list in the file. Be precise about the line number.",
        "model": "flash",
    }

    print("2. Testing Chat tool with user's actual file:")
    print(f"   File: {chat_request['files'][0]}")
    print(f"   Prompt: {chat_request['prompt']}")

    try:
        response = await chat_tool.execute(chat_request)
        result = json.loads(response[0].text)

        if result["status"] == "success":
            print(f"   Response excerpt: {result['content'][:300]}...")
        else:
            print(f"   Error: {result}")
    except Exception as e:
        print(f"   Exception: {e}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_line_number_reporting())
