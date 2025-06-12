# MCP Protocol Implementation

## Overview

The Gemini MCP Server implements the Model Context Protocol (MCP) specification, providing Claude with standardized access to Google's Gemini AI models through a secure, tool-based interface.

## Protocol Specification

### MCP Version
- **Implemented Version**: MCP v1.0
- **Transport**: stdio (standard input/output)
- **Serialization**: JSON-RPC 2.0
- **Authentication**: Environment-based API key management

### Core Protocol Flow

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "chat",
        "description": "Quick questions and general collaboration",
        "inputSchema": {
          "type": "object",
          "properties": {
            "prompt": {"type": "string"},
            "continuation_id": {"type": "string", "optional": true}
          },
          "required": ["prompt"]
        }
      }
    ]
  }
}
```

## Tool Registration System

### Tool Discovery (`server.py:67`)

```python
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Dynamic tool discovery and registration"""
    tools = []
    
    # Scan tools directory for available tools
    for tool_module in REGISTERED_TOOLS:
        tool_instance = tool_module()
        schema = tool_instance.get_schema()
        tools.append(schema)
    
    return tools
```

### Tool Schema Definition

Each tool must implement a standardized schema:

```python
def get_schema(self) -> types.Tool:
    return types.Tool(
        name="analyze",
        description="Code exploration and understanding",
        inputSchema={
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files or directories to analyze"
                },
                "question": {
                    "type": "string", 
                    "description": "What to analyze or look for"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["architecture", "performance", "security", "quality", "general"],
                    "default": "general"
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "default": "medium"
                },
                "continuation_id": {
                    "type": "string",
                    "description": "Thread continuation ID for multi-turn conversations"
                }
            },
            "required": ["files", "question"]
        }
    )
```

## Tool Execution Protocol

### Request Processing (`server.py:89`)

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Tool execution with comprehensive error handling"""
    
    try:
        # 1. Tool validation
        tool_class = TOOL_REGISTRY.get(name)
        if not tool_class:
            raise ToolNotFoundError(f"Tool '{name}' not found")
        
        # 2. Parameter validation
        tool_instance = tool_class()
        validated_args = tool_instance.validate_parameters(arguments)
        
        # 3. Security validation
        if 'files' in validated_args:
            validated_args['files'] = validate_file_paths(validated_args['files'])
        
        # 4. Tool execution
        result = await tool_instance.execute(validated_args)
        
        # 5. Response formatting
        return [types.TextContent(
            type="text",
            text=result.content
        )]
        
    except Exception as e:
        # Error response with context
        error_response = format_error_response(e, name, arguments)
        return [types.TextContent(
            type="text", 
            text=error_response
        )]
```

### Response Standardization

All tools return standardized `ToolOutput` objects:

```python
@dataclass
class ToolOutput:
    content: str
    metadata: Dict[str, Any]
    continuation_id: Optional[str] = None
    files_processed: List[str] = field(default_factory=list)
    thinking_tokens_used: int = 0
    status: str = "success"  # success, partial, error
    
    def to_mcp_response(self) -> str:
        """Convert to MCP-compatible response format"""
        response_parts = [self.content]
        
        if self.metadata:
            response_parts.append("\n## Metadata")
            for key, value in self.metadata.items():
                response_parts.append(f"- {key}: {value}")
        
        if self.files_processed:
            response_parts.append("\n## Files Processed")
            for file_path in self.files_processed:
                response_parts.append(f"- {file_path}")
        
        if self.continuation_id:
            response_parts.append(f"\n## Continuation ID: {self.continuation_id}")
        
        return '\n'.join(response_parts)
```

## Individual Tool APIs

### 1. Chat Tool

**Purpose**: Quick questions, brainstorming, general discussion

**API Specification**:
```json
{
  "name": "chat",
  "parameters": {
    "prompt": "string (required)",
    "continuation_id": "string (optional)",
    "temperature": "number (optional, 0.0-1.0, default: 0.5)",
    "thinking_mode": "string (optional, default: 'medium')"
  }
}
```

**Example Request**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "chat",
    "arguments": {
      "prompt": "Explain the benefits of using MCP protocol",
      "thinking_mode": "low"
    }
  }
}
```

**Response Format**:
```json
{
  "result": [{
    "type": "text",
    "text": "The Model Context Protocol (MCP) provides several key benefits:\n\n1. **Standardization**: Unified interface across different AI tools...\n\n## Metadata\n- thinking_mode: low\n- tokens_used: 156\n- response_time: 1.2s"
  }]
}
```

### 2. ThinkDeep Tool

**Purpose**: Complex architecture, system design, strategic planning

**API Specification**:
```json
{
  "name": "thinkdeep", 
  "parameters": {
    "current_analysis": "string (required)",
    "problem_context": "string (optional)",
    "focus_areas": "array of strings (optional)",
    "thinking_mode": "string (optional, default: 'high')",
    "files": "array of strings (optional)",
    "continuation_id": "string (optional)"
  }
}
```

**Example Request**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "thinkdeep",
    "arguments": {
      "current_analysis": "We have an MCP server with 6 specialized tools",
      "problem_context": "Need to scale to handle 100+ concurrent Claude sessions",
      "focus_areas": ["performance", "architecture", "resource_management"],
      "thinking_mode": "max"
    }
  }
}
```

### 3. Analyze Tool

**Purpose**: Code exploration, understanding existing systems

**API Specification**:
```json
{
  "name": "analyze",
  "parameters": {
    "files": "array of strings (required)",
    "question": "string (required)", 
    "analysis_type": "enum: architecture|performance|security|quality|general",
    "thinking_mode": "string (optional, default: 'medium')",
    "continuation_id": "string (optional)"
  }
}
```

**File Processing Behavior**:
- **Directories**: Recursively scanned for relevant files
- **Token Budget**: Allocated based on file priority (source code > docs > logs)
- **Security**: All paths validated and sandboxed to PROJECT_ROOT
- **Formatting**: Line numbers added for precise code references

### 4. CodeReview Tool

**Purpose**: Code quality, security, bug detection

**API Specification**:
```json
{
  "name": "codereview",
  "parameters": {
    "files": "array of strings (required)",
    "context": "string (required)",
    "review_type": "enum: full|security|performance|quick (default: full)",
    "severity_filter": "enum: critical|high|medium|all (default: all)", 
    "standards": "string (optional)",
    "thinking_mode": "string (optional, default: 'medium')"
  }
}
```

**Response Includes**:
- **Issue Categorization**: Critical → High → Medium → Low
- **Specific Fixes**: Concrete code suggestions with line numbers
- **Security Assessment**: Vulnerability detection and mitigation
- **Performance Analysis**: Optimization opportunities

### 5. Debug Tool

**Purpose**: Root cause analysis, error investigation

**API Specification**:
```json
{
  "name": "debug",
  "parameters": {
    "error_description": "string (required)",
    "error_context": "string (optional)", 
    "files": "array of strings (optional)",
    "previous_attempts": "string (optional)",
    "runtime_info": "string (optional)",
    "thinking_mode": "string (optional, default: 'medium')"
  }
}
```

**Diagnostic Capabilities**:
- **Stack Trace Analysis**: Multi-language error parsing
- **Root Cause Identification**: Systematic error investigation
- **Reproduction Steps**: Detailed debugging procedures
- **Fix Recommendations**: Prioritized solution approaches

### 6. Precommit Tool

**Purpose**: Automated quality gates, validation before commits

**API Specification**:
```json
{
  "name": "precommit",
  "parameters": {
    "path": "string (required, git repository root)",
    "include_staged": "boolean (default: true)",
    "include_unstaged": "boolean (default: true)",
    "review_type": "enum: full|security|performance|quick (default: full)",
    "original_request": "string (optional, user's intent)",
    "thinking_mode": "string (optional, default: 'medium')"
  }
}
```

**Validation Process**:
1. **Git Analysis**: Staged/unstaged changes detection
2. **Quality Review**: Comprehensive code analysis
3. **Security Scan**: Vulnerability and secret detection  
4. **Documentation Check**: Ensures docs match code changes
5. **Test Validation**: Recommends testing strategies
6. **Commit Readiness**: Go/no-go recommendation

## Error Handling & Status Codes

### Standard Error Responses

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "validation_errors": [
        {
          "field": "files",
          "error": "Path outside sandbox: /etc/passwd"
        }
      ]
    }
  }
}
```

### Error Categories

**Security Errors** (Code: -32001):
- Path traversal attempts
- Unauthorized file access
- Sandbox boundary violations

**Validation Errors** (Code: -32602):
- Missing required parameters
- Invalid parameter types
- Schema validation failures

**Tool Errors** (Code: -32603):
- Tool execution failures
- Gemini API errors
- Resource exhaustion

**System Errors** (Code: -32000):
- Redis connection failures
- File system errors
- Configuration issues

## Performance & Limits

### Request Limits

- **Maximum File Size**: 10MB per file
- **Maximum Files**: 50 files per request
- **Token Budget**: 1M tokens total context
- **Thinking Tokens**: 32K maximum per tool
- **Request Timeout**: 300 seconds

### Rate Limiting

```python
# Per-client rate limiting (future implementation)
RATE_LIMITS = {
    'chat': '10/minute',
    'analyze': '5/minute', 
    'thinkdeep': '3/minute',
    'codereview': '5/minute',
    'debug': '5/minute',
    'precommit': '3/minute'
}
```

### Optimization Features

- **File Deduplication**: Avoid reprocessing same files across conversation
- **Context Caching**: Redis-based conversation persistence
- **Priority Processing**: Source code files processed first
- **Concurrent Execution**: AsyncIO-based parallel processing

## Security Considerations

### Authentication
- **API Key**: Gemini API key via environment variable
- **No User Auth**: Runs in trusted Claude Desktop environment
- **Local Only**: No network exposure beyond Gemini API

### Data Protection
- **Sandbox Enforcement**: PROJECT_ROOT boundary enforcement
- **Path Validation**: Multi-layer dangerous path detection
- **Response Sanitization**: Automatic sensitive data removal
- **Temporary Storage**: Redis with TTL-based cleanup

### Access Controls
- **Read-Only Default**: Most operations are read-only
- **Explicit Write Gates**: Write operations require explicit confirmation
- **Docker Isolation**: Container-based runtime isolation

---

This MCP protocol implementation provides a secure, performant, and extensible foundation for AI-assisted development workflows while maintaining compatibility with Claude's expectations and requirements.
