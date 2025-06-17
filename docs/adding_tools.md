# Adding a New Tool to Zen MCP Server

This guide provides step-by-step instructions for adding new tools to the Zen MCP Server. Tools are specialized interfaces that let Claude interact with AI models for specific tasks like code review, debugging, consensus gathering, and more.

## Quick Overview

Every tool must:
- Inherit from `BaseTool` and implement 6 abstract methods
- Define a Pydantic request model for validation
- Create a system prompt in `systemprompts/`
- Register in `server.py`
- Handle file/image inputs and conversation threading

**Key Features**: Automatic conversation threading, file deduplication, token management, model-specific capabilities, web search integration, and comprehensive error handling.

## Core Architecture

### Components
1. **BaseTool** (`tools/base.py`): Abstract base with conversation memory, file handling, and model management
2. **Request Models**: Pydantic validation with common fields (model, temperature, thinking_mode, continuation_id, images, use_websearch)
3. **System Prompts**: AI behavior configuration with placeholders for dynamic content
4. **Model Context**: Automatic provider resolution and token allocation

### Execution Flow
1. **MCP Boundary**: Parameter validation, file security checks, image validation
2. **Model Resolution**: Automatic provider selection and capability checking  
3. **Conversation Context**: History reconstruction and file deduplication
4. **Prompt Preparation**: System prompt + user content + file content + conversation history
5. **AI Generation**: Provider-agnostic model calls with retry logic
6. **Response Processing**: Format output, offer continuation, store in conversation memory

## Step-by-Step Implementation Guide

### 1. Create the Tool File

Create `tools/example.py` with proper imports and structure:

```python
"""
Example tool - Intelligent code analysis and recommendations

This tool provides comprehensive code analysis including style, performance, 
and maintainability recommendations for development teams.
"""

from typing import TYPE_CHECKING, Any, Optional
from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_BALANCED
from systemprompts import EXAMPLE_PROMPT  # You'll create this

from .base import BaseTool, ToolRequest

# No need to import ToolOutput or logging - handled by base class
```

**Key Points:**
- Use `TYPE_CHECKING` import for ToolModelCategory to avoid circular imports
- Import temperature constants from `config.py`
- System prompt imported from `systemprompts/`
- Base class handles all common functionality

### 2. Define the Request Model

Create a Pydantic model inheriting from `ToolRequest`:

```python
class ExampleRequest(ToolRequest):
    """Request model for example tool."""
    
    # Required field - main user input
    prompt: str = Field(
        ...,
        description=(
            "Detailed description of the code analysis needed. Include specific areas "
            "of concern, goals, and any constraints. The more context provided, "
            "the more targeted and valuable the analysis will be."
        )
    )
    
    # Optional file input with proper default
    files: Optional[list[str]] = Field(
        default_factory=list,  # Use factory for mutable defaults
        description="Code files to analyze (must be absolute paths)"
    )
    
    # Tool-specific parameters
    analysis_depth: Optional[str] = Field(
        default="standard",
        description="Analysis depth: 'quick', 'standard', or 'comprehensive'"
    )
    
    focus_areas: Optional[list[str]] = Field(
        default_factory=list,
        description="Specific areas to focus on (e.g., 'performance', 'security', 'maintainability')"
    )
    
    # Images field inherited from ToolRequest - no need to redefine
    # use_websearch field inherited from ToolRequest - no need to redefine
    # continuation_id field inherited from ToolRequest - no need to redefine
```

**Key Points:**
- Use `default_factory=list` for mutable defaults (not `default=None`)
- Common fields (images, use_websearch, continuation_id, model, temperature) are inherited
- Detailed descriptions help Claude understand when/how to use parameters
- Focus on tool-specific parameters only

### 3. Implement the Tool Class

Implement the 6 required abstract methods:

```python
class ExampleTool(BaseTool):
    """Intelligent code analysis and recommendations tool."""
    
    def get_name(self) -> str:
        """Return unique tool identifier (used by MCP clients)."""
        return "example"
    
    def get_description(self) -> str:
        """Return detailed description to help Claude understand when to use this tool."""
        return (
            "CODE ANALYSIS & RECOMMENDATIONS - Provides comprehensive code analysis including "
            "style improvements, performance optimizations, and maintainability suggestions. "
            "Perfect for: code reviews, refactoring planning, performance analysis, best practices "
            "validation. Supports multi-file analysis with focus areas. Use 'comprehensive' analysis "
            "for complex codebases, 'standard' for regular reviews, 'quick' for simple checks."
        )
    
    def get_input_schema(self) -> dict[str, Any]:
        """Generate JSON schema - inherit common fields from base class."""
        schema = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed description of the code analysis needed. Include specific areas "
                        "of concern, goals, and any constraints."
                    ),
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Code files to analyze (must be absolute paths)",
                },
                "analysis_depth": {
                    "type": "string",
                    "enum": ["quick", "standard", "comprehensive"],
                    "description": "Analysis depth level",
                    "default": "standard",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific areas to focus on (e.g., 'performance', 'security')",
                },
                # Common fields added automatically by base class
                "model": self.get_model_field_schema(),
                "temperature": {
                    "type": "number",
                    "description": "Response creativity (0-1, default varies by tool)",
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth: minimal (0.5% of model max), low (8%), medium (33%), high (67%), max (100%)",
                },
                "use_websearch": {
                    "type": "boolean",
                    "description": "Enable web search for current best practices and documentation",
                    "default": True,
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional screenshots or diagrams for visual context",
                },
                "continuation_id": {
                    "type": "string",
                    "description": "Thread continuation ID for multi-turn conversations",
                },
            },
            "required": ["prompt"] + (["model"] if self.is_effective_auto_mode() else []),
        }
        return schema
    
    def get_system_prompt(self) -> str:
        """Return system prompt that configures AI behavior."""
        return EXAMPLE_PROMPT
    
    def get_request_model(self):
        """Return Pydantic request model class for validation."""
        return ExampleRequest
    
    async def prepare_prompt(self, request: ExampleRequest) -> str:
        """Prepare complete prompt with user request + file content + context."""
        # Handle large prompts via prompt.txt file mechanism
        prompt_content, updated_files = self.handle_prompt_file(request.files)
        user_content = prompt_content if prompt_content else request.prompt
        
        # Check MCP transport size limits on user input
        size_check = self.check_prompt_size(user_content)
        if size_check:
            from tools.models import ToolOutput
            raise ValueError(f"MCP_SIZE_CHECK:{ToolOutput(**size_check).model_dump_json()}")
        
        # Update files list if prompt.txt was found
        if updated_files is not None:
            request.files = updated_files
        
        # Add focus areas to user content
        if request.focus_areas:
            focus_text = "\n\nFocus areas: " + ", ".join(request.focus_areas)
            user_content += focus_text
        
        # Add file content using centralized handler (handles deduplication & token limits)
        if request.files:
            file_content, processed_files = self._prepare_file_content_for_prompt(
                request.files, request.continuation_id, "Code files"
            )
            self._actually_processed_files = processed_files  # For conversation memory
            if file_content:
                user_content = f"{user_content}\n\n=== CODE FILES ===\n{file_content}\n=== END FILES ==="
        
        # Validate final prompt doesn't exceed model context window
        self._validate_token_limit(user_content, "Prompt content")
        
        # Add web search instruction if enabled
        websearch_instruction = self.get_websearch_instruction(
            request.use_websearch,
            """Consider searching for:
- Current best practices for the technologies used
- Recent security advisories or performance improvements
- Community solutions to similar code patterns"""
        )
        
        return f"""{self.get_system_prompt()}{websearch_instruction}

=== ANALYSIS REQUEST ===
Analysis Depth: {request.analysis_depth}

{user_content}
=== END REQUEST ===

Provide comprehensive code analysis with specific, actionable recommendations:"""

    # Optional: Override these methods for customization
    def get_default_temperature(self) -> float:
        return TEMPERATURE_BALANCED  # 0.5 - good for analytical tasks
    
    def get_model_category(self) -> "ToolModelCategory":
        from tools.models import ToolModelCategory
        return ToolModelCategory.BALANCED  # Standard analysis capabilities
    
    def wants_line_numbers_by_default(self) -> bool:
        return True  # Essential for precise code feedback
    
    def format_response(self, response: str, request: ExampleRequest, model_info: Optional[dict] = None) -> str:
        """Add custom formatting - base class handles continuation offers automatically."""
        return f"{response}\n\n---\n\n**Next Steps:** Review recommendations and prioritize implementation based on impact."
```

**Key Changes from Documentation:**
- **Schema Inheritance**: Common fields handled by base class automatically
- **MCP Size Checking**: Required for large prompt handling
- **File Processing**: Use `_prepare_file_content_for_prompt()` for conversation-aware deduplication
- **Error Handling**: `check_prompt_size()` and `_validate_token_limit()` prevent crashes
- **Web Search**: Use `get_websearch_instruction()` for consistent implementation

### 4. Create the System Prompt

Create `systemprompts/example_prompt.py`:

```python
"""System prompt for the example code analysis tool."""

EXAMPLE_PROMPT = """You are an expert code analyst and software engineering consultant specializing in comprehensive code review and optimization recommendations.

Your analysis should cover:

TECHNICAL ANALYSIS:
- Code structure, organization, and architectural patterns
- Performance implications and optimization opportunities  
- Security vulnerabilities and defensive programming practices
- Maintainability factors and technical debt assessment
- Best practices adherence and industry standards compliance

RECOMMENDATIONS FORMAT:
1. **Critical Issues** - Security, bugs, or breaking problems (fix immediately)
2. **Performance Optimizations** - Specific improvements with expected impact
3. **Code Quality Improvements** - Maintainability, readability, and structure
4. **Best Practices** - Industry standards and modern patterns
5. **Future Considerations** - Scalability and extensibility suggestions

ANALYSIS GUIDELINES:
- Reference specific line numbers when discussing code (file:line format)
- Provide concrete, actionable recommendations with examples
- Explain the "why" behind each suggestion
- Consider the broader system context and trade-offs
- Prioritize suggestions by impact and implementation difficulty

Be precise, practical, and constructive in your analysis. Focus on improvements that provide tangible value to the development team."""
```

**Add to `systemprompts/__init__.py`:**
```python
from .example_prompt import EXAMPLE_PROMPT
```

**Key Elements:**
- Clear role definition and expertise area
- Structured output format that's useful for developers
- Specific guidelines for code references and explanations
- Focus on actionable, prioritized recommendations

### 5. Register the Tool

**Step 5.1: Import in `server.py`**
```python
from tools.example import ExampleTool
```

**Step 5.2: Add to TOOLS dictionary in `server.py`**
```python
TOOLS = {
    "thinkdeep": ThinkDeepTool(),
    "codereview": CodeReviewTool(),
    "debug": DebugIssueTool(),
    "analyze": AnalyzeTool(),
    "chat": ChatTool(),
    "example": ExampleTool(),  # Add your tool here
    # ... other tools
}
```

**That's it!** The server automatically:
- Exposes the tool via MCP protocol
- Handles request validation and routing
- Manages model resolution and provider selection
- Implements conversation threading and file deduplication

### 6. Write Tests

Create `tests/test_example.py`:

```python
"""Tests for the example tool."""

import pytest
from unittest.mock import Mock, patch

from tools.example import ExampleTool, ExampleRequest
from tools.models import ToolModelCategory


class TestExampleTool:
    """Test suite for ExampleTool."""
    
    def test_tool_metadata(self):
        """Test basic tool metadata and configuration."""
        tool = ExampleTool()
        
        assert tool.get_name() == "example"
        assert "CODE ANALYSIS" in tool.get_description()
        assert tool.get_default_temperature() == 0.5  # TEMPERATURE_BALANCED
        assert tool.get_model_category() == ToolModelCategory.BALANCED
        assert tool.wants_line_numbers_by_default() is True
    
    def test_request_validation(self):
        """Test Pydantic request model validation."""
        # Valid request
        request = ExampleRequest(prompt="Analyze this code for performance issues")
        assert request.prompt == "Analyze this code for performance issues"
        assert request.analysis_depth == "standard"  # default
        assert request.focus_areas == []  # default_factory
        
        # Invalid request (missing required field)
        with pytest.raises(ValueError):
            ExampleRequest()  # Missing prompt
    
    def test_input_schema_generation(self):
        """Test JSON schema generation for MCP client."""
        tool = ExampleTool()
        schema = tool.get_input_schema()
        
        assert schema["type"] == "object"
        assert "prompt" in schema["properties"]
        assert "prompt" in schema["required"]
        assert "analysis_depth" in schema["properties"]
        
        # Common fields should be present
        assert "model" in schema["properties"]
        assert "continuation_id" in schema["properties"]
        assert "images" in schema["properties"]
    
    def test_model_category_for_auto_mode(self):
        """Test model category affects auto mode selection."""
        tool = ExampleTool()
        category = tool.get_model_category()
        
        # Should match expected category for provider selection
        assert category == ToolModelCategory.BALANCED
    
    @pytest.mark.asyncio
    async def test_prepare_prompt_basic(self):
        """Test prompt preparation with basic input."""
        tool = ExampleTool()
        request = ExampleRequest(
            prompt="Review this code",
            analysis_depth="comprehensive",
            focus_areas=["performance", "security"]
        )
        
        # Mock validation methods
        with patch.object(tool, 'check_prompt_size', return_value=None):
            with patch.object(tool, '_validate_token_limit'):
                with patch.object(tool, 'get_websearch_instruction', return_value=""):
                    prompt = await tool.prepare_prompt(request)
        
        assert "Review this code" in prompt
        assert "performance, security" in prompt
        assert "comprehensive" in prompt
        assert "ANALYSIS REQUEST" in prompt
    
    @pytest.mark.asyncio
    async def test_file_handling_with_deduplication(self):
        """Test file processing with conversation-aware deduplication."""
        tool = ExampleTool()
        request = ExampleRequest(
            prompt="Analyze these files",
            files=["/path/to/file1.py", "/path/to/file2.py"],
            continuation_id="test-thread-123"
        )
        
        # Mock file processing
        with patch.object(tool, 'check_prompt_size', return_value=None):
            with patch.object(tool, '_validate_token_limit'):
                with patch.object(tool, 'get_websearch_instruction', return_value=""):
                    with patch.object(tool, '_prepare_file_content_for_prompt') as mock_prep:
                        mock_prep.return_value = ("file content", ["/path/to/file1.py"])
                        
                        prompt = await tool.prepare_prompt(request)
                        
                        # Should call centralized file handler with continuation_id
                        mock_prep.assert_called_once_with(
                            ["/path/to/file1.py", "/path/to/file2.py"],
                            "test-thread-123",
                            "Code files"
                        )
        
        assert "CODE FILES" in prompt
        assert "file content" in prompt
    
    @pytest.mark.asyncio
    async def test_prompt_file_handling(self):
        """Test prompt.txt file handling for large inputs."""
        tool = ExampleTool()
        request = ExampleRequest(
            prompt="small prompt",  # Will be replaced
            files=["/path/to/prompt.txt", "/path/to/other.py"]
        )
        
        # Mock prompt.txt handling
        with patch.object(tool, 'handle_prompt_file') as mock_handle:
            mock_handle.return_value = ("Large prompt content from file", ["/path/to/other.py"])
            with patch.object(tool, 'check_prompt_size', return_value=None):
                with patch.object(tool, '_validate_token_limit'):
                    with patch.object(tool, 'get_websearch_instruction', return_value=""):
                        with patch.object(tool, '_prepare_file_content_for_prompt', return_value=("", [])):
                            prompt = await tool.prepare_prompt(request)
        
        assert "Large prompt content from file" in prompt
        mock_handle.assert_called_once()
    
    def test_format_response_customization(self):
        """Test custom response formatting."""
        tool = ExampleTool()
        request = ExampleRequest(prompt="test")
        
        formatted = tool.format_response("Analysis complete", request)
        
        assert "Analysis complete" in formatted
        assert "Next Steps:" in formatted
        assert "prioritize implementation" in formatted


# Integration test (requires actual model context)
class TestExampleToolIntegration:
    """Integration tests that require full tool setup."""
    
    def setup_method(self):
        """Set up model context for integration tests."""
        # Initialize model context for file processing
        from utils.model_context import ModelContext
        self.tool = ExampleTool()
        self.tool._model_context = ModelContext("flash")  # Test model
    
    @pytest.mark.asyncio
    async def test_full_prompt_preparation(self):
        """Test complete prompt preparation flow."""
        request = ExampleRequest(
            prompt="Analyze this codebase for security issues",
            analysis_depth="comprehensive", 
            focus_areas=["security", "performance"]
        )
        
        # Mock file system and validation
        with patch.object(self.tool, 'check_prompt_size', return_value=None):
            with patch.object(self.tool, '_validate_token_limit'):
                with patch.object(self.tool, 'get_websearch_instruction', return_value="\nWEB_SEARCH_ENABLED"):
                    prompt = await self.tool.prepare_prompt(request)
        
        # Verify complete prompt structure
        assert self.tool.get_system_prompt() in prompt
        assert "WEB_SEARCH_ENABLED" in prompt
        assert "security, performance" in prompt
        assert "comprehensive" in prompt
        assert "ANALYSIS REQUEST" in prompt
```

**Key Testing Patterns:**
- **Metadata Tests**: Verify tool configuration and schema generation
- **Validation Tests**: Test Pydantic request models and edge cases  
- **Prompt Tests**: Mock external dependencies, test prompt composition
- **Integration Tests**: Test full flow with model context
- **File Handling**: Test conversation-aware deduplication
- **Error Cases**: Test size limits, validation failures

## Essential Gotchas & Best Practices

### Critical Requirements

**🚨 MUST DO:**
1. **Inherit from ToolRequest**: Request models MUST inherit from `ToolRequest` to get common fields
2. **Use `default_factory=list`**: For mutable defaults, never use `default=[]` - causes shared state bugs
3. **Implement all 6 abstract methods**: `get_name()`, `get_description()`, `get_input_schema()`, `get_system_prompt()`, `get_request_model()`, `prepare_prompt()`
4. **Handle MCP size limits**: Call `check_prompt_size()` on user input in `prepare_prompt()`
5. **Use centralized file processing**: Call `_prepare_file_content_for_prompt()` for conversation-aware deduplication
6. **Register in server.py**: Import tool and add to `TOOLS` dictionary

**🚨 COMMON MISTAKES:**
- **Forgetting TYPE_CHECKING**: Import `ToolModelCategory` under `TYPE_CHECKING` to avoid circular imports
- **Hardcoding models**: Use `get_model_category()` instead of hardcoding model selection
- **Ignoring continuation_id**: File processing should pass `continuation_id` for deduplication
- **Missing error handling**: Always validate token limits with `_validate_token_limit()`
- **Wrong default patterns**: Use `default_factory=list` not `default=None` for file lists

### File Handling Patterns

```python
# ✅ CORRECT: Conversation-aware file processing
file_content, processed_files = self._prepare_file_content_for_prompt(
    request.files, request.continuation_id, "Context files"
)
self._actually_processed_files = processed_files  # For conversation memory

# ❌ WRONG: Direct file reading (no deduplication)
file_content = read_files(request.files)
```

### Request Model Patterns

```python
# ✅ CORRECT: Proper defaults and inheritance
class MyToolRequest(ToolRequest):
    files: Optional[list[str]] = Field(default_factory=list, ...)
    options: Optional[list[str]] = Field(default_factory=list, ...)
    
# ❌ WRONG: Shared mutable defaults
class MyToolRequest(ToolRequest):
    files: Optional[list[str]] = Field(default=[], ...)  # BUG!
```

### Testing Requirements

**Required Tests:**
- Tool metadata (name, description, category)
- Request validation (valid/invalid cases)
- Schema generation for MCP
- Prompt preparation with mocks
- File handling with conversation IDs
- Error cases (size limits, validation failures)

### Model Categories Guide

- **FAST_RESPONSE**: Chat, simple queries, quick tasks (→ o4-mini, flash)
- **BALANCED**: Standard analysis, code review, general tasks (→ o3-mini, pro)  
- **EXTENDED_REASONING**: Complex debugging, deep analysis (→ o3, pro with high thinking)

### Advanced Features

**Conversation Threading**: Automatic if `continuation_id` provided
**File Deduplication**: Automatic via `_prepare_file_content_for_prompt()`
**Web Search**: Use `get_websearch_instruction()` for consistent implementation
**Image Support**: Inherited from ToolRequest, validated automatically
**Large Prompts**: Handle via `check_prompt_size()` → prompt.txt mechanism

## Quick Checklist

**Before Submitting PR:**
- [ ] Tool inherits from `BaseTool`, request from `ToolRequest`
- [ ] All 6 abstract methods implemented
- [ ] System prompt created in `systemprompts/`
- [ ] Tool registered in `server.py` TOOLS dict
- [ ] Comprehensive unit tests written
- [ ] File handling uses `_prepare_file_content_for_prompt()`
- [ ] MCP size checking with `check_prompt_size()`
- [ ] Token validation with `_validate_token_limit()`
- [ ] Proper model category selected
- [ ] No hardcoded model names

**Run Before Commit:**
```bash
# Test your tool
pytest tests/test_example.py -xvs

# Run all tests
./code_quality_checks.sh
```

## Complete Example

The example tool we built provides:
- **Comprehensive code analysis** with configurable depth
- **Multi-file support** with conversation-aware deduplication  
- **Focus areas** for targeted analysis
- **Web search integration** for current best practices
- **Image support** for screenshots/diagrams
- **Conversation threading** for follow-up discussions
- **Automatic model selection** based on task complexity

**Usage by Claude:**
```json
{
  "tool": "example",
  "arguments": {
    "prompt": "Analyze this codebase for security vulnerabilities and performance issues",
    "files": ["/path/to/src/", "/path/to/config.py"],
    "analysis_depth": "comprehensive", 
    "focus_areas": ["security", "performance"],
    "model": "o3"
  }
}
```

The tool automatically handles file deduplication, validates inputs, manages token limits, and offers continuation opportunities for deeper analysis.

---

**Need Help?** Look at existing tools like `chat.py` and `consensus.py` for reference implementations, or check GitHub issues for support.