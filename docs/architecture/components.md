# System Components & Interactions

## Component Architecture

The Gemini MCP Server is built on a modular component architecture that enables sophisticated AI collaboration patterns while maintaining security and performance.

## Core Components

### 1. MCP Protocol Engine

**Location**: `server.py:45-120`
**Purpose**: Central communication hub implementing Model Context Protocol specification

**Key Responsibilities**:
- **Protocol Compliance**: Implements MCP v1.0 specification for Claude integration
- **Message Routing**: Dispatches requests to appropriate tool handlers
- **Error Handling**: Graceful degradation and error response formatting
- **Lifecycle Management**: Server startup, shutdown, and resource cleanup

**Implementation Details**:
```python
# server.py:67
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Dynamic tool discovery and registration"""
    return [tool.get_schema() for tool in REGISTERED_TOOLS]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Tool execution with error handling and response formatting"""
```

**Dependencies**:
- `mcp` library for protocol implementation
- `asyncio` for concurrent request processing
- Tool registry for dynamic handler discovery

### 2. Tool Architecture System

**Location**: `tools/` directory
**Purpose**: Modular plugin system for specialized AI capabilities

#### BaseTool Abstract Class (`tools/base.py:25`)

**Interface Contract**:
```python
class BaseTool(ABC):
    @abstractmethod
    async def execute(self, request: dict) -> ToolOutput:
        """Core tool execution logic"""
        
    @abstractmethod
    def get_schema(self) -> types.Tool:
        """MCP tool schema definition"""
        
    def _format_response(self, content: str, metadata: dict) -> ToolOutput:
        """Standardized response formatting"""
```

#### Individual Tool Components

**Chat Tool** (`tools/chat.py:30`)
- **Purpose**: Quick questions and general collaboration
- **Thinking Mode**: Default 'medium' (8192 tokens)
- **Use Cases**: Brainstorming, simple explanations, immediate answers

**ThinkDeep Tool** (`tools/thinkdeep.py:45`)
- **Purpose**: Complex analysis and strategic planning
- **Thinking Mode**: Default 'high' (16384 tokens)
- **Use Cases**: Architecture decisions, design exploration, comprehensive analysis

**CodeReview Tool** (`tools/codereview.py:60`)
- **Purpose**: Code quality and security analysis
- **Thinking Mode**: Default 'medium' (8192 tokens)
- **Use Cases**: Bug detection, security audits, quality validation

**Analyze Tool** (`tools/analyze.py:75`)
- **Purpose**: Codebase exploration and understanding
- **Thinking Mode**: Variable based on scope
- **Use Cases**: Dependency analysis, pattern detection, system comprehension

**Debug Tool** (`tools/debug.py:90`)
- **Purpose**: Error investigation and root cause analysis
- **Thinking Mode**: Default 'medium' (8192 tokens)
- **Use Cases**: Stack trace analysis, bug diagnosis, performance issues

**Precommit Tool** (`tools/precommit.py:105`)
- **Purpose**: Automated quality gates and validation
- **Thinking Mode**: Default 'medium' (8192 tokens)
- **Use Cases**: Pre-commit validation, change analysis, quality assurance

### 3. Security Engine

**Location**: `utils/file_utils.py:45-120`
**Purpose**: Multi-layer security validation and enforcement

#### Security Components

**Path Validation System**:
```python
# utils/file_utils.py:67
def validate_file_path(file_path: str) -> bool:
    """Multi-layer path security validation"""
    # 1. Dangerous path detection
    dangerous_patterns = ['../', '~/', '/etc/', '/var/', '/usr/']
    if any(pattern in file_path for pattern in dangerous_patterns):
        return False
    
    # 2. Absolute path requirement
    if not os.path.isabs(file_path):
        return False
    
    # 3. Sandbox boundary enforcement
    return file_path.startswith(PROJECT_ROOT)
```

**Docker Path Translation**:
```python
# utils/file_utils.py:89
def translate_docker_path(host_path: str) -> str:
    """Convert host paths to container paths for Docker environment"""
    if host_path.startswith(WORKSPACE_ROOT):
        return host_path.replace(WORKSPACE_ROOT, '/workspace', 1)
    return host_path
```

**Security Layers**:
1. **Input Sanitization**: Path cleaning and normalization
2. **Pattern Matching**: Dangerous path detection and blocking
3. **Boundary Enforcement**: PROJECT_ROOT containment validation
4. **Container Translation**: Safe host-to-container path mapping

### 4. Conversation Memory System

**Location**: `utils/conversation_memory.py:30-150`
**Purpose**: Cross-session context preservation and threading

#### Memory Components

**Thread Context Management**:
```python
# utils/conversation_memory.py:45
class ThreadContext:
    thread_id: str
    tool_history: List[ToolExecution]
    conversation_files: Set[str]
    context_tokens: int
    created_at: datetime
    last_accessed: datetime
```

**Redis Integration**:
```python
# utils/conversation_memory.py:78
class ConversationMemory:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def store_thread(self, context: ThreadContext) -> None:
        """Persist conversation thread to Redis"""
    
    async def retrieve_thread(self, thread_id: str) -> Optional[ThreadContext]:
        """Reconstruct conversation from storage"""
    
    async def cleanup_expired_threads(self) -> int:
        """Remove old conversations to manage memory"""
```

**Memory Features**:
- **Thread Persistence**: UUID-based conversation storage
- **Context Reconstruction**: Full conversation history retrieval
- **File Deduplication**: Efficient storage of repeated file references
- **Automatic Cleanup**: Time-based thread expiration

### 5. File Processing Pipeline

**Location**: `utils/file_utils.py:120-200`
**Purpose**: Token-aware file reading and content optimization

#### Processing Components

**Priority System**:
```python
# utils/file_utils.py:134
FILE_PRIORITIES = {
    '.py': 1,    # Python source code (highest priority)
    '.js': 1,    # JavaScript source
    '.ts': 1,    # TypeScript source
    '.md': 2,    # Documentation
    '.txt': 3,   # Text files
    '.log': 4,   # Log files (lowest priority)
}
```

**Token Management**:
```python
# utils/file_utils.py:156
def read_file_with_token_limit(file_path: str, max_tokens: int) -> str:
    """Read file content with token budget enforcement"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Token estimation and truncation
        estimated_tokens = len(content) // 4  # Rough estimation
        if estimated_tokens > max_tokens:
            # Truncate with preservation of structure
            content = content[:max_tokens * 4]
        
        return format_file_content(content, file_path)
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"
```

**Content Formatting**:
- **Line Numbers**: Added for precise code references
- **Error Handling**: Graceful failure with informative messages
- **Structure Preservation**: Maintains code formatting and indentation

### 6. Gemini API Integration

**Location**: `tools/models.py:25-80`
**Purpose**: Standardized interface to Google's Gemini models

#### Integration Components

**API Client**:
```python
# tools/models.py:34
class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-thinking-exp"):
        self.client = genai.GenerativeModel(model)
        self.api_key = api_key
    
    async def generate_response(self, 
                              prompt: str, 
                              thinking_mode: str = 'medium',
                              files: List[str] = None) -> str:
        """Generate response with thinking mode and file context"""
```

**Model Configuration**:
```python
# config.py:24
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-thinking-exp')
MAX_CONTEXT_TOKENS = int(os.getenv('MAX_CONTEXT_TOKENS', '1000000'))
```

**Thinking Mode Management**:
```python
# tools/models.py:67
THINKING_MODE_TOKENS = {
    'minimal': 128,
    'low': 2048,
    'medium': 8192,
    'high': 16384,
    'max': 32768
}
```

## Component Interactions

### 1. Request Processing Flow

```
Claude Request
    ↓
MCP Protocol Engine (server.py:67)
    ↓ (validate & route)
Tool Selection & Loading
    ↓
Security Validation (utils/file_utils.py:67)
    ↓ (if files involved)
File Processing Pipeline (utils/file_utils.py:134)
    ↓
Conversation Context Loading (utils/conversation_memory.py:78)
    ↓ (if continuation_id provided)
Gemini API Integration (tools/models.py:34)
    ↓
Response Processing & Formatting
    ↓
Conversation Storage (utils/conversation_memory.py:78)
    ↓
MCP Response to Claude
```

### 2. Security Integration Points

**Pre-Tool Execution**:
- Path validation before any file operations
- Sandbox boundary enforcement
- Docker path translation for container environments

**During Tool Execution**:
- Token budget enforcement to prevent memory exhaustion
- File access logging and monitoring
- Error containment and graceful degradation

**Post-Tool Execution**:
- Response sanitization
- Conversation storage with access controls
- Resource cleanup and memory management

### 3. Memory System Integration

**Thread Creation**:
```python
# New conversation
thread_id = str(uuid.uuid4())
context = ThreadContext(thread_id=thread_id, ...)
await memory.store_thread(context)
```

**Thread Continuation**:
```python
# Continuing conversation
if continuation_id:
    context = await memory.retrieve_thread(continuation_id)
    # Merge new request with existing context
```

**Cross-Tool Communication**:
```python
# Tool A stores findings
await memory.add_tool_execution(thread_id, tool_execution)

# Tool B retrieves context
context = await memory.retrieve_thread(thread_id)
previous_findings = context.get_tool_outputs('analyze')
```

## Configuration & Dependencies

### Environment Configuration

**Required Settings** (`config.py`):
```python
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Required
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-thinking-exp')
PROJECT_ROOT = os.getenv('PROJECT_ROOT', '/workspace')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
MAX_CONTEXT_TOKENS = int(os.getenv('MAX_CONTEXT_TOKENS', '1000000'))
```

### Component Dependencies

**Core Dependencies**:
- `mcp`: MCP protocol implementation
- `google-generativeai`: Gemini API client
- `redis`: Conversation persistence
- `asyncio`: Concurrent processing

**Security Dependencies**:
- `pathlib`: Path manipulation and validation
- `os`: File system operations and environment access

**Tool Dependencies**:
- `pydantic`: Data validation and serialization
- `typing`: Type hints and contract definition

## Extension Architecture

### Adding New Components

1. **Tool Components**: Inherit from BaseTool and implement required interface
2. **Security Components**: Extend validation chain in file_utils.py
3. **Memory Components**: Add new storage backends via interface abstraction
4. **Processing Components**: Extend file pipeline with new content types

### Integration Patterns

- **Plugin Architecture**: Dynamic discovery and registration
- **Interface Segregation**: Clear contracts between components
- **Dependency Injection**: Configuration-driven component assembly
- **Error Boundaries**: Isolated failure handling per component

---

This component architecture provides a robust foundation for AI collaboration while maintaining security, performance, and extensibility requirements.