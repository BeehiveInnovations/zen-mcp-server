# Testing Strategy & Guidelines

## Overview

This document outlines the comprehensive testing strategy for the Gemini MCP Server project, including unit testing, integration testing, and quality assurance practices that align with CLAUDE.md collaboration patterns.

## Testing Philosophy

### Test-Driven Development (TDD)

**TDD Cycle**:
1. **Red**: Write failing test for new functionality
2. **Green**: Implement minimal code to pass the test
3. **Refactor**: Improve code while maintaining test coverage
4. **Repeat**: Continue cycle for all new features

**Example TDD Flow**:
```python
# 1. Write failing test
def test_chat_tool_should_process_simple_prompt():
    tool = ChatTool()
    result = tool.execute({"prompt": "Hello"})
    assert result.status == "success"
    assert "hello" in result.content.lower()

# 2. Implement minimal functionality
class ChatTool:
    def execute(self, request):
        return ToolOutput(content="Hello!", status="success")

# 3. Refactor and enhance
```

### Testing Pyramid

```
    /\
   /  \     E2E Tests (Few, High-Value)
  /____\    Integration Tests (Some, Key Paths)  
 /______\   Unit Tests (Many, Fast, Isolated)
/________\  
```

**Distribution**:
- **70% Unit Tests**: Fast, isolated, comprehensive coverage
- **20% Integration Tests**: Component interaction validation
- **10% End-to-End Tests**: Complete workflow validation

## Test Categories

### 1. Unit Tests

**Purpose**: Test individual functions and classes in isolation

**Location**: `tests/unit/`

**Example Structure**:
```python
# tests/unit/test_file_utils.py
import pytest
from unittest.mock import Mock, patch, mock_open

from utils.file_utils import validate_file_path, read_file_with_token_limit

class TestFileUtils:
    """Unit tests for file utility functions."""
    
    def test_validate_file_path_with_safe_path(self):
        """Test that safe file paths pass validation."""
        safe_path = "/workspace/tools/chat.py"
        assert validate_file_path(safe_path) is True
    
    def test_validate_file_path_with_traversal_attack(self):
        """Test that directory traversal attempts are blocked."""
        dangerous_path = "/workspace/../../../etc/passwd"
        with pytest.raises(SecurityError):
            validate_file_path(dangerous_path)
    
    @patch('builtins.open', new_callable=mock_open, read_data="test content")
    def test_read_file_with_token_limit(self, mock_file):
        """Test file reading with token budget enforcement."""
        content = read_file_with_token_limit("/test/file.py", max_tokens=100)
        assert "test content" in content
        mock_file.assert_called_once_with("/test/file.py", 'r', encoding='utf-8')
```

**Unit Test Guidelines**:
- **Isolation**: Mock external dependencies (file system, network, database)
- **Fast Execution**: Each test should complete in milliseconds
- **Single Responsibility**: One test per behavior/scenario
- **Descriptive Names**: Test names should describe the scenario and expected outcome

### 2. Integration Tests

**Purpose**: Test component interactions and system integration

**Location**: `tests/integration/`

**Example Structure**:
```python
# tests/integration/test_tool_execution.py
import pytest
import asyncio
from unittest.mock import patch

from server import call_tool
from tools.chat import ChatTool
from utils.conversation_memory import ConversationMemory

class TestToolExecution:
    """Integration tests for tool execution pipeline."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis for conversation memory testing."""
        with patch('redis.Redis') as mock:
            yield mock
    
    @pytest.fixture
    def conversation_memory(self, mock_redis):
        """Create conversation memory with mocked Redis."""
        return ConversationMemory("redis://mock")
    
    async def test_chat_tool_execution_with_memory(self, conversation_memory):
        """Test chat tool execution with conversation memory integration."""
        # Arrange
        request = {
            "name": "chat",
            "arguments": {
                "prompt": "Hello",
                "continuation_id": "test-thread-123"
            }
        }
        
        # Act
        result = await call_tool(request["name"], request["arguments"])
        
        # Assert
        assert len(result) == 1
        assert result[0].type == "text"
        assert "hello" in result[0].text.lower()
    
    async def test_tool_execution_error_handling(self):
        """Test error handling in tool execution pipeline."""
        # Test with invalid tool name
        with pytest.raises(ToolNotFoundError):
            await call_tool("nonexistent_tool", {})
```

**Integration Test Guidelines**:
- **Real Component Interaction**: Test actual component communication
- **Mock External Services**: Mock external APIs (Gemini, Redis) for reliability
- **Error Scenarios**: Test error propagation and handling
- **Async Testing**: Use pytest-asyncio for async code testing

### 3. Live Integration Tests

**Purpose**: Test real API integration with external services

**Location**: `tests/live/`

**Requirements**: 
- Valid `GEMINI_API_KEY` environment variable
- Redis server running (for conversation memory tests)
- Network connectivity

**Example Structure**:
```python
# tests/live/test_gemini_integration.py
import pytest
import os

from tools.chat import ChatTool
from tools.models import GeminiClient

@pytest.mark.live
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="API key required")
class TestGeminiIntegration:
    """Live tests requiring actual Gemini API access."""
    
    def setup_method(self):
        """Set up for live testing."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = GeminiClient(self.api_key)
    
    async def test_basic_gemini_request(self):
        """Test basic Gemini API request/response."""
        response = await self.client.generate_response(
            prompt="Say 'test successful'",
            thinking_mode="minimal"
        )
        assert "test successful" in response.lower()
    
    async def test_chat_tool_with_real_api(self):
        """Test ChatTool with real Gemini API integration."""
        tool = ChatTool()
        result = await tool.execute({
            "prompt": "What is 2+2?",
            "thinking_mode": "minimal"
        })
        
        assert result.status == "success"
        assert "4" in result.content
```

**Live Test Guidelines**:
- **Skip When Unavailable**: Skip if API keys or services unavailable
- **Rate Limiting**: Respect API rate limits with delays
- **Minimal Mode**: Use minimal thinking mode for speed
- **Cleanup**: Clean up any created resources

### 4. Security Tests

**Purpose**: Validate security measures and vulnerability prevention

**Location**: `tests/security/`

**Example Structure**:
```python
# tests/security/test_path_validation.py
import pytest

from utils.file_utils import validate_file_path
from exceptions import SecurityError

class TestSecurityValidation:
    """Security-focused tests for input validation."""
    
    @pytest.mark.parametrize("dangerous_path", [
        "../../../etc/passwd",
        "/etc/shadow", 
        "~/../../root/.ssh/id_rsa",
        "/var/log/auth.log",
        "\\..\\..\\windows\\system32\\config\\sam"
    ])
    def test_dangerous_path_rejection(self, dangerous_path):
        """Test that dangerous file paths are rejected."""
        with pytest.raises(SecurityError):
            validate_file_path(dangerous_path)
    
    def test_secret_sanitization_in_logs(self):
        """Test that sensitive data is sanitized in log output."""
        request_data = {
            "prompt": "Hello",
            "api_key": "sk-secret123",
            "token": "bearer-token-456"
        }
        
        sanitized = sanitize_for_logging(request_data)
        
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"
        assert sanitized["prompt"] == "Hello"  # Non-sensitive data preserved
```

## Test Configuration

### pytest Configuration

**pytest.ini**:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --disable-warnings
    --cov=tools
    --cov=utils
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (component interaction)
    live: Live tests requiring API keys and external services
    security: Security-focused tests
    slow: Tests that take more than 1 second
```

**conftest.py**:
```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import Mock, patch

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing without API calls."""
    with patch('tools.models.GeminiClient') as mock:
        mock_instance = Mock()
        mock_instance.generate_response.return_value = "Mocked response"
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing without Redis server."""
    with patch('redis.Redis') as mock:
        yield mock

@pytest.fixture
def sample_file_content():
    """Sample file content for testing file processing."""
    return """
def example_function():
    # This is a sample function
    return "hello world"

class ExampleClass:
    def method(self):
        pass
"""

@pytest.fixture
def temp_project_directory(tmp_path):
    """Create temporary project directory structure for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create subdirectories
    (project_dir / "tools").mkdir()
    (project_dir / "utils").mkdir()
    (project_dir / "tests").mkdir()
    
    # Create sample files
    (project_dir / "tools" / "sample.py").write_text("# Sample tool")
    (project_dir / "utils" / "helper.py").write_text("# Helper utility")
    
    return project_dir
```

## Test Data Management

### Test Fixtures

**File-based Fixtures**:
```python
# tests/fixtures/sample_code.py
PYTHON_CODE_SAMPLE = '''
import asyncio
from typing import Dict, List

async def process_data(items: List[str]) -> Dict[str, int]:
    """Process a list of items and return counts."""
    result = {}
    for item in items:
        result[item] = len(item)
    return result
'''

JAVASCRIPT_CODE_SAMPLE = '''
async function processData(items) {
    const result = {};
    for (const item of items) {
        result[item] = item.length;
    }
    return result;
}
'''

ERROR_LOGS_SAMPLE = '''
2025-01-11 23:45:12 ERROR [tool_execution] Tool 'analyze' failed: File not found
Traceback (most recent call last):
  File "/app/tools/analyze.py", line 45, in execute
    content = read_file(file_path)
  File "/app/utils/file_utils.py", line 23, in read_file
    with open(file_path, 'r') as f:
FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/file.py'
'''
```

### Mock Data Factories

**ToolOutput Factory**:
```python
# tests/factories.py
from dataclasses import dataclass
from typing import Dict, Any, List

def create_tool_output(
    content: str = "Default response",
    status: str = "success",
    metadata: Dict[str, Any] = None,
    files_processed: List[str] = None
) -> ToolOutput:
    """Factory for creating ToolOutput test instances."""
    return ToolOutput(
        content=content,
        metadata=metadata or {},
        files_processed=files_processed or [],
        status=status
    )

def create_thread_context(
    thread_id: str = "test-thread-123",
    files: List[str] = None
) -> ThreadContext:
    """Factory for creating ThreadContext test instances."""
    return ThreadContext(
        thread_id=thread_id,
        conversation_files=set(files or []),
        tool_history=[],
        context_tokens=0
    )
```

## Mocking Strategies

### External Service Mocking

**Gemini API Mocking**:
```python
class MockGeminiClient:
    """Mock Gemini client for testing."""
    
    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {
            "default": "This is a mocked response from Gemini"
        }
        self.call_count = 0
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Mock response generation."""
        self.call_count += 1
        
        # Return specific response for specific prompts
        for key, response in self.responses.items():
            if key in prompt.lower():
                return response
        
        return self.responses.get("default", "Mock response")

# Usage in tests
@patch('tools.models.GeminiClient', MockGeminiClient)
def test_with_mocked_gemini():
    # Test implementation
    pass
```

**File System Mocking**:
```python
@patch('builtins.open', mock_open(read_data="file content"))
@patch('os.path.exists', return_value=True)
@patch('os.path.getsize', return_value=1024)
def test_file_operations():
    """Test file operations with mocked file system."""
    content = read_file("/mocked/file.py")
    assert content == "file content"
```

## Performance Testing

### Load Testing

**Concurrent Tool Execution**:
```python
# tests/performance/test_load.py
import asyncio
import pytest
import time

@pytest.mark.slow
class TestPerformance:
    """Performance tests for system load handling."""
    
    async def test_concurrent_tool_execution(self):
        """Test system performance under concurrent load."""
        start_time = time.time()
        
        # Create 10 concurrent tool execution tasks
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                call_tool("chat", {"prompt": f"Request {i}"})
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify all requests succeeded
        assert len(results) == 10
        assert all(len(result) == 1 for result in results)
        
        # Performance assertion (adjust based on requirements)
        assert execution_time < 30.0  # All requests should complete within 30s
    
    async def test_memory_usage_stability(self):
        """Test that memory usage remains stable under load."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Execute multiple operations
        for i in range(100):
            await call_tool("chat", {"prompt": f"Memory test {i}"})
            
            # Force garbage collection periodically
            if i % 10 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (adjust threshold as needed)
        assert memory_growth < 100 * 1024 * 1024  # Less than 100MB growth
```

## Test Execution

### Running Tests

**Basic Test Execution**:
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m "not live"             # All tests except live tests
pytest -m "live and not slow"    # Live tests that are fast

# Run with coverage
pytest --cov=tools --cov=utils --cov-report=html

# Run specific test file
pytest tests/unit/test_file_utils.py -v

# Run specific test method
pytest tests/unit/test_file_utils.py::TestFileUtils::test_validate_file_path -v
```

**Continuous Integration**:
```bash
# CI test script
#!/bin/bash
set -e

echo "Running unit tests..."
pytest -m unit --cov=tools --cov=utils --cov-fail-under=80

echo "Running integration tests..."
pytest -m integration

echo "Running security tests..."
pytest -m security

echo "Checking code quality..."
flake8 tools/ utils/ tests/
mypy tools/ utils/

echo "All tests passed!"
```

### Test Reports

**Coverage Reports**:
```bash
# Generate HTML coverage report
pytest --cov=tools --cov=utils --cov-report=html
open htmlcov/index.html

# Generate terminal coverage report
pytest --cov=tools --cov=utils --cov-report=term-missing
```

**Test Results Export**:
```bash
# Export test results to JUnit XML (for CI integration)
pytest --junitxml=test-results.xml

# Export test results with timing information
pytest --durations=10  # Show 10 slowest tests
```

## Quality Metrics

### Coverage Targets

**Minimum Coverage Requirements**:
- **Overall Coverage**: 80%
- **Critical Modules**: 90% (security, file_utils, conversation_memory)
- **Tool Modules**: 85%
- **Utility Modules**: 80%

**Coverage Enforcement**:
```bash
# Fail build if coverage drops below threshold
pytest --cov-fail-under=80
```

### Test Quality Metrics

**Test Suite Characteristics**:
- **Fast Execution**: Unit test suite should complete in <30 seconds
- **Reliable**: Tests should have <1% flaky failure rate
- **Maintainable**: Test code should follow same quality standards as production code
- **Comprehensive**: All critical paths and edge cases covered

## Integration with Development Workflow

### Pre-commit Testing

**Git Hook Integration**:
```bash
#!/bin/sh
# .git/hooks/pre-commit

echo "Running pre-commit tests..."

# Run fast tests before commit
pytest -m "unit and not slow" --cov-fail-under=80

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit blocked."
    exit 1
fi

echo "Pre-commit tests passed."
```

### CI/CD Integration

**GitHub Actions Workflow**:
```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run unit tests
        run: pytest -m unit --cov=tools --cov=utils --cov-fail-under=80
      
      - name: Run integration tests
        run: pytest -m integration
      
      - name: Run security tests
        run: pytest -m security
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

This comprehensive testing strategy ensures high-quality, reliable code while maintaining development velocity and supporting the collaborative patterns defined in CLAUDE.md.