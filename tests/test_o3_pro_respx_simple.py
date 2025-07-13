"""
Tests for o3-pro output_text parsing fix using respx for HTTP recording/replay.

This test uses respx's built-in recording capabilities to record/replay HTTP responses,
allowing the OpenAI SDK to create real response objects with all convenience methods.
"""

import os
import unittest
from pathlib import Path

import pytest
from dotenv import load_dotenv

from tests.test_helpers.respx_recorder import RespxRecorder
from tools.chat import ChatTool

# Load environment variables from .env file
load_dotenv()

# Use absolute path for cassette directory  
cassette_dir = Path(__file__).parent / "respx_cassettes"
cassette_dir.mkdir(exist_ok=True)


@pytest.mark.no_mock_provider  # Disable provider mocking for this test
class TestO3ProRespxSimple(unittest.IsolatedAsyncioTestCase):
    """Test o3-pro response parsing using respx for HTTP recording/replay."""

    async def test_o3_pro_with_respx_recording(self):
        """Test o3-pro parsing with respx HTTP recording - real SDK objects."""
        cassette_path = cassette_dir / "o3_pro_respx.json"
        
        # Skip if no API key available and no cassette exists
        if not cassette_path.exists() and (not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY").startswith("dummy")):
            pytest.skip("Set real OPENAI_API_KEY to record HTTP cassettes")

        # Use RespxRecorder for automatic recording/replay
        async with RespxRecorder(str(cassette_path)) as recorder:
            # Execute the chat tool test - recorder handles recording or replay automatically
            result = await self._execute_chat_tool_test()
            
            # Verify the response works correctly with real SDK objects
            self._verify_chat_tool_response(result)

        # Verify cassette was created in record mode
        if not os.getenv("OPENAI_API_KEY", "").startswith("dummy"):
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

        # Additional verification
        self.assertTrue(actual_content.strip(), "Content should not be empty")
        self.assertIsInstance(actual_content, str, "Content should be string")

        # Verify successful status
        self.assertEqual(response_data.get("status"), "continuation_available", "Should have successful status")


if __name__ == "__main__":
    print("🔥 Respx HTTP Recording Tests for O3-Pro with Real SDK Objects")
    print("=" * 60)
    print("This tests the concept of using respx for HTTP-level recording")
    print("Currently using pass_through mode to validate the approach")
    print()

    unittest.main()