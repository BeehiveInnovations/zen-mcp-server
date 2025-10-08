# Zen MCP Server - UX Improvement Plan

## Executive Summary

**Critical Finding**: The two-stage token optimization architecture achieves 82% token reduction but **sacrifices usability to the point where users cannot successfully use the tools**.

**User Impact**: Real-world testing showed a user attempting 6+ different approaches over 4000+ tokens with **zero successful outputs**. This is a complete UX failure despite the technical achievement.

**Root Cause**: We optimized for tokens at the expense of clarity, documentation, and error handling.

**Recommendation**: Implement Critical Fixes immediately before any PR submission. The current implementation will frustrate users and damage adoption.

---

## Issue Analysis

### 🔴 Critical Issue #1: Broken Backward Compatibility

**What Happens:**
```
User: calls mcp__zen__analyze(request="Review this code")
Zen: "Tool 'analyze' has been optimized. Please use 'zen_execute'"
User: calls zen_execute(mode='analyze', ...)
Zen: ValidationError - missing required fields
```

**Root Cause:**
- Stub tools only redirect, don't provide working schema
- User follows redirect but gets validation errors
- No clear path from stub → working call

**Impact**: High - Users expect tools by name to work. Our stubs are false advertising.

**Current Code Problem:**
```python
# tools/mode_selector.py - compatibility stub
async def execute(self, arguments: dict[str, Any]) -> list:
    # Just redirects to zen_select_mode
    # Doesn't validate or transform arguments
    # Doesn't show complete schema requirements
```

### 🔴 Critical Issue #2: Vague Field Requirements

**Example Errors:**
```
ValidationError: total_steps Field required
  (User didn't know this field exists)

ValidationError: relevant_files Field required
  (User provided 'files' instead)
```

**Root Cause:**
- zen_select_mode returns generic guidance: "Provide your request based on examples above"
- No actual examples shown
- Field names inconsistent between modes
- Required fields not documented in response

**Impact**: High - Users cannot construct valid requests even after mode selection

**Current Response:**
```json
{
  "field_guidance": {
    "general": "Provide your request based on the examples above"
  },
  "tips": ["Use the examples as a guide"]
}
```

**What Users Actually Need:**
```json
{
  "required_fields": {
    "step": "string - Current workflow step description",
    "step_number": "integer - 1, 2, 3, etc.",
    "total_steps": "integer - Total workflow steps",
    "findings": "string - What you've discovered so far",
    "next_step_required": "boolean - true if more investigation needed"
  },
  "example": {
    "mode": "analyze",
    "complexity": "workflow",
    "request": {
      "step": "Initial architecture review",
      "step_number": 1,
      "total_steps": 3,
      "findings": "Examining system design...",
      "next_step_required": true
    }
  }
}
```

### 🔴 Critical Issue #3: Poor Mode Selection

**Example:**
```
User request: "Architectural review of completed system"
Zen selected: mode='debug', complexity='workflow'
Expected: mode='analyze' or 'codereview'
```

**Root Cause:**
```python
# tools/mode_selector.py
MODE_KEYWORDS = {
    "debug": ["error", "bug", "broken", "fix", "issue", "problem"],
    "analyze": ["analyze", "analysis", "examine", "inspect"],
    # ...
}

# Problem: "review" appears in multiple modes
# Problem: No weighting or context awareness
# Problem: No explanation of selection logic
```

**Impact**: Medium-High - Wrong tool selection leads to inappropriate schemas and confusion

### 🟡 Medium Issue #4: Schema Complexity Mismatch

**Problem:**
- `simple` complexity: requires {relevant_files, analysis_type, context}
- `workflow` complexity: requires {step, step_number, total_steps, findings, next_step_required}
- `expert` complexity: requires unknown fields (undocumented)

**Impact**: Medium - Users can't switch complexities without completely restructuring requests

### 🟡 Medium Issue #5: No Workflow Enforcement

**Problem:**
- zen_execute can be called directly (fails with validation errors)
- Individual tools can be called (redirect without clear path)
- No guidance to use two-stage pattern

**Impact**: Medium - Users waste tokens trying wrong approaches

### 🟡 Medium Issue #6: Token Optimization Irony

**Claim**: "Saves 82% tokens"
**Reality**: User spent 4000+ tokens trying to get any successful response

**Impact**: High (perception) - Marketing claim undermined by poor UX

---

## Proposed Solutions

### 🚨 Critical Fixes (Must-Have Before PR)

#### Fix 1: Make Stub Tools Actually Work

**Option A: Smart Stubs (Recommended)**
```python
class CompatibilityStub(BaseTool):
    """Stub that actually works by internally using two-stage flow."""

    async def execute(self, arguments: dict[str, Any]) -> list:
        # Step 1: Auto-select mode (internal, no user interaction)
        mode_result = await mode_selector.execute({
            "task_description": arguments.get("request", ""),
            "confidence_level": "medium"
        })

        # Step 2: Build valid request for zen_execute
        mode_data = json.loads(mode_result[0].text)

        # Step 3: Transform user's simple request to valid zen_execute format
        if mode_data["complexity"] == "workflow":
            # Auto-generate workflow structure
            request = {
                "step": "Initial investigation",
                "step_number": 1,
                "total_steps": 1,
                "findings": arguments.get("request", ""),
                "next_step_required": False
            }
        else:
            # Use simple schema
            request = {
                "prompt": arguments.get("request", ""),
                "relevant_files": arguments.get("files", [])
            }

        # Step 4: Call zen_execute internally
        return await zen_execute.execute({
            "mode": mode_data["selected_mode"],
            "complexity": mode_data["complexity"],
            "request": request
        })
```

**Pros**: Users can call any tool name and it "just works"
**Cons**: Adds 2 internal tool calls (but user doesn't see this)

**Option B: Remove Stubs Entirely**
```python
# Only expose:
# - zen_select_mode
# - zen_execute

# Remove all compatibility stubs
# Update documentation to only show two-stage pattern
```

**Pros**: Simpler, clearer API
**Cons**: Breaking change, no backward compatibility

**Recommendation**: Implement Option A for backward compatibility, but add config option to disable stubs.

#### Fix 2: Complete Schema Documentation

**Update zen_select_mode response:**
```python
# tools/mode_selector.py - Updated response

response = {
    "status": "mode_selected",
    "selected_mode": selected_mode,
    "complexity": complexity,
    "reasoning": f"Selected '{selected_mode}' because: {self._explain_selection(task_lower, mode_scores)}",

    # CRITICAL: Full schema specification
    "required_schema": self._get_schema_for_mode(selected_mode, complexity),

    # CRITICAL: Working example
    "working_example": self._get_example_for_mode(selected_mode, complexity),

    # Keep existing
    "next_step": {...},
    "token_savings": "...",
}

def _get_schema_for_mode(self, mode: str, complexity: str) -> dict:
    """Return complete JSON schema for this mode/complexity combination."""
    if mode == "debug" and complexity == "workflow":
        return {
            "type": "object",
            "required": ["step", "step_number", "total_steps", "findings", "next_step_required"],
            "properties": {
                "step": {
                    "type": "string",
                    "description": "Description of current investigation step",
                    "example": "Initial investigation of OAuth token persistence"
                },
                "step_number": {
                    "type": "integer",
                    "description": "Current step number (1, 2, 3, ...)",
                    "example": 1
                },
                "total_steps": {
                    "type": "integer",
                    "description": "Total number of planned investigation steps",
                    "example": 3
                },
                "findings": {
                    "type": "string",
                    "description": "What you've discovered so far in this step",
                    "example": "OAuth tokens not persisting across browser sessions"
                },
                "next_step_required": {
                    "type": "boolean",
                    "description": "Whether more investigation steps are needed",
                    "example": true
                }
            }
        }
    # ... schemas for all mode/complexity combinations

def _get_example_for_mode(self, mode: str, complexity: str) -> dict:
    """Return copy-paste ready working example."""
    if mode == "debug" and complexity == "workflow":
        return {
            "mode": "debug",
            "complexity": "workflow",
            "request": {
                "step": "Initial investigation",
                "step_number": 1,
                "total_steps": 3,
                "findings": "Users report OAuth tokens not persisting across sessions",
                "next_step_required": true
            }
        }
    # ... examples for all combinations
```

#### Fix 3: Improve Mode Selection Logic

**Add reasoning and scoring:**
```python
def _explain_selection(self, task: str, mode_scores: dict) -> str:
    """Explain why this mode was selected."""
    explanations = []

    top_mode = max(mode_scores, key=mode_scores.get)
    top_score = mode_scores[top_mode]

    # Find matching keywords
    matched_keywords = []
    for keyword in MODE_KEYWORDS[top_mode]:
        if keyword in task:
            matched_keywords.append(keyword)

    if matched_keywords:
        explanations.append(f"Task contains keywords: {', '.join(matched_keywords)}")

    # Show alternatives
    alternatives = sorted(
        [(mode, score) for mode, score in mode_scores.items() if mode != top_mode],
        key=lambda x: x[1],
        reverse=True
    )[:2]

    if alternatives:
        alt_text = ", ".join([f"{mode} (score: {score})" for mode, score in alternatives])
        explanations.append(f"Alternatives considered: {alt_text}")

    return "; ".join(explanations)
```

**Improve keyword mapping:**
```python
MODE_KEYWORDS = {
    "debug": {
        "primary": ["error", "bug", "broken", "crash", "fail"],
        "secondary": ["fix", "issue", "problem", "troubleshoot"]
    },
    "analyze": {
        "primary": ["architecture", "design", "structure", "pattern"],
        "secondary": ["analyze", "examine", "inspect", "understand"]
    },
    "codereview": {
        "primary": ["review", "audit", "assess", "evaluate"],
        "secondary": ["quality", "security", "performance", "best practices"]
    },
    # Weight primary keywords 2x
}
```

#### Fix 4: Better Error Messages

**Update zen_execute validation errors:**
```python
# tools/zen_execute.py

try:
    validated_request = RequestModel(**request_data)
except ValidationError as e:
    # Enhanced error message
    error_details = []
    for error in e.errors():
        field = error['loc'][0]
        error_type = error['type']

        if error_type == 'missing':
            # Show what the field is for and example
            field_info = FIELD_DESCRIPTIONS.get(field, {})
            error_details.append({
                "field": field,
                "error": "Required field missing",
                "description": field_info.get("description", "No description available"),
                "example": field_info.get("example", "N/A"),
                "type": field_info.get("type", "unknown")
            })

    return [{
        "type": "text",
        "text": json.dumps({
            "status": "validation_error",
            "message": f"Request validation failed for {mode} mode with {complexity} complexity",
            "errors": error_details,
            "hint": "Use zen_select_mode first to get the correct schema and examples",
            "schema_reference": f"See required_schema in zen_select_mode response for {mode}/{complexity}"
        }, indent=2)
    }]
```

### 🟡 Medium-Priority Improvements

#### Improvement 1: Adaptive Complexity

**Auto-detect complexity from request content:**
```python
def _auto_detect_complexity(self, request: dict) -> str:
    """Automatically detect appropriate complexity level."""

    # Check if request already has workflow structure
    if all(k in request for k in ["step", "step_number", "total_steps"]):
        return "workflow"

    # Check request size and detail
    request_text = json.dumps(request)
    if len(request_text) < 200:
        return "simple"
    elif len(request_text) < 1000:
        return "workflow"
    else:
        return "expert"
```

#### Improvement 2: Progressive Workflow

**Start simple, escalate if needed:**
```python
# zen_execute first try with simple schema
# If AI indicates need for multi-step, auto-upgrade to workflow
# User doesn't need to know about complexity levels
```

#### Improvement 3: Working Examples Library

**Create `examples/` directory with real working examples:**
```json
// examples/debug_oauth_issue.json
{
  "description": "Debug OAuth token persistence issue",
  "stage_1_call": {
    "tool": "zen_select_mode",
    "arguments": {
      "task_description": "Debug why OAuth tokens aren't persisting across browser sessions",
      "confidence_level": "exploring"
    }
  },
  "stage_1_response": {
    "selected_mode": "debug",
    "complexity": "workflow"
  },
  "stage_2_call": {
    "tool": "zen_execute",
    "arguments": {
      "mode": "debug",
      "complexity": "workflow",
      "request": {
        "step": "Initial investigation",
        "step_number": 1,
        "total_steps": 3,
        "findings": "Users must re-authenticate after closing browser",
        "next_step_required": true
      }
    }
  }
}
```

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Before PR) - 4-6 hours

**Priority 1 (Blocking):**
- [ ] Implement smart compatibility stubs (Fix 1, Option A)
- [ ] Add complete schema documentation to zen_select_mode (Fix 2)
- [ ] Add working examples to zen_select_mode (Fix 2)
- [ ] Improve mode selection logic and add reasoning (Fix 3)

**Priority 2 (High):**
- [ ] Enhanced error messages in zen_execute (Fix 4)
- [ ] Update CLAUDE.md with clearer examples
- [ ] Add troubleshooting guide to README.md

**Testing:**
- [ ] Test all stub tools end-to-end
- [ ] Verify schema documentation completeness
- [ ] Test mode selection with 20+ example queries
- [ ] Validate error messages are helpful

### Phase 2: Medium Improvements (Post-PR) - 6-8 hours

- [ ] Adaptive complexity detection (Improvement 1)
- [ ] Progressive workflow escalation (Improvement 2)
- [ ] Working examples library (Improvement 3)
- [ ] Interactive schema builder concept
- [ ] Telemetry for mode selection accuracy

### Phase 3: Long-term Vision (Future) - TBD

- [ ] ML-based mode selection
- [ ] Natural language request parsing
- [ ] Auto-schema inference from request
- [ ] Unified single-call API option

---

## Updated Token Analysis

### Current Reality (with UX issues):

```
User Experience:
  Attempts: 6+
  Tokens spent: ~4,000
  Successful outputs: 0
  Frustration: High

Actual Token "Savings": NEGATIVE
  (More tokens wasted on failed attempts than saved by optimization)
```

### After Critical Fixes:

```
User Experience:
  First attempt: Works (stub tools or proper two-stage)
  Tokens per successful call: ~2,000
  Success rate: 95%+

Token Savings (Real):
  Baseline: 43,000 tokens (18 tools)
  Optimized: 7,800 tokens (with working stubs)
  Actual savings: 35,200 tokens per session
  User confidence: High
```

---

## PR Impact Assessment

### Current PR Status: **NOT READY**

**Blocking Issues:**
1. ❌ Users cannot successfully use the tools
2. ❌ Documentation doesn't match reality
3. ❌ Error messages are unhelpful
4. ❌ Token optimization claim undermined by poor UX

**Recommendation**: **DO NOT submit PR** until Phase 1 Critical Fixes are complete.

### After Phase 1 Fixes: **READY FOR PR**

**Strengths:**
1. ✅ 82% token reduction verified
2. ✅ Tools actually work end-to-end
3. ✅ Clear documentation with examples
4. ✅ Helpful error messages
5. ✅ Backward compatibility that works

---

## Metrics for Success

### Before Improvements (Current):
- User success rate: ~0% (failed all attempts)
- Tokens wasted on errors: 4,000+
- User sentiment: Frustrated

### After Phase 1 (Target):
- User success rate: >90% on first attempt
- Tokens wasted on errors: <500
- User sentiment: Satisfied

### After Phase 2 (Goal):
- User success rate: >95%
- Average tokens per task: <2,000
- User sentiment: Delighted

---

## Conclusion

The two-stage token optimization is **technically sound but UX-broken**. We achieved our token reduction goal but failed the primary objective: **making AI tools more usable**.

### Key Realizations:

1. **Token optimization is worthless if tools don't work**
2. **Backward compatibility stubs must actually work, not just redirect**
3. **Clear documentation > clever optimization**
4. **Users need examples, not generic guidance**

### Immediate Action Required:

**PAUSE PR submission. Implement Phase 1 Critical Fixes first.**

The feedback from real-world usage is invaluable. Better to delay the PR and ship something that works than rush out a technically impressive but unusable tool.

### Estimated Timeline:

- Phase 1 Critical Fixes: 4-6 hours
- Testing and validation: 2-3 hours
- Updated PR materials: 1 hour
- **Total delay: ~1 day**

This delay is acceptable and necessary for a quality implementation.

---

**Report Generated**: 2025-10-07
**Status**: Awaiting approval to implement Critical Fixes
**Next Step**: Implement smart compatibility stubs and enhanced documentation
