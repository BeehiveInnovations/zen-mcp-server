# Tiered Consensus Tool

**Status:** ✅ Active (Phase 1 Complete)
**Version:** 1.0.0
**Date:** 2025-11-09

---

## Overview

The `tiered_consensus` tool provides a simple API for multi-model consensus analysis with additive tier architecture. Get comprehensive perspectives from 3-8 AI models with just 2 parameters: `prompt` + `level`.

**Key Features:**
- **Simple API:** Just 2 required parameters (vs 7 in deprecated tools)
- **Additive Tiers:** Level 2 includes Level 1's models + additions
- **Data-Driven:** No hardcoded model lists, uses BandSelector
- **Free Model Failover:** Handles transient availability automatically
- **Domain-Specific:** Roles tailored to code_review, security, architecture, general

**Replaces:** smart_consensus_v2, smart_consensus_simple, layered_consensus

---

## Quick Start

### Basic Usage (Level 1 - Free)

```json
{
  "prompt": "Should we migrate from PostgreSQL to MongoDB?",
  "level": 1
}
```

**What happens:**
- 3 free models consult independently
- Each model assigned a professional role
- Perspectives aggregated into consensus
- **Cost:** $0

### Professional Analysis (Level 2)

```json
{
  "prompt": "Evaluate our microservices architecture",
  "level": 2,
  "domain": "architecture"
}
```

**What happens:**
- 6 models consult (Level 1's 3 + 3 economy models)
- Architecture-specific roles assigned
- Comprehensive multi-perspective analysis
- **Cost:** ~$0.50

### Executive Decision (Level 3)

```json
{
  "prompt": "Should we rewrite our backend in Rust?",
  "level": 3,
  "domain": "code_review",
  "max_cost": 3.0
}
```

**What happens:**
- 8 models consult (Level 2's 6 + 2 premium models)
- Executive-level roles included
- Deep analysis with synthesis
- **Cost:** ~$5.00 (capped at $3.00 by max_cost)

---

## API Reference

### Required Parameters

#### `prompt` (string)
**Description:** The question or proposal to analyze with consensus

**Examples:**
```
"Should we migrate from PostgreSQL to MongoDB?"
"Evaluate our microservices architecture"
"Is it worth rewriting our frontend in React?"
"Should we adopt TypeScript for our Python codebase?"
```

**Best Practices:**
- Be specific and clear
- Include relevant context
- Avoid yes/no questions (ask "evaluate" or "analyze" instead)
- One topic per consensus request

#### `level` (integer: 1-3)
**Description:** Organizational tier level determining model count and cost

**Options:**

| Level | Name | Models | Cost | Use Case |
|-------|------|--------|------|----------|
| **1** | Foundation | 3 free | $0 | Quick validation, early ideas |
| **2** | Professional | 6 total | ~$0.50 | Standard decisions, architecture |
| **3** | Executive | 8 total | ~$5.00 | Critical decisions, rewrites |

**Additive Architecture:**
- Level 2 includes ALL of Level 1's models + 3 economy models
- Level 3 includes ALL of Level 2's models + 2 premium models
- Higher levels = more perspectives, not replacement

---

### Optional Parameters

#### `domain` (string, default: "code_review")
**Description:** Domain type for specialized role assignments

**Options:**
- **code_review:** Code quality, maintainability, best practices
- **security:** Security vulnerabilities, compliance, threats
- **architecture:** System design, scalability, patterns
- **general:** Balanced general-purpose analysis

**Example:**
```json
{
  "prompt": "Evaluate our API authentication system",
  "level": 2,
  "domain": "security"  // Assigns security-focused roles
}
```

#### `include_synthesis` (boolean, default: true)
**Description:** Include detailed synthesis report

**When to set false:**
- Just want quick perspectives
- Cost-conscious usage
- Already familiar with the topic

#### `max_cost` (float, optional)
**Description:** Override cost limit per consensus

**Example:**
```json
{
  "prompt": "Critical decision requiring deep analysis",
  "level": 3,
  "max_cost": 10.0  // Allow higher cost for critical decision
}
```

**Default Limits:**
- Level 1: $0 (free models only)
- Level 2: ~$0.50
- Level 3: ~$5.00

---

## Tier Architecture

### Additive Design

**Level 1 (Foundation):**
```
Models: [free1, free2, free3]
Roles:  [code_reviewer, security_checker, technical_validator]
Cost:   $0
```

**Level 2 (Professional):**
```
Models: [free1, free2, free3, economy1, economy2, economy3]
        └─────── Level 1 ──────┘  └────── Added ──────┘
Roles:  [code_reviewer, security_checker, technical_validator,
         senior_developer, system_architect, devops_engineer]
Cost:   ~$0.50
```

**Level 3 (Executive):**
```
Models: [free1, free2, free3, economy1, economy2, economy3, premium1, premium2]
        └────────────────── Level 2 ───────────────────┘  └─── Added ──┘
Roles:  [code_reviewer, security_checker, technical_validator,
         senior_developer, system_architect, devops_engineer,
         lead_architect, technical_director]
Cost:   ~$5.00
```

### Why Additive?

**Benefits:**
1. **Consistency:** Higher levels include all lower-level perspectives
2. **Validation:** Free models provide baseline, paid models add depth
3. **Cost Control:** Start at Level 1, escalate if needed
4. **Trust:** Same free models across all levels = reproducible baseline

**Comparison to Deprecated Tools:**
- **Old:** Level 2 replaced Level 1's models (no overlap)
- **New:** Level 2 includes Level 1's models + additions

---

## Domain-Specific Roles

### Code Review Domain
**Focus:** Code quality, maintainability, best practices

**Level 1 Roles:**
- code_reviewer
- security_checker
- technical_validator

**Level 2 Adds:**
- senior_developer
- system_architect
- devops_engineer

**Level 3 Adds:**
- lead_architect
- technical_director

### Security Domain
**Focus:** Vulnerabilities, compliance, threat modeling

**Level 1 Roles:**
- security_checker
- vulnerability_scanner
- compliance_validator

**Level 2 Adds:**
- penetration_tester
- security_architect
- threat_modeler

**Level 3 Adds:**
- security_director
- compliance_officer

### Architecture Domain
**Focus:** System design, scalability, patterns

**Level 1 Roles:**
- system_architect
- technical_validator
- scalability_engineer

**Level 2 Adds:**
- infrastructure_architect
- data_architect
- platform_engineer

**Level 3 Adds:**
- enterprise_architect
- technical_director

### General Domain
**Focus:** Balanced general-purpose analysis

**Level 1 Roles:**
- generalist
- technical_validator
- practical_engineer

**Level 2 Adds:**
- senior_consultant
- technical_advisor
- solution_architect

**Level 3 Adds:**
- executive_advisor
- strategic_planner

---

## Free Model Failover

### How It Works

**Challenge:** Free models have transient availability
- 404 today ≠ broken forever
- Different free models available at different times

**Solution:** Smart failover with caching

**Algorithm:**
1. BandSelector fetches 5 free model candidates
2. Check AvailabilityCache (5-minute TTL)
3. Skip models cached as unavailable
4. Health check uncached models
5. Collect 3 available free models
6. If < 3 available, log warning and continue

**Cache Benefits:**
- Avoid repeated health checks (same model)
- Fast failover (skip known unavailable)
- 5-minute TTL handles recovery

**Paid Model Handling:**
- No failover for economy/premium models
- 404/429 = alert (indicates deprecation needed)
- Permanent availability expected

---

## Cost Management

### Estimation vs Actual

**Before Execution:**
```
Level 1: $0.00 (estimated)
Level 2: $0.45 (estimated)
Level 3: $4.80 (estimated)
```

**After Execution:**
```
Level 1: $0.00 (actual: 3 free models)
Level 2: $0.52 (actual: 3 free + 3 economy)
Level 3: $5.23 (actual: 6 + 2 premium)
```

**Cost Tracking:**
- Per-model cost tracked
- Total cost calculated
- Compared to estimate
- Included in synthesis report

### Cost Control Strategies

**1. Start Low, Escalate:**
```
Step 1: Level 1 ($0) - Quick validation
Step 2: If unclear, Level 2 (~$0.50) - Professional analysis
Step 3: If critical, Level 3 (~$5) - Executive decision
```

**2. Use max_cost:**
```json
{
  "level": 3,
  "max_cost": 2.0  // Limit Level 3 to $2
}
```

**3. Domain Selection:**
- General domain = broader roles = higher cost
- Specific domain = focused roles = lower cost

---

## Workflow Steps

### Internal Workflow (User Sees Progress)

**Step 1: Configuration**
```
**Consensus Analysis Configuration**

- Level: 2 (Professional)
- Domain: architecture
- Models: 6 (deepseek-chat:free, llama-3.3-70b:free, qwen-coder:free, ...)
- Roles: 6 (system_architect, infrastructure_architect, ...)
- Estimated Cost: $0.45

**Next Steps:**
1. Consult each model with role-specific prompt
2. Collect perspectives from all models
3. Synthesize consensus analysis
4. Generate executive summary
```

**Steps 2-7: Model Consultations**
```
**Step 2/8:** Collected perspective from deepseek-chat:free as system_architect

Progress: 1/6 models consulted
```

**Step 8: Synthesis**
```
**Consensus Analysis: Should we adopt microservices?**

**Executive Summary:**
Based on analysis from 6 models (system_architect, infrastructure_architect, ...):

**Strong Consensus (5/6 models):**
- Microservices recommended for your scale
- Gradual migration preferred over big-bang rewrite
- Start with authentication service (identified as good candidate)

**Key Concerns (unanimous):**
- Distributed tracing essential from day 1
- Team training required (DevOps skills)
- Operational complexity will increase

**Disagreement (1/6 models):**
- data_architect recommended waiting 6 months
- Reason: Current monolith still manageable
- Consider: Team size and expertise

**Recommendation:**
Proceed with gradual microservices adoption starting Q2.
Begin with authentication service as pilot.

**Cost:** $0.52 (6 models consulted)
```

---

## Usage Examples

### Example 1: Database Migration Decision

**Scenario:** E-commerce platform considering MongoDB migration

**Request:**
```json
{
  "prompt": "Should we migrate our e-commerce platform from PostgreSQL to MongoDB? We have 500k daily active users, complex product catalog, and frequent queries on nested product attributes.",
  "level": 2,
  "domain": "architecture"
}
```

**Expected Outcome:**
- 6 models (3 free + 3 economy) analyze from architecture perspective
- Roles: system_architect, data_architect, infrastructure_architect, etc.
- Cost: ~$0.50
- Synthesis includes:
  - Trade-offs (ACID vs flexibility)
  - Scale implications
  - Migration path recommendations
  - Risk assessment

### Example 2: Security Audit

**Scenario:** API authentication system review

**Request:**
```json
{
  "prompt": "Evaluate our API authentication system. We use JWT tokens with 24h expiration, bcrypt password hashing, and rate limiting. Is this secure for a financial application?",
  "level": 3,
  "domain": "security"
}
```

**Expected Outcome:**
- 8 models (6 from Level 2 + 2 premium) analyze security
- Roles: security_checker, penetration_tester, compliance_validator, etc.
- Cost: ~$5.00
- Synthesis includes:
  - Security vulnerabilities identified
  - Compliance concerns (financial regulations)
  - Recommendations with priority
  - Implementation guidance

### Example 3: Code Quality Check

**Scenario:** Quick validation of refactoring approach

**Request:**
```json
{
  "prompt": "I'm refactoring our legacy monolith into modules. Planning to extract user service first, then product catalog. Does this order make sense?",
  "level": 1,
  "domain": "code_review"
}
```

**Expected Outcome:**
- 3 free models provide quick feedback
- Roles: code_reviewer, system_architect, technical_validator
- Cost: $0
- Synthesis includes:
  - Order validation
  - Dependency concerns
  - Quick recommendations

---

## Migration from Deprecated Tools

### smart_consensus_v2 → tiered_consensus

**Old API:**
```json
{
  "question": "Should we migrate to MongoDB?",
  "org_level": "scaleup",
  "step": "Initial analysis",
  "step_number": 1,
  "total_steps": 3,
  "next_step_required": true,
  "findings": "Starting consensus"
}
```

**New API:**
```json
{
  "prompt": "Should we migrate to MongoDB?",
  "level": 2
}
```

**Changes:**
- `question` → `prompt` (clearer naming)
- `org_level: "scaleup"` → `level: 2` (numeric tiers)
- Workflow params hidden (step, step_number, total_steps, next_step_required, findings)
- 71% parameter reduction (7 → 2 required)

**Migration Steps:**
1. Replace `question` with `prompt`
2. Map org_level to level:
   - `startup` → `level: 1`
   - `scaleup` → `level: 2`
   - `enterprise` → `level: 3`
3. Remove workflow parameters (handled internally)
4. Update tool name: `smart_consensus_v2` → `tiered_consensus`

### layered_consensus → tiered_consensus

**Old:** SimpleTool (1 LLM call simulating multiple perspectives)
**New:** WorkflowTool (actual multi-model consultations)

**Why Change?**
- layered_consensus was not true multi-model consensus
- Single model simulated different perspectives (not actual diversity)
- tiered_consensus consults real independent models

---

## Phase 2: Coming Soon

**Current Status:** Phase 1 Complete
- ✅ Architecture implemented
- ✅ Additive tiers working
- ✅ BandSelector integration
- ✅ Documentation complete
- ⏳ **Simulated model responses** (Phase 2 will replace with real API calls)

**Phase 2 Plans:**
- Real model API calls via ModelProviderRegistry
- Parallel model consultations (performance)
- Response streaming (progressive updates)
- Enhanced error handling
- Production-ready deployment

**Timeline:** Phase 2 estimated 1-2 weeks

**Current Capability:**
- Workflow structure fully functional
- Tier architecture validated
- Role assignments working
- Synthesis engine operational
- **Use for testing workflow, not production decisions yet**

---

## Technical Details

### Architecture Components

**1. tiered_consensus.py (Main Tool)**
- WorkflowTool base class
- User-facing API orchestration
- Multi-step workflow management
- Perspective collection coordination

**2. consensus_models.py (TierManager)**
- Additive tier model selection
- BandSelector integration
- Free model failover logic
- Cost estimation

**3. consensus_roles.py (RoleAssigner)**
- Domain-specific role definitions (18 roles)
- Additive role assignment per tier
- Role-specific prompt generation

**4. consensus_synthesis.py (SynthesisEngine)**
- Multi-perspective aggregation
- Consensus/disagreement identification
- Executive summary generation

### Data Flow

```
User Request (prompt + level)
    ↓
TieredConsensusTool.execute()
    ↓
TierManager.get_tier_models(level)  → [model1, model2, ...]
    ↓
RoleAssigner.get_roles_for_level(level, domain) → [role1, role2, ...]
    ↓
For each (model, role) pair:
    Create role-specific prompt
    Call model (Phase 2: real API)
    Collect perspective
    ↓
SynthesisEngine.add_perspective(role, model, analysis)
    ↓
SynthesisEngine.generate_consensus()
    ↓
Formatted consensus result
```

### Key Classes

**TierManager:**
```python
def get_tier_models(level: int) -> List[str]:
    """Get models for tier level (additive)."""
    if level == 1:
        return get_available_free_models(target=3)
    elif level == 2:
        tier1 = get_available_free_models(target=3)
        economy = get_economy_models(target=3)
        return tier1 + economy  # ADDITIVE
    else:  # level == 3
        tier1 = get_available_free_models(target=3)
        economy = get_economy_models(target=3)
        premium = get_premium_models(target=2)
        return tier1 + economy + premium  # ADDITIVE
```

**RoleAssigner:**
```python
DOMAIN_ROLES = {
    "code_review": {
        1: ["code_reviewer", "security_checker", "technical_validator"],
        2: [...level 1 roles..., "senior_developer", "system_architect", ...],
        3: [...level 2 roles..., "lead_architect", "technical_director"],
    },
    # ... other domains
}
```

---

## Troubleshooting

### Issue: "Invalid level: 0"
**Cause:** Level must be 1, 2, or 3
**Fix:** Use valid level value

### Issue: "Invalid domain: xyz"
**Cause:** Domain not in [code_review, security, architecture, general]
**Fix:** Use valid domain name

### Issue: "Insufficient free models available"
**Cause:** Free models temporarily unavailable
**Fix:** Automatic - failover system handles this. Warning logged.

### Issue: "Cost limit exceeded"
**Cause:** Estimated cost > max_cost
**Fix:** Increase max_cost or use lower level

---

## Best Practices

### 1. Start with Level 1
**Why:** Free, fast, good baseline
**When:** Initial exploration, quick validation

### 2. Use Specific Domains
**Why:** More focused analysis, better roles
**When:** Clear problem domain (security, architecture, etc.)

### 3. Escalate When Needed
**Why:** Cost-effective progressive analysis
**Pattern:**
```
Level 1 ($0) → Still unclear? → Level 2 (~$0.50) → Critical? → Level 3 (~$5)
```

### 4. Include Context in Prompt
**Good:**
```
"Should we adopt GraphQL for our REST API?
 We have 50 endpoints, 3 mobile clients, and real-time requirements."
```

**Bad:**
```
"Should we use GraphQL?"
```

### 5. Review All Perspectives
**Why:** Synthesis summarizes, but individual perspectives have nuance
**How:** Set `include_synthesis: true` (default)

---

## Related Documentation

- [Architecture Decision Record](../../development/adrs/tiered-consensus-implementation.md)
- [BandSelector Documentation](../../models/README.md)
- [Dynamic Model Availability ADR](../../development/adrs/dynamic-model-availability.md)
- [Centralized Model Registry ADR](../../development/adrs/centralized-model-registry.md)

---

## Support

**Issues:** Report via GitHub Issues
**Questions:** See ADR documentation
**Phase 2 Status:** Check `tmp_cleanup/.tmp-tiered-consensus-phase2-plan-20251109.md`

---

**Last Updated:** 2025-11-09
**Version:** 1.0.0 (Phase 1)
