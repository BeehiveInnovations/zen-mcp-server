# Token Optimization V2 - Rebase Implementation Plan

## Overview

Reimplementing two-stage token optimization architecture on main v8.0.0, using the original implementation (tagged as `reference-two-stage`) as a guide.

**Goal:** Achieve 95% token reduction (43k → 800 tokens) while leveraging main's modern registry pattern and new features.

**Reference Branch:** `reference-two-stage` (token-optimization-two-stage)
**Target Branch:** `token-optimization-v2` (based on main v8.0.0)

## Key Components from Reference Branch

### Core Files (~1,400 lines)
- `server_token_optimized.py` (~283 lines) - Optimization orchestration
- `tools/mode_selector.py` (~324 lines) - zen_select_mode tool
- `tools/mode_executor.py` (~414 lines) - zen_execute tool
- `tools/zen_execute.py` (~269 lines) - Alternative executor
- `token_optimization_config.py` (~235 lines) - Configuration

### Integration Files
- `server.py` - Tool registration modifications
- `config.py` - Feature flags

### Documentation
- `TOKEN_OPTIMIZATION_*.md` files
- `CLAUDE.md` updates
- `TEST_TWO_STAGE.md`

## Implementation Strategy

### Phase 1: Core Logic Port (4-6 hours)

**Step 1: Cherry-pick pure optimization logic**
```bash
# Copy modular core files
git show reference-two-stage:server_token_optimized.py > server_token_optimized.py
git show reference-two-stage:token_optimization_config.py > token_optimization_config.py

# Test imports
python -c "from server_token_optimized import get_optimized_tools; print('✓')"
```

**Step 2: Adapt mode selector for registry pattern**
- Update `tools/mode_selector.py` to use `RegistryBackedProviderMixin`
- Leverage registry introspection for smarter mode recommendations
- Use main's `ModelCapabilities` structure

**Step 3: Update zen_execute for new tool structure**
- Adapt `tools/mode_executor.py` to main's `BaseTool.execute()` pattern
- Inherit all main improvements (error handling, context, etc.)

### Phase 2: Registry Integration (3-4 hours)

**Leverage main's improvements:**
```python
# Mode-specific schemas can use registry metadata
from providers.registries.base import BaseModelRegistry

def build_mode_schema(mode: str):
    # Query registry for mode requirements
    # Generate minimal schema dynamically
    # Automatically adapts to new models/providers
```

**Key advantages:**
- Registry pattern → cleaner schema generation
- Centralized capabilities → easier mode selection
- Better model discovery

### Phase 3: Server Integration (2-3 hours)

**Update server.py:**
```python
from server_token_optimized import get_optimized_tools

# Check if optimization enabled
optimized_tools = get_optimized_tools()
if optimized_tools:
    TOOLS = optimized_tools  # Uses new registry pattern
else:
    TOOLS = {
        # All main's tools including new ones
        "clink": CLinkTool(),      # ← NEW in main!
        "apilookup": LookupTool(), # ← NEW in main!
        # ... etc
    }
```

### Phase 4: Testing & Validation (2-3 hours)

```bash
# Run quality checks
./code_quality_checks.sh

# Test token optimization
python test_two_stage_flow.py

# Telemetry comparison
python analyze_telemetry.py

# Validate against reference
git diff reference-two-stage --stat
```

## Architecture Improvements Over Original

### 1. Registry Pattern Benefits
- **Old:** Manual `SUPPORTED_MODELS` dict parsing
- **New:** Dynamic registry introspection
- **Benefit:** Smarter mode selection, automatic adaptation

### 2. Schema Generation
- **Old:** Manual schema construction
- **New:** Registry-driven minimal schemas
- **Benefit:** Automatically adapts to new providers/models

### 3. Tool Structure
- **Old:** Custom execution patterns
- **New:** Inherits main's `BaseTool.execute()`
- **Benefit:** All main improvements included automatically

### 4. Feature Completeness
- **Old:** Missing CLinkTool, Azure, etc.
- **New:** All 253 main commits included
- **Benefit:** Full feature parity + optimization

## File Mapping: Old → New

| Reference Branch | New Implementation | Changes Needed |
|------------------|-------------------|----------------|
| `server_token_optimized.py` | Same | Test with new registry |
| `token_optimization_config.py` | Same | Minimal updates |
| `tools/mode_selector.py` | Rewrite | Use registry pattern |
| `tools/mode_executor.py` | Adapt | Inherit from new `BaseTool` |
| `tools/zen_execute.py` | Adapt | Use registry capabilities |
| `server.py` | Modify | Integrate with main's structure |

## Success Criteria

1. ✅ Achieves 95% token reduction (43k → 800 tokens)
2. ✅ All 361 unit tests pass
3. ✅ Linting passes (ruff, black, isort)
4. ✅ Compatible with main's registry pattern
5. ✅ Includes all main v8.0 features
6. ✅ Telemetry shows equivalent performance
7. ✅ Clean PR ready for upstream contribution

## Contribution Preparation

**PR Title:** `feat: Add two-stage token optimization architecture`

**Requirements:**
- Conventional commits format ✓
- All tests passing ✓
- Documentation complete ✓
- Type hints and docstrings ✓
- No breaking changes ✓

## Timeline

- **Day 1:** Core logic port + registry adaptation (4-8 hours)
- **Day 2:** Integration + testing (4-6 hours)
- **Day 3:** Validation + documentation (2-4 hours)

**Total:** 10-18 hours (~2-3 days)

## Next Steps

1. [IN PROGRESS] Create this plan document
2. [PENDING] Port core optimization files
3. [PENDING] Adapt mode selector for registry
4. [PENDING] Update executor with main's patterns
5. [PENDING] Integrate with server.py
6. [PENDING] Comprehensive testing
7. [PENDING] Prepare upstream PR

---
*Created: 2025-10-07*
*Branch: token-optimization-v2*
*Reference: reference-two-stage tag*
