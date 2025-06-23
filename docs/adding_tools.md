# Adding Tools to Zen MCP Server

This guide explains how to add new tools to the Zen MCP Server. Tools enable Claude to interact with AI models for specialized tasks like code analysis, debugging, and collaborative thinking.

## Tool Types

Zen supports two tool architectures:

### Simple Tools
- **Pattern**: Single request → AI response → formatted output
- **Use cases**: Chat, quick analysis, straightforward tasks
- **Benefits**: Clean, lightweight, easy to implement
- **Base class**: `SimpleTool` (`tools/simple/base.py`)

### Multi-step Workflow Tools  
- **Pattern**: Step-by-step investigation with Claude pausing between steps to investigate
- **Use cases**: Complex analysis, debugging, code review, security audits
- **Benefits**: Systematic investigation, expert analysis integration, better results for complex tasks
- **Base class**: `WorkflowTool` (`tools/workflow/base.py`)

**Recommendation**: Use workflow tools for most complex analysis tasks as they produce significantly better results by forcing systematic investigation.

## Implementation Guide

### Simple Tool Example

```python
from tools.simple.base import SimpleTool
from tools.shared.base_models import ToolRequest
from pydantic import Field

class ChatTool(SimpleTool):
    def get_name(self) -> str:
        return "chat"
    
    def get_description(self) -> str:
        return "GENERAL CHAT & COLLABORATIVE THINKING..."
    
    def get_tool_fields(self) -> dict:
        return {
            "prompt": {
                "type": "string", 
                "description": "Your question or idea..."
            },
            "files": SimpleTool.FILES_FIELD  # Reuse common field
        }
    
    def get_required_fields(self) -> list[str]:
        return ["prompt"]
    
    async def prepare_prompt(self, request) -> str:
        return self.prepare_chat_style_prompt(request)
```

### Workflow Tool Example

```python  
from tools.workflow.base import WorkflowTool

class DebugTool(WorkflowTool):
    def get_name(self) -> str:
        return "debug"
    
    def get_description(self) -> str:
        return "DEBUG & ROOT CAUSE ANALYSIS - Step-by-step investigation..."
    
    def get_required_actions(self, step_number, confidence, findings, total_steps):
        if step_number == 1:
            return ["Search for code related to issue", "Examine relevant files"]
        return ["Trace execution flow", "Verify hypothesis with code evidence"]
    
    def should_call_expert_analysis(self, consolidated_findings):
        return len(consolidated_findings.relevant_files) > 0
    
    def prepare_expert_analysis_context(self, consolidated_findings):
        return f"Investigation findings: {consolidated_findings.findings}"
```

## Key Implementation Points

### Simple Tools
- Inherit from `SimpleTool` 
- Implement: `get_name()`, `get_description()`, `get_tool_fields()`, `prepare_prompt()`
- Override: `get_required_fields()`, `format_response()` (optional)

### Workflow Tools  
- Inherit from `WorkflowTool`
- Implement: `get_name()`, `get_description()`, `get_required_actions()`, `should_call_expert_analysis()`, `prepare_expert_analysis_context()`
- Override: `get_tool_fields()` (optional)

### Registration
1. Create system prompt in `systemprompts/`
2. Import in `server.py` 
3. Add to `TOOLS` dictionary

## Testing Your Tool

### Simulator Tests (Recommended)
The most important validation is adding your tool to the simulator test suite:

```python
# Add to communication_simulator_test.py
def test_your_tool_validation(self):
    """Test your new tool with real API calls"""
    response = self.call_tool("your_tool", {
        "prompt": "Test the tool functionality",
        "model": "flash"
    })
    
    # Validate response structure and content
    self.assertIn("status", response)
    self.assertEqual(response["status"], "success")
```

**Why simulator tests matter:**
- Test actual MCP communication with Claude
- Validate real AI model interactions  
- Catch integration issues unit tests miss
- Ensure proper conversation threading
- Verify file handling and deduplication

### Running Tests
```bash
# Test your specific tool
python communication_simulator_test.py --individual your_tool_validation

# Quick comprehensive test
python communication_simulator_test.py --quick
```

## Examples to Study

- **Simple Tool**: `tools/chat.py` - Clean request/response pattern
- **Workflow Tool**: `tools/debug.py` - Multi-step investigation with expert analysis

**Recommendation**: Start with existing tools as templates and explore the base classes to understand available hooks and methods.

