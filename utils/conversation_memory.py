"""
Conversation Memory for AI-to-AI Multi-turn Discussions

This module provides conversation persistence and context reconstruction for
stateless MCP environments. It enables multi-turn conversations between Claude
and Gemini by storing conversation state in Redis across independent request cycles.

Key Features:
- UUID-based conversation thread identification
- Turn-by-turn conversation history storage
- Automatic turn limiting to prevent runaway conversations
- Context reconstruction for stateless request continuity
- Redis-based persistence with automatic expiration
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel

# Configuration constants
MAX_CONVERSATION_TURNS = 5  # Maximum turns allowed per conversation thread


class ConversationTurn(BaseModel):
    """Single turn in a conversation"""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    follow_up_question: Optional[str] = None
    files: Optional[list[str]] = None  # Files referenced in this turn
    tool_name: Optional[str] = None  # Tool used for this turn


class ThreadContext(BaseModel):
    """Complete conversation context"""

    thread_id: str
    created_at: str
    last_updated_at: str
    tool_name: str
    turns: list[ConversationTurn]
    initial_context: dict[str, Any]


def get_redis_client():
    """Get Redis client from environment"""
    try:
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.from_url(redis_url, decode_responses=True)
    except ImportError:
        raise ValueError("redis package required. Install with: pip install redis")


def create_thread(tool_name: str, initial_request: dict[str, Any]) -> str:
    """Create new conversation thread and return thread ID"""
    thread_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Filter out non-serializable parameters
    filtered_context = {
        k: v
        for k, v in initial_request.items()
        if k not in ["temperature", "thinking_mode", "model", "continuation_id"]
    }

    context = ThreadContext(
        thread_id=thread_id,
        created_at=now,
        last_updated_at=now,
        tool_name=tool_name,
        turns=[],
        initial_context=filtered_context,
    )

    # Store in Redis with 1 hour TTL
    client = get_redis_client()
    key = f"thread:{thread_id}"
    client.setex(key, 3600, context.model_dump_json())

    return thread_id


def get_thread(thread_id: str) -> Optional[ThreadContext]:
    """Retrieve thread context from Redis"""
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
        return None


def add_turn(
    thread_id: str,
    role: str,
    content: str,
    follow_up_question: Optional[str] = None,
    files: Optional[list[str]] = None,
    tool_name: Optional[str] = None,
) -> bool:
    """Add turn to existing thread"""
    context = get_thread(thread_id)
    if not context:
        return False

    # Check turn limit
    if len(context.turns) >= MAX_CONVERSATION_TURNS:
        return False

    # Add new turn
    turn = ConversationTurn(
        role=role,
        content=content,
        timestamp=datetime.now(timezone.utc).isoformat(),
        follow_up_question=follow_up_question,
        files=files,
        tool_name=tool_name,
    )

    context.turns.append(turn)
    context.last_updated_at = datetime.now(timezone.utc).isoformat()

    # Save back to Redis
    try:
        client = get_redis_client()
        key = f"thread:{thread_id}"
        client.setex(key, 3600, context.model_dump_json())  # Refresh TTL
        return True
    except Exception:
        return False


def build_conversation_history(context: ThreadContext) -> str:
    """Build formatted conversation history"""
    if not context.turns:
        return ""

    history_parts = [
        "=== CONVERSATION HISTORY ===",
        f"Thread: {context.thread_id}",
        f"Tool: {context.tool_name}",
        f"Turn {len(context.turns)}/{MAX_CONVERSATION_TURNS}",
        "",
        "Previous exchanges:",
    ]

    for i, turn in enumerate(context.turns, 1):
        role_label = "Claude" if turn.role == "user" else "Gemini"

        # Add turn header with tool info if available
        turn_header = f"\n--- Turn {i} ({role_label}"
        if turn.tool_name:
            turn_header += f" using {turn.tool_name}"
        turn_header += ") ---"
        history_parts.append(turn_header)

        # Add files context if present
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
    """Validate UUID format for security"""
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False
