# Centralized Model Registry and Band Selector - Architecture Decision Record (ADR)

**Status**: ✅ IMPLEMENTED (Partial - Needs Full Adoption)
**Date**: 2025-08-11 (Original), 2025-11-09 (Updated)
**System**: Centralized Model Management
**Components**: models.csv, bands_config.json, BandSelector, model_evaluator

---

## Context

### The Problem: AI Model Economics Are Dynamic

The AI model landscape is constantly evolving with three key trends:

1. **Performance Improvements**: New models regularly outperform previous "flagship" models
2. **Cost Reductions**: Providers lower prices as competition increases and efficiency improves
3. **Availability Changes**: Models get deprecated, rate-limited, or become unavailable

**Real-World Example (2025):**
```
Anthropic Claude Opus 4.1 (Released March 2025)
├── Input Cost: $15.00 per million tokens
├── Output Cost: $75.00 per million tokens
├── HumanEval Score: 88.0
└── Status: Premium flagship model

Anthropic Claude Sonnet 4.5 (Released October 2025)
├── Input Cost: $3.00 per million tokens  ← 80% cheaper
├── Output Cost: $15.00 per million tokens ← 80% cheaper
├── HumanEval Score: 87.0                  ← Nearly same performance
└── Status: Better value proposition
```

**Traditional Approach Fails:**
```python
# Hardcoded in smart_consensus_v2.py
PREMIUM_MODELS = [
    "anthropic/claude-opus-4.1",  # ← Now outdated choice
    "openai/gpt-5",
    "google/gemini-2.5-pro",
]

# Problem:
# - Requires code changes to update models
# - Misses cost optimization opportunities
# - Cannot adapt to market changes automatically
# - Developers must manually track model performance
```

### Historical Context: Why This Matters

**August 2025:** Built initial consensus tools with hardcoded model lists
- Seemed reasonable at the time
- Small number of quality models
- Infrequent changes

**November 2025:** Industry acceleration
- Models release every few weeks
- Performance improvements dramatic
- Cost reductions significant
- Free tier models match previous paid quality

**Result:** Tools using outdated models, missing cost savings, requiring constant code updates

---

## Decision

**Adopt a centralized, data-driven model registry with band-based selection criteria.**

### Core Principle

> **Configuration, Not Code**: Model selection should be data-driven through centralized configuration, not hardcoded in tool implementations.

### Architecture Components

#### 1. **Centralized Model Registry (models.csv)**

Single source of truth for all available AI models.

**Location:** `docs/models/models.csv`

**Schema:**
```csv
rank,model,provider,tier,status,context,input_cost,output_cost,
org_level,specialization,role,strength,humaneval_score,swe_bench_score,
openrouter_url,last_updated
```

**Example Entry:**
```csv
4,anthropic/claude-sonnet-4.5,anthropic,high_perf,paid,200K,3.0,15.0,
senior,reasoning,senior_developer,balanced,87.0,74.0,
https://openrouter.ai/anthropic/claude-sonnet-4.5,2025-11-09
```

**Key Features:**
- **36 models** across 6 cost tiers
- **Benchmark scores** (HumanEval, SWE-bench) for objective ranking
- **Pre-assigned roles** (code_reviewer, architect, etc.)
- **Org level mapping** (junior/senior/executive)
- **Specialization tags** (coding, reasoning, vision, general)
- **Status tracking** (active, deprecated, experimental)
- **Cost transparency** (input/output per million tokens)

#### 2. **Band Configuration (bands_config.json)**

Centralized criteria for automatic model classification.

**Location:** `docs/models/bands_config.json`

**9 Band Categories:**
1. **context_window_bands** - Compact, standard, extended, large (1M+)
2. **cost_tier_bands** - Free, economy, value, premium
3. **performance_bands** - Basic, good, excellent, exceptional
4. **tier_classification_bands** - Free champion, value tier, high perf, premium
5. **org_level_assignment_bands** - Junior, senior, executive
6. **provider_trust_bands** - Tier 1-4 provider classifications
7. **role_assignment_bands** - Technical, architecture, analysis, validation roles
8. **rank_assignment_bands** - Tier 1-4 flagship/professional/efficient/specialized
9. **strength_classification_bands** - Next-generation, advanced, balanced, efficient

**Example Band Definition:**
```json
{
  "cost_tier_bands": {
    "free": {
      "max_cost": 0.0,
      "description": "Free models with zero cost",
      "target_allocation": "8 models (32%)"
    },
    "economy": {
      "min_cost": 0.01,
      "max_cost": 1.0,
      "description": "Low-cost efficient models",
      "target_allocation": "4-5 models"
    },
    "value": {
      "min_cost": 1.01,
      "max_cost": 10.0,
      "description": "Balanced cost-performance models",
      "target_allocation": "6 models (24%)"
    },
    "premium": {
      "min_cost": 10.01,
      "description": "High-cost flagship models",
      "target_allocation": "6 models (24%)"
    }
  }
}
```

**Critical Insight:** When band thresholds change, ALL model assignments automatically update.

#### 3. **BandSelector Query Engine**

Intelligent model selection using centralized registry.

**Location:** `tools/custom/band_selector.py`

**Core Methods:**
```python
class BandSelector:
    def get_models_by_org_level(self, org_level: str, limit: int = 10) -> List[str]
    def get_models_by_cost_tier(self, tier: str, limit: int = 5) -> List[str]
    def get_models_by_role(self, role: str, org_level: str = "senior", limit: int = 3) -> List[str]
    def get_models_by_specialization(self, spec: str, tier: str) -> List[Dict]
```

**How It Works:**
```python
selector = BandSelector()

# Automatically selects best models for startup tier
startup_models = selector.get_models_by_org_level("startup", limit=3)
# Returns: Top 3 free models by HumanEval score

# Automatically selects best models for enterprise tier
enterprise_models = selector.get_models_by_org_level("enterprise", limit=8)
# Returns: Top 8 premium models by HumanEval score

# When models.csv updates, selections automatically adapt!
```

#### 4. **Model Evaluator Tool**

Automated system for adding/updating models in registry.

**Location:** `tools/custom/model_evaluator.py`, `docs/models/automated_evaluation_criteria.py`

**Workflow:**
```
1. User provides OpenRouter URL for new model
   ↓
2. Tool scrapes model metadata (cost, context, availability)
   ↓
3. Tool gathers benchmarks (HumanEval, SWE-bench, MMLU)
   ↓
4. Tool applies qualification criteria
   ↓
5. Tool determines tier, role, org_level via band criteria
   ↓
6. Tool finds replacement candidates (if applicable)
   ↓
7. Tool adds model to models.csv (if qualified)
   ↓
8. BandSelector automatically picks up new model
   ↓
9. Consensus tools automatically use it
   ↓
NO CODE CHANGES REQUIRED!
```

**Example Usage:**
```bash
# Sonnet 4.5 released
model_evaluator(
    openrouter_url="https://openrouter.ai/anthropic/claude-sonnet-4.5",
    evaluation_type="comprehensive"
)

# Output:
# ✅ Model qualified
# ✅ HumanEval: 87.0 (exceeds 75.0 threshold)
# ✅ Cost: $3.00 input, $15.00 output
# ✅ Classification: high_perf tier, senior org_level
# ✅ Replacement candidate: claude-opus-4.1 (better cost/performance)
# ✅ Added to models.csv
# ✅ Available immediately for consensus tools
```

---

## Consequences

### Benefits

#### 1. **Automatic Cost Optimization**

**Before (Hardcoded):**
```python
# October 2025 - Using expensive flagship
PREMIUM_MODELS = ["anthropic/claude-opus-4.1"]  # $15 input / $75 output

# November 2025 - Sonnet 4.5 released
# Developer must:
# 1. Learn about new model
# 2. Compare benchmarks
# 3. Update code
# 4. Test changes
# 5. Deploy update
# 6. Users benefit from cost savings
```

**After (Data-Driven):**
```python
# October 2025
selector.get_models_by_cost_tier("premium", limit=1)
# Returns: ["anthropic/claude-opus-4.1"]

# November 2025 - models.csv updated
selector.get_models_by_cost_tier("premium", limit=1)
# Returns: ["anthropic/claude-sonnet-4.5"]  ← Automatic switch!

# No code changes
# No testing needed
# No deployment required
# Users immediately benefit from 80% cost reduction
```

**Cost Savings Example:**
```
1M tokens analyzed with premium model:
- Opus 4.1: $15 input + $75 output = $90
- Sonnet 4.5: $3 input + $15 output = $18
- Savings: $72 per million tokens (80% reduction)

1000 analyses per month:
- Old cost: $90,000/month
- New cost: $18,000/month
- Automatic savings: $72,000/month
```

#### 2. **Performance Tracking Over Time**

**Band thresholds can be adjusted as industry improves:**

**2025 Standards:**
```json
{
  "performance_bands": {
    "excellent": {"min_score": 75.1, "max_score": 85.0}
  }
}
```

**2026 Standards (if industry improves):**
```json
{
  "performance_bands": {
    "excellent": {"min_score": 80.0, "max_score": 90.0}  ← Raised threshold
  }
}
```

**Result:** Models automatically re-classified, selections adapt to higher standards

#### 3. **Graceful Model Deprecation**

**Scenario: Model becomes unavailable**

**Before:**
```python
# Tool tries to use deprecated model
response = call_model("deepseek/deepseek-chat:free")
# Error: 404 - Model not found
# Users experience failures
# Emergency code fix required
```

**After:**
```csv
# Update models.csv status column
rank,model,...,status
24,deepseek/deepseek-chat:free,...,deprecated  ← Status change

# BandSelector automatically filters out deprecated models
# Next best free model automatically selected
# Zero downtime
```

#### 4. **Domain-Specific Tool Creation**

**Original Goal:** "If we ever wanted to have a consensus tool focused on something other than code review, we could duplicate the advanced consensus tool, and change the roles"

**Implementation:**
```python
# security_consensus.py - 50 lines of role definitions
class SecurityConsensusTool(WorkflowTool):
    def _get_roles_for_tier(self, tier: int) -> List[str]:
        if tier == 1:
            return ["security_checker", "vulnerability_scanner", "compliance_validator"]
        elif tier == 2:
            return [
                "security_checker", "vulnerability_scanner", "compliance_validator",
                "penetration_tester", "security_architect", "threat_modeler",
            ]
        elif tier == 3:
            return [
                # Tier 1 + 2 roles
                "security_chief", "risk_analyst",
            ]

    # Inherits ALL BandSelector logic
    # Automatic model selection for security roles
    # Automatic cost optimization
    # Automatic model updates
    # NO hardcoded model lists needed!
```

**Result:** New consensus tool in 50 lines vs 500+ lines with hardcoded models

#### 5. **Vendor Neutrality**

**Registry maintains provider diversity:**
```
OpenAI:     10 models (27%)
Anthropic:   3 models (8%)
Google:      2 models (5%)
Meta:        5 models (14%)
Qwen:        8 models (22%)
DeepSeek:    4 models (11%)
Others:      4 models (11%)
```

**If provider becomes expensive:**
- Update cost in models.csv
- BandSelector automatically de-prioritizes
- Tools automatically prefer alternatives
- No vendor lock-in

### Challenges

#### 1. **Initial Setup Complexity**

**Trade-off:**
- More complex initial architecture
- But dramatically simpler long-term maintenance

**Mitigation:**
- Comprehensive documentation (this ADR)
- BandSelector API abstracts complexity
- Tools just call `get_models_by_org_level()` - simple interface

#### 2. **Data Quality Dependency**

**Risk:** models.csv accuracy critical

**Mitigation:**
- model_evaluator automates benchmark gathering
- OpenRouter API provides canonical cost data
- Validation rules enforce data quality
- Regular audits via automated scripts

#### 3. **Performance Overhead**

**Concern:** CSV parsing on every model selection

**Mitigation:**
- Pandas DataFrame caching (in-memory)
- Sub-100ms query performance
- One-time load at startup
- Hot-reload on configuration changes only

---

## Implementation Status

### ✅ Completed Components

1. **models.csv** - 36 models catalogued with comprehensive metadata
2. **bands_config.json** - 9 band categories with centralized criteria
3. **BandSelector** - Query engine with 12+ selection methods
4. **model_evaluator** - Tool for adding models from OpenRouter URLs
5. **automated_evaluation_criteria.py** - Benchmark scraping and qualification

### ⚠️ Partial Implementation

**Current Issue:** Consensus tools have hardcoded model lists

**Files with hardcoded lists:**
- `tools/custom/smart_consensus_v2.py` (lines 108-122)
  - FREE_MODELS = [...]  ← Should use BandSelector
  - PREMIUM_MODELS = [...] ← Should use BandSelector

**Impact:**
- Tools don't benefit from automatic updates
- Miss cost optimization (e.g., Sonnet 4.5 over Opus 4.1)
- Vulnerable to model availability issues

### 📋 Remaining Work

**Phase 1: Fix Model Availability (Week 1)**
```bash
# Update models.csv - mark unavailable models
# Verified against OpenRouter API
```

**Phase 2: Enhance BandSelector (Week 2)**
```python
# Add additive tier support
def get_additive_tier_models(self, tier: int) -> List[str]:
    """
    Tier 1: 3 free models
    Tier 2: Tier 1 + 3 economy models (additive)
    Tier 3: Tier 2 + 2 premium models (additive)
    """
```

**Phase 3: Remove Hardcoded Lists (Week 3)**
```python
# In smart_consensus_v2.py
# Remove: FREE_MODELS = [...]
# Remove: PREMIUM_MODELS = [...]
# Add: self.band_selector = BandSelector()
# Use: self.band_selector.get_models_by_cost_tier()
```

**Phase 4: Convert layered_consensus (Week 4)**
```python
# Change from SimpleTool to WorkflowTool
# Implement true multi-model calling
# Use BandSelector for model selection
```

---

## Examples

### Example 1: Automatic Model Update

**Scenario:** OpenAI releases GPT-5.1 with better performance at lower cost

```bash
# Step 1: Evaluate new model
model_evaluator(
    openrouter_url="https://openrouter.ai/openai/gpt-5.1",
    evaluation_type="comprehensive"
)

# Step 2: Tool adds to models.csv
# rank,model,provider,tier,status,context,input_cost,output_cost,org_level,specialization,role,strength,humaneval_score
# 2,openai/gpt-5.1,openai,premium,paid,500K,4.0,12.0,executive,general,lead_architect,next_generation,92.0

# Step 3: BandSelector automatically picks it up
selector = BandSelector()
executive_models = selector.get_models_by_org_level("executive", limit=8)
# Returns: ['openai/gpt-5.1', 'anthropic/claude-opus-4.1', ...]
#           ↑ New model automatically included

# Step 4: Consensus tools automatically use it
# NO CODE CHANGES
# NO DEPLOYMENTS
# IMMEDIATE BENEFIT
```

### Example 2: Cost Threshold Adjustment

**Scenario:** Free tier models now match previous paid model quality

**2025 State:**
```json
{
  "org_level_assignment_bands": {
    "senior": {
      "cost_criteria": {"max_input_cost": 10.0},
      "performance_criteria": {"min_humaneval": 70.0}
    }
  }
}
```

**2026 State (Industry Improvement):**
```json
{
  "org_level_assignment_bands": {
    "senior": {
      "cost_criteria": {"max_input_cost": 5.0},  ← Lowered threshold
      "performance_criteria": {"min_humaneval": 75.0}  ← Raised bar
    }
  }
}
```

**Result:**
- Senior tier automatically re-selects models
- Higher quality bar enforced
- Lower cost preference
- All tools adapt automatically

### Example 3: Provider Outage

**Scenario:** Anthropic API experiences 4-hour outage

**Current models.csv:**
```csv
4,anthropic/claude-sonnet-4.5,anthropic,high_perf,paid,...
```

**During Outage:**
```csv
# Update status temporarily
4,anthropic/claude-sonnet-4.5,anthropic,high_perf,unavailable,...
```

**BandSelector Behavior:**
```python
# Automatically filters out unavailable models
models = selector.get_models_by_org_level("senior", limit=6)
# Returns: [openai/gpt-5-mini, google/gemini-2.5-flash, ...]
#          (Anthropic models excluded)

# Tools continue working with alternative models
# Users experience degraded service but not complete failure
```

**After Outage:**
```csv
# Revert status
4,anthropic/claude-sonnet-4.5,anthropic,high_perf,paid,...
```

**BandSelector automatically includes it again - zero code changes**

---

## Related Decisions

### ADR: Additive Tier Architecture

**Decision:** Implement additive tier structure for consensus tools

**Tiers:**
- Tier 1 (Startup/Junior): 3 free models [A, B, C]
- Tier 2 (Scaleup/Senior): Tier 1 + 3 economy = [A, B, C, D, E, F]
- Tier 3 (Enterprise/Executive): Tier 2 + 2 premium = [A, B, C, D, E, F, G, H]

**Rationale:**
- Consistency across tiers (same free models in all)
- Progressive enhancement (upgrade by adding tiers)
- Cost efficiency (startup only pays for 3 models)
- Predictable escalation path

**Implementation:**
```python
class BandSelector:
    def get_additive_tier_models(self, tier: int) -> List[str]:
        if tier == 1:
            return self.get_models_by_cost_tier("free", limit=3)
        elif tier == 2:
            tier1 = self.get_models_by_cost_tier("free", limit=3)
            additions = self.get_models_by_cost_tier("economy", limit=3)
            return tier1 + additions  # ADDITIVE
        elif tier == 3:
            tier2 = self.get_additive_tier_models(2)  # Includes tier 1
            additions = self.get_models_by_cost_tier("premium", limit=2)
            return tier2 + additions  # ADDITIVE
```

### ADR: Deprecate Hardcoded Model Lists

**Decision:** Remove all hardcoded model lists from consensus tools

**Affected Files:**
- tools/custom/smart_consensus_v2.py
- Any future consensus tools

**Migration Path:**
```python
# Before
FREE_MODELS = ["deepseek/deepseek-chat:free", ...]
PREMIUM_MODELS = ["anthropic/claude-opus-4.1", ...]

# After
from tools.custom.band_selector import BandSelector
selector = BandSelector()
free_models = selector.get_models_by_cost_tier("free", limit=5)
premium_models = selector.get_models_by_cost_tier("premium", limit=5)
```

**Timeline:** Complete by 2025-12-15

---

## Lessons Learned

### 1. **Future-Proof Architecture Requires Data-Driven Design**

**Wrong:** Hardcode model names in tool implementations
**Right:** Query centralized registry with selection criteria

**Principle:** Configuration beats code for rapidly changing domains

### 2. **Band Thresholds Enable Industry Adaptation**

**Insight:** AI model economics are non-stationary

**Solution:** Centralized band criteria allow threshold adjustments without code changes

**Example:** When "good" performance was 70.0 HumanEval, now it's 75.0

### 3. **Tool Simplicity Through Abstraction**

**BandSelector API hides complexity:**
- Tools just call `get_models_by_org_level("startup")`
- Don't need to know about bands, criteria, scoring
- Registry changes transparent to tools

### 4. **Model Evaluator Critical for Scalability**

**Without automation:**
- Developer manually researches new models
- Developer manually updates models.csv
- Developer manually tests changes
- Slow, error-prone, doesn't scale

**With model_evaluator:**
- Provide OpenRouter URL
- Tool scrapes benchmarks
- Tool applies criteria
- Tool adds to registry
- Immediate availability

---

## Future Considerations

### 1. **Real-Time Model Performance Tracking**

**Current:** Static benchmark scores in models.csv

**Future:** Track actual performance in production
```json
{
  "model": "anthropic/claude-sonnet-4.5",
  "benchmark_humaneval": 87.0,
  "production_metrics": {
    "avg_quality_score": 4.2,  // User ratings
    "success_rate": 0.94,      // Task completion
    "avg_latency_ms": 2100,    // Response time
    "cost_efficiency": 0.89    // Value per dollar
  }
}
```

**Benefit:** Select models based on real usage, not just benchmarks

### 2. **Multi-Provider Fallback Chains**

**Current:** Single model selection per role

**Future:** Automatic fallback across providers
```python
selector.get_models_with_fallback("senior_developer", "senior")
# Returns: [
#   {"primary": "anthropic/claude-sonnet-4.5", "fallback": "openai/gpt-5-mini"},
#   ...
# ]
```

**Benefit:** Higher reliability, automatic provider failover

### 3. **Cost Budget Management**

**Future:** Enforce cost budgets at org level
```python
selector.get_models_by_org_level(
    "enterprise",
    limit=8,
    max_cost_per_million=25.0  # Budget constraint
)
```

**Benefit:** Cost control while maintaining quality

### 4. **Specialization-Based Auto-Routing**

**Future:** Route different parts of analysis to specialized models
```python
# Security analysis → security-specialized model
# Code generation → coding-specialized model
# Architecture design → reasoning-specialized model
```

**Benefit:** Optimal model for each sub-task

### 5. **Community Model Contributions**

**Future:** Allow users to contribute model evaluations
- Crowdsourced benchmark validation
- Production performance feedback
- Model recommendation voting

**Benefit:** Wisdom of crowds improves selection quality

---

## References

### Core Files

- **models.csv**: `docs/models/models.csv` (36 models)
- **bands_config.json**: `docs/models/bands_config.json` (9 band categories)
- **BandSelector**: `tools/custom/band_selector.py` (500+ lines)
- **model_evaluator**: `tools/custom/model_evaluator.py` (WorkflowTool)
- **Evaluation Criteria**: `docs/models/automated_evaluation_criteria.py` (300+ lines)

### Related Documentation

- **Model Allocation Config**: `docs/models/model_allocation_config.yaml`
- **Dynamic Model Selector**: `docs/tools/custom/dynamic_model_selector.md`
- **Model Schema**: `docs/models/models_schema.json`
- **README**: `docs/models/README.md`

### External Resources

- **OpenRouter API**: https://openrouter.ai/api/v1/models
- **HumanEval Benchmark**: https://github.com/openai/human-eval
- **SWE-bench**: https://www.swebench.com/

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-08-11 | 1.0 | Byron W. | Initial architecture design and implementation |
| 2025-11-09 | 2.0 | Byron W. + Claude Code | Comprehensive documentation, identified partial implementation, defined migration path |

---

## Status Summary

**✅ Architecture: EXCELLENT** - Well-designed, future-proof, scalable

**⚠️ Implementation: PARTIAL** - Core components exist but not fully utilized

**📋 Action Required:** Remove hardcoded model lists from consensus tools (4 weeks)

**🎯 Goal:** Full data-driven model selection with zero code changes for model updates

---

*This ADR documents the foundational architecture decision that enables the Zen MCP Server to adapt automatically to AI model market changes. It must not be forgotten or replaced with hardcoded approaches.*
