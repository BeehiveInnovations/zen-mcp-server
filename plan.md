# Tool Model Request Interface Refactoring Plan

## Problem Statement

The current architecture has a fundamental design mismatch where the base class assumes all tools use a single model, but the ConsensusTool uses multiple models. The current "fix" is a hack that returns a hardcoded placeholder string instead of solving the architectural issue.

### Current Issues
- `get_request_model_name()` method assumes single model pattern
- ConsensusTool inherits this method but uses multiple models
- Hack solution returns `"multi-model-consensus"` placeholder
- Violates Liskov Substitution Principle
- Creates misleading metadata and logging

## Solution: Test-First Comprehensive Refactoring

Implement a proper architectural solution using test-driven development with careful migration path.

## Implementation Strategy: 3-Phase Approach

### Phase 1: Add Tests & New Interface (Tests fail, then pass)
1. Add comprehensive tests for new `get_request_model_names()` interface
2. Update tests to support both old and new signatures
3. Implement new interface alongside old one
4. **Commit**: "feat: add get_request_model_names() with backward compatibility"

### Phase 2: Migrate Client Code (All tests pass)
1. Update all client usage sites to use new interface
2. Keep old interface working for compatibility
3. Verify all tests still pass
4. **Commit**: "refactor: migrate clients to use get_request_model_names()"

### Phase 3: Remove Legacy Interface (Clean architecture)
1. Remove tests for old `get_request_model_name()` interface
2. Remove the old method from all classes
3. Final validation of all tests
4. **Commit**: "refactor: remove deprecated get_request_model_name() method"

## Detailed Implementation Plan

### Phase 1: Add Tests & New Interface

#### Step 1.1: Create Comprehensive Test Suite

Create `tests/test_model_interface_refactoring.py`:

```python
import pytest
from tools.simple.base import SimpleTool
from tools.workflow.base import WorkflowTool
from tools.consensus import ConsensusTool
from tools.shared.base_tool import BaseTool

class TestModelInterfaceRefactoring:
    """Test suite for model interface refactoring that supports both old and new signatures."""
    
    def test_new_interface_single_model_tools(self):
        """Test that single-model tools return list with one model."""
        # This will initially fail until we implement get_request_model_names()
        from tools.chat import ChatTool
        tool = ChatTool()
        
        # New interface
        model_names = tool.get_request_model_names()
        assert isinstance(model_names, list)
        assert len(model_names) <= 1  # Single model or empty
        
    def test_new_interface_multi_model_tools(self):
        """Test that multi-model tools return list with multiple models."""
        # This will initially fail until we implement get_request_model_names()
        tool = ConsensusTool()
        tool.models = [
            type('Model', (), {'name': 'gemini-2.5-pro'}),
            type('Model', (), {'name': 'claude-sonnet-4'})
        ]
        
        # New interface
        model_names = tool.get_request_model_names()
        assert isinstance(model_names, list)
        assert len(model_names) == 2
        assert 'gemini-2.5-pro' in model_names
        assert 'claude-sonnet-4' in model_names
        
    def test_backward_compatibility_bridge(self):
        """Test that old interface still works via compatibility bridge."""
        from tools.chat import ChatTool
        tool = ChatTool()
        
        # Old interface should work via bridge
        request = type('Request', (), {'model': 'test-model'})
        model_name = tool.get_request_model_name(request)
        assert isinstance(model_name, str)
        
    def test_consensus_compatibility_bridge(self):
        """Test that consensus tool compatibility bridge returns meaningful name."""
        tool = ConsensusTool()
        tool.models = [
            type('Model', (), {'name': 'gemini-2.5-pro'}),
            type('Model', (), {'name': 'claude-sonnet-4'})
        ]
        
        # Old interface via bridge should return multi-model indicator
        request = type('Request', (), {})
        model_name = tool.get_request_model_name(request)
        assert 'multi-model' in model_name
        assert 'consensus' in model_name
```

#### Step 1.2: Add Abstract Method to BaseTool

Update `tools/shared/base_tool.py`:

```python
@abstractmethod  
def get_request_model_names(self) -> list[str]:
    """
    Returns list of model names used by this tool.
    
    For single-model tools, this returns a list with one model name.
    For multi-model tools (like ConsensusTool), this returns all models used.
    
    Returns:
        list[str]: List of model names used by this tool
    """
    pass

def get_request_model_name(self, request) -> str:
    """
    Legacy method - use get_request_model_names() instead.
    
    This method is kept for backward compatibility but delegates to
    the new get_request_model_names() method. For tools using multiple
    models, it returns a descriptive placeholder name.
    
    Args:
        request: The request object (not used in default implementation)
        
    Returns:
        str: Single model name or placeholder for multi-model tools
    """
    names = self.get_request_model_names()
    if len(names) > 1:
        return f"multi-model-{self.get_name()}"
    return names[0] if names else "unknown"
```

#### Step 1.3: Implement in All Tool Classes

**SimpleTool** (`tools/simple/base.py`):
```python
def get_request_model_names(self) -> list[str]:
    """Returns list of model names used by this tool."""
    # Simple tools get their model from the request at runtime
    # Return empty list to indicate dynamic model selection
    return []
```

**WorkflowMixin** (`tools/workflow/workflow_mixin.py`):
```python
def get_request_model_names(self) -> list[str]:
    """Returns list of model names used by this tool."""
    # Workflow tools typically use one model from request
    return []
```

**ConsensusTool** (`tools/consensus.py`):
```python
def get_request_model_names(self) -> list[str]:
    """Returns list of all models used for consensus."""
    return [model.name for model in self.models]
```

**ListModelsTool** and **VersionTool** (direct BaseTool inheritors):
```python
def get_request_model_names(self) -> list[str]:
    """Returns empty list as utility tools don't use models."""
    return []
```

### Phase 2: Migrate Client Code

#### Step 2.1: Find All Usage Sites

```bash
# Find all client usage of get_request_model_name
grep -r "get_request_model_name" --include="*.py" tools/
```

#### Step 2.2: Update Each Usage Pattern

**Pattern 1: Model Resolution/Fallback**
```python
# Before:
model_name = self.get_request_model_name(request)
if not model_name:
    model_name = DEFAULT_MODEL

# After:
model_names = self.get_request_model_names()
if not model_names:
    # Try to get from request for dynamic tools
    model_name = self.get_request_model_name(request)
    if not model_name:
        model_name = DEFAULT_MODEL
else:
    model_name = model_names[0]  # Use first/primary model
```

**Pattern 2: Metadata Generation**
```python
# Before:
metadata["model_used"] = self.get_request_model_name(request)

# After:
model_names = self.get_request_model_names()
if len(model_names) > 1:
    metadata["models_used"] = model_names
    metadata["primary_model"] = model_names[0]
else:
    # Single model or dynamic selection
    metadata["model_used"] = self.get_request_model_name(request)
```

**Pattern 3: ModelContext Creation**
```python
# Before:
model_name = self.get_request_model_name(request)
model_context = ModelContext(model_name)

# After:
model_names = self.get_request_model_names()
if model_names and len(model_names) == 1:
    model_context = ModelContext(model_names[0])
else:
    # Fall back to request-based selection
    model_name = self.get_request_model_name(request)
    model_context = ModelContext(model_name)
```

### Phase 3: Remove Legacy Interface

#### Step 3.1: Update Tests

Remove backward compatibility tests and update all tests to use new interface only:

```python
# Remove these test methods:
# - test_backward_compatibility_bridge
# - Any tests using get_request_model_name directly

# Update remaining tests to only use get_request_model_names()
```

#### Step 3.2: Remove Old Methods

1. Remove `get_request_model_name()` from `BaseTool`
2. Remove overrides from `SimpleTool`
3. Remove overrides from `WorkflowMixin`
4. Remove the hack from `ConsensusTool`

#### Step 3.3: Final Cleanup

Update any remaining references and documentation.

## Testing Strategy

### Phase 1 Testing
```bash
# Run new tests (should fail initially)
python -m pytest tests/test_model_interface_refactoring.py -v

# After implementation, all should pass
python -m pytest tests/test_model_interface_refactoring.py -v

# Existing tests should still pass via compatibility bridge
./code_quality_checks.sh
```

### Phase 2 Testing
```bash
# All tests should pass with migrated clients
./code_quality_checks.sh
python communication_simulator_test.py --quick
```

### Phase 3 Testing
```bash
# Remove compatibility tests
# All remaining tests should pass with clean architecture
./code_quality_checks.sh
./run_integration_tests.sh
```

## Migration Safety Checklist

### Before Each Commit
- [ ] All existing tests pass
- [ ] New tests demonstrate the feature working
- [ ] No hardcoded placeholders remain
- [ ] Consensus tool reports actual model names

### Phase Transitions
- [ ] Phase 1→2: Both interfaces work correctly
- [ ] Phase 2→3: All clients migrated to new interface
- [ ] Phase 3 complete: Old interface completely removed

## Expected Outcomes

### After Phase 1
- Both old and new interfaces work
- Tests validate both signatures
- ConsensusTool can report actual models

### After Phase 2
- All clients use new interface
- Better metadata for multi-model tools
- Old interface still available but unused

### After Phase 3
- Clean architecture with single interface
- No LSP violations
- Accurate model reporting throughout

## Success Criteria

1. **Test Coverage**: All new functionality has tests
2. **Backward Compatibility**: No breaking changes during migration
3. **Clean Architecture**: Single, consistent interface at end
4. **Accurate Metadata**: Multi-model tools report all models correctly
5. **No Hacks**: No hardcoded placeholders or workarounds

This test-first approach ensures safe, incremental refactoring with validation at each step.