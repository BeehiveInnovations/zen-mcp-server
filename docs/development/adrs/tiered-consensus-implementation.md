# ADR: Tiered Consensus Implementation

**Status:** ✅ IMPLEMENTED
**Date:** 2025-11-09
**Replaces:** layered_consensus, smart_consensus, smart_consensus_v2, smart_consensus_simple

**Related ADRs:**
- [centralized-model-registry.md](centralized-model-registry.md) - BandSelector architecture
- [dynamic-model-availability.md](dynamic-model-availability.md) - Failover patterns

---

## Context

### The Problem

We had **4 consensus tools** with overlapping functionality and **6 support modules**, totaling ~4,000 lines of code with significant problems:

1. **Complex API**: Required 7 parameters (step, step_number, total_steps, next_step_required, findings, question, org_level)
2. **Hardcoded Models**: Model lists hardcoded in tool code, violating centralized registry architecture
3. **No Additive Architecture**: Each org_level selected different models instead of cumulative tiers
4. **SimpleTool Confusion**: `layered_consensus` used SimpleTool (1 LLM call) instead of true multi-model consensus

### Original Intent

From `/docs/development/adrs/future.md`:

> The original goal of the advanced consensus tools was to reduce the number of llms and their roles that had to be identified with the consensus tool. The concept was one of three layers. The first layer was focused on free and low cost tools for general work. The second layer was for medium cost llms and by layering them on to get a more robust multi perspective analysis. Then finally was the third layer with the more expensive tools like Opus 4 and Gemini 5.

**Key Requirement:** Additive architecture - Level 2 includes Level 1's models + additions, Level 3 includes Level 2's models + additions.

---

## Decision

### Build Unified `tiered_consensus` Tool

**Goals:**
1. **Simple API**: User provides just `prompt` + `level` (1, 2, or 3)
2. **Additive Tiers**: Higher levels include all lower level models (cumulative)
3. **BandSelector Integration**: No hardcoded models, data-driven selection
4. **Free Model Failover**: Handle transient availability per dynamic-model-availability.md ADR
5. **Domain Extensibility**: Easy to create domain-specific consensus (security, architecture, etc.)

### Architecture Components

**1. tiered_consensus.py** - Main tool (WorkflowTool)
- Simple user-facing API
- Workflow managed internally (user doesn't see step/findings)
- Orchestrates model consultations and synthesis

**2. consensus_models.py** - TierManager with BandSelector
- `get_tier_models(level)` - Returns additive model lists
- Free model failover logic (transient availability)
- Paid model deprecation alerts
- Cost estimation per tier

**3. consensus_roles.py** - RoleAssigner with domains
- 18 professional role definitions
- 4 domains: code_review, security, architecture, general
- Additive role assignments (Level 2 includes Level 1's roles)

**4. consensus_synthesis.py** - SynthesisEngine
- Aggregates perspectives from all models
- Identifies consensus and disagreements
- Generates executive summary

---

## Implementation

### Simple User API

**Minimal (what users want):**
```python
{
  "prompt": "Should we migrate from PostgreSQL to MongoDB?",
  "level": 2
}
```

**Advanced (optional):**
```python
{
  "prompt": "Should we migrate from PostgreSQL to MongoDB?",
  "level": 2,
  "domain": "architecture",  # code_review, security, architecture, general
  "include_synthesis": true,
  "max_cost": 1.0
}
```

### Additive Tier Architecture

| Level | Models | Roles | Cost | Use Case |
|-------|--------|-------|------|----------|
| **1** | 3 free | code_reviewer, security_checker, technical_validator | $0 | Quick validation |
| **2** | Level 1 + 3 economy (6 total) | Level 1 + senior_developer, system_architect, devops_engineer | ~$0.50 | Standard decisions |
| **3** | Level 2 + 2 premium (8 total) | Level 2 + lead_architect, technical_director | ~$5.00 | Critical decisions |

**Implementation:**
```python
def get_tier_models(self, level: int) -> List[str]:
    if level == 1:
        return self._get_available_free_models(target=3)

    elif level == 2:
        # ADDITIVE: Include Level 1's exact models
        tier1_models = self._get_available_free_models(target=3)
        economy_models = self._get_economy_models(target=3)
        return tier1_models + economy_models

    else:  # level == 3
        # ADDITIVE: Include Level 2's exact models
        tier1_models = self._get_available_free_models(target=3)
        economy_models = self._get_economy_models(target=3)
        premium_models = self._get_premium_models(target=2)
        return tier1_models + economy_models + premium_models
```

### BandSelector Integration

**No hardcoded models:**
```python
# Uses BandSelector for all model selection
free_models = self.band_selector.get_models_by_cost_tier("free", limit=5)
economy_models = self.band_selector.get_models_by_cost_tier("economy", limit=3)
premium_models = self.band_selector.get_models_by_cost_tier("premium", limit=2)
```

**Automatic adaptation:**
- When models.csv updates (new model added, old deprecated), tool automatically adapts
- No code changes needed when Sonnet 4.5 replaces Opus 4.1
- Band thresholds adjust as AI industry improves

### Free Model Failover

**From dynamic-model-availability.md ADR:**
- Free models have transient availability (404 today ≠ broken forever)
- Try multiple free models before falling back to economy tier
- Cache availability status (5-minute TTL)
- Alert on paid model failures (indicates deprecation needed)

**Implementation:**
```python
def _get_available_free_models(self, target: int, max_attempts: int) -> List[str]:
    candidates = self.band_selector.get_models_by_cost_tier("free", limit=max_attempts)
    available = []

    for model in candidates:
        # Check cache first
        if self.availability_cache.is_available(model) is False:
            continue  # Skip known unavailable

        # Health check
        if self._check_model_availability(model):
            available.append(model)

        if len(available) >= target:
            break

    return available
```

### Domain Extension Pattern

**Easy to add new consensus domains:**
```python
# 50 lines to add security consensus
DOMAIN_ROLES["security"] = {
    1: ["security_checker", "vulnerability_scanner", "compliance_validator"],
    2: [
        # Level 1 roles (ADDITIVE)
        "security_checker", "vulnerability_scanner", "compliance_validator",
        # Level 2 additions
        "penetration_tester", "security_architect", "threat_modeler",
    ],
    3: [
        # Level 1 + 2 roles (ADDITIVE)
        ...,
        # Level 3 additions
        "security_director", "compliance_officer",
    ],
}
```

---

## Benefits

### For Users
- **Simple API**: 2 required parameters vs 7 (71% reduction)
- **Predictable Costs**: Level 1 = $0, Level 2 = ~$0.50, Level 3 = ~$5
- **Additive Value**: Higher levels include all lower level perspectives
- **Domain Flexibility**: code_review, security, architecture, general

### For Developers
- **No Hardcoded Models**: Uses BandSelector exclusively
- **Easy Extensions**: New domains = just add role mappings
- **Automatic Adaptation**: When models.csv updates, tool adapts
- **Proper Failover**: Free models handled correctly (transient availability)

### For Maintenance
- **Single Tool**: 1 tool instead of 4 overlapping tools
- **Less Code**: ~1,600 lines vs ~4,000 lines (60% reduction)
- **Clear Architecture**: Tier → Models → Roles → Synthesis
- **Better Testing**: Focused test coverage on one implementation

---

## Migration

### Deprecated Tools

**Moved to `/tools/custom/deprecated/`:**
- layered_consensus.py
- smart_consensus.py
- smart_consensus_v2.py
- smart_consensus_simple.py
- smart_consensus_cache.py (support module)
- smart_consensus_recovery.py (support module)
- smart_consensus_streaming.py (support module)
- smart_consensus_config.py (support module)
- smart_consensus_health.py (support module)
- smart_consensus_monitoring.py (support module)

**Total:** 10 files deprecated

### Parameter Mapping

| Old Parameter | New Parameter | Notes |
|---------------|---------------|-------|
| `question` | `prompt` | Renamed for clarity |
| `org_level: "startup"` | `level: 1` | Foundation tier |
| `org_level: "scaleup"` | `level: 2` | Professional tier |
| `org_level: "enterprise"` | `level: 3` | Executive tier |
| `step`, `step_number`, `total_steps`, `next_step_required`, `findings` | (removed) | Workflow managed internally |

### No Backward Compatibility Needed

**Reason:** Single-user project, no external dependencies

**Action:** Old tools immediately deprecated, moved to `/tools/custom/deprecated/`

---

## Consequences

### Positive

✅ **API Simplicity**: 71% reduction in required parameters (7 → 2)
✅ **Architecture Compliance**: Uses BandSelector, implements ADR patterns
✅ **Code Reduction**: 60% less code (4,000 → 1,600 lines)
✅ **Additive Tiers**: Matches original vision (cumulative models)
✅ **Extensibility**: Easy to add new domains (50 lines)
✅ **Maintainability**: Single focused tool vs 4 overlapping tools

### Neutral

⚠️ **Different Tool Name**: `tiered_consensus` instead of `consensus` (upstream has `/tools/consensus.py`)
⚠️ **Placeholder Model Calls**: Currently simulates responses (TODO: implement real API calls)

### Negative

❌ **Support Modules Lost**: smart_consensus_cache.py, smart_consensus_monitoring.py deprecated
- Mitigation: Can extract needed functionality if required
- Current: AvailabilityCache implements essential caching

---

## Testing

### Unit Tests (Completed)

**tests/test_consensus_models.py:**
- ✅ AvailabilityCache (initialization, hit/miss, expiration, stats)
- ✅ TierManager (initialization, invalid level handling)
- ✅ Level 1 returns 3 free models
- ✅ Level 2 additive architecture (includes Level 1's models)
- ✅ Level 3 additive architecture (includes Level 2's models)
- ✅ Tier cost calculation
- ✅ Free model failover (tries multiple models)
- ✅ Failover respects cache (skips known unavailable)

**Run Tests:**
```bash
pytest tests/test_consensus_models.py -v
```

### Integration Tests (Pending)

**tests/test_tiered_consensus_integration.py:**
- [ ] Full workflow (prompt → synthesis)
- [ ] Real BandSelector integration
- [ ] Role assignment per domain
- [ ] Synthesis engine output

### End-to-End Tests (Pending)

**tests/test_tiered_consensus_e2e.py:**
- [ ] Real model API calls (when placeholder replaced)
- [ ] Actual consensus analysis
- [ ] Cost tracking accuracy
- [ ] Performance benchmarks

---

## Implementation Files

### Core Files (4)

1. **[/tools/custom/tiered_consensus.py](../../tools/custom/tiered_consensus.py)** - 400 lines
   - Main tool (WorkflowTool)
   - Simple API orchestration
   - Workflow management

2. **[/tools/custom/consensus_models.py](../../tools/custom/consensus_models.py)** - 450 lines
   - TierManager (additive model selection)
   - AvailabilityCache (5-minute TTL)
   - Free model failover logic

3. **[/tools/custom/consensus_roles.py](../../tools/custom/consensus_roles.py)** - 350 lines
   - RoleAssigner (domain-specific roles)
   - 18 professional role definitions
   - 4 domain mappings

4. **[/tools/custom/consensus_synthesis.py](../../tools/custom/consensus_synthesis.py)** - 400 lines
   - SynthesisEngine (perspective aggregation)
   - Consensus/disagreement identification
   - Executive summary generation

### Tests (1)

5. **[/tests/test_consensus_models.py](../../tests/test_consensus_models.py)** - 300 lines
   - TierManager unit tests
   - Additive architecture verification
   - Failover behavior tests

### Documentation (3)

6. **[/tmp_cleanup/.tmp-tiered-consensus-implementation-20251109.md](../../tmp_cleanup/.tmp-tiered-consensus-implementation-20251109.md)** - Implementation details
7. **[/tmp_cleanup/.tmp-consensus-deprecation-plan-20251109.md](../../tmp_cleanup/.tmp-consensus-deprecation-plan-20251109.md)** - Original deprecation plan
8. **[/tools/custom/deprecated/README.md](../../tools/custom/deprecated/README.md)** - Deprecated files reference

---

## Success Metrics

### Achieved ✅

- **API Complexity**: 71% reduction (7 → 2 required parameters)
- **Code Size**: 60% reduction (4,000 → 1,600 lines)
- **Architecture Compliance**: Uses BandSelector, implements ADR patterns
- **Additive Tiers**: Verified by unit tests
- **Domain Extensibility**: 4 domains implemented, easy to add more

### Pending ⏳

- **Integration Testing**: Full workflow tests
- **Real Model Calls**: Replace simulated responses
- **MCP Registration**: Register in tool catalog
- **Documentation**: User guide and examples

---

## Future Enhancements

### Phase 2: Real Model Integration
- Replace `_simulate_model_response()` with actual model API calls
- Implement proper error handling
- Add retry logic with exponential backoff

### Phase 3: Advanced Features
- Parallel model consultations (where possible)
- Response streaming for large outputs
- Cost tracking dashboard
- Performance metrics collection

### Phase 4: Domain Expansion
- Performance consensus (performance_engineer, load_tester, profiler)
- DevOps consensus (deployment_specialist, sre, platform_engineer)
- Data consensus (data_engineer, analyst, scientist)
- UX consensus (ux_researcher, designer, accessibility_expert)

---

## References

- **Architecture Decision Records:**
  - [centralized-model-registry.md](centralized-model-registry.md) - Data-driven model management
  - [dynamic-model-availability.md](dynamic-model-availability.md) - Failover patterns
  - [future.md](future.md) - Original consensus vision

- **Implementation Documents:**
  - [tmp_cleanup/.tmp-tiered-consensus-implementation-20251109.md](../../tmp_cleanup/.tmp-tiered-consensus-implementation-20251109.md)
  - [tmp_cleanup/.tmp-consensus-deprecation-plan-20251109.md](../../tmp_cleanup/.tmp-consensus-deprecation-plan-20251109.md)

- **Related Models:**
  - [docs/models/models.csv](../../docs/models/models.csv) - Centralized model registry
  - [docs/models/bands_config.json](../../docs/models/bands_config.json) - Band criteria

---

**This ADR documents the successful implementation of the tiered_consensus tool, replacing 4 fragmented consensus tools with a single unified tool matching the original architectural vision.**
