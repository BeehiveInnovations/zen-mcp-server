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

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configuration constants
MAX_CONVERSATION_TURNS = 10  # Maximum turns allowed per conversation thread


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

    Uses Redis pipelining to efficiently create the thread and any
    associated metadata in a single network round trip.

    Args:
        tool_name: Name of the tool creating this thread (e.g., "analyze", "chat")
        initial_request: Original request parameters (will be filtered for serialization)

    Returns:
        str: UUID thread identifier that can be used for continuation

    Note:
        - Thread expires after 1 hour (3600 seconds)
        - Non-serializable parameters are filtered out automatically
        - Thread can be continued by any tool using the returned UUID
        - Uses Redis pipelining for efficient thread creation
    """
    thread_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Filter out non-serializable parameters to avoid JSON encoding issues
    filtered_context = {
        k: v
        for k, v in initial_request.items()
        if k not in ["temperature", "thinking_mode", "model", "continuation_id", "_remaining_tokens"]
    }

    context = ThreadContext(
        thread_id=thread_id,
        created_at=now,
        last_updated_at=now,
        tool_name=tool_name,  # Track which tool initiated this conversation
        turns=[],  # Empty initially, turns added via add_turn()
        initial_context=filtered_context,
    )

    # Use Redis pipeline to create thread and metadata efficiently
    client = get_redis_client()
    
    try:
        with client.pipeline() as pipe:
            # Create thread with TTL
            key = f"thread:{thread_id}"
            pipe.setex(key, 3600, context.model_dump_json())
            
            # Execute all commands in one round trip
            results = pipe.execute()
            
            if results[0]:
                logger.debug(f"[FLOW] Created thread {thread_id} with pipeline")
                return thread_id
            else:
                raise RuntimeError(f"Failed to create thread: {results}")
                
    except Exception as e:
        logger.error(f"[FLOW] Failed to create thread: {type(e).__name__}: {e}")
        raise


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

    Uses Redis pipelining for improved performance by batching the read,
    modify, and write operations.

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
        - Maximum turn limit reached (10 turns)
        - Redis connection failure

    Note:
        - Refreshes thread TTL to 1 hour on successful update
        - Turn limits prevent runaway conversations
        - File references are preserved for cross-tool access
        - Uses Redis pipelining to reduce network round trips
    """
    logger.debug(f"[FLOW] Adding {role} turn to {thread_id} ({tool_name})")

    context = get_thread(thread_id)
    if not context:
        logger.debug(f"[FLOW] Thread {thread_id} not found for turn addition")
        return False

    # Check turn limit to prevent runaway conversations
    if len(context.turns) >= MAX_CONVERSATION_TURNS:
        logger.debug(f"[FLOW] Thread {thread_id} at max turns ({MAX_CONVERSATION_TURNS})")
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

    # Use Redis pipeline to batch operations
    try:
        client = get_redis_client()
        key = f"thread:{thread_id}"
        
        # Use pipeline for atomic update and TTL refresh
        with client.pipeline() as pipe:
            # Update thread data and refresh TTL in one round trip
            pipe.setex(key, 3600, context.model_dump_json())
            
            # Execute all commands in a single round trip
            results = pipe.execute()
            
            # Check if the setex command succeeded (returns True)
            if results[0]:
                logger.debug(f"[FLOW] Successfully added turn to {thread_id} using pipeline")
                return True
            else:
                logger.warning(f"[FLOW] Pipeline execution returned unexpected result: {results}")
                return False
                
    except Exception as e:
        logger.debug(f"[FLOW] Failed to save turn to Redis: {type(e).__name__}: {e}")
        return False


def get_conversation_file_list(context: ThreadContext) -> list[str]:
    """
    Get all unique files referenced across all turns in a conversation.

    This function extracts and deduplicates file references from all conversation
    turns to enable efficient file embedding - files are read once and shared
    across all turns rather than being embedded multiple times.

    Args:
        context: ThreadContext containing the complete conversation

    Returns:
        list[str]: Deduplicated list of file paths referenced in the conversation
    """
    if not context.turns:
        logger.debug("[FILES] No turns found, returning empty file list")
        return []

    # Collect all unique files from all turns, preserving order of first appearance
    seen_files = set()
    unique_files = []

    logger.debug(f"[FILES] Collecting files from {len(context.turns)} turns")

    for i, turn in enumerate(context.turns):
        if turn.files:
            logger.debug(f"[FILES] Turn {i+1} has {len(turn.files)} files: {turn.files}")
            for file_path in turn.files:
                if file_path not in seen_files:
                    seen_files.add(file_path)
                    unique_files.append(file_path)
                    logger.debug(f"[FILES] Added new file: {file_path}")
                else:
                    logger.debug(f"[FILES] Duplicate file skipped: {file_path}")
        else:
            logger.debug(f"[FILES] Turn {i+1} has no files")

    logger.debug(f"[FILES] Final unique file list ({len(unique_files)}): {unique_files}")
    return unique_files


def build_conversation_history(context: ThreadContext, read_files_func=None) -> tuple[str, int]:
    """
    Build formatted conversation history for tool prompts with embedded file contents.

    Creates a formatted string representation of the conversation history that includes
    full file contents from all referenced files. Files are embedded only ONCE at the
    start, even if referenced in multiple turns, to prevent duplication and optimize
    token usage.

    Args:
        context: ThreadContext containing the complete conversation

    Returns:
        tuple[str, int]: (formatted_conversation_history, total_tokens_used)
        Returns ("", 0) if no conversation turns exist

    Format:
        - Header with thread metadata and turn count
        - All referenced files embedded once with full contents
        - Each turn shows: role, tool used, which files were used, content
        - Clear delimiters for AI parsing
        - Continuation instruction at end

    Note:
        This formatted history allows tools to "see" both conversation context AND
        file contents from previous tools, enabling true cross-tool collaboration
        while preventing duplicate file embeddings.
    """
    if not context.turns:
        return "", 0

    # Get all unique files referenced in this conversation
    all_files = get_conversation_file_list(context)
    logger.debug(f"[FILES] Found {len(all_files)} unique files in conversation history")

    history_parts = [
        "=== CONVERSATION HISTORY ===",
        f"Thread: {context.thread_id}",
        f"Tool: {context.tool_name}",  # Original tool that started the conversation
        f"Turn {len(context.turns)}/{MAX_CONVERSATION_TURNS}",
        "",
    ]

    # Embed all files referenced in this conversation once at the start
    if all_files:
        logger.debug(f"[FILES] Starting embedding for {len(all_files)} files")
        history_parts.extend(
            [
                "=== FILES REFERENCED IN THIS CONVERSATION ===",
                "The following files have been shared and analyzed during our conversation.",
                "Refer to these when analyzing the context and requests below:",
                "",
            ]
        )

        # Import required functions
        from config import MAX_CONTENT_TOKENS

        if read_files_func is None:
            from utils.file_utils import read_file_content

            # Optimized: read files incrementally with token tracking
            file_contents = []
            total_tokens = 0
            files_included = 0
            files_truncated = 0

            for file_path in all_files:
                try:
                    logger.debug(f"[FILES] Processing file {file_path}")
                    # Correctly unpack the tuple returned by read_file_content
                    formatted_content, content_tokens = read_file_content(file_path)
                    if formatted_content:
                        # read_file_content already returns formatted content, use it directly
                        # Check if adding this file would exceed the limit
                        if total_tokens + content_tokens <= MAX_CONTENT_TOKENS:
                            file_contents.append(formatted_content)
                            total_tokens += content_tokens
                            files_included += 1
                            logger.debug(
                                f"📄 File embedded in conversation history: {file_path} ({content_tokens:,} tokens)"
                            )
                            logger.debug(
                                f"[FILES] Successfully embedded {file_path} - {content_tokens:,} tokens (total: {total_tokens:,})"
                            )
                        else:
                            files_truncated += 1
                            logger.debug(
                                f"📄 File truncated due to token limit: {file_path} ({content_tokens:,} tokens, would exceed {MAX_CONTENT_TOKENS:,} limit)"
                            )
                            logger.debug(
                                f"[FILES] File {file_path} would exceed token limit - skipping (would be {total_tokens + content_tokens:,} tokens)"
                            )
                            # Stop processing more files
                            break
                    else:
                        logger.debug(f"📄 File skipped (empty content): {file_path}")
                        logger.debug(f"[FILES] File {file_path} has empty content - skipping")
                except Exception as e:
                    # Skip files that can't be read but log the failure
                    logger.warning(
                        f"📄 Failed to embed file in conversation history: {file_path} - {type(e).__name__}: {e}"
                    )
                    logger.debug(f"[FILES] Failed to read file {file_path} - {type(e).__name__}: {e}")
                    continue

            if file_contents:
                files_content = "".join(file_contents)
                if files_truncated > 0:
                    files_content += (
                        f"\n[NOTE: {files_truncated} additional file(s) were truncated due to token limit]\n"
                    )
                history_parts.append(files_content)
                logger.debug(
                    f"📄 Conversation history file embedding complete: {files_included} files embedded, {files_truncated} truncated, {total_tokens:,} total tokens"
                )
                logger.debug(
                    f"[FILES] File embedding summary - {files_included} embedded, {files_truncated} truncated, {total_tokens:,} tokens total"
                )
            else:
                history_parts.append("(No accessible files found)")
                logger.debug(
                    f"📄 Conversation history file embedding: no accessible files found from {len(all_files)} requested"
                )
                logger.debug(f"[FILES] No accessible files found from {len(all_files)} requested files")
        else:
            # Fallback to original read_files function for backward compatibility
            files_content = read_files_func(all_files)
            if files_content:
                # Add token validation for the combined file content
                from utils.token_utils import check_token_limit

                within_limit, estimated_tokens = check_token_limit(files_content)
                if within_limit:
                    history_parts.append(files_content)
                else:
                    # Handle token limit exceeded for conversation files
                    error_message = f"ERROR: The total size of files referenced in this conversation has exceeded the context limit and cannot be displayed.\nEstimated tokens: {estimated_tokens}, but limit is {MAX_CONTENT_TOKENS}."
                    history_parts.append(error_message)
            else:
                history_parts.append("(No accessible files found)")

        history_parts.extend(
            [
                "",
                "=== END REFERENCED FILES ===",
                "",
            ]
        )

    history_parts.append("Previous conversation turns:")

    for i, turn in enumerate(context.turns, 1):
        role_label = "Claude" if turn.role == "user" else "Gemini"

        # Add turn header with tool attribution for cross-tool tracking
        turn_header = f"\n--- Turn {i} ({role_label}"
        if turn.tool_name:
            turn_header += f" using {turn.tool_name}"
        turn_header += ") ---"
        history_parts.append(turn_header)

        # Add files context if present - but just reference which files were used
        # (the actual contents are already embedded above)
        if turn.files:
            history_parts.append(f"📁 Files used in this turn: {', '.join(turn.files)}")
            history_parts.append("")  # Empty line for readability

        # Add the actual content
        history_parts.append(turn.content)

        # Add follow-up question if present
        if turn.follow_up_question:
            history_parts.append(f"\n[Gemini's Follow-up: {turn.follow_up_question}]")

    history_parts.extend(
        ["", "=== END CONVERSATION HISTORY ===", "", "Continue this conversation by building on the previous context."]
    )

    # Calculate total tokens for the complete conversation history
    complete_history = "\n".join(history_parts)
    from utils.token_utils import estimate_tokens

    total_conversation_tokens = estimate_tokens(complete_history)

    # Summary log of what was built
    user_turns = len([t for t in context.turns if t.role == "user"])
    assistant_turns = len([t for t in context.turns if t.role == "assistant"])
    logger.debug(
        f"[FLOW] Built conversation history: {user_turns} user + {assistant_turns} assistant turns, {len(all_files)} files, {total_conversation_tokens:,} tokens"
    )

    return complete_history, total_conversation_tokens


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
