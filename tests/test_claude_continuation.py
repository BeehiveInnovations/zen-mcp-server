"""
Test suite for Claude continuation opportunities

Tests the system that offers Claude the opportunity to continue conversations
when Gemini doesn't explicitly ask a follow-up question.
"""

import json
from unittest.mock import Mock, patch

import pytest
from pydantic import Field

from tools.base import BaseTool, ToolRequest
from tools.models import ContinuationOffer, ToolOutput
from utils.conversation_memory import MAX_CONVERSATION_TURNS


class ContinuationRequest(ToolRequest):
    """Test request model with prompt field"""

    prompt: str = Field(..., description="The prompt to analyze")
    files: list[str] = Field(default_factory=list, description="Optional files to analyze")


class ClaudeContinuationTool(BaseTool):
    """Test tool for continuation functionality"""

    def get_name(self) -> str:
        return "test_continuation"

    def get_description(self) -> str:
        return "Test tool for Claude continuation"

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "continuation_id": {"type": "string", "required": False},
            },
        }

    def get_system_prompt(self) -> str:
        return "Test system prompt"

    def get_request_model(self):
        return ContinuationRequest

    async def prepare_prompt(self, request) -> str:
        return f"System: {self.get_system_prompt()}\nUser: {request.prompt}"


class TestClaudeContinuationOffers:
    """Test Claude continuation offer functionality"""

    def setup_method(self):
        self.tool = ClaudeContinuationTool()

    @patch("utils.conversation_memory.get_redis_client")
    def test_new_conversation_offers_continuation(self, mock_redis):
        """Test that new conversations offer Claude continuation opportunity"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Test request without continuation_id (new conversation)
        request = ContinuationRequest(prompt="Analyze this code")

        # Check continuation opportunity
        continuation_data = self.tool._check_continuation_opportunity(request)

        assert continuation_data is not None
        assert continuation_data["remaining_turns"] == MAX_CONVERSATION_TURNS - 1
        assert continuation_data["tool_name"] == "test_continuation"

    def test_existing_conversation_no_continuation_offer(self):
        """Test that existing threaded conversations don't offer continuation"""
        # Test request with continuation_id (existing conversation)
        request = ContinuationRequest(
            prompt="Continue analysis", continuation_id="12345678-1234-1234-1234-123456789012"
        )

        # Check continuation opportunity
        continuation_data = self.tool._check_continuation_opportunity(request)

        assert continuation_data is None

    @patch("utils.conversation_memory.get_redis_client")
    def test_create_continuation_offer_response(self, mock_redis):
        """Test creating continuation offer response"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        request = ContinuationRequest(prompt="Test prompt")
        content = "This is the analysis result."
        continuation_data = {"remaining_turns": 4, "tool_name": "test_continuation"}

        # Create continuation offer response
        response = self.tool._create_continuation_offer_response(content, continuation_data, request)

        assert isinstance(response, ToolOutput)
        assert response.status == "continuation_available"
        assert response.content == content
        assert response.continuation_offer is not None

        offer = response.continuation_offer
        assert isinstance(offer, ContinuationOffer)
        assert offer.remaining_turns == 4
        assert "continuation_id" in offer.suggested_tool_params
        assert "You have 4 more exchange(s) available" in offer.message_to_user

    @patch("utils.conversation_memory.get_redis_client")
    async def test_full_response_flow_with_continuation_offer(self, mock_redis):
        """Test complete response flow that creates continuation offer"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Mock the model to return a response without follow-up question
        with patch.object(self.tool, "create_model") as mock_create_model:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = [
                Mock(
                    content=Mock(parts=[Mock(text="Analysis complete. The code looks good.")]),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            # Execute tool with new conversation
            arguments = {"prompt": "Analyze this code"}
            response = await self.tool.execute(arguments)

            # Parse response
            assert len(response) == 1
            response_data = json.loads(response[0].text)

            # Debug output
            if response_data.get("status") == "error":
                print(f"Error content: {response_data.get('content')}")

            assert response_data["status"] == "continuation_available"
            assert response_data["content"] == "Analysis complete. The code looks good."
            assert "continuation_offer" in response_data

            offer = response_data["continuation_offer"]
            assert "continuation_id" in offer
            assert offer["remaining_turns"] == MAX_CONVERSATION_TURNS - 1
            assert "You have" in offer["message_to_user"]
            assert "more exchange(s) available" in offer["message_to_user"]

    @patch("utils.conversation_memory.get_redis_client")
    async def test_gemini_follow_up_takes_precedence(self, mock_redis):
        """Test that Gemini follow-up questions take precedence over continuation offers"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Mock the model to return a response WITH follow-up question
        with patch.object(self.tool, "create_model") as mock_create_model:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = [
                Mock(
                    content=Mock(
                        parts=[
                            Mock(
                                text="""Analysis complete. The code looks good.

```json
{
  "follow_up_question": "Would you like me to examine the error handling patterns?",
  "suggested_params": {"files": ["/src/error_handler.py"]},
  "ui_hint": "Examining error handling would help ensure robustness"
}
```"""
                            )
                        ]
                    ),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            # Execute tool
            arguments = {"prompt": "Analyze this code"}
            response = await self.tool.execute(arguments)

            # Parse response
            response_data = json.loads(response[0].text)

            # Should be follow-up, not continuation offer
            assert response_data["status"] == "requires_continuation"
            assert "follow_up_request" in response_data
            assert response_data.get("continuation_offer") is None

    @patch("utils.conversation_memory.get_redis_client")
    async def test_threaded_conversation_with_continuation_offer(self, mock_redis):
        """Test that threaded conversations still get continuation offers when turns remain"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Mock existing thread context
        from utils.conversation_memory import ThreadContext

        thread_context = ThreadContext(
            thread_id="12345678-1234-1234-1234-123456789012",
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:01:00Z",
            tool_name="test_continuation",
            turns=[],
            initial_context={"prompt": "Previous analysis"},
        )
        mock_client.get.return_value = thread_context.model_dump_json()

        # Mock the model
        with patch.object(self.tool, "create_model") as mock_create_model:
            mock_model = Mock()
            mock_response = Mock()
            mock_response.candidates = [
                Mock(
                    content=Mock(parts=[Mock(text="Continued analysis complete.")]),
                    finish_reason="STOP",
                )
            ]
            mock_model.generate_content.return_value = mock_response
            mock_create_model.return_value = mock_model

            # Execute tool with continuation_id
            arguments = {"prompt": "Continue the analysis", "continuation_id": "12345678-1234-1234-1234-123456789012"}
            response = await self.tool.execute(arguments)

            # Parse response
            response_data = json.loads(response[0].text)

            # Should offer continuation since there are remaining turns (9 remaining: 10 max - 0 current - 1)
            assert response_data["status"] == "continuation_available"
            assert response_data.get("continuation_offer") is not None
            assert response_data["continuation_offer"]["remaining_turns"] == 9

    def test_max_turns_reached_no_continuation_offer(self):
        """Test that no continuation is offered when max turns would be exceeded"""
        # Mock MAX_CONVERSATION_TURNS to be 1 for this test
        with patch("tools.base.MAX_CONVERSATION_TURNS", 1):
            request = ContinuationRequest(prompt="Test prompt")

            # Check continuation opportunity
            continuation_data = self.tool._check_continuation_opportunity(request)

            # Should be None because remaining_turns would be 0
            assert continuation_data is None

    @patch("utils.conversation_memory.get_redis_client")
    def test_continuation_offer_thread_creation_failure_fallback(self, mock_redis):
        """Test fallback to normal response when thread creation fails"""
        # Mock Redis to fail
        mock_client = Mock()
        mock_client.setex.side_effect = Exception("Redis failure")
        mock_redis.return_value = mock_client

        request = ContinuationRequest(prompt="Test prompt")
        content = "Analysis result"
        continuation_data = {"remaining_turns": 4, "tool_name": "test_continuation"}

        # Should fallback to normal response
        response = self.tool._create_continuation_offer_response(content, continuation_data, request)

        assert response.status == "success"
        assert response.content == content
        assert response.continuation_offer is None

    @patch("utils.conversation_memory.get_redis_client")
    def test_continuation_offer_message_format(self, mock_redis):
        """Test that continuation offer message is properly formatted for Claude"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        request = ContinuationRequest(prompt="Analyze architecture")
        content = "Architecture analysis complete."
        continuation_data = {"remaining_turns": 3, "tool_name": "test_continuation"}

        response = self.tool._create_continuation_offer_response(content, continuation_data, request)

        offer = response.continuation_offer
        message = offer.message_to_user

        # Check message contains key information for Claude
        assert "continue this analysis" in message
        assert "continuation_id" in message
        assert "test_continuation tool call" in message
        assert "3 more exchange(s)" in message

        # Check suggested params are properly formatted
        suggested_params = offer.suggested_tool_params
        assert "continuation_id" in suggested_params
        assert "prompt" in suggested_params
        assert isinstance(suggested_params["continuation_id"], str)

    @patch("utils.conversation_memory.get_redis_client")
    def test_continuation_offer_metadata(self, mock_redis):
        """Test that continuation offer includes proper metadata"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        request = ContinuationRequest(prompt="Test")
        content = "Test content"
        continuation_data = {"remaining_turns": 2, "tool_name": "test_continuation"}

        response = self.tool._create_continuation_offer_response(content, continuation_data, request)

        metadata = response.metadata
        assert metadata["tool_name"] == "test_continuation"
        assert metadata["remaining_turns"] == 2
        assert "thread_id" in metadata
        assert len(metadata["thread_id"]) == 36  # UUID length


class TestContinuationIntegration:
    """Integration tests for continuation offers with conversation memory"""

    def setup_method(self):
        self.tool = ClaudeContinuationTool()

    @patch("utils.conversation_memory.get_redis_client")
    def test_continuation_offer_creates_proper_thread(self, mock_redis):
        """Test that continuation offers create properly formatted threads"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Mock the get call that add_turn makes to retrieve the existing thread
        # We'll set this up after the first setex call
        def side_effect_get(key):
            # Return the context from the first setex call
            if mock_client.setex.call_count > 0:
                first_call_data = mock_client.setex.call_args_list[0][0][2]
                return first_call_data
            return None

        mock_client.get.side_effect = side_effect_get

        request = ContinuationRequest(prompt="Initial analysis", files=["/test/file.py"])
        content = "Analysis result"
        continuation_data = {"remaining_turns": 4, "tool_name": "test_continuation"}

        self.tool._create_continuation_offer_response(content, continuation_data, request)

        # Verify thread creation was called (should be called twice: create_thread + add_turn)
        assert mock_client.setex.call_count == 2

        # Check the first call (create_thread)
        first_call = mock_client.setex.call_args_list[0]
        thread_key = first_call[0][0]
        assert thread_key.startswith("thread:")
        assert len(thread_key.split(":")[-1]) == 36  # UUID length

        # Check the second call (add_turn) which should have the assistant response
        second_call = mock_client.setex.call_args_list[1]
        thread_data = second_call[0][2]
        thread_context = json.loads(thread_data)

        assert thread_context["tool_name"] == "test_continuation"
        assert len(thread_context["turns"]) == 1  # Assistant's response added
        assert thread_context["turns"][0]["role"] == "assistant"
        assert thread_context["turns"][0]["content"] == content
        assert thread_context["turns"][0]["files"] == ["/test/file.py"]  # Files from request
        assert thread_context["initial_context"]["prompt"] == "Initial analysis"
        assert thread_context["initial_context"]["files"] == ["/test/file.py"]

    @patch("utils.conversation_memory.get_redis_client")
    def test_claude_can_use_continuation_id(self, mock_redis):
        """Test that Claude can use the provided continuation_id in subsequent calls"""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Step 1: Initial request creates continuation offer
        request1 = ToolRequest(prompt="Analyze code structure")
        continuation_data = {"remaining_turns": 4, "tool_name": "test_continuation"}
        response1 = self.tool._create_continuation_offer_response(
            "Structure analysis done.", continuation_data, request1
        )

        thread_id = response1.continuation_offer.continuation_id

        # Step 2: Mock the thread context for Claude's follow-up
        from utils.conversation_memory import ConversationTurn, ThreadContext

        existing_context = ThreadContext(
            thread_id=thread_id,
            created_at="2023-01-01T00:00:00Z",
            last_updated_at="2023-01-01T00:01:00Z",
            tool_name="test_continuation",
            turns=[
                ConversationTurn(
                    role="assistant",
                    content="Structure analysis done.",
                    timestamp="2023-01-01T00:00:30Z",
                    tool_name="test_continuation",
                )
            ],
            initial_context={"prompt": "Analyze code structure"},
        )
        mock_client.get.return_value = existing_context.model_dump_json()

        # Step 3: Claude uses continuation_id
        request2 = ToolRequest(prompt="Now analyze the performance aspects", continuation_id=thread_id)

        # Should still offer continuation if there are remaining turns
        continuation_data2 = self.tool._check_continuation_opportunity(request2)
        assert continuation_data2 is not None
        assert continuation_data2["remaining_turns"] == 8  # MAX_CONVERSATION_TURNS(10) - current_turns(1) - 1
        assert continuation_data2["tool_name"] == "test_continuation"


if __name__ == "__main__":
    pytest.main([__file__])
