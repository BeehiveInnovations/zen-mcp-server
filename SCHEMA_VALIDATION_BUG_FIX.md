# Schema Validation Bug Fix - Critical Issue

**Date**: 2025-10-07
**Severity**: CRITICAL - Tool unusable due to schema mismatch
**Status**: In Progress

---

## Problem Description

The zen_select_mode tool advertises one schema in its response, but zen_execute validates against a completely different schema. This makes the two-stage token optimization unusable.

### User Report

```
// What zen_select_mode returns:
"required_schema": {
  "required": ["prompt"],  // Says only prompt needed
  "properties": {
    "prompt": {"type": "string"}
  }
}

// What zen_execute actually validates:
Errors: [
  "step - Field required",
  "step_number - Field required",
  "total_steps - Field required",
  "findings - Field required",
  "next_step_required - Field required"
]
```

---

## Root Cause Analysis

### Issue 1: Incomplete Schema Definitions

`mode_selector.py` (`_get_complete_schema` method) only defines schemas for 5 mode/complexity combinations:
- ("debug", "simple")
- ("debug", "workflow")
- ("analyze", "simple")
- ("codereview", "simple")
- ("chat", "simple")

But there are 10 modes × 2 complexities = **20 combinations** needed:
- debug (simple, workflow)
- codereview (simple, workflow)
- analyze (simple, workflow)
- consensus (simple, workflow)
- chat (simple, workflow)
- security (simple, workflow)
- refactor (simple, workflow)
- testgen (simple, workflow)
- planner (simple, workflow)
- tracer (simple, workflow)

**Missing**: 15 combinations fall back to generic {"required": ["prompt"]} schema

### Issue 2: Wrong Complexity Value

`_determine_complexity` can return "expert", but:
- NO request models exist for "expert" complexity in mode_executor.py
- MODE_REQUEST_MAP only has "simple" and "workflow" complexities
- This causes all "expert" selections to fall back to generic schema

### Issue 3: Schema Mismatches

Even the existing schemas don't match the actual Pydantic models:

**Example: ("analyze", "simple")**
- mode_selector says: required ["relevant_files", "analysis_type"]
- AnalyzeSimpleRequest actually requires: ["step", "step_number", "total_steps", "next_step_required", "findings", "relevant_files"]

---

## Complete Required Field Mapping

Based on `mode_executor.py` Pydantic models:

### debug
- **simple**: required ["problem"], optional ["files", "confidence", "hypothesis"]
- **workflow**: required ["step", "step_number", "findings", "next_step_required"], optional ["total_steps", "files_checked", "confidence"]

### codereview
- **simple**: required ["files"], optional ["review_type", "focus"]
- **workflow**: required ["step", "step_number", "total_steps", "next_step_required", "findings"], optional ["files_checked", "relevant_files", "relevant_context", "issues_found", "confidence", "review_validation_type"]

### analyze
- **simple**: required ["relevant_files"] + workflow fields ["step", "step_number", "total_steps", "next_step_required", "findings"], optional ["files_checked", "relevant_context", "issues_found", "confidence", "analysis_type", "output_format"]
- **workflow**: same as simple (reuses AnalyzeSimpleRequest)

### consensus
- **simple**: required ["prompt", "models"], optional ["relevant_files", "images"]
- **workflow**: required ["models"] + workflow fields ["step", "step_number", "total_steps", "next_step_required", "findings"], optional ["files_checked", "relevant_files", "relevant_context", "issues_found", "confidence", "current_model_index", "model_responses"]

### chat
- **simple**: required ["prompt"], optional ["model", "temperature", "images"]
- **workflow**: same as simple (reuses ChatRequest)

### security
- **simple**: required workflow fields ["step", "step_number", "total_steps", "next_step_required", "findings"], optional ["files_checked", "relevant_files", "relevant_context", "issues_found", "confidence", "security_scope", "threat_level", "compliance_requirements", "audit_focus", "severity_filter"]
- **workflow**: same as simple (reuses SecurityWorkflowRequest)

### refactor
- **simple**: required workflow fields ["step", "step_number", "total_steps", "next_step_required", "findings"], optional ["files_checked", "relevant_files", "relevant_context", "issues_found", "confidence", "refactor_type", "focus_areas", "style_guide_examples"]
- **workflow**: same as simple (reuses RefactorSimpleRequest)

### testgen
- **simple**: required ["relevant_files"] + workflow fields ["step", "step_number", "total_steps", "next_step_required", "findings"], optional ["files_checked", "relevant_context", "issues_found", "confidence"]
- **workflow**: same as simple (reuses TestGenSimpleRequest)

### planner
- **simple**: required workflow fields ["step", "step_number", "total_steps", "next_step_required", "findings"], optional ["files_checked", "relevant_files", "relevant_context", "issues_found", "confidence", "is_step_revision", "revises_step_number", "is_branch_point", "branch_from_step", "branch_id", "more_steps_needed"]
- **workflow**: same as simple (reuses PlannerWorkflowRequest)

### tracer
- **simple**: required ["target"] + workflow fields ["step", "step_number", "total_steps", "next_step_required", "findings"], optional ["files_checked", "relevant_files", "relevant_context", "issues_found", "confidence", "trace_mode", "files"]
- **workflow**: same as simple (reuses TracerSimpleRequest)

---

## Fix Plan

### 1. Fix _determine_complexity (Line 266-296)
Remove "expert" complexity, only return "simple" or "workflow"

### 2. Complete _get_complete_schema (Line 481-592)
Add all 20 mode/complexity combinations with correct required fields matching Pydantic models

### 3. Complete _get_working_example (Line 594+)
Add all 20 examples with valid request structures

---

## Testing Plan

After fix:
1. Test zen_select_mode for each mode
2. Verify returned schema matches actual validation
3. Test zen_execute with the working_example from zen_select_mode
4. Confirm no validation errors

---

## Fix Implemented

**Date**: 2025-10-07
**Status**: ✅ FIXED - Ready for testing

### Changes Made

#### 1. Fixed `_determine_complexity` Method
- Removed "expert" complexity (doesn't exist in mode_executor.py)
- Map complex/expert indicators to "workflow" instead
- Now only returns "simple" or "workflow"
- Updated docstring to clarify only 2 complexities exist

#### 2. Completely Rewrote `_get_complete_schema` Method
- Added all 20 mode/complexity combinations
- Each schema matches the exact Pydantic model in mode_executor.py
- Used common workflow_fields dict to reduce duplication
- Removed generic fallback (all combinations now defined)
- Added error logging if combination is missing

**Schema Coverage**:
- debug (simple, workflow) ✅
- codereview (simple, workflow) ✅
- analyze (simple, workflow) ✅
- consensus (simple, workflow) ✅
- chat (simple, workflow) ✅
- security (simple, workflow) ✅
- refactor (simple, workflow) ✅
- testgen (simple, workflow) ✅
- planner (simple, workflow) ✅
- tracer (simple, workflow) ✅

**Total**: 20/20 combinations (100% coverage)

#### 3. Completely Rewrote `_get_working_example` Method
- Added all 20 working examples
- Each example matches the required fields from schemas
- Fixed incorrect examples (e.g., analyze/simple now includes workflow fields)
- Removed generic fallback (all combinations now defined)
- Added error logging if example is missing

### Key Fixes

**Before**:
- Only 5 combinations defined
- "expert" complexity caused fallback to generic ["prompt"] schema
- Many modes (security, refactor, etc.) had no schemas
- Schema mismatches (e.g., analyze/simple)

**After**:
- All 20 combinations defined
- Only "simple" and "workflow" complexities
- Every mode has both simple and workflow schemas
- All schemas verified against Pydantic models
- All examples match their schemas

---

**Status**: Ready for Docker rebuild and testing
