# Fix for Conversation History Bug in Continuation Flow

## Problem
When using `continuation_id` to continue a conversation, the conversation history (with embedded files) was being lost for tools that don't have a `prompt` field. Only new file content was being passed to the tool, resulting in minimal content (e.g., 322 chars for just a NOTE about files already in history).

## Root Cause
1. `reconstruct_thread_context()` builds conversation history and stores it in `arguments["prompt"]`
2. Different tools use different field names for user input:
   - `chat` → `prompt`
   - `analyze` → `question`
   - `debug` → `error_description`
   - `codereview` → `context`
   - `thinkdeep` → `current_analysis`
   - `precommit` → `original_request`
3. The enhanced prompt with conversation history was being placed in the wrong field
4. Tools would only see their new input, not the conversation history

## Solution
Modified `reconstruct_thread_context()` in `server.py` to:
1. Create a mapping of tool names to their primary input fields
2. Extract the user's new input from the correct field based on the tool
3. Store the enhanced prompt (with conversation history) back into the correct field

## Changes Made
1. **server.py**: 
   - Added `prompt_field_mapping` to map tools to their input fields
   - Modified to extract user input from the correct field
   - Modified to store enhanced prompt in the correct field

2. **tests/test_conversation_field_mapping.py**:
   - Added comprehensive tests to verify the fix works for all tools
   - Tests ensure conversation history is properly mapped to each tool's field

## Verification
All existing tests pass, including:
- `test_conversation_memory.py` (18 tests)
- `test_cross_tool_continuation.py` (4 tests)
- New `test_conversation_field_mapping.py` (2 tests)

The fix ensures that when continuing conversations, tools receive the full conversation history with embedded files, not just new content.