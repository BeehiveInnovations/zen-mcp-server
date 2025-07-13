"""
Tests for o3-pro output_text parsing fix using HTTP-level recording via respx.

This test validates the fix using real OpenAI SDK objects by recording/replaying
HTTP responses instead of creating mock objects.
"""

import os
import unittest
from pathlib import Path

import pytest
from dotenv import load_dotenv

from tests.test_helpers.http_recorder import HTTPRecorder
from tools.chat import ChatTool

# Load environment variables from .env file
load_dotenv()

# Use absolute path for cassette directory
cassette_dir = Path(__file__).parent / "http_cassettes"
cassette_dir.mkdir(exist_ok=True)


@pytest.mark.no_mock_provider  # Disable provider mocking for this test
class TestO3ProHTTPRecording(unittest.IsolatedAsyncioTestCase):
    """Test o3-pro response parsing using HTTP-level recording with real SDK objects."""

    async def test_o3_pro_real_sdk_objects(self):
        """Test that o3-pro parsing works with real OpenAI SDK objects from HTTP replay."""
        # Skip if no API key available and cassette doesn't exist
        cassette_path = cassette_dir / "o3_pro_real_sdk.json"
        if not cassette_path.exists() and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("Set real OPENAI_API_KEY to record HTTP cassettes")

        # Use HTTPRecorder to record/replay raw HTTP responses
        async with HTTPRecorder(str(cassette_path)):
            # Execute the chat tool test - real SDK objects will be created
            result = await self._execute_chat_tool_test()

            # Verify the response works correctly with real SDK objects
            self._verify_chat_tool_response(result)

        # Verify cassette was created in record mode
        if os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY").startswith("dummy"):
            self.assertTrue(cassette_path.exists(), f"HTTP cassette not created at {cassette_path}")

    async def _execute_chat_tool_test(self):
        """Execute the ChatTool with o3-pro and return the result."""
        chat_tool = ChatTool()
        arguments = {"prompt": "What is 2 + 2?", "model": "o3-pro", "temperature": 1.0}

        return await chat_tool.execute(arguments)

    def _verify_chat_tool_response(self, result):
        """Verify the ChatTool response contains expected data."""
        # Verify we got a valid response
        self.assertIsNotNone(result, "Should get response from ChatTool")

        # Parse the result content (ChatTool returns MCP TextContent format)
        self.assertIsInstance(result, list, "ChatTool should return list of content")
        self.assertTrue(len(result) > 0, "Should have at least one content item")

        # Get the text content (result is a list of TextContent objects)
        content_item = result[0]
        self.assertEqual(content_item.type, "text", "First item should be text content")

        text_content = content_item.text
        self.assertTrue(len(text_content) > 0, "Should have text content")

        # Parse the JSON response from chat tool
        import json
        try:
            response_data = json.loads(text_content)
        except json.JSONDecodeError:
            self.fail(f"Could not parse chat tool response as JSON: {text_content}")

        # Verify the response makes sense for the math question
        actual_content = response_data.get("content", "")
        self.assertIn("4", actual_content, "Should contain the answer '4'")

        # Verify metadata shows o3-pro was used
        metadata = response_data.get("metadata", {})
        self.assertEqual(metadata.get("model_used"), "o3-pro", "Should use o3-pro model")
        self.assertEqual(metadata.get("provider_used"), "openai", "Should use OpenAI provider")

        # Additional verification that the fix is working
        self.assertTrue(actual_content.strip(), "Content should not be empty")
        self.assertIsInstance(actual_content, str, "Content should be string")

        # Verify successful status
        self.assertEqual(response_data.get("status"), "continuation_available", "Should have successful status")


if __name__ == "__main__":
    print("🌐 HTTP-Level Recording Tests for O3-Pro with Real SDK Objects")
    print("=" * 60)
    print("FIRST RUN: Requires OPENAI_API_KEY - records HTTP responses (EXPENSIVE!)")
    print("SUBSEQUENT RUNS: Uses recorded HTTP responses - free and fast")
    print("RECORDING: Delete .json files in tests/http_cassettes/ to re-record")
    print()

    unittest.main()