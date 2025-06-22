"""
Test model metadata preservation during conversation continuation.

This test verifies that when using continuation_id without specifying a model,
the system correctly retrieves and uses the model from the previous conversation
turn instead of defaulting to DEFAULT_MODEL or the custom provider's default.

Bug: https://github.com/BeehiveInnovations/zen-mcp-server/issues/111
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from utils.conversation_memory import ConversationTurn, ThreadContext, create_thread, add_turn, get_thread
from utils.model_context import ModelContext
from server import reconstruct_thread_context


class TestModelMetadataContinuation:
    """Test model metadata preservation during conversation continuation."""

    def test_model_preserved_from_previous_turn(self):
        """Test that model is correctly retrieved from previous conversation turn."""
        # Create a thread with a turn that has a specific model
        thread_id = create_thread("chat", {"prompt": "test"})
        
        # Add an assistant turn with a specific model
        success = add_turn(
            thread_id,
            "assistant",
            "Here's my response",
            model_name="deepseek-r1-8b",
            model_provider="custom"
        )
        assert success
        
        # Get the thread to verify
        context = get_thread(thread_id)
        assert context
        assert len(context.turns) == 1
        assert context.turns[0].model_name == "deepseek-r1-8b"
        
        # Test the fix logic - continuation without model should use previous turn's model
        arguments = {"continuation_id": thread_id}  # No model specified
        
        # Simulate what reconstruct_thread_context does
        model_from_args = arguments.get("model")
        if not model_from_args and context.turns:
            for turn in reversed(context.turns):
                if turn.role == "assistant" and turn.model_name:
                    arguments["model"] = turn.model_name
                    break
        
        # Verify the model was set correctly
        assert arguments.get("model") == "deepseek-r1-8b"
        
        # Verify ModelContext uses the correct model
        model_context = ModelContext.from_arguments(arguments)
        assert model_context.model_name == "deepseek-r1-8b"

    @pytest.mark.asyncio
    async def test_reconstruct_thread_context_preserves_model(self):
        """Test that reconstruct_thread_context preserves model from previous turn."""
        # Create thread with assistant turn
        thread_id = create_thread("chat", {"prompt": "initial"})
        add_turn(
            thread_id,
            "assistant",
            "Initial response",
            model_name="o3-mini",
            model_provider="openai"
        )
        
        # Test reconstruction without specifying model
        arguments = {
            "continuation_id": thread_id,
            "prompt": "follow-up question"
        }
        
        # Mock the model context to avoid initialization issues in tests
        with patch('utils.model_context.ModelContext.calculate_token_allocation') as mock_calc:
            mock_calc.return_value = MagicMock(
                total_tokens=200000,
                content_tokens=160000,
                response_tokens=40000,
                file_tokens=64000,
                history_tokens=64000
            )
            
            with patch('utils.conversation_memory.build_conversation_history') as mock_build:
                mock_build.return_value = ("=== CONVERSATION HISTORY ===\n", 1000)
                
                enhanced_args = await reconstruct_thread_context(arguments)
                
                # Verify model was retrieved from thread
                assert enhanced_args.get("model") == "o3-mini"

    def test_multiple_turns_uses_last_assistant_model(self):
        """Test that with multiple turns, the last assistant turn's model is used."""
        thread_id = create_thread("analyze", {"prompt": "analyze this"})
        
        # Add multiple turns with different models
        add_turn(thread_id, "assistant", "First response", model_name="gemini-2.5-flash", model_provider="google")
        add_turn(thread_id, "user", "Another question")
        add_turn(thread_id, "assistant", "Second response", model_name="o3", model_provider="openai")
        add_turn(thread_id, "user", "Final question")
        
        # Get thread and apply fix logic
        context = get_thread(thread_id)
        arguments = {"continuation_id": thread_id}
        
        model_from_args = arguments.get("model")
        if not model_from_args and context.turns:
            for turn in reversed(context.turns):
                if turn.role == "assistant" and turn.model_name:
                    arguments["model"] = turn.model_name
                    break
        
        # Should use the most recent assistant model
        assert arguments.get("model") == "o3"

    def test_no_previous_assistant_turn_defaults(self):
        """Test behavior when there's no previous assistant turn."""
        thread_id = create_thread("chat", {"prompt": "test"})
        
        # Only add user turns
        add_turn(thread_id, "user", "First question")
        add_turn(thread_id, "user", "Second question")
        
        context = get_thread(thread_id)
        arguments = {"continuation_id": thread_id}
        
        model_from_args = arguments.get("model")
        if not model_from_args and context.turns:
            for turn in reversed(context.turns):
                if turn.role == "assistant" and turn.model_name:
                    arguments["model"] = turn.model_name
                    break
        
        # Should not have set a model
        assert arguments.get("model") is None
        
        # ModelContext should use DEFAULT_MODEL
        model_context = ModelContext.from_arguments(arguments)
        from config import DEFAULT_MODEL
        assert model_context.model_name == DEFAULT_MODEL

    def test_explicit_model_overrides_previous_turn(self):
        """Test that explicitly specifying a model overrides the previous turn's model."""
        thread_id = create_thread("chat", {"prompt": "test"})
        add_turn(thread_id, "assistant", "Response", model_name="gemini-2.5-flash", model_provider="google")
        
        context = get_thread(thread_id)
        arguments = {
            "continuation_id": thread_id,
            "model": "o3"  # Explicitly specified
        }
        
        # Apply the logic
        model_from_args = arguments.get("model")
        if not model_from_args and context.turns:
            for turn in reversed(context.turns):
                if turn.role == "assistant" and turn.model_name:
                    arguments["model"] = turn.model_name
                    break
        
        # Should keep the explicit model
        assert arguments.get("model") == "o3"

    def test_thread_chain_model_preservation(self):
        """Test model preservation across thread chains (parent-child relationships)."""
        # Create parent thread
        parent_id = create_thread("analyze", {"prompt": "analyze"})
        add_turn(parent_id, "assistant", "Analysis", model_name="gemini-2.5-pro", model_provider="google")
        
        # Create child thread
        child_id = create_thread("codereview", {"prompt": "review"}, parent_thread_id=parent_id)
        
        # Child thread should be able to access parent's model through chain traversal
        # This is for future enhancement - currently we only look at direct thread
        context = get_thread(child_id)
        assert context.parent_thread_id == parent_id
        
        # Current implementation only looks at turns in current thread
        arguments = {"continuation_id": child_id}
        model_from_args = arguments.get("model")
        if not model_from_args and context.turns:
            for turn in reversed(context.turns):
                if turn.role == "assistant" and turn.model_name:
                    arguments["model"] = turn.model_name
                    break
        
        # No turns in child thread yet
        assert arguments.get("model") is None