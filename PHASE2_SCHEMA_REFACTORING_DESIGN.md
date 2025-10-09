# Phase 2: Schema Refactoring Design Document

## Overview

**Goal:** Eliminate hardcoded schema duplication in `mode_selector.py` by generating schemas dynamically from Pydantic models in `mode_executor.py`, while preserving all Phase 1 UX enhancements.

**Motivation:** The 7 validation bugs we fixed earlier were caused by schema drift between hardcoded schemas (mode_selector.py) and Pydantic models (mode_executor.py). This refactoring eliminates the root cause.

## Current Architecture

### Problem: Dual Schema Definition

**Location 1:** `tools/mode_selector.py` (lines 482-808)
```python
def _get_complete_schema(self, mode: str, complexity: str) -> dict:
    schemas = {
        ("debug", "simple"): {
            "type": "object",
            "required": ["problem"],
            "properties": {
                "problem": {"type": "string", "description": "..."},
                # ... 15 more properties hardcoded
            }
        },
        # ... 19 more mode/complexity combinations
    }
```

**Location 2:** `tools/mode_executor.py` (lines 30-500)
```python
class DebugSimpleRequest(BaseModel):
    problem: str = Field(..., description="The issue to debug")
    files: Optional[List[str]] = Field(None, description="...")
    # ... 15 more fields via Pydantic
```

**Issue:** Any change to request models requires updating TWO places, causing drift and validation bugs.

## Proposed Architecture

### Hybrid Dynamic + Enhanced Generation

```python
class ModeSchemaGenerator:
    """
    Generates schemas dynamically from Pydantic models with manual UX enhancements.
    """

    def __init__(self):
        # Import mode executor models
        from tools.mode_executor import MODE_REQUEST_MAP
        self.mode_request_map = MODE_REQUEST_MAP

    def generate_schema(self, mode: str, complexity: str) -> dict:
        """
        Generate complete schema for a mode/complexity combination.

        Steps:
        1. Get base schema from Pydantic model via .model_json_schema()
        2. Apply manual UX enhancements (descriptions, examples, hints)
        3. Validate schema compatibility
        4. Return enhanced schema
        """
        # Step 1: Get base schema from Pydantic
        base_schema = self._get_pydantic_schema(mode, complexity)

        # Step 2: Apply UX enhancements
        enhanced_schema = self._apply_enhancements(base_schema, mode, complexity)

        # Step 3: Validate (optional, for debugging)
        # self._validate_schema_structure(enhanced_schema, mode, complexity)

        return enhanced_schema

    def _get_pydantic_schema(self, mode: str, complexity: str) -> dict:
        """Generate base schema from Pydantic model"""
        key = (mode, complexity)
        model_class = self.mode_request_map.get(key)

        if not model_class:
            raise ValueError(f"No request model for {mode}/{complexity}")

        # Use Pydantic's built-in JSON schema generation
        return model_class.model_json_schema()

    def _apply_enhancements(self, base_schema: dict, mode: str, complexity: str) -> dict:
        """
        Apply manual UX enhancements to base schema.

        Enhancements:
        - Field-level hints and examples
        - Weighted keywords for mode selection
        - Human-friendly descriptions
        - Working examples
        """
        enhancements = SCHEMA_ENHANCEMENTS.get((mode, complexity), {})

        # Deep merge enhancements into base schema
        enhanced = {**base_schema}

        # Apply field-level enhancements
        if "field_hints" in enhancements:
            for field, hint in enhancements["field_hints"].items():
                if field in enhanced.get("properties", {}):
                    enhanced["properties"][field]["x-hint"] = hint

        # Apply top-level metadata
        if "keywords" in enhancements:
            enhanced["x-keywords"] = enhancements["keywords"]

        if "tips" in enhancements:
            enhanced["x-tips"] = enhancements["tips"]

        return enhanced
```

## Implementation Plan

### Step 1: Create Schema Generator Module (2 hours)

**File:** `tools/schema_generator.py`

```python
"""
Schema Generator - Dynamic schema generation from Pydantic models

Generates JSON schemas dynamically from Pydantic models and applies
manual UX enhancements while preventing schema drift.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel

# UX enhancements for each mode/complexity
SCHEMA_ENHANCEMENTS = {
    ("debug", "simple"): {
        "field_hints": {
            "problem": "Clear, concise description of the bug or issue",
            "files": "List of file paths relevant to the issue",
            "confidence": "How certain are you about the cause?"
        },
        "keywords": ["bug", "error", "broken", "debug", "fix"],
        "tips": [
            "Include specific error messages if available",
            "Provide minimal reproduction steps",
            "List files you've already checked"
        ]
    },
    # ... enhancements for all 20 combinations
}

class ModeSchemaGenerator:
    # Implementation from above
    pass

# Global instance
schema_generator = ModeSchemaGenerator()
```

**Tasks:**
1. ✅ Create `tools/schema_generator.py` with ModeSchemaGenerator class
2. ✅ Migrate SCHEMA_ENHANCEMENTS from implicit knowledge to explicit config
3. ✅ Implement `_get_pydantic_schema()` using `.model_json_schema()`
4. ✅ Implement `_apply_enhancements()` for UX features
5. ✅ Add comprehensive docstrings

### Step 2: Update mode_selector.py (2 hours)

**Changes to `tools/mode_selector.py`:**

```python
# Old (lines 482-808): 326 lines of hardcoded schemas
def _get_complete_schema(self, mode: str, complexity: str) -> dict:
    schemas = {
        # ... 326 lines of hardcoded schemas
    }
    return schemas.get((mode, complexity), {})

# New (3 lines)
def _get_complete_schema(self, mode: str, complexity: str) -> dict:
    from tools.schema_generator import schema_generator
    return schema_generator.generate_schema(mode, complexity)
```

**Tasks:**
1. ✅ Import schema_generator in mode_selector.py
2. ✅ Replace `_get_complete_schema()` body with generator call
3. ✅ Remove 326 lines of hardcoded schemas
4. ✅ Keep MODE_KEYWORDS and MODE_DESCRIPTIONS (still useful)
5. ✅ Update docstrings to reference dynamic generation

### Step 3: Add Startup Validation (1 hour)

**File:** `tools/schema_generator.py`

```python
class ModeSchemaGenerator:

    def validate_all_schemas(self) -> Dict[str, Any]:
        """
        Validate all mode/complexity schemas at startup.

        Checks:
        1. All 20 mode/complexity combinations have Pydantic models
        2. Generated schemas are valid JSON Schema
        3. Required fields match Pydantic model requirements
        4. No schema drift from previous versions

        Returns validation report with any issues found.
        """
        report = {
            "total_schemas": 0,
            "valid": 0,
            "errors": [],
            "warnings": []
        }

        expected_combinations = [
            # All 20 mode/complexity pairs
            ("debug", "simple"), ("debug", "workflow"),
            ("codereview", "simple"), ("codereview", "workflow"),
            # ... etc
        ]

        for mode, complexity in expected_combinations:
            report["total_schemas"] += 1
            try:
                schema = self.generate_schema(mode, complexity)

                # Validate schema structure
                if not self._is_valid_json_schema(schema):
                    report["errors"].append(
                        f"{mode}/{complexity}: Invalid JSON Schema structure"
                    )
                    continue

                # Check required fields
                model_class = self.mode_request_map[(mode, complexity)]
                required_fields = self._get_required_fields(model_class)
                schema_required = set(schema.get("required", []))

                if required_fields != schema_required:
                    report["warnings"].append(
                        f"{mode}/{complexity}: Required fields mismatch. "
                        f"Model: {required_fields}, Schema: {schema_required}"
                    )

                report["valid"] += 1

            except Exception as e:
                report["errors"].append(
                    f"{mode}/{complexity}: Generation failed - {e}"
                )

        return report
```

**Startup Integration in `server.py`:**

```python
# In server initialization
from tools.schema_generator import schema_generator

logger.info("Validating token optimization schemas...")
validation_report = schema_generator.validate_all_schemas()

if validation_report["errors"]:
    logger.error(f"Schema validation errors: {validation_report['errors']}")
    # Could fail-fast here or fall back to original tools

if validation_report["warnings"]:
    logger.warning(f"Schema warnings: {validation_report['warnings']}")

logger.info(
    f"Schema validation complete: "
    f"{validation_report['valid']}/{validation_report['total_schemas']} valid"
)
```

**Tasks:**
1. ✅ Implement `validate_all_schemas()` method
2. ✅ Add JSON Schema structure validation
3. ✅ Add required field consistency checks
4. ✅ Integrate validation into server startup
5. ✅ Add logging for validation results

### Step 4: Migrate Enhancement Data (2 hours)

**Extract UX enhancements from current hardcoded schemas:**

For each of the 20 mode/complexity combinations:
1. Identify field-level hints and examples
2. Extract weighted keywords (already in MODE_KEYWORDS)
3. Document tips and best practices
4. Create SCHEMA_ENHANCEMENTS entries

**Example:**

```python
SCHEMA_ENHANCEMENTS = {
    ("debug", "simple"): {
        "field_hints": {
            "problem": "Concise description of the bug or error",
            "files": "Relevant source files - focus on likely culprits",
            "confidence": "exploring: need investigation | medium: have theory | high: know cause",
            "hypothesis": "Your current theory about what's causing the issue"
        },
        "keywords": {
            "primary": ["bug", "error", "broken", "crash", "exception"],
            "secondary": ["fix", "debug", "issue", "problem"]
        },
        "tips": [
            "Include exact error messages when available",
            "List files you've already checked",
            "Mention recent changes that might be related"
        ],
        "working_example": {
            "problem": "OAuth tokens not persisting across sessions",
            "files": ["/src/auth.py", "/src/session.py"],
            "confidence": "exploring",
            "hypothesis": "Session storage might not be flushing to Redis"
        }
    },
    # ... 19 more combinations
}
```

**Tasks:**
1. ✅ Extract all field hints from current schemas
2. ✅ Migrate MODE_KEYWORDS to SCHEMA_ENHANCEMENTS
3. ✅ Document tips for each mode
4. ✅ Create working examples (some exist in `_get_working_example()`)
5. ✅ Validate no information loss during migration

### Step 5: Comprehensive Testing (2 hours)

**Test Plan:**

1. **Unit Tests** (`tests/test_schema_generator.py`):
   ```python
   def test_pydantic_schema_generation():
       """Verify base schemas match Pydantic models"""

   def test_enhancement_application():
       """Verify UX enhancements are applied correctly"""

   def test_schema_validation():
       """Verify all 20 schemas validate successfully"""

   def test_required_fields_match():
       """Verify required fields match Pydantic models"""
   ```

2. **Integration Tests** (existing test suite):
   - Run all 15 token optimization tests
   - Verify zen_select_mode returns correct schemas
   - Verify zen_execute validates requests correctly
   - Test smart stubs still work with generated schemas

3. **Manual Validation**:
   - Compare generated schemas to current hardcoded schemas
   - Verify field descriptions preserved
   - Check working examples still helpful
   - Ensure no token count regression

**Tasks:**
1. ✅ Create comprehensive unit test suite
2. ✅ Run existing 15 token optimization tests
3. ✅ Manual schema comparison (old vs new)
4. ✅ Verify no validation errors in test runs
5. ✅ Document any differences and rationale

## Testing Strategy

### Validation Checkpoints

1. **Pre-Refactoring Baseline:**
   - Capture current schema output for all 20 combinations
   - Document token counts for each mode
   - Save validation test results

2. **Post-Refactoring Comparison:**
   - Compare generated schemas to baseline
   - Verify token counts unchanged or improved
   - Ensure all validation tests still pass

3. **Regression Prevention:**
   - Add startup validation to detect drift
   - Create schema snapshot tests
   - Monitor validation error rates

### Test Coverage Goals

- ✅ 100% of 20 mode/complexity combinations tested
- ✅ All Pydantic fields represented in schemas
- ✅ All UX enhancements preserved
- ✅ No validation errors introduced
- ✅ Token counts stable or improved

## Benefits

### Immediate

1. **Eliminates Root Cause of Bugs:** Schema drift impossible - single source of truth
2. **Reduces Maintenance Burden:** Update Pydantic model → schema updates automatically
3. **Improves Code Quality:** Removes 326 lines of duplication
4. **Easier Updates:** Add new fields in one place (Pydantic model)

### Long-Term

1. **Prevents Future Bugs:** Startup validation catches issues before production
2. **Easier Evolution:** Can add new modes/complexities easily
3. **Better Documentation:** Pydantic models are self-documenting
4. **Type Safety:** Pydantic validation ensures correctness

## Risks and Mitigations

### Risk 1: Generated Schemas Don't Match Manual Schemas

**Mitigation:**
- Comprehensive baseline comparison before deployment
- Side-by-side testing of old vs new schemas
- Gradual rollout with feature flag

### Risk 2: UX Enhancements Lost in Translation

**Mitigation:**
- Explicit SCHEMA_ENHANCEMENTS configuration
- Manual review of all 20 combinations
- User testing with generated schemas

### Risk 3: Performance Regression

**Mitigation:**
- Schema generation happens once at startup
- Cache generated schemas in memory
- Benchmark token counts vs baseline

### Risk 4: Breaking Changes in Pydantic

**Mitigation:**
- Pin Pydantic version in requirements.txt
- Add tests for `.model_json_schema()` output format
- Monitor Pydantic release notes

## Timeline

**Total Estimated Time:** 8-10 hours

- **Step 1:** Create Schema Generator (2 hours)
- **Step 2:** Update mode_selector.py (2 hours)
- **Step 3:** Add Startup Validation (1 hour)
- **Step 4:** Migrate Enhancement Data (2 hours)
- **Step 5:** Comprehensive Testing (2-3 hours)
- **Buffer:** Documentation and refinement (1 hour)

## Rollout Strategy

### Phase 2a: Development Branch

1. Create feature branch: `feature/phase2-schema-refactoring`
2. Implement all changes per plan above
3. Run comprehensive test suite
4. Manual validation of all schemas

### Phase 2b: Testing and Validation

1. Deploy to test environment
2. Run full integration tests
3. Compare token counts to baseline
4. User acceptance testing

### Phase 2c: Production Deployment

1. Create PR to main repository
2. Code review with maintainers
3. Merge after approval
4. Monitor for any issues
5. Document any lessons learned

## Success Criteria

✅ All 20 mode/complexity schemas generated dynamically
✅ Zero validation errors in test suite
✅ UX enhancements preserved (field hints, examples, tips)
✅ Token counts stable or improved vs baseline
✅ Startup validation detects any schema drift
✅ Code reduction: ~326 lines removed from mode_selector.py
✅ Comprehensive test coverage maintained
✅ Documentation updated

## Follow-Up Work

After Phase 2 completion:

1. **Enhanced Validation:**
   - Add schema evolution tracking
   - Implement automated drift detection in CI/CD
   - Create schema changelog

2. **Developer Experience:**
   - Add CLI tool to preview generated schemas
   - Provide schema diff tool for reviews
   - Generate schema documentation automatically

3. **Performance Monitoring:**
   - Track token usage metrics over time
   - Monitor validation error rates
   - Optimize schema generation if needed

---

**Status:** Design Phase Complete - Ready for Implementation
**Target:** Separate PR after Phase 1 merges
**Author:** Claude Code with human oversight
**Date:** 2025-01-09
