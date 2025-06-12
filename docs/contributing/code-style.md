# Code Style Guide

## Overview

This document establishes coding standards and style guidelines for the Gemini MCP Server project. Consistent code style improves readability, maintainability, and collaboration efficiency.

## Python Style Guidelines

### PEP 8 Compliance

**Base Standard**: Follow [PEP 8](https://peps.python.org/pep-0008/) as the foundation for all Python code.

**Automated Formatting**: Use Black formatter with default settings:
```bash
black tools/ utils/ tests/ --line-length 88
```

**Line Length**: 88 characters (Black default)
```python
# Good
result = some_function_with_long_name(
    parameter_one, parameter_two, parameter_three
)

# Avoid
result = some_function_with_long_name(parameter_one, parameter_two, parameter_three)
```

### Import Organization

**Import Order** (enforced by isort):
```python
# 1. Standard library imports
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# 2. Third-party imports
import redis
from pydantic import BaseModel

# 3. Local application imports
from tools.base import BaseTool
from utils.file_utils import validate_file_path
```

**Import Formatting**:
```python
# Good - Explicit imports
from typing import Dict, List, Optional
from utils.conversation_memory import ThreadContext, ConversationMemory

# Avoid - Wildcard imports
from utils.conversation_memory import *
```

### Naming Conventions

**Functions and Variables**: snake_case
```python
def process_file_content(file_path: str) -> str:
    context_tokens = calculate_token_count(content)
    return formatted_content
```

**Classes**: PascalCase
```python
class GeminiClient:
    pass

class ThreadContext:
    pass
```

**Constants**: UPPER_SNAKE_CASE
```python
MAX_CONTEXT_TOKENS = 1000000
THINKING_MODE_TOKENS = {
    'minimal': 128,
    'low': 2048,
    'medium': 8192
}
```

**Private Methods**: Leading underscore
```python
class ToolBase:
    def execute(self):
        return self._process_internal_logic()
    
    def _process_internal_logic(self):
        # Private implementation
        pass
```

## Type Hints

### Mandatory Type Hints

**Function Signatures**: Always include type hints
```python
# Good
def validate_file_path(file_path: str) -> bool:
    return os.path.exists(file_path)

async def process_request(request: dict) -> ToolOutput:
    # Implementation
    pass

# Avoid
def validate_file_path(file_path):
    return os.path.exists(file_path)
```

**Complex Types**: Use typing module
```python
from typing import Dict, List, Optional, Union, Any

def process_files(files: List[str]) -> Dict[str, Any]:
    return {"processed": files}

def get_config(key: str) -> Optional[str]:
    return os.getenv(key)
```

**Generic Types**: Use TypeVar for reusable generics
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Repository(Generic[T]):
    def get(self, id: str) -> Optional[T]:
        # Implementation
        pass
```

## Documentation Standards

### Docstring Format

**Use Google Style** docstrings:
```python
def execute_tool(name: str, arguments: dict, context: Optional[str] = None) -> ToolOutput:
    """Execute a tool with given arguments and context.
    
    Args:
        name: The name of the tool to execute
        arguments: Tool-specific parameters and configuration
        context: Optional conversation context for threading
        
    Returns:
        ToolOutput containing the execution result and metadata
        
    Raises:
        ToolNotFoundError: If the specified tool doesn't exist
        ValidationError: If arguments don't match tool schema
        
    Example:
        >>> output = execute_tool("chat", {"prompt": "Hello"})
        >>> print(output.content)
        "Hello! How can I help you today?"
    """
    # Implementation
    pass
```

**Class Documentation**:
```python
class ConversationMemory:
    """Manages conversation threading and context persistence.
    
    This class handles storing and retrieving conversation contexts
    using Redis as the backend storage. It supports thread-based
    organization and automatic cleanup of expired conversations.
    
    Attributes:
        redis_client: Redis connection for storage operations
        default_ttl: Default time-to-live for conversation threads
        
    Example:
        >>> memory = ConversationMemory("redis://localhost:6379")
        >>> context = ThreadContext("thread-123")
        >>> await memory.store_thread(context)
    """
    
    def __init__(self, redis_url: str, default_ttl: int = 86400):
        """Initialize conversation memory with Redis connection.
        
        Args:
            redis_url: Redis connection string
            default_ttl: Default TTL in seconds (default: 24 hours)
        """
        pass
```

### Inline Comments

**When to Comment**:
```python
# Good - Explain complex business logic
def calculate_token_budget(files: List[str], total_budget: int) -> Dict[str, int]:
    # Priority 1 files (source code) get 60% of budget
    priority_1_budget = int(total_budget * 0.6)
    
    # Group files by priority based on extension
    priority_groups = defaultdict(list)
    for file in files:
        ext = Path(file).suffix.lower()
        priority = FILE_PRIORITIES.get(ext, 4)
        priority_groups[priority].append(file)
    
    return allocate_budget_by_priority(priority_groups, total_budget)

# Avoid - Stating the obvious
def get_file_size(file_path: str) -> int:
    # Get the size of the file
    return os.path.getsize(file_path)
```

**Security and Performance Notes**:
```python
def validate_file_path(file_path: str) -> bool:
    # Security: Prevent directory traversal attacks
    if '..' in file_path or file_path.startswith('/etc/'):
        return False
    
    # Performance: Early return for non-existent files
    if not os.path.exists(file_path):
        return False
        
    return True
```

## Error Handling

### Exception Handling Patterns

**Specific Exceptions**:
```python
# Good - Specific exception handling
try:
    with open(file_path, 'r') as f:
        content = f.read()
except FileNotFoundError:
    logger.warning(f"File not found: {file_path}")
    return None
except PermissionError:
    logger.error(f"Permission denied: {file_path}")
    raise SecurityError(f"Access denied to {file_path}")
except UnicodeDecodeError:
    logger.warning(f"Encoding error in {file_path}")
    return f"Error: Cannot decode file {file_path}"

# Avoid - Bare except clauses
try:
    content = f.read()
except:
    return None
```

**Custom Exceptions**:
```python
class GeminiMCPError(Exception):
    """Base exception for Gemini MCP Server errors."""
    pass

class ToolNotFoundError(GeminiMCPError):
    """Raised when a requested tool is not found."""
    pass

class ValidationError(GeminiMCPError):
    """Raised when input validation fails."""
    pass
```

### Logging Standards

**Logging Levels**:
```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: Detailed diagnostic information
logger.debug(f"Processing file: {file_path}, size: {file_size}")

# INFO: General operational information  
logger.info(f"Tool '{tool_name}' executed successfully")

# WARNING: Something unexpected but recoverable
logger.warning(f"File {file_path} exceeds recommended size limit")

# ERROR: Error condition but application continues
logger.error(f"Failed to process file {file_path}: {str(e)}")

# CRITICAL: Serious error, application may not continue
logger.critical(f"Redis connection failed: {connection_error}")
```

**Structured Logging**:
```python
# Good - Structured logging with context
logger.info(
    "Tool execution completed",
    extra={
        "tool_name": tool_name,
        "execution_time": execution_time,
        "files_processed": len(files),
        "thinking_mode": thinking_mode
    }
)

# Avoid - Unstructured string formatting
logger.info(f"Tool {tool_name} took {execution_time}s to process {len(files)} files")
```

## Async/Await Patterns

### Async Function Design

**Async When Needed**:
```python
# Good - I/O operations should be async
async def fetch_gemini_response(prompt: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(GEMINI_API_URL, json=payload) as response:
            return await response.text()

# Good - CPU-bound work remains sync
def parse_stack_trace(trace_text: str) -> List[StackFrame]:
    # CPU-intensive parsing logic
    return parsed_frames
```

**Async Context Managers**:
```python
class AsyncRedisClient:
    async def __aenter__(self):
        self.connection = await redis.connect(self.url)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.connection.close()

# Usage
async with AsyncRedisClient(redis_url) as client:
    await client.store_data(key, value)
```

## Security Best Practices

### Input Validation

**Path Validation**:
```python
def validate_file_path(file_path: str) -> bool:
    """Validate file path for security and accessibility."""
    # Convert to absolute path
    abs_path = os.path.abspath(file_path)
    
    # Check for directory traversal
    if not abs_path.startswith(PROJECT_ROOT):
        raise SecurityError(f"Path outside project root: {abs_path}")
    
    # Check for dangerous patterns
    dangerous_patterns = ['../', '~/', '/etc/', '/var/']
    if any(pattern in file_path for pattern in dangerous_patterns):
        raise SecurityError(f"Dangerous path pattern detected: {file_path}")
    
    return True
```

**Data Sanitization**:
```python
def sanitize_user_input(user_input: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    # Remove null bytes
    sanitized = user_input.replace('\x00', '')
    
    # Limit length
    if len(sanitized) > MAX_INPUT_LENGTH:
        sanitized = sanitized[:MAX_INPUT_LENGTH]
    
    # Remove control characters
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
    
    return sanitized
```

### Secret Management

**Environment Variables**:
```python
# Good - Environment variable with validation
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ConfigurationError("GEMINI_API_KEY environment variable required")

# Avoid - Hardcoded secrets
API_KEY = "sk-1234567890abcdef"  # Never do this
```

**Secret Logging Prevention**:
```python
def log_request_safely(request_data: dict) -> None:
    """Log request data while excluding sensitive fields."""
    safe_data = request_data.copy()
    
    # Remove sensitive fields
    sensitive_fields = ['api_key', 'token', 'password', 'secret']
    for field in sensitive_fields:
        if field in safe_data:
            safe_data[field] = '[REDACTED]'
    
    logger.info(f"Processing request: {safe_data}")
```

## Performance Guidelines

### Memory Management

**Generator Usage**:
```python
# Good - Memory efficient for large datasets
def process_large_file(file_path: str) -> Generator[str, None, None]:
    with open(file_path, 'r') as f:
        for line in f:
            yield process_line(line)

# Avoid - Loading entire file into memory
def process_large_file(file_path: str) -> List[str]:
    with open(file_path, 'r') as f:
        return [process_line(line) for line in f.readlines()]
```

**Context Managers**:
```python
# Good - Automatic resource cleanup
class FileProcessor:
    def __enter__(self):
        self.temp_files = []
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup temporary files
        for temp_file in self.temp_files:
            os.unlink(temp_file)
```

### Caching Patterns

**LRU Cache for Expensive Operations**:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def parse_file_content(file_path: str, file_hash: str) -> str:
    """Parse file content with caching based on file hash."""
    with open(file_path, 'r') as f:
        return expensive_parsing_operation(f.read())
```

## Testing Standards

### Test File Organization

**Test Structure**:
```python
# tests/test_tools.py
import pytest
from unittest.mock import Mock, patch

from tools.chat import ChatTool
from tools.models import ToolOutput

class TestChatTool:
    """Test suite for ChatTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.chat_tool = ChatTool()
        self.mock_gemini_client = Mock()
    
    def test_basic_chat_execution(self):
        """Test basic chat tool execution with simple prompt."""
        # Arrange
        request = {"prompt": "Hello"}
        
        # Act
        result = self.chat_tool.execute(request)
        
        # Assert
        assert isinstance(result, ToolOutput)
        assert result.status == "success"
    
    @patch('tools.chat.GeminiClient')
    def test_chat_with_mocked_api(self, mock_client):
        """Test chat tool with mocked Gemini API responses."""
        # Test implementation
        pass
```

### Test Naming Conventions

**Test Method Names**:
```python
def test_should_validate_file_path_when_path_is_safe():
    """Test that safe file paths are correctly validated."""
    pass

def test_should_raise_security_error_when_path_contains_traversal():
    """Test that directory traversal attempts raise SecurityError."""
    pass

def test_should_return_none_when_file_not_found():
    """Test that missing files return None gracefully."""
    pass
```

## Configuration Management

### Environment-Based Configuration

**Configuration Class**:
```python
class Config:
    """Application configuration with validation."""
    
    def __init__(self):
        self.gemini_api_key = self._require_env('GEMINI_API_KEY')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.project_root = os.getenv('PROJECT_ROOT', '/workspace')
        self.max_context_tokens = int(os.getenv('MAX_CONTEXT_TOKENS', '1000000'))
        
        # Validate configuration
        self._validate_configuration()
    
    def _require_env(self, key: str) -> str:
        """Require environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(f"Required environment variable: {key}")
        return value
    
    def _validate_configuration(self) -> None:
        """Validate configuration values."""
        if not os.path.exists(self.project_root):
            raise ConfigurationError(f"PROJECT_ROOT not found: {self.project_root}")
```

## Pre-commit Hooks

### Automated Quality Checks

**Required Tools**:
```bash
# Install development dependencies
pip install black isort flake8 mypy pytest

# Format code
black tools/ utils/ tests/
isort tools/ utils/ tests/

# Check code quality
flake8 tools/ utils/ tests/
mypy tools/ utils/

# Run tests
pytest tests/ -v --cov=tools --cov=utils
```

**Pre-commit Configuration** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
```

---

Following these code style guidelines ensures consistent, maintainable, and secure code across the Gemini MCP Server project. All team members should adhere to these standards and use the automated tools to enforce compliance.

