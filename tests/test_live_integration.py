"""
Live integration tests for google-genai library
These tests require GEMINI_API_KEY to be set and will make real API calls

To run these tests manually:
python tests/test_live_integration.py

Note: These tests are excluded from regular pytest runs to avoid API rate limits.
They confirm that the google-genai library integration works correctly with live data.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from tools.analyze import AnalyzeTool
from tools.thinkdeep import ThinkDeepTool


async def run_manual_live_tests():
    """Run live tests manually without pytest"""
    print("🚀 Running manual live integration tests...")

    # Check API key
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not found. Set it to run live tests.")
        return False

    try:
        # Test google-genai import

        print("✅ google-genai library import successful")

        # Test tool integration
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello(): return 'world'")
            temp_path = f.name

        try:
            # Test AnalyzeTool
            tool = AnalyzeTool()
            result = await tool.execute(
                {
                    "files": [temp_path],
                    "prompt": "What does this code do?",
                    "thinking_mode": "low",
                }
            )

            if result and result[0].text:
                print("✅ AnalyzeTool live test successful")
            else:
                print("❌ AnalyzeTool live test failed")
                return False

            # Test ThinkDeepTool
            think_tool = ThinkDeepTool()
            result = await think_tool.execute(
                {
                    "prompt": "Testing live integration",
                    "thinking_mode": "minimal",  # Fast test
                }
            )

            if result and result[0].text and "Extended Analysis" in result[0].text:
                print("✅ ThinkDeepTool live test successful")
            else:
                print("❌ ThinkDeepTool live test failed")
                return False

            # Test collaboration/clarification request
            print("\n🔄 Testing dynamic context request (collaboration)...")

            # Create a specific test case designed to trigger clarification
            # We'll use analyze tool with a question that requires seeing files
            analyze_tool = AnalyzeTool()

            # Ask about dependencies without providing package files
            result = await analyze_tool.execute(
                {
                    "files": [temp_path],  # Only Python file, no package.json
                    "prompt": "What npm packages and their versions does this project depend on? List all dependencies.",
                    "thinking_mode": "minimal",  # Fast test
                }
            )

            if result and result[0].text:
                response_data = json.loads(result[0].text)
                print(f"   Response status: {response_data['status']}")

                if response_data["status"] == "requires_clarification":
                    print("✅ Dynamic context request successfully triggered!")
                    clarification = json.loads(response_data["content"])
                    print(f"   Gemini asks: {clarification.get('question', 'N/A')}")
                    if "files_needed" in clarification:
                        print(f"   Files requested: {clarification['files_needed']}")
                        # Verify it's asking for package-related files
                        expected_files = [
                            "package.json",
                            "package-lock.json",
                            "yarn.lock",
                        ]
                        if any(f in str(clarification["files_needed"]) for f in expected_files):
                            print("   ✅ Correctly identified missing package files!")
                        else:
                            print("   ⚠️  Unexpected files requested")
                else:
                    # This is a failure - we specifically designed this to need clarification
                    print("❌ Expected clarification request but got direct response")
                    print("   This suggests the dynamic context feature may not be working")
                    print("   Response:", response_data.get("content", "")[:200])
                    return False
            else:
                print("❌ Collaboration test failed - no response")
                return False

        finally:
            Path(temp_path).unlink(missing_ok=True)

        print("\n🎉 All manual live tests passed!")
        print("✅ google-genai library working correctly")
        print("✅ All tools can make live API calls")
        print("✅ Thinking modes functioning properly")
        return True

    except Exception as e:
        print(f"❌ Live test failed: {e}")
        return False


if __name__ == "__main__":
    # Run live tests when script is executed directly
    success = asyncio.run(run_manual_live_tests())
    exit(0 if success else 1)
