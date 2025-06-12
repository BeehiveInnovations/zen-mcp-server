# Gemini MCP Server Architecture Overview

## System Overview

The **Gemini MCP Server** implements a sophisticated Model Context Protocol (MCP) server architecture that provides Claude with access to Google's Gemini AI models through specialized tools. This enables advanced AI-assisted development workflows combining Claude's general capabilities with Gemini's deep analytical and creative thinking abilities.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Interface                         │
│                 (Claude Desktop App)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ MCP Protocol (stdio)
┌─────────────────────▼───────────────────────────────────────┐
│                MCP Core Engine                              │
│  • AsyncIO Event Loop (server.py:45)                      │
│  • Tool Discovery & Registration                           │
│  • Request/Response Processing                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Tool Architecture                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   chat      │ │ thinkdeep   │ │  analyze    │           │
│  │ (quick Q&A) │ │(deep think) │ │(code review)│           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ codereview  │ │   debug     │ │ precommit   │           │
│  │(quality)    │ │(root cause) │ │(validation) │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│               Support Services                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐│
│  │Redis Conversation│ │Security Engine  │ │Gemini API      ││
│  │Memory & Threading│ │Multi-layer      │ │Integration     ││
│  │                  │ │Validation       │ │                ││
│  └─────────────────┘ └─────────────────┘ └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MCP Core Engine (server.py:45)

**Purpose**: Central coordination hub managing the MCP protocol implementation
**Key Components**:
- **AsyncIO Event Loop**: Handles concurrent tool execution and request processing
- **Tool Discovery**: Dynamic loading and registration via `@server.list_tools()` decorator
- **Protocol Management**: MCP message parsing, validation, and response formatting

**Architecture Pattern**: Event-driven architecture with asyncio for non-blocking operations

### 2. Tool System Architecture

**Purpose**: Modular plugin system for specialized AI capabilities
**Key Components**:
- **BaseTool Abstract Class** (`tools/base.py:25`): Common interface for all tools
- **Plugin Architecture**: Individual tool implementations in `tools/` directory
- **Tool Selection Matrix**: CLAUDE.md defines appropriate tool usage patterns

**Data Flow**:
```
Claude Request → MCP Engine → Tool Selection → Gemini API → Response Processing → Claude
```

**Tool Categories**:
- **Quick Response**: `chat` - immediate answers and brainstorming
- **Deep Analysis**: `thinkdeep` - complex architecture and strategic planning  
- **Code Quality**: `codereview` - security audits and bug detection
- **Investigation**: `debug` - root cause analysis and error investigation
- **Exploration**: `analyze` - codebase comprehension and dependency analysis
- **Validation**: `precommit` - automated quality gates

### 3. Security Architecture

**Purpose**: Multi-layer defense system protecting against malicious operations
**Key Components**:
- **Path Validation** (`utils/file_utils.py:45`): Prevents directory traversal attacks
- **Sandbox Enforcement**: PROJECT_ROOT containment for file operations
- **Docker Path Translation**: Host-to-container path mapping with WORKSPACE_ROOT
- **Absolute Path Requirement**: Eliminates relative path vulnerabilities

**Security Layers**:
1. **Input Validation**: Path sanitization and dangerous operation detection
2. **Container Isolation**: Docker environment with controlled file access
3. **Permission Boundaries**: Read-only access patterns with explicit write gates
4. **Error Recovery**: Graceful handling of unauthorized operations

### 4. Thinking Modes System

**Purpose**: Computational budget control for Gemini's analysis depth
**Implementation**: 
- **Token Allocation**: `minimal (128), low (2048), medium (8192), high (16384), max (32768)`
- **Dynamic Selection**: Tools adjust thinking depth based on task complexity
- **Resource Management**: Prevents token exhaustion on complex analysis

**Usage Pattern**:
```python
# tools/thinkdeep.py:67
thinking_mode = request.get('thinking_mode', 'high')
context_tokens = THINKING_MODE_TOKENS[thinking_mode]
```

### 5. Conversation System

**Purpose**: Cross-session context preservation and threading
**Key Components**:
- **Redis Persistence** (`utils/conversation_memory.py:30`): Thread storage and retrieval
- **Thread Reconstruction**: UUID-based conversation continuity
- **Cross-Tool Continuation**: `continuation_id` parameter for context flow
- **Follow-up Management**: Structured multi-turn conversation support

**Data Structures**:
```python
# utils/conversation_memory.py:45
class ThreadContext:
    thread_id: str
    tool_history: List[ToolExecution]
    conversation_files: List[str]
    context_tokens: int
```

## Integration Points

### Configuration Management (config.py)

**Critical Settings**:
- **`GEMINI_MODEL`** (config.py:24): Model selection for API calls
- **`MAX_CONTEXT_TOKENS`** (config.py:30): Token limits for conversation management
- **`REDIS_URL`** (config.py:60): Conversation memory backend
- **`PROJECT_ROOT`** (config.py:15): Security sandbox boundary

### Utility Services

**File Operations** (`utils/file_utils.py`):
- Token-aware reading with priority system
- Directory expansion with filtering
- Error-resistant content formatting

**Git Integration** (`utils/git_utils.py`):
- Repository state analysis for precommit validation
- Change detection for documentation updates
- Branch and commit tracking

**Token Management** (`utils/token_utils.py`):
- Context optimization and pruning
- File prioritization strategies
- Memory usage monitoring

## Data Flow Patterns

### 1. Tool Execution Flow

```
1. Claude sends MCP request with tool name and parameters
2. MCP Engine validates request and routes to appropriate tool
3. Tool loads conversation context from Redis (if continuation_id provided)
4. Tool processes request using Gemini API with thinking mode configuration
5. Tool stores results in conversation memory and returns formatted response
6. MCP Engine serializes response and sends to Claude via stdio
```

### 2. File Processing Pipeline

```
1. File paths received and validated against security rules
2. Docker path translation (host → container mapping)
3. Token budget allocation based on file size and context limits
4. Priority-based file reading (code files > documentation > logs)
5. Content formatting with line numbers and error handling
6. Context assembly with deduplication across conversation turns
```

### 3. Security Validation Chain

```
1. Path Input → Dangerous Path Detection → Rejection/Sanitization
2. Validated Path → Absolute Path Conversion → Sandbox Boundary Check
3. Bounded Path → Docker Translation → Container Path Generation
4. Safe Path → File Operation → Error-Resistant Content Return
```

## Performance Characteristics

### Scalability Factors

- **Concurrent Tool Execution**: AsyncIO enables parallel processing of multiple tool requests
- **Memory Efficiency**: Token-aware file processing prevents memory exhaustion
- **Context Optimization**: Conversation deduplication reduces redundant processing
- **Error Resilience**: Graceful degradation maintains functionality during failures

### Resource Management

- **Token Budgeting**: 40% context reservation (30% Memory Bank + 10% Memory MCP)
- **File Prioritization**: Direct code files prioritized over supporting documentation
- **Redis Optimization**: Thread-based storage with automatic cleanup
- **Gemini API Efficiency**: Thinking mode selection optimizes computational costs

## Extension Points

### Adding New Tools

1. **Inherit from BaseTool** (`tools/base.py:25`)
2. **Implement required methods**: `execute()`, `get_schema()`
3. **Register with MCP Engine**: Add to tool discovery system
4. **Update CLAUDE.md**: Define collaboration patterns and usage guidelines

### Security Extensions

1. **Custom Validators**: Add to `utils/file_utils.py` validation chain
2. **Path Translators**: Extend Docker path mapping for new mount points
3. **Permission Gates**: Implement granular access controls for sensitive operations

### Performance Optimizations

1. **Caching Layers**: Add Redis caching for frequently accessed files
2. **Context Compression**: Implement intelligent context summarization
3. **Parallel Processing**: Extend AsyncIO patterns for I/O-bound operations

---

This architecture provides a robust, secure, and extensible foundation for AI-assisted development workflows while maintaining clear separation of concerns and comprehensive error handling.