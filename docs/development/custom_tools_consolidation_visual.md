# Custom Tools Consolidation - Visual Architecture

## Current State: Smart Consensus Complexity

```
                         smart_consensus.py
                         (5,535 lines)
                              |
                    ┌─────────┼─────────────┬────────────┬─────────────┐
                    |         |             |            |             |
                    v         v             v            v             v
            cache     config   health    recovery   streaming      monitoring
          (300+)   (200+)   (200+)     (200+)      (250+)          (200+)
            
            BUT: Only imported, never used directly!
```

**Problem**: 
- 9 files total (1 main + 2 alternatives + 6 support modules)
- 5,535 + 655 + 229 + 1,550 (support) = 8,000+ lines
- Two "v2" variants, neither clearly marked as canonical
- Support modules imported but unused - "Phase 3" features never implemented in practice

---

## Target State: Smart Consensus Simplified

```
                    smart_consensus_v2.py
                        (655 lines)
                             |
         ┌───────────────────┼────────────────────┐
         |                   |                    |
      org_level           roles              model_pool
    (startup/             (code_reviewer,   (free/premium
     scaleup/            architect,etc.)    fallback)
    enterprise)
```

**Benefits**:
- Single, clean implementation
- Role-based professional perspectives
- Org-level configuration (proven pattern)
- 655 lines vs 8,000+ lines
- Features user-facing, not internal optimizations

---

## Model Selection Architecture Confusion

```
CURRENT (Confusing):

     dynamic_model_selector.py
              |
              v
        model_selector/
        (60 files, 2,500+ lines)
        
     ALSO EXISTS:
     
     band_selector.py
     (70 lines, same functionality)
```

**Issue**: Three different ways to do model selection

```
TARGET (Clear):

Option A: Band-Based (Simple)
     dynamic_model_selector.py
              |
              v
        band_selector.py
        (70 lines)
        
Option B: Full-Featured (if needed)
     dynamic_model_selector.py
              |
              v
        model_selector/ (refactored)
        (consolidated, well-tested)
```

---

## Model Evaluator Circular Reference

```
CURRENT (Broken):

     model_evaluator.py
     (300+ lines)
         |
         v [IMPORTS from]
     model_evaluator/
     (1,000+ lines)
     
     [ALSO DEFINES same classes]
     [DUPLICATE code]
```

**Problem**: Same module name for tool and package

```
TARGET (Clean):

     evaluate_new_model.py    [RENAMED]
           |
           v [Uses]
     model_evaluator/          [Single source of truth]
     (consolidated)
```

---

## Tool Integration Landscape

```
pr_prepare.py ──────┐
                    |
                    v
              [shared metadata]
                    ^
                    |
pr_review.py ───────┼──────> layered_consensus.py
                    |
                    └──────> [CONFLICT with smart_consensus_v2?]
                    
smart_consensus_v2.py <── used by: [unknown, need audit]
layered_consensus.py   <── used by: pr_review.py

CONFLICT: pr_review uses layered_consensus, not smart_consensus
QUESTION: Should they be consolidated?
```

---

## Consolidation Priority & Impact

### CRITICAL (Immediate - 8,000+ lines)
```
Smart Consensus Family:
├─ Remove: smart_consensus.py (5,535 lines)
├─ Remove: smart_consensus_simple.py (229 lines)  
├─ Archive: 6 support modules (1,550 lines)
└─ Keep: smart_consensus_v2.py (655 lines)

IMPACT: 88% reduction, single canonical tool
```

### HIGH (Important - 2,500+ lines)
```
Model Selection:
├─ Audit actual usage
├─ Consolidate duplicates
├─ Option A: BandSelector if sufficient (90% reduction)
└─ Option B: Refactor model_selector package (cleanup)

IMPACT: 50-90% reduction
```

### MEDIUM (Clarify - 1,300+ lines)
```
Model Evaluator:
├─ Rename model_evaluator.py
├─ Remove duplicates
├─ Consolidate with model_evaluator/ package

IMPACT: 50% reduction + cleaner architecture
```

### LOW (Consider)
```
Layered Consensus:
├─ Define relationship to smart_consensus_v2
├─ Merge or specialize based on pr_review needs

IMPACT: Architectural clarity, not size
```

---

## File Dependency Graph

```
EXTERNAL MCP INTERFACE:
│
├─ smart_consensus_v2.py ────────> [RoleBasedConsensus]
├─ layered_consensus.py ──────────> [LayeredConsensus]
├─ dynamic_model_selector.py ─────> [ModelSelection]
├─ pr_prepare.py ─────────────────> [PRPreparation]
├─ pr_review.py ──────────────────> [PRReview]
│                                      │
│                                      v
│                            layered_consensus.py
│
└─ Others
    ├─ model_evaluator.py ────────────> [ModelEvaluation]
    │                                       │
    │                                       v
    │                                  model_evaluator/
    │
    ├─ band_selector.py ──────────────> [ModelBands]
    │
    └─ promptcraft_bridge.py ─────────> [ExternalIntegration]

INTERNAL ONLY (Support):
    ├─ smart_consensus_cache.py
    ├─ smart_consensus_config.py
    ├─ smart_consensus_health.py
    ├─ smart_consensus_recovery.py
    ├─ smart_consensus_streaming.py
    └─ smart_consensus_monitoring.py
    
    ALL IMPORTED ONLY BY: smart_consensus.py (5,535 lines)
                         [BEING REMOVED]
```

---

## Lines of Code Audit

```
SMART CONSENSUS FAMILY:
smart_consensus.py          5,535 ████████████████████████████████ (will remove)
smart_consensus_v2.py         655 ███ (will keep)
smart_consensus_simple.py     229 █ (will remove - facade)
smart_consensus_cache.py      300 ██ (will archive)
smart_consensus_config.py     250 █ (will archive)
smart_consensus_health.py     250 █ (will archive)
smart_consensus_recovery.py   250 █ (will archive)
smart_consensus_streaming.py  350 ██ (will archive)
smart_consensus_monitoring.py 250 █ (will archive)
─────────────────────────────────────────────────────
Subtotal: 8,284 lines → Target: 655 lines (92% reduction)

MODEL SELECTION:
dynamic_model_selector.py     150 █
band_selector.py               70 
model_selector/             2,500 ████████████████ (needs audit)
─────────────────────────────────────────────────────
Subtotal: 2,720 lines → Target: ~150-300 lines (80-90% reduction)

MODEL EVALUATION:
model_evaluator.py            300 ██
model_evaluator/            1,000 ██████ (consolidate with above)
─────────────────────────────────────────────────────
Subtotal: 1,300 lines → Target: ~500 lines (60% reduction)

OTHER TOOLS:
pr_prepare.py                 300
pr_review.py                  250
layered_consensus.py           80
promptcraft_bridge.py         150
promptcraft_client/           300
─────────────────────────────────────────────────────
Subtotal: 1,080 lines (keep mostly intact)

TOTAL BEFORE: ~13,384 lines
TOTAL AFTER:  ~1,700 lines (87% reduction)
```

---

## Decision Tree

### Smart Consensus v2
```
QUESTION: Are Phase 2/3 features (parallel, caching, streaming) used?
├─ YES, critical features
│  └─ Keep smart_consensus.py, simplify v2 support
├─ NO, rarely used
│  └─ PROCEED: Keep v2, archive others (RECOMMENDED)
└─ UNKNOWN, needs audit
   └─ FIRST: Audit actual usage patterns
```

### Model Selector
```
QUESTION: Is model_selector/ package feature-complete and well-tested?
├─ YES, production-grade
│  └─ Keep it, remove duplicates, document it
├─ NO, over-engineered for current use
│  └─ Simplify to BandSelector + core logic (RECOMMENDED)
└─ UNKNOWN, needs evaluation
   └─ FIRST: Benchmark complexity vs actual usage
```

### Model Evaluator
```
QUESTION: What's the actual purpose (web scraping vs internal evaluation)?
├─ Web scraping from OpenRouter
│  └─ Keep full package, refactor tool as wrapper
├─ Internal model evaluation only
│  └─ Consolidate, remove web scraping component
└─ Both, but unclear
   └─ FIRST: Define requirements, then consolidate
```

### Layered vs Smart Consensus
```
QUESTION: Is layered distribution fundamentally different from role-based?
├─ Different enough to maintain both
│  └─ Keep separate, document differences clearly
├─ Mostly same, different terminology
│  └─ Consolidate into single tool with options (RECOMMENDED)
└─ Not sure
   └─ FIRST: Define concrete use case differences
```

---

## Migration Path

### Week 1: Assessment
```
□ Audit actual usage of smart_consensus.py features
□ Identify code depending on Phase 2/3 features
□ Evaluate model_selector/ package usage
□ Determine model_evaluator requirements
□ Profile layered_consensus vs smart_consensus usage
```

### Week 2: Smart Consensus Cleanup
```
□ Mark smart_consensus.py as deprecated with timeline
□ Create migration guide smart_consensus.py → v2
□ Rename smart_consensus_v2.py to smart_consensus.py
□ Archive support modules (git tag, docs/)
□ Update imports/references
□ Test all consensus workflows
```

### Week 3-4: Model Systems
```
□ Consolidate model selection (choose A or B)
□ Clarify model evaluator (wrapper vs consolidate)
□ Clean up circular imports
□ Document decision for each system
□ Update tests for new architecture
```

### Week 5: Final Integration
```
□ Verify layered_consensus still works
□ Update pr_review if using consolidated tools
□ Full integration test suite
□ Update external documentation
□ Release changelog entry
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking external dependencies | 6-month deprecation period + backward compat stubs |
| Losing Phase 2/3 features | Archive code + decision log in docs/archived/ |
| Uncertainty about usage | Audit logs + telemetry before cleanup |
| Model selector complexity | Start with simplification (BandSelector) + gradual enhancement |
| Layered consensus breakage | Keep separate until proven equivalent |

---

## Success Criteria

- [ ] Smart Consensus: 1 canonical implementation (not 3)
- [ ] Model Selection: 1-2 clear patterns, not 3 confused ones
- [ ] Model Evaluator: No circular imports, single source of truth
- [ ] Documentation: Clear decision log explaining each consolidation
- [ ] Tests: All integration tests passing
- [ ] Performance: No regression in model selection latency
- [ ] Maintenance: 40-50% reduction in code lines
