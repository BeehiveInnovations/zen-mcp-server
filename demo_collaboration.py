#!/usr/bin/env python3
"""
Demo script showing how Claude-Gemini collaboration works
with dynamic context requests.

This demonstrates how tools can request additional context
and how Claude would handle these requests.
"""

import asyncio
import json
import os
from tools.debug_issue import DebugIssueTool


async def simulate_collaboration():
    """Simulate a Claude-Gemini collaboration workflow"""
    
    print("🤝 Claude-Gemini Collaboration Demo\n")
    print("Scenario: Claude asks Gemini to debug an import error")
    print("-" * 50)
    
    # Initialize the debug tool
    debug_tool = DebugIssueTool()
    
    # Step 1: Initial request without full context
    print("\n1️⃣  Claude's initial request:")
    print("   'Debug this ImportError - the app can't find the utils module'")
    
    initial_request = {
        "error_description": "ImportError: cannot import name 'config' from 'utils'",
        "error_context": "Error occurs on line 5 of main.py when starting the application"
    }
    
    print("\n   Sending to Gemini...")
    result = await debug_tool.execute(initial_request)
    
    # Parse the response
    response = json.loads(result[0].text)
    print(f"\n   Gemini's response status: {response['status']}")
    
    if response['status'] == 'requires_clarification':
        # Gemini needs more context
        clarification = json.loads(response['content'])
        print("\n2️⃣  Gemini requests additional context:")
        print(f"   Question: {clarification.get('question', 'N/A')}")
        if 'files_needed' in clarification:
            print(f"   Files needed: {clarification['files_needed']}")
        
        # Step 2: Claude provides additional context
        print("\n3️⃣  Claude provides the requested files:")
        enhanced_request = {
            **initial_request,
            "files": clarification.get('files_needed', []),
            "runtime_info": "Python 3.11, project structure includes utils/ directory"
        }
        
        print("   Re-sending with additional context...")
        result2 = await debug_tool.execute(enhanced_request)
        
        final_response = json.loads(result2[0].text)
        print(f"\n4️⃣  Gemini's final analysis (status: {final_response['status']}):")
        if final_response['status'] == 'success':
            print("\n" + final_response['content'][:500] + "...")
        
    else:
        # Gemini had enough context initially
        print("\n✅ Gemini provided analysis without needing additional context:")
        print("\n" + response['content'][:500] + "...")
    
    print("\n" + "=" * 50)
    print("🎯 Key Points:")
    print("- Tools return structured JSON with status field")
    print("- Status 'requires_clarification' triggers context request")
    print("- Claude can then provide additional files/info")
    print("- Enables true collaborative problem-solving!")


async def main():
    """Run the demo"""
    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("⚠️  Note: This is a simulated demo. Set GEMINI_API_KEY for live testing.")
        print("   The actual behavior depends on Gemini's response.\n")
    
    await simulate_collaboration()


if __name__ == "__main__":
    asyncio.run(main())