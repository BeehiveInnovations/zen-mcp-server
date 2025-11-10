# Custom Tools Analysis: Overlaps and Consolidation Opportunities

## Executive Summary

The `/tools/custom/` directory contains **17 Python files** with significant overlaps, redundancy, and architectural debt:

- **3 Smart Consensus implementations** (main, v2, simple) with 5 support modules
- **2 Model selection systems** (dynamic_model_selector vs model_selector package)
- **2 Model evaluation tools** (model_evaluator.py vs model_evaluator/ package)
- **Unused support modules** that are imported but not actively used
- **High complexity** with overlapping responsibilities
- **Migration patterns** indicating incomplete refactoring

## Detailed Findings

### 1. SMART CONSENSUS FAMILY (Critical Consolidation Needed)

#### Current State
- **smart_consensus.py** (primary/canonical - 5,535 lines)
  - Complex workflow tool with Phase 1, 2, 3 features
  - Imports ALL support modules (cache, config, health, recovery, streaming, monitoring)
  - ~4,800+ lines of actual implementation
  - Supports parallel execution, cost optimization, intelligent fallback, enhanced synthesis
  - Features circuit breaker, health monitoring, error recovery, response streaming, token optimization

- **smart_consensus_v2.py** (newer/simpler - 655 lines)
  - Role-based consensus with org level configuration (startup/scaleup/enterprise)
  - Professional role assignments (code_reviewer, security_checker, etc.)
  - Simpler sequential execution model
  - MORE PRODUCTION-READY (cleaner, more focused)
  - Better documented and easier to understand

- **smart_consensus_simple.py** (wrapper/facade - 229 lines)
  - Facade pattern delegating to SmartConsensusTool (smart_consensus.py)
  - Converts simple interface (question + org_level) to workflow format
  - Usage logging and telemetry collection
  - Created Oct 2025 as "Phase 1 of Smart Consensus Simplification Plan"

#### Support Modules (All imported by smart_consensus.py)
- **smart_consensus_cache.py** (Thread-safe LRU with TTL)
  - CacheConfig, CacheEntry, CacheMetrics, SmartConsensusCache class
  - Comprehensive but appears functional

- **smart_consensus_config.py** (Configuration management)
  - OrgLevel enum, ConfigProfile enum, SmartConsensusConfigProfile dataclass
  - Validation and profile management
  - Phase 3 component - appears functional

- **smart_consensus_health.py** (Circuit breaker + monitoring)
  - CircuitBreakerState, CircuitBreakerConfig, HealthMetrics
  - HealthMonitor class
  - Phase 3 component - appears functional

- **smart_consensus_recovery.py** (Error recovery)
  - ErrorSeverity, ErrorCategory, ErrorPattern enums
  - RecoveryConfig dataclass
  - Phase 3 component - appears functional

- **smart_consensus_streaming.py** (Response streaming + token optimization)
  - StreamingMode enum, TokenOptimizationConfig, TokenUsageMetrics
  - ContextOptimizer, ResponseOptimizer, StreamingManager, TokenUsageTracker
  - Phase 3 component - appears functional

- **smart_consensus_monitoring.py** (Production monitoring)
  - StateMetrics, StateAlert dataclasses
  - StateMetricsCollector class
  - Appears functional but dated (Phase 3 component)

#### Problem
- **No usage of support modules in codebase** (only smart_consensus.py imports them)
- smart_consensus.py is complex and heavy (5,535 lines)
- smart_consensus_v2.py is cleaner but overlaps with smart_consensus.py
- smart_consensus_simple.py wraps smart_consensus.py with usage tracking
- Confusing: "v2" is actually simpler than original, but original has more features
- Unclear which is canonical or should be used

#### Consolidation Recommendation
1. **Keep smart_consensus_v2.py as the primary public tool** (cleaner, role-based)
2. **Make it a WorkflowTool if needed** (currently SimpleTool facade)
3. **Remove smart_consensus.py** (too complex, features rarely used)
4. **Deprecate smart_consensus_simple.py** (no longer needed if v2 is simplified)
5. **Archive support modules** (can restore if features needed, but not importing)
6. **Focus on role-based model selection** (more valuable than Phase 2/3 features)

---

### 2. MODEL SELECTION DUPLICATION

#### Current State

**dynamic_model_selector.py** (tool wrapper - 100+ lines)
- SimpleTool that wraps model_selector package
- DynamicModelSelectorRequest: requirements, task_type, complexity_level, budget_preference, num_models
- Currently delegating to model_selector package
- Marked as "Intelligently selects optimal AI models based on requirements"

**model_selector/ package** (sophisticated library)
- Full directory with 60+ files
- Modular architecture with v2.0 refactoring
- Components: data_types, data_repository, model_selector, cost_estimator, fallback_strategy, etc.
- Services layer: ModelSelectionService, CachingService, BandEvaluationService, etc.
- Very comprehensive (~2,500+ lines total)

**band_selector.py** (70+ lines)
- BandSelector class using band configuration system
- Loads models.csv and bands_config.json
- Filters by org_level (startup->junior, scaleup->senior, enterprise->executive)
- Appears to be a simpler alternative to the full model_selector package

#### Problem
- **Two model selection systems**: dynamic_model_selector.py + model_selector/ package
- **Three model selection approaches**: DynamicModelSelector, BandSelector, full orchestrator
- **Unclear relationship**: Which should be used? Are they compatible?
- **Over-engineered**: model_selector has 60 files for what BandSelector does in 70 lines
- **Possible migration**: dynamic_model_selector.py might be wrapper from PromptCraft migration

#### Consolidation Recommendation
1. **Evaluate which system is actually used**
   - Is model_selector/ package feature-complete?
   - Is BandSelector sufficient for all use cases?
   - Can DynamicModelSelector delegate to one primary system?
2. **Standardize on one approach**
   - Option A: Keep full model_selector/ package, make it the source of truth
   - Option B: Simplify to BandSelector + core selection logic
3. **Clean up exports**: Ensure consistent naming and API surface

---

### 3. MODEL EVALUATOR DUPLICATION

#### Current State

**model_evaluator.py** (300+ lines)
- WorkflowTool that evaluates models from OpenRouter URLs
- Imports from model_evaluator/ package (circular/confusing)
- References: DynamicModelSelector (line 40)
- Dataclasses: ModelMetrics, enums for Tier, OrgLevel, Specialization, etc.

**model_evaluator/ package** (directory with ~20 files)
- Modular evaluation system
- Components: classification/, config/, reporting/, scoring/, web_scraping/
- ModelEvaluator class as main interface
- Sophisticated scoring and classification system

#### Problem
- **Same name for tool and package**: Confusing imports
- **Circular reference**: model_evaluator.py imports from model_evaluator/ package
- **Two implementations**: Tool duplicates package functionality
- **web_scraping/ component**: Only used by package, not tool

#### Consolidation Recommendation
1. **Rename model_evaluator.py** → something like `model_analysis.py` or `evaluate_new_model.py`
2. **Make it a proper wrapper** around model_evaluator/ package (don't duplicate logic)
3. **Or consolidate into single tool** if web scraping is core requirement
4. **Clean up imports** to avoid circular references

---

### 4. PR TOOLS RELATIONSHIP

#### Current State

**pr_prepare.py** (300+ lines)
- Comprehensive PR preparation: branch validation, git analysis, change assessment
- PR template population, GitHub integration, dependency validation
- Dry run, draft PR creation, automatic pushing
- What the Diff integration
- Migrated from PromptCraft's workflow-prepare-pr

**pr_review.py** (partial - 100+ lines visible)
- AI-powered PR review analysis
- Quality issue detection and categorization
- Consensus-based recommendations (integrates with layered_consensus)
- Recommendation generation: APPROVE, REQUEST_CHANGES, COMMENT
- Org level determination for consensus depth

#### Problem
- **Complementary rather than overlapping** (prepare vs review)
- **Dependency relationship**: pr_review depends on pr_prepare output
- **Tool isolation**: Both are standalone tools, could be more integrated

#### Assessment
- **No consolidation needed** - these serve different purposes
- **Consider**: metadata exchange between tools if workflows combine them

---

### 5. LAYERED CONSENSUS

#### Current State

**layered_consensus.py** (tool - 80+ lines visible)
- SimpleTool that provides layered consensus analysis
- Request model: question, org_level, model_count, layers, cost_threshold
- Layers: strategic, analytical, practical, technical
- Distributes models across layers

#### Relationship to Smart Consensus
- **Different approach**: Layered distribution vs role-based assignment
- **Used by**: pr_review.py calls it via _call_zen_tool("layered_consensus", ...)
- **org_level support**: Similar to smart_consensus_v2 (startup/scaleup/enterprise)

#### Problem
- **Design conflict with smart_consensus_v2**: Both provide multi-model consensus with org levels
- **Unclear differentiation**: What's the actual difference?
- **Integration point**: pr_review specifically uses layered_consensus, not smart_consensus

#### Consolidation Recommendation
1. **Clarify the design difference**:
   - smart_consensus_v2: Role-based (code_reviewer, architect, etc.)
   - layered_consensus: Layer-based (strategic, analytical, practical)
2. **Merge or specialize**:
   - Option A: Consolidate into smart_consensus_v2 with layer support
   - Option B: Keep layered as specialized variant for specific workflows (pr_review)
3. **Update pr_review** to use consolidated tool if merged

---

### 6. PROMPTCRAFT MIGRATION ARTIFACTS

**promptcraft_mcp_bridge.py** + **promptcraft_mcp_client/** (directory)
- Bridge protocol for PromptCraft MCP client
- Subprocess management, error handling
- Appears to be infrastructure for external PromptCraft integration
- Not related to other custom tools

#### Assessment
- **Separate concern**: Integration infrastructure, not business logic
- **Keep separate**: No consolidation needed unless removing PromptCraft support

---

## Summary Table

| File | Type | Lines | Status | Issue | Recommendation |
|------|------|-------|--------|-------|-----------------|
| smart_consensus.py | Main | 5,535 | Complex | Too heavy, overlaps v2 | Remove |
| smart_consensus_v2.py | Alternative | 655 | Good | Cleaner design | Keep as primary |
| smart_consensus_simple.py | Wrapper | 229 | Redundant | Facade to main | Remove |
| smart_consensus_cache.py | Support | 300+ | Functional | Not imported | Archive |
| smart_consensus_config.py | Support | 200+ | Functional | Not imported | Archive |
| smart_consensus_health.py | Support | 200+ | Functional | Not imported | Archive |
| smart_consensus_recovery.py | Support | 200+ | Functional | Not imported | Archive |
| smart_consensus_streaming.py | Support | 250+ | Functional | Not imported | Archive |
| smart_consensus_monitoring.py | Support | 200+ | Functional | Not imported | Archive |
| dynamic_model_selector.py | Tool | 100+ | Active | Overlaps model_selector | Consolidate |
| band_selector.py | Utility | 70+ | Active | Duplicates selection logic | Evaluate |
| model_selector/ | Package | 2500+ | Complex | Comprehensive but overpowered | Simplify or remove |
| model_evaluator.py | Tool | 300+ | Active | Circular reference with package | Rename + clean |
| model_evaluator/ | Package | 1000+ | Complex | Duplicates evaluator.py | Consolidate |
| pr_prepare.py | Tool | 300+ | Active | Core functionality | Keep |
| pr_review.py | Tool | 200+ | Active | Depends on pr_prepare | Keep |
| layered_consensus.py | Tool | 80+ | Active | Overlaps smart_consensus_v2 | Merge or specialize |
| promptcraft_mcp_bridge.py | Bridge | 100+ | Active | Infrastructure | Keep (separate) |

---

## Consolidation Action Plan

### Phase 1: Smart Consensus Cleanup (Immediate)
```
1. Keep: smart_consensus_v2.py (rename to smart_consensus.py)
2. Remove: smart_consensus.py (archive as backup)
3. Remove: smart_consensus_simple.py (v2 is already simple)
4. Archive: smart_consensus_*support*.py (cache, config, health, etc.)
   - Tag in git, move to docs/archived/
   - Keep import stubs for backward compatibility if needed
```

Result: 1 primary smart_consensus tool instead of 3 implementations + 6 support modules

### Phase 2: Model Selection Consolidation
```
1. Audit actual usage of model_selector/ package
2. If band-based selection is sufficient:
   - Simplify dynamic_model_selector to use BandSelector
   - Archive model_selector/ package
3. If full features needed:
   - Remove duplicate logic from dynamic_model_selector.py
   - Make it thin wrapper around model_selector/ package
4. Document which system to use where
```

### Phase 3: Model Evaluator Clarification
```
1. Rename model_evaluator.py → model_analysis.py or evaluate_openrouter.py
2. Remove duplicate class definitions
3. Make it proper wrapper/client to model_evaluator/ package
4. Or: Consolidate evaluation logic into single canonical implementation
5. Resolve circular imports
```

### Phase 4: Layered Consensus Decision
```
1. Define relationship between layered_consensus and smart_consensus_v2
2. If redundant: Merge features into smart_consensus_v2
3. If specialized: Create smart_consensus_layered variant
4. Update pr_review to use consolidated tool
```

---

## Estimated Impact

- **Lines of code reduction**: 2,000+ lines (consolidation)
- **Complexity reduction**: 40-50% (fewer overlapping implementations)
- **Maintenance burden**: Significantly reduced (fewer versions to maintain)
- **Backward compatibility**: Need migration plan for external users
- **Development velocity**: Faster feature development on single codebase

---

## Critical Assumptions

1. **smart_consensus.py features are rarely used**
   - Phase 2 parallel execution
   - Phase 3 caching, circuit breaker, streaming
   - If these are critical, need different consolidation approach

2. **model_selector/ package is either over-engineered or under-used**
   - If heavily used: keep it, remove duplicates
   - If rarely used: simplify to BandSelector

3. **pr_review specifically needs layered_consensus**
   - May indicate layered approach is important
   - But could also be consolidated into role-based system

4. **External tools depend on current API surface**
   - Need migration period for deprecation
   - Backward compatibility stubs may be needed

---

## References

### File Locations
- `/home/byron/dev/zen-mcp-server/tools/custom/` - All custom tools
- `/home/byron/dev/zen-mcp-server/tools/custom/model_selector/` - Model selection package
- `/home/byron/dev/zen-mcp-server/tools/custom/model_evaluator/` - Model evaluation package

### Key Lines of Code
- smart_consensus.py lines 20-47: All support module imports
- smart_consensus_v2.py lines 36-105: Role definitions (valuable asset)
- dynamic_model_selector.py lines 22-28: Imports from model_selector package
- pr_review.py lines 1-10: Calls layered_consensus tool

