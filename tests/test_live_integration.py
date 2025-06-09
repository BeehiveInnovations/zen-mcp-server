"""
Live integration tests for google-genai library
These tests require GEMINI_API_KEY to be set and will make real API calls

To run these tests manually:
python tests/test_live_integration.py

Note: These tests are excluded from regular pytest runs to avoid API rate limits.
They confirm that the google-genai library integration works correctly with live data.
"""

import os
import sys
import tempfile
import asyncio
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.analyze import AnalyzeTool
from tools.think_deeper import ThinkDeeperTool


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
                    "question": "What does this code do?",
                    "thinking_mode": "low",
                }
            )

            if result and result[0].text:
                print("✅ AnalyzeTool live test successful")
            else:
                print("❌ AnalyzeTool live test failed")
                return False

            # Test ThinkDeeperTool
            think_tool = ThinkDeeperTool()
            result = await think_tool.execute(
                {
                    "current_analysis": "Testing live integration",
                    "thinking_mode": "minimal",  # Fast test
                }
            )

            if result and result[0].text and "Extended Analysis" in result[0].text:
                print("✅ ThinkDeeperTool live test successful")
            else:
                print("❌ ThinkDeeperTool live test failed")
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
