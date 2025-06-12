# Chat Tool API Reference

## Overview

The **Chat Tool** provides immediate access to Gemini's conversational capabilities for quick questions, brainstorming sessions, and general collaboration. It's designed for rapid iteration and exploration of ideas without the computational overhead of deeper analysis tools.

## Tool Schema

```json
{
  "name": "chat",
  "description": "Quick questions, brainstorming, simple code snippets",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "Your question, topic, or current thinking to discuss with Gemini"
      },
      "continuation_id": {
        "type": "string",
        "description": "Thread continuation ID for multi-turn conversations",
        "optional": true
      },
      "temperature": {
        "type": "number",
        "description": "Response creativity (0-1, default 0.5)",
        "minimum": 0,
        "maximum": 1,
        "default": 0.5
      },
      "thinking_mode": {
        "type": "string",
        "description": "Thinking depth: minimal|low|medium|high|max",
        "enum": ["minimal", "low", "medium", "high", "max"],
        "default": "medium"
      },
      "files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional files for context (must be absolute paths)",
        "optional": true
      }
    },
    "required": ["prompt"]
  }
}
```

## Usage Patterns

### 1. Quick Questions

**Ideal For**:
- Clarifying concepts or terminology
- Getting immediate explanations
- Understanding code snippets
- Exploring ideas rapidly

**Example**:
```json
{
  "name": "chat",
  "arguments": {
    "prompt": "What's the difference between async and await in Python?",
    "thinking_mode": "low"
  }
}
```

### 2. Brainstorming Sessions

**Ideal For**:
- Generating multiple solution approaches
- Exploring design alternatives
- Creative problem solving
- Architecture discussions

**Example**:
```json
{
  "name": "chat", 
  "arguments": {
    "prompt": "I need to design a caching layer for my MCP server. What are some approaches I should consider?",
    "temperature": 0.7,
    "thinking_mode": "medium"
  }
}
```

### 3. Code Discussions

**Ideal For**:
- Reviewing small code snippets
- Understanding implementation patterns
- Getting quick feedback
- Exploring API designs

**Example**:
```json
{
  "name": "chat",
  "arguments": {
    "prompt": "Review this error handling pattern and suggest improvements",
    "files": ["/workspace/utils/error_handling.py"],
    "thinking_mode": "medium"
  }
}
```

### 4. Multi-Turn Conversations

**Ideal For**:
- Building on previous discussions
- Iterative refinement of ideas
- Context-aware follow-ups
- Continuous collaboration

**Example**:
```json
{
  "name": "chat",
  "arguments": {
    "prompt": "Based on our previous discussion about caching, how would you implement cache invalidation?",
    "continuation_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Parameter Details

### prompt (required)
- **Type**: string
- **Purpose**: The main input for Gemini to process
- **Best Practices**:
  - Be specific and clear about what you need
  - Include relevant context in the prompt itself
  - Ask focused questions for better responses
  - Use conversational language for brainstorming

### continuation_id (optional)
- **Type**: string (UUID format)
- **Purpose**: Links to previous conversation context
- **Behavior**:
  - If provided, loads conversation history from Redis
  - Maintains context across multiple tool calls
  - Enables follow-up questions and refinement
  - Automatically generated on first call if not provided

### temperature (optional)
- **Type**: number (0.0 - 1.0)
- **Default**: 0.5
- **Purpose**: Controls response creativity and variability
- **Guidelines**:
  - **0.0-0.3**: Focused, deterministic responses (technical questions)
  - **0.4-0.6**: Balanced creativity and accuracy (general discussion)
  - **0.7-1.0**: High creativity (brainstorming, exploration)

### thinking_mode (optional)
- **Type**: string enum
- **Default**: "medium"
- **Purpose**: Controls computational budget for analysis depth
- **Options**:
  - **minimal** (128 tokens): Quick yes/no, simple clarifications
  - **low** (2048 tokens): Basic explanations, straightforward questions
  - **medium** (8192 tokens): Standard discussions, moderate complexity
  - **high** (16384 tokens): Deep explanations, complex topics
  - **max** (32768 tokens): Maximum depth, research-level discussions

### files (optional)
- **Type**: array of strings
- **Purpose**: Provides file context for discussion
- **Constraints**:
  - Must be absolute paths
  - Subject to sandbox validation (PROJECT_ROOT)
  - Limited to 50 files per request
  - Total content limited by thinking_mode token budget

## Response Format

### Standard Response Structure

```json
{
  "content": "Main response content...",
  "metadata": {
    "thinking_mode": "medium",
    "temperature": 0.5,
    "tokens_used": 2156,
    "response_time": "1.2s",
    "files_processed": 3
  },
  "continuation_id": "550e8400-e29b-41d4-a716-446655440000",
  "files_processed": [
    "/workspace/utils/error_handling.py"
  ],
  "status": "success"
}
```

### Response Content Types

**Explanatory Responses**:
- Clear, structured explanations
- Step-by-step breakdowns
- Code examples with annotations
- Concept comparisons and contrasts

**Brainstorming Responses**:
- Multiple approach options
- Pros/cons analysis
- Creative alternatives
- Implementation considerations

**Code Discussion Responses**:
- Specific line-by-line feedback
- Pattern recognition and naming
- Improvement suggestions
- Best practice recommendations

## Error Handling

### Common Errors

**Invalid Temperature**:
```json
{
  "error": "Invalid temperature value: 1.5. Must be between 0.0 and 1.0"
}
```

**File Access Error**:
```json
{
  "error": "File access denied: /etc/passwd. Path outside project sandbox."
}
```

**Token Limit Exceeded**:
```json
{
  "error": "Content exceeds token limit for thinking_mode 'low'. Consider using 'medium' or 'high'."
}
```

### Error Recovery Strategies

1. **Parameter Validation**: Adjust invalid parameters to acceptable ranges
2. **File Filtering**: Remove inaccessible files and continue with available ones
3. **Token Management**: Truncate large content while preserving structure
4. **Graceful Degradation**: Provide partial responses when possible

## Performance Characteristics

### Response Times
- **minimal mode**: ~0.5-1s (simple questions)
- **low mode**: ~1-2s (basic explanations)
- **medium mode**: ~2-4s (standard discussions)
- **high mode**: ~4-8s (deep analysis)
- **max mode**: ~8-15s (research-level)

### Resource Usage
- **Memory**: ~50-200MB per conversation thread
- **Network**: Minimal (only Gemini API calls)
- **Storage**: Redis conversation persistence (24h TTL)
- **CPU**: Low (primarily I/O bound)

### Optimization Tips

1. **Use Appropriate Thinking Mode**: Don't over-engineer simple questions
2. **Leverage Continuation**: Build on previous context rather than repeating
3. **Focus Prompts**: Specific questions get better responses
4. **Batch Related Questions**: Use conversation threading for related topics

## Best Practices

### Effective Prompting

**Good Examples**:
```
"Explain the trade-offs between Redis and in-memory caching for an MCP server"
"Help me brainstorm error handling strategies for async file operations"
"What are the security implications of this authentication pattern?"
```

**Avoid**:
```
"Help me" (too vague)
"Fix this code" (without context)
"What should I do?" (open-ended without scope)
```

### Conversation Management

1. **Use Continuation IDs**: Maintain context across related discussions
2. **Logical Grouping**: Keep related topics in same conversation thread
3. **Clear Transitions**: Explicitly state when changing topics
4. **Context Refresh**: Occasionally summarize progress in long conversations

### File Usage

1. **Relevant Files Only**: Include only files directly related to discussion
2. **Prioritize Source Code**: Code files provide more value than logs
3. **Reasonable Scope**: 5-10 files maximum for focused discussions
4. **Absolute Paths**: Always use full paths for reliability

## Integration Examples

### With Other Tools

**Chat → Analyze Flow**:
```json
// 1. Quick discussion
{"name": "chat", "arguments": {"prompt": "Should I refactor this module?"}}

// 2. Deep analysis based on chat insights
{"name": "analyze", "arguments": {
  "files": ["/workspace/module.py"],
  "question": "Analyze refactoring opportunities based on maintainability",
  "continuation_id": "previous-chat-thread-id"
}}
```

**Chat → ThinkDeep Flow**:
```json
// 1. Initial exploration
{"name": "chat", "arguments": {"prompt": "I need to scale my API to handle 1000 RPS"}}

// 2. Strategic planning
{"name": "thinkdeep", "arguments": {
  "current_analysis": "Need to scale API to 1000 RPS",
  "focus_areas": ["performance", "architecture", "caching"],
  "continuation_id": "previous-chat-thread-id"
}}
```

### Workflow Integration

**Development Workflow**:
1. **Chat**: Quick question about implementation approach
2. **Analyze**: Deep dive into existing codebase
3. **Chat**: Discussion of findings and next steps
4. **CodeReview**: Quality validation of changes

**Learning Workflow**:
1. **Chat**: Ask about unfamiliar concepts
2. **Chat**: Request examples and clarifications
3. **Chat**: Discuss practical applications
4. **Analyze**: Study real codebase examples

---

The Chat Tool serves as the primary interface for rapid AI collaboration, providing immediate access to Gemini's knowledge while maintaining conversation context and enabling seamless integration with deeper analysis tools.

