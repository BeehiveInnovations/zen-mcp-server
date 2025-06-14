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
# Get max conversation turns from environment, default to 20 turns (10 exchanges)
try:
    MAX_CONVERSATION_TURNS = int(os.getenv("MAX_CONVERSATION_TURNS", "20"))
    if MAX_CONVERSATION_TURNS <= 0:
        logger.warning(f"Invalid MAX_CONVERSATION_TURNS value ({MAX_CONVERSATION_TURNS}), using default of 20 turns")
        MAX_CONVERSATION_TURNS = 20
except ValueError:
    logger.warning(
        f"Invalid MAX_CONVERSATION_TURNS value ('{os.getenv('MAX_CONVERSATION_TURNS')}'), using default of 20 turns"
    )
    MAX_CONVERSATION_TURNS = 20

# Get conversation timeout from environment (in hours), default to 3 hours
try:
    CONVERSATION_TIMEOUT_HOURS = int(os.getenv("CONVERSATION_TIMEOUT_HOURS", "3"))
    if CONVERSATION_TIMEOUT_HOURS <= 0:
        logger.warning(
            f"Invalid CONVERSATION_TIMEOUT_HOURS value ({CONVERSATION_TIMEOUT_HOURS}), using default of 3 hours"
        )
        CONVERSATION_TIMEOUT_HOURS = 3
except ValueError:
    logger.warning(
        f"Invalid CONVERSATION_TIMEOUT_HOURS value ('{os.getenv('CONVERSATION_TIMEOUT_HOURS')}'), using default of 3 hours"
    )
    CONVERSATION_TIMEOUT_HOURS = 3

CONVERSATION_TIMEOUT_SECONDS = CONVERSATION_TIMEOUT_HOURS * 3600


class ConversationTurn(BaseModel):
    """
    Single turn in a conversation

    Represents one exchange in the AI-to-AI conversation, tracking both
    the content and metadata needed for cross-tool continuation.

    Attributes:
        role: "user" (Claude) or "assistant" (Gemini/O3/etc)
        content: The actual message content/response
        timestamp: ISO timestamp when this turn was created
        files: List of file paths referenced in this specific turn
        tool_name: Which tool generated this turn (for cross-tool tracking)
        model_provider: Provider used (e.g., "google", "openai")
        model_name: Specific model used (e.g., "gemini-2.5-flash-preview-05-20", "o3-mini")
        model_metadata: Additional model-specific metadata (e.g., thinking mode, token usage)
    """

    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    files: Optional[list[str]] = None  # Files referenced in this turn
    tool_name: Optional[str] = None  # Tool used for this turn
    model_provider: Optional[str] = None  # Model provider (google, openai, etc)
    model_name: Optional[str] = None  # Specific model used
    model_metadata: Optional[dict[str, Any]] = None  # Additional model info


class ThreadContext(BaseModel):
    """
    Complete conversation context for a thread

    Contains all information needed to reconstruct a conversation state
    across different tools and request cycles. This is the core data
    structure that enables cross-tool continuation.

    Attributes:
        thread_id: UUID identifying this conversation thread
        parent_thread_id: UUID of parent thread (for conversation chains)
        created_at: ISO timestamp when thread was created
        last_updated_at: ISO timestamp of last modification
        tool_name: Name of the tool that initiated this thread
        turns: List of all conversation turns in chronological order
        initial_context: Original request data that started the conversation
    """

    thread_id: str
    parent_thread_id: Optional[str] = None  # Parent thread for conversation chains
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


def create_thread(tool_name: str, initial_request: dict[str, Any], parent_thread_id: Optional[str] = None) -> str:
    """
    Create new conversation thread and return thread ID

    Initializes a new conversation thread for AI-to-AI discussions.
    This is called when a tool wants to enable follow-up conversations
    or when Claude explicitly starts a multi-turn interaction.

    Args:
        tool_name: Name of the tool creating this thread (e.g., "analyze", "chat")
        initial_request: Original request parameters (will be filtered for serialization)
        parent_thread_id: Optional parent thread ID for conversation chains

    Returns:
        str: UUID thread identifier that can be used for continuation

    Note:
        - Thread expires after the configured timeout (default: 3 hours)
        - Non-serializable parameters are filtered out automatically
        - Thread can be continued by any tool using the returned UUID
        - Parent thread creates a chain for conversation history traversal
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
        parent_thread_id=parent_thread_id,  # Link to parent for conversation chains
        created_at=now,
        last_updated_at=now,
        tool_name=tool_name,  # Track which tool initiated this conversation
        turns=[],  # Empty initially, turns added via add_turn()
        initial_context=filtered_context,
    )

    # Store in Redis with configurable TTL to prevent indefinite accumulation
    client = get_redis_client()
    key = f"thread:{thread_id}"
    client.setex(key, CONVERSATION_TIMEOUT_SECONDS, context.model_dump_json())

    logger.debug(f"[THREAD] Created new thread {thread_id} with parent {parent_thread_id}")

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
    files: Optional[list[str]] = None,
    tool_name: Optional[str] = None,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
    model_metadata: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Add turn to existing thread

    Appends a new conversation turn to an existing thread. This is the core
    function for building conversation history and enabling cross-tool
    continuation. Each turn preserves the tool and model that generated it.

    Args:
        thread_id: UUID of the conversation thread
        role: "user" (Claude) or "assistant" (Gemini/O3/etc)
        content: The actual message/response content
        files: Optional list of files referenced in this turn
        tool_name: Name of the tool adding this turn (for attribution)
        model_provider: Provider used (e.g., "google", "openai")
        model_name: Specific model used (e.g., "gemini-2.5-flash-preview-05-20", "o3-mini")
        model_metadata: Additional model info (e.g., thinking mode, token usage)

    Returns:
        bool: True if turn was successfully added, False otherwise

    Failure cases:
        - Thread doesn't exist or expired
        - Maximum turn limit reached
        - Redis connection failure

    Note:
        - Refreshes thread TTL to configured timeout on successful update
        - Turn limits prevent runaway conversations
        - File references are preserved for cross-tool access
        - Model information enables cross-provider conversations
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
        files=files,  # Preserved for cross-tool file context
        tool_name=tool_name,  # Track which tool generated this turn
        model_provider=model_provider,  # Track model provider
        model_name=model_name,  # Track specific model
        model_metadata=model_metadata,  # Additional model info
    )

    context.turns.append(turn)
    context.last_updated_at = datetime.now(timezone.utc).isoformat()

    # Save back to Redis and refresh TTL
    try:
        client = get_redis_client()
        key = f"thread:{thread_id}"
        client.setex(key, CONVERSATION_TIMEOUT_SECONDS, context.model_dump_json())  # Refresh TTL to configured timeout
        return True
    except Exception as e:
        logger.debug(f"[FLOW] Failed to save turn to Redis: {type(e).__name__}")
        return False


def get_thread_chain(thread_id: str, max_depth: int = 20) -> list[ThreadContext]:
    """
    Traverse the parent chain to get all threads in conversation sequence.

    Retrieves the complete conversation chain by following parent_thread_id
    links. Returns threads in chronological order (oldest first).

    Args:
        thread_id: Starting thread ID
        max_depth: Maximum chain depth to prevent infinite loops

    Returns:
        list[ThreadContext]: All threads in chain, oldest first
    """
    chain = []
    current_id = thread_id
    seen_ids = set()

    # Build chain from current to oldest
    while current_id and len(chain) < max_depth:
        # Prevent circular references
        if current_id in seen_ids:
            logger.warning(f"[THREAD] Circular reference detected in thread chain at {current_id}")
            break

        seen_ids.add(current_id)

        context = get_thread(current_id)
        if not context:
            logger.debug(f"[THREAD] Thread {current_id} not found in chain traversal")
            break

        chain.append(context)
        current_id = context.parent_thread_id

    # Reverse to get chronological order (oldest first)
    chain.reverse()

    logger.debug(f"[THREAD] Retrieved chain of {len(chain)} threads for {thread_id}")
    return chain


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
            logger.debug(f"[FILES] Turn {i + 1} has {len(turn.files)} files: {turn.files}")
            for file_path in turn.files:
                if file_path not in seen_files:
                    seen_files.add(file_path)
                    unique_files.append(file_path)
                    logger.debug(f"[FILES] Added new file: {file_path}")
                else:
                    logger.debug(f"[FILES] Duplicate file skipped: {file_path}")
        else:
            logger.debug(f"[FILES] Turn {i + 1} has no files")

    logger.debug(f"[FILES] Final unique file list ({len(unique_files)}): {unique_files}")
    return unique_files


def build_conversation_history(context: ThreadContext, model_context=None, read_files_func=None) -> tuple[str, int]:
    """
    Build formatted conversation history for tool prompts with embedded file contents.

    Creates a formatted string representation of the conversation history that includes
    full file contents from all referenced files. Files are embedded only ONCE at the
    start, even if referenced in multiple turns, to prevent duplication and optimize
    token usage.

    If the thread has a parent chain, this function traverses the entire chain to
    include the complete conversation history.

    Args:
        context: ThreadContext containing the complete conversation
        model_context: ModelContext for token allocation (optional, uses DEFAULT_MODEL if not provided)
        read_files_func: Optional function to read files (for testing)

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
    # Get the complete thread chain
    if context.parent_thread_id:
        # This thread has a parent, get the full chain
        chain = get_thread_chain(context.thread_id)

        # Collect all turns from all threads in chain
        all_turns = []
        all_files_set = set()
        total_turns = 0

        for thread in chain:
            all_turns.extend(thread.turns)
            total_turns += len(thread.turns)

            # Collect files from this thread
            for turn in thread.turns:
                if turn.files:
                    all_files_set.update(turn.files)

        all_files = list(all_files_set)
        logger.debug(f"[THREAD] Built history from {len(chain)} threads with {total_turns} total turns")
    else:
        # Single thread, no parent chain
        all_turns = context.turns
        total_turns = len(context.turns)
        all_files = get_conversation_file_list(context)

    if not all_turns:
        return "", 0

    logger.debug(f"[FILES] Found {len(all_files)} unique files in conversation history")

    # Get model-specific token allocation early (needed for both files and turns)
    if model_context is None:
        from config import DEFAULT_MODEL, IS_AUTO_MODE
        from utils.model_context import ModelContext

        # In auto mode, use an intelligent fallback model for token calculations
        # since "auto" is not a real model with a provider
        model_name = DEFAULT_MODEL
        if IS_AUTO_MODE and model_name.lower() == "auto":
            # Use intelligent fallback based on available API keys
            from providers.registry import ModelProviderRegistry

            model_name = ModelProviderRegistry.get_preferred_fallback_model()

        model_context = ModelContext(model_name)

    token_allocation = model_context.calculate_token_allocation()
    max_file_tokens = token_allocation.file_tokens
    max_history_tokens = token_allocation.history_tokens

    logger.debug(f"[HISTORY] Using model-specific limits for {model_context.model_name}:")
    logger.debug(f"[HISTORY]   Max file tokens: {max_file_tokens:,}")
    logger.debug(f"[HISTORY]   Max history tokens: {max_history_tokens:,}")

    history_parts = [
        "=== CONVERSATION HISTORY (CONTINUATION) ===",
        f"Thread: {context.thread_id}",
        f"Tool: {context.tool_name}",  # Original tool that started the conversation
        f"Turn {total_turns}/{MAX_CONVERSATION_TURNS}",
        "You are continuing this conversation thread from where it left off.",
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
                        if total_tokens + content_tokens <= max_file_tokens:
                            file_contents.append(formatted_content)
                            total_tokens += content_tokens
                            files_included += 1
                            logger.debug(
                                f"File embedded in conversation history: {file_path} ({content_tokens:,} tokens)"
                            )
                            logger.debug(
                                f"[FILES] Successfully embedded {file_path} - {content_tokens:,} tokens (total: {total_tokens:,})"
                            )
                        else:
                            files_truncated += 1
                            logger.debug(
                                f"File truncated due to token limit: {file_path} ({content_tokens:,} tokens, would exceed {max_file_tokens:,} limit)"
                            )
                            logger.debug(
                                f"[FILES] File {file_path} would exceed token limit - skipping (would be {total_tokens + content_tokens:,} tokens)"
                            )
                            # Stop processing more files
                            break
                    else:
                        logger.debug(f"File skipped (empty content): {file_path}")
                        logger.debug(f"[FILES] File {file_path} has empty content - skipping")
                except Exception as e:
                    # Skip files that can't be read but log the failure
                    logger.warning(
                        f"Failed to embed file in conversation history: {file_path} - {type(e).__name__}: {e}"
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
                    f"Conversation history file embedding complete: {files_included} files embedded, {files_truncated} truncated, {total_tokens:,} total tokens"
                )
                logger.debug(
                    f"[FILES] File embedding summary - {files_included} embedded, {files_truncated} truncated, {total_tokens:,} tokens total"
                )
            else:
                history_parts.append("(No accessible files found)")
                logger.debug(
                    f"Conversation history file embedding: no accessible files found from {len(all_files)} requested"
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
                    error_message = f"ERROR: The total size of files referenced in this conversation has exceeded the context limit and cannot be displayed.\nEstimated tokens: {estimated_tokens}, but limit is {max_file_tokens}."
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

    # Build conversation turns bottom-up (most recent first) but present chronologically
    # This ensures we include as many recent turns as possible within the token budget
    turn_entries = []  # Will store (index, formatted_turn_content) for chronological ordering
    total_turn_tokens = 0
    file_embedding_tokens = sum(model_context.estimate_tokens(part) for part in history_parts)

    # Process turns in reverse order (most recent first) to prioritize recent context
    for idx in range(len(all_turns) - 1, -1, -1):
        turn = all_turns[idx]
        turn_num = idx + 1
        role_label = "Claude" if turn.role == "user" else "Gemini"

        # Build the complete turn content
        turn_parts = []

        # Add turn header with tool attribution for cross-tool tracking
        turn_header = f"\n--- Turn {turn_num} ({role_label}"
        if turn.tool_name:
            turn_header += f" using {turn.tool_name}"

        # Add model info if available
        if turn.model_provider and turn.model_name:
            turn_header += f" via {turn.model_provider}/{turn.model_name}"

        turn_header += ") ---"
        turn_parts.append(turn_header)

        # Add files context if present - but just reference which files were used
        # (the actual contents are already embedded above)
        if turn.files:
            turn_parts.append(f"Files used in this turn: {', '.join(turn.files)}")
            turn_parts.append("")  # Empty line for readability

        # Add the actual content
        turn_parts.append(turn.content)

        # Calculate tokens for this turn
        turn_content = "\n".join(turn_parts)
        turn_tokens = model_context.estimate_tokens(turn_content)

        # Check if adding this turn would exceed history budget
        if file_embedding_tokens + total_turn_tokens + turn_tokens > max_history_tokens:
            # Stop adding turns - we've reached the limit
            logger.debug(f"[HISTORY] Stopping at turn {turn_num} - would exceed history budget")
            logger.debug(f"[HISTORY]   File tokens: {file_embedding_tokens:,}")
            logger.debug(f"[HISTORY]   Turn tokens so far: {total_turn_tokens:,}")
            logger.debug(f"[HISTORY]   This turn: {turn_tokens:,}")
            logger.debug(f"[HISTORY]   Would total: {file_embedding_tokens + total_turn_tokens + turn_tokens:,}")
            logger.debug(f"[HISTORY]   Budget: {max_history_tokens:,}")
            break

        # Add this turn to our list (we'll reverse it later for chronological order)
        turn_entries.append((idx, turn_content))
        total_turn_tokens += turn_tokens

    # Reverse to get chronological order (oldest first)
    turn_entries.reverse()

    # Add the turns in chronological order
    for _, turn_content in turn_entries:
        history_parts.append(turn_content)

    # Log what we included
    included_turns = len(turn_entries)
    total_turns = len(all_turns)
    if included_turns < total_turns:
        logger.info(f"[HISTORY] Included {included_turns}/{total_turns} turns due to token limit")
        history_parts.append(f"\n[Note: Showing {included_turns} most recent turns out of {total_turns} total]")

    history_parts.extend(
        [
            "",
            "=== END CONVERSATION HISTORY ===",
            "",
            "IMPORTANT: You are continuing an existing conversation thread. Build upon the previous exchanges shown above,",
            "reference earlier points, and maintain consistency with what has been discussed.",
            "",
            "DO NOT repeat or summarize previous analysis, findings, or instructions that are already covered in the",
            "conversation history. Instead, provide only new insights, additional analysis, or direct answers to",
            "the follow-up question / concerns / insights. Assume the user has read the prior conversation.",
            "",
            f"This is turn {len(all_turns) + 1} of the conversation - use the conversation history above to provide a coherent continuation.",
        ]
    )

    # Calculate total tokens for the complete conversation history
    complete_history = "\n".join(history_parts)
    from utils.token_utils import estimate_tokens

    total_conversation_tokens = estimate_tokens(complete_history)

    # Summary log of what was built
    user_turns = len([t for t in all_turns if t.role == "user"])
    assistant_turns = len([t for t in all_turns if t.role == "assistant"])
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
