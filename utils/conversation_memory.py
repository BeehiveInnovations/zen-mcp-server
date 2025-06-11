"""
Conversation Memory for AI-to-AI Multi-turn Discussions

This module provides conversation persistence and context reconstruction for
stateless MCP (Model Context Protocol) environments. It enables multi-turn
conversations between Claude and Gemini by storing conversation state in Redis
across independent request cycles.

ARCHITECTURE OVERVIEW:
The MCP protocol is inherently stateless - each tool request is independent
with no memory of previous interactions. This module bridges that gap by:

1. Creating persistent conversation threads with unique UUIDs
2. Storing complete conversation context (turns, files, metadata) in Redis
3. Reconstructing conversation history when tools are called with continuation_id
4. Supporting cross-tool continuation - seamlessly switch between different tools
   while maintaining full conversation context and file references

CROSS-TOOL CONTINUATION:
A conversation started with one tool (e.g., 'analyze') can be continued with
any other tool (e.g., 'codereview', 'debug', 'chat') using the same continuation_id.
The second tool will have access to:
- All previous conversation turns and responses
- File context from previous tools (preserved in conversation history)
- Original thread metadata and timing information
- Accumulated knowledge from the entire conversation

Key Features:
- UUID-based conversation thread identification with security validation
- Turn-by-turn conversation history storage with tool attribution
- Cross-tool continuation support - switch tools while preserving context
- File context preservation - files shared in earlier turns remain accessible
- Automatic turn limiting (5 turns max) to prevent runaway conversations
- Context reconstruction for stateless request continuity
- Redis-based persistence with automatic expiration (1 hour TTL)
- Thread-safe operations for concurrent access
- Graceful degradation when Redis is unavailable

USAGE EXAMPLE:
1. Tool A creates thread: create_thread("analyze", request_data) → returns UUID
2. Tool A adds response: add_turn(UUID, "assistant", response, files=[...], tool_name="analyze")
3. Tool B continues thread: get_thread(UUID) → retrieves full context
4. Tool B sees conversation history via build_conversation_history()
5. Tool B adds its response: add_turn(UUID, "assistant", response, tool_name="codereview")

This enables true AI-to-AI collaboration across the entire tool ecosystem.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel

# Configuration constants
MAX_CONVERSATION_TURNS = 5  # Maximum turns allowed per conversation thread


class ConversationTurn(BaseModel):
    """
    Single turn in a conversation

    Represents one exchange in the AI-to-AI conversation, tracking both
    the content and metadata needed for cross-tool continuation.

    Attributes:
        role: "user" (Claude) or "assistant" (Gemini)
        content: The actual message content/response
        timestamp: ISO timestamp when this turn was created
        follow_up_question: Optional follow-up question from Gemini to Claude
        files: List of file paths referenced in this specific turn
        tool_name: Which tool generated this turn (for cross-tool tracking)
    """

    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    follow_up_question: Optional[str] = None
    files: Optional[list[str]] = None  # Files referenced in this turn
    tool_name: Optional[str] = None  # Tool used for this turn


class ThreadContext(BaseModel):
    """
    Complete conversation context for a thread

    Contains all information needed to reconstruct a conversation state
    across different tools and request cycles. This is the core data
    structure that enables cross-tool continuation.

    Attributes:
        thread_id: UUID identifying this conversation thread
        created_at: ISO timestamp when thread was created
        last_updated_at: ISO timestamp of last modification
        tool_name: Name of the tool that initiated this thread
        turns: List of all conversation turns in chronological order
        initial_context: Original request data that started the conversation
    """

    thread_id: str
    created_at: str
    last_updated_at: str
    tool_name: str  # Tool that created this thread (preserved for attribution)
    turns: list[ConversationTurn]
    initial_context: dict[str, Any]  # Original request parameters


def get_redis_client():
    """
    Get Redis client from environment configuration

    Creates a Redis client using the REDIS_URL environment variable.
    Defaults to localhost:6379/0 if not specified.

    Returns:
        redis.Redis: Configured Redis client with decode_responses=True

    Raises:
        ValueError: If redis package is not installed
    """
    try:
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.from_url(redis_url, decode_responses=True)
    except ImportError:
        raise ValueError("redis package required. Install with: pip install redis")


def create_thread(tool_name: str, initial_request: dict[str, Any]) -> str:
    """
    Create new conversation thread and return thread ID

    Initializes a new conversation thread for AI-to-AI discussions.
    This is called when a tool wants to enable follow-up conversations
    or when Claude explicitly starts a multi-turn interaction.

    Args:
        tool_name: Name of the tool creating this thread (e.g., "analyze", "chat")
        initial_request: Original request parameters (will be filtered for serialization)

    Returns:
        str: UUID thread identifier that can be used for continuation

    Note:
        - Thread expires after 1 hour (3600 seconds)
        - Non-serializable parameters are filtered out automatically
        - Thread can be continued by any tool using the returned UUID
    """
    thread_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Filter out non-serializable parameters to avoid JSON encoding issues
    filtered_context = {
        k: v
        for k, v in initial_request.items()
        if k not in ["temperature", "thinking_mode", "model", "continuation_id"]
    }

    context = ThreadContext(
        thread_id=thread_id,
        created_at=now,
        last_updated_at=now,
        tool_name=tool_name,  # Track which tool initiated this conversation
        turns=[],  # Empty initially, turns added via add_turn()
        initial_context=filtered_context,
    )

    # Store in Redis with 1 hour TTL to prevent indefinite accumulation
    client = get_redis_client()
    key = f"thread:{thread_id}"
    client.setex(key, 3600, context.model_dump_json())

    return thread_id


def get_thread(thread_id: str) -> Optional[ThreadContext]:
    """
    Retrieve thread context from Redis

    Fetches complete conversation context for cross-tool continuation.
    This is the core function that enables tools to access conversation
    history from previous interactions.

    Args:
        thread_id: UUID of the conversation thread

    Returns:
        ThreadContext: Complete conversation context if found
        None: If thread doesn't exist, expired, or invalid UUID

    Security:
        - Validates UUID format to prevent injection attacks
        - Handles Redis connection failures gracefully
        - No error information leakage on failure
    """
    if not thread_id or not _is_valid_uuid(thread_id):
        return None

    try:
        client = get_redis_client()
        key = f"thread:{thread_id}"
        data = client.get(key)

        if data:
            return ThreadContext.model_validate_json(data)
        return None
    except Exception:
        # Silently handle errors to avoid exposing Redis details
        return None


def add_turn(
    thread_id: str,
    role: str,
    content: str,
    follow_up_question: Optional[str] = None,
    files: Optional[list[str]] = None,
    tool_name: Optional[str] = None,
) -> bool:
    """
    Add turn to existing thread

    Appends a new conversation turn to an existing thread. This is the core
    function for building conversation history and enabling cross-tool
    continuation. Each turn preserves the tool that generated it.

    Args:
        thread_id: UUID of the conversation thread
        role: "user" (Claude) or "assistant" (Gemini)
        content: The actual message/response content
        follow_up_question: Optional follow-up question from Gemini
        files: Optional list of files referenced in this turn
        tool_name: Name of the tool adding this turn (for attribution)

    Returns:
        bool: True if turn was successfully added, False otherwise

    Failure cases:
        - Thread doesn't exist or expired
        - Maximum turn limit reached (5 turns)
        - Redis connection failure

    Note:
        - Refreshes thread TTL to 1 hour on successful update
        - Turn limits prevent runaway conversations
        - File references are preserved for cross-tool access
    """
    context = get_thread(thread_id)
    if not context:
        return False

    # Check turn limit to prevent runaway conversations
    if len(context.turns) >= MAX_CONVERSATION_TURNS:
        return False

    # Create new turn with complete metadata
    turn = ConversationTurn(
        role=role,
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
        follow_up_question=follow_up_question,
        files=files,  # Preserved for cross-tool file context
        tool_name=tool_name,  # Track which tool generated this turn
    )

    context.turns.append(turn)
    context.last_updated_at = datetime.now(timezone.utc).isoformat()

    # Save back to Redis and refresh TTL
    try:
        client = get_redis_client()
        key = f"thread:{thread_id}"
        client.setex(key, 3600, context.model_dump_json())  # Refresh TTL to 1 hour
        return True
    except Exception:
        return False


def build_conversation_history(context: ThreadContext) -> str:
    """
    Build formatted conversation history for tool prompts

    Creates a formatted string representation of the conversation history
    that can be included in tool prompts to provide context. This is the
    critical function that enables cross-tool continuation by reconstructing
    the full conversation context.

    Args:
        context: ThreadContext containing the complete conversation

    Returns:
        str: Formatted conversation history ready for inclusion in prompts
        Empty string if no conversation turns exist

    Format:
        - Header with thread metadata and turn count
        - Each turn shows: role, tool used, files referenced, content
        - Files from previous turns are explicitly listed
        - Clear delimiters for AI parsing
        - Continuation instruction at end

    Note:
        This formatted history allows tools to "see" files and context
        from previous tools, enabling true cross-tool collaboration.
    """
    if not context.turns:
        return ""

    history_parts = [
        "=== CONVERSATION HISTORY ===",
        f"Thread: {context.thread_id}",
        f"Tool: {context.tool_name}",  # Original tool that started the conversation
        f"Turn {len(context.turns)}/{MAX_CONVERSATION_TURNS}",
        "",
        "Previous exchanges:",
    ]

    for i, turn in enumerate(context.turns, 1):
        role_label = "Claude" if turn.role == "user" else "Gemini"

        # Add turn header with tool attribution for cross-tool tracking
        turn_header = f"\n--- Turn {i} ({role_label}"
        if turn.tool_name:
            turn_header += f" using {turn.tool_name}"
        turn_header += ") ---"
        history_parts.append(turn_header)

        # Add files context if present - critical for cross-tool file access
        if turn.files:
            history_parts.append(f"📁 Files referenced: {', '.join(turn.files)}")
            history_parts.append("")  # Empty line for readability

        # Add the actual content
        history_parts.append(turn.content)

        # Add follow-up question if present
        if turn.follow_up_question:
            history_parts.append(f"\n[Gemini's Follow-up: {turn.follow_up_question}]")

    history_parts.extend(
        ["", "=== END HISTORY ===", "", "Continue this conversation by building on the previous context."]
    )

    return "\n".join(history_parts)


def _is_valid_uuid(val: str) -> bool:
    """
    Validate UUID format for security

    Ensures thread IDs are valid UUIDs to prevent injection attacks
    and malformed requests.

    Args:
        val: String to validate as UUID

    Returns:
        bool: True if valid UUID format, False otherwise
    """
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False
