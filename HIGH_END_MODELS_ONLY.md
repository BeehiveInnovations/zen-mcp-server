# Zen-MCP High-End Model Configuration

## Overview
Zen-MCP is now configured for complex, multi-step workflows requiring premium models only.
Simple, focused tasks are handled by Claude subagents for efficiency.

## Removed Tools (Handled by Subagents)
- `codereview_prompt.py` - Use code-review-specialist subagent
- `precommit_prompt.py` - Use multiple specialized subagents
- `refactor_prompt.py` - Use complexity-guard + refactoring subagents
- `testgen_prompt.py` - Use universal-test-engineer subagent
- `docgen_prompt.py` - Use documentation subagents

## Active Premium Tools

### 1. **thinkdeep** - Deep Investigation Workflow
- **Purpose**: Comprehensive problem analysis with systematic investigation
- **Model Category**: EXTENDED_REASONING
- **Recommended Models**: 
  - `o3` - Best for complex logical problems
  - `gemini-2.5-pro` - Best for research with 1M context
  - `gpt-4.1-2025-04-14` - Best for balanced deep analysis

### 2. **consensus** - Multi-Model Consensus Building
- **Purpose**: Complex decisions requiring multiple perspectives
- **Model Category**: BALANCED (multiple models)
- **Recommended Models**: 
  - Mix of `o3`, `gemini-2.5-pro`, `gpt-4.1` for diverse perspectives
  - Never use mini variants

### 3. **debug** - Root Cause Analysis
- **Purpose**: Systematic debugging of complex issues
- **Model Category**: EXTENDED_REASONING
- **Recommended Models**:
  - `o3` - Best for logical debugging
  - `gpt-4.1-2025-04-14` - Best for code analysis

### 4. **analyze** - Comprehensive Code Analysis
- **Purpose**: System-wide architectural and performance analysis
- **Model Category**: BALANCED
- **Recommended Models**:
  - `gemini-2.5-pro` - Best for large codebases (1M context)
  - `gpt-4.1-2025-04-14` - Best for architectural insights

### 5. **secaudit** - Security Audit Workflow
- **Purpose**: Comprehensive security assessment
- **Model Category**: EXTENDED_REASONING
- **Recommended Models**:
  - `o3` - Best for security logic analysis
  - `gpt-4.1-2025-04-14` - Best for vulnerability patterns

### 6. **planner** - Sequential Planning
- **Purpose**: Complex task planning with revision capabilities
- **Model Category**: BALANCED
- **Recommended Models**:
  - `gemini-2.5-pro` - Best for creative planning
  - `o3` - Best for logical task breakdown

### 7. **tracer** - Code Flow Analysis
- **Purpose**: Trace execution paths and dependencies
- **Model Category**: BALANCED
- **Recommended Models**:
  - `gpt-4.1-2025-04-14` - Best for code comprehension
  - `gemini-2.5-pro` - Best for large trace contexts

### 8. **chat** - Collaborative Thinking
- **Purpose**: General brainstorming and discussion
- **Model Category**: FAST_RESPONSE (but should use premium for quality)
- **Recommended Models**:
  - `gemini-2.5-pro` - Best for creative discussion
  - `gpt-4.1-2025-04-14` - Best for technical discussion

## Model Selection Rules

### NEVER USE:
- `o3-mini`
- `o4-mini` 
- `gpt-4.1-mini`
- `claude-3.5-haiku`
- Any "mini" or "lite" variants
- Any model with reduced capabilities

### ALWAYS USE:
- `o3` - For reasoning and logical analysis
- `o3-pro-2025-06-10` - ONLY for universe-scale complexity OR explicit user request
- `gemini-2.5-pro` - For large context and research
- `gpt-4.1-2025-04-14` - For balanced performance
- `google/gemini-2.5-flash` - Acceptable for simple chat only

## Environment Configuration

Set DEFAULT_MODEL to "auto" to force explicit model selection:
```bash
export DEFAULT_MODEL=auto
```

This ensures Claude must explicitly choose a high-end model for each zen-mcp invocation.

## Usage Pattern

```python
# When invoking zen-mcp tools, always specify a premium model:
await mcp__zen__thinkdeep(
    model="o3",  # or "gemini-2.5-pro" or "gpt-4.1-2025-04-14"
    # ... other parameters
)
```

## Enforcement

The zen-mcp server will:
1. Require explicit model selection when DEFAULT_MODEL=auto
2. Show only available premium models in the enum
3. Tools are configured with appropriate ToolModelCategory for guidance

## Migration Complete

As of this configuration:
- Conflicting prompts have been archived to `systemprompts/_archived_conflicts/`
- `__init__.py` updated to exclude archived prompts
- Only premium workflow tools remain active
- Subagents handle all rapid, focused tasks