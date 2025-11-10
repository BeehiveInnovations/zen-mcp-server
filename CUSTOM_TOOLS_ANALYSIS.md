# Custom Tools LLM Usage Analysis

## Summary

This analysis examines 16 custom tools in `/home/byron/dev/zen-mcp-server/tools/custom/` to identify which tools actually use LLM APIs and how they select models.

**Key Finding:** Only **4 tools are actual MCP tools** that users call directly. The remaining **12 files are support modules**, helper classes, or tools that delegate to other tools.

---

## ACTUAL MCP TOOLS (User-Callable)

### 1. smart_consensus_v2.py

**Status:** YES - Actual Tool (WorkflowTool)

**Tool Name:** `smart_consensus_v2`

**Purpose:** Intelligent multi-model consensus with automatic model selection based on organizational level and role-based professional perspectives.

**LLM Usage:**
- **Multi-model:** YES - Consults multiple models in sequence
- **User specifies models:** NO
- **System auto-selects:** YES
- **Mechanism:** Organization-level based selection

**Model Selection Details:**

```python
ORG_LEVEL_CONFIGS = {
    "startup": {
        "max_models": 3,
        "roles": ["code_reviewer", "security_checker", "technical_validator"],
        "prefer_free_models": True,
    },
    "scaleup": {
        "max_models": 6,
        "roles": ["code_reviewer", "security_checker", "technical_validator",
                  "senior_developer", "system_architect", "devops_engineer"],
        "prefer_free_models": False,
    },
    "enterprise": {
        "max_models": 8,
        "roles": ["code_reviewer", "security_checker", "technical_validator",
                  "senior_developer", "system_architect", "devops_engineer",
                  "lead_architect", "technical_director"],
        "prefer_free_models": False,
    }
}

FREE_MODELS = [
    "deepseek/deepseek-chat:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
    "microsoft/phi-4-reasoning:free",
    "meta-llama/llama-3.1-405b-instruct:free",
]

PREMIUM_MODELS = [
    "anthropic/claude-opus-4.1",
    "openai/gpt-5",
    "google/gemini-2.5-pro",
    "deepseek/deepseek-r1-0528",
    "mistralai/mistral-large-2411",
]
```

**Input Schema:**
- `question` (required) - The question/proposal to analyze
- `org_level` (optional, default "scaleup") - Organization level for model selection

**Workflow Mechanism:**
- **Step 1:** Create role assignments based on org_level
- **Steps 2+:** Consult one model per step (each model gets a professional role)
- **Final step:** Synthesize all role perspectives into consensus

**Temperature & Thinking:** Uses `TEMPERATURE_ANALYTICAL` with `thinking_mode="medium"`

---

### 2. smart_consensus_simple.py

**Status:** YES - Actual Tool (SimpleTool)

**Tool Name:** `smart_consensus` (wrapper/facade for smart_consensus_v2)

**Purpose:** Simple, user-friendly interface for smart consensus without workflow complexity

**LLM Usage:**
- **Multi-model:** YES
- **User specifies models:** NO
- **System auto-selects:** YES
- **Delegates to:** SmartConsensusTool (smart_consensus_v2)

**Input Schema (SIMPLE):**
- `question` (required)
- `org_level` (optional, default "scaleup") 
- `relevant_files` (optional)
- `images` (optional)

**Key Difference:** Converts simple interface to workflow format internally, delegates all work to SmartConsensusTool.

---

### 3. layered_consensus.py

**Status:** YES - Actual Tool (SimpleTool)

**Tool Name:** `layered_consensus`

**Purpose:** Multi-layered consensus analysis with role-based model assignments

**LLM Usage:**
- **Multi-model:** YES
- **User specifies models:** NO
- **System auto-selects:** YES (via band_selector)
- **Mechanism:** Organization-level + band_selector

**Input Schema:**
- `question` (required)
- `org_level` (optional, default "startup") - Determines role count
- `model_count` (optional, default 5)
- `layers` (optional, default ["strategic", "analytical", "practical"])
- `cost_threshold` (optional, default "balanced")

**Model Selection Strategy:**
Uses `BandSelector` class to select models based on:
- Organization level (startup → scaleup → enterprise)
- Additive role structure (each level builds on previous)
- Cost tier preferences

**Role Assignments by Org Level:**
```
Startup (3 roles):
  - code_reviewer
  - security_checker
  - technical_validator

Scaleup (6 roles = startup + 3 professional):
  - [all above plus]
  - senior_developer
  - system_architect
  - devops_engineer

Enterprise (8 roles = scaleup + 2 executive):
  - [all above plus]
  - lead_architect
  - technical_director
```

**Model Selection:** Uses `band_selector.get_models_by_role(role, org_level, limit=1)` for each role.

---

### 4. dynamic_model_selector.py

**Status:** PARTIAL - Tool + Support Module

**As Tool (DynamicModelSelectorTool):** YES - SimpleTool for model selection recommendations

**Tool Name:** `dynamic_model_selector`

**Purpose:** Intelligent model selection based on task requirements, complexity, and budget

**LLM Usage:**
- **This tool itself:** NO - It generates prompts for an AI to answer
- **But used by:** Yes - Other tools call it to get model recommendations
- **Mechanism:** Uses prompt + AI model to generate recommendations

**Input Schema:**
- `requirements` (required) - Description of task requirements
- `task_type` (optional, default "general")
- `complexity_level` (optional, default "medium", enum: low/medium/high/critical)
- `budget_preference` (optional, default "balanced", enum: cost-optimized/balanced/performance)
- `num_models` (optional, default 3, range 1-10)

**Key Detail:** This tool *asks an AI model* to recommend which models to use, rather than auto-selecting itself.

**How It Works:**
1. Takes requirements + task type + complexity + budget
2. Creates a prompt asking an AI to recommend models
3. Uses new modular `ModelSelector` architecture if available
4. Falls back to simple prompt if not available

**Support Module Included:** `DynamicModelSelector` - Deprecated compatibility wrapper for model selection operations

---

## SUPPORT MODULES (Not Direct MCP Tools)

### 5. band_selector.py
**Type:** Support Module (no Tool class)
**Purpose:** Core model selection engine using band configuration
**Used by:** layered_consensus, dynamic_model_selector, other tools
**Key Methods:**
- `get_models_by_org_level(org_level, limit, role)`
- `get_models_by_cost_tier(tier, limit)`
- `get_models_by_role(role, org_level, limit)`
- `get_models_by_specialization(specialization, tier)`

**Model Pool Sources:**
- Loads from `docs/models/bands_config.json`
- Loads from `docs/models/models.csv`
- Has extensive fallback hardcoded models

---

### 6. smart_consensus.py (Phase 2/3)
**Type:** Support/Core Module (complex implementation with Phase 1-3 features)
**Purpose:** Complex smart consensus implementation with:
- Phase 1: Basic multi-model consensus
- Phase 2: Dynamic routing, cost optimization, intelligent fallback
- Phase 3: Caching, circuit breakers, health monitoring, streaming, recovery
**Status:** Core implementation file for `smart_consensus_v2`

---

### 7. model_evaluator.py
**Status:** YES - Actual Tool (WorkflowTool) 

**Tool Name:** `model_evaluator`

**Purpose:** Step-by-step evaluation of new models from OpenRouter URLs

**LLM Usage:** 
- **Auto Model Selection:** NO - uses parent class expert analysis
- **Web Scraping:** YES - Extracts model metrics from OpenRouter
- **AI Analysis:** YES - Calls expert analysis at final step
- **Not multi-model consensus** - workflow tool for evaluation

**Input Schema:**
- `openrouter_url` (required in step 1)
- `evaluation_type` (optional, enum: comprehensive/quick/metrics_only)

**Workflow Steps:**
1. Extract metrics via web scraping
2. Classify model (tier, org_level, specialization)
3. Score against existing models
4. Generate recommendations
5. Expert analysis (optional)

**Key Point:** This tool evaluates models but doesn't use multi-model consensus itself.

---

### 8. pr_prepare.py

**Status:** YES - Actual Tool (BaseTool)

**Tool Name:** `pr_prepare`

**Purpose:** Comprehensive PR preparation with GitHub integration

**LLM Usage:** NO - Pure git/GitHub operations
- No model selection
- No AI calls
- Analyzes git changes, generates PR content, creates GitHub PRs

**Input Schema:**
- `target_branch` (default "main")
- `base_branch` (default "auto")
- `change_type` (enum: feat/fix/docs/style/refactor/perf/test/chore)
- `title` (default "auto")
- `create_pr` (default false)
- Multiple flags: breaking, security, performance, phase_merge, etc.

**Key Point:** This is a pure automation tool with NO LLM integration.

---

### 9. pr_review.py

**Status:** YES - Actual Tool (BaseTool with AI integration)

**Tool Name:** `pr_review`

**Purpose:** Comprehensive GitHub PR review with AI consensus

**LLM Usage:**
- **Calls other tools:** YES - Uses `layered_consensus` for AI review decisions
- **Multi-model:** YES (via layered_consensus delegation)
- **User specifies models:** NO
- **Auto-select:** YES (via layered_consensus)

**Key Mechanism:**
1. Analyzes PR for code quality issues
2. Determines org_level based on issue severity
3. Calls layered_consensus tool for consensus review decision
4. Maps consensus result to PR approval recommendation

**Org Level Determination:**
```python
# Enterprise - for critical/security/performance or many issues
# Scaleup - for thorough reviews or moderate issues  
# Startup - for quick reviews and low issues
```

---

## SUPPORT/HELPER MODULES (No Tool Classes)

### 10. smart_consensus_cache.py
**Type:** Support Module
**Purpose:** LRU cache with TTL for Smart Consensus responses
**Features:** Hit rate tracking, metrics, automatic cleanup

### 11. smart_consensus_config.py
**Type:** Support Module
**Purpose:** Configuration profiles and validation
**Features:** Environment-based overrides, profile validation

### 12. smart_consensus_health.py
**Type:** Support Module
**Purpose:** Circuit breaker and health monitoring
**Features:** Failure detection, recovery strategies

### 13. smart_consensus_recovery.py
**Type:** Support Module
**Purpose:** Error classification and recovery strategies
**Features:** Exponential backoff, graceful degradation, context truncation

### 14. smart_consensus_monitoring.py
**Type:** Support Module
**Purpose:** Production monitoring and alerting
**Features:** State metrics, performance thresholds, alert callbacks

### 15. smart_consensus_streaming.py
**Type:** Support Module
**Purpose:** Response streaming and token optimization
**Features:** Context optimization, response compression, token tracking

### 16. promptcraft_mcp_bridge.py
**Status:** YES - Actual Tool (SimpleTool)

**Tool Name:** `promptcraft_mcp_bridge`

**Purpose:** Bridge between PromptCraft MCP client and zen-mcp-server tools

**LLM Usage:**
- **Delegates to:** ChatTool, ListModelsTool, DynamicModelSelectorTool
- **Not itself:** No direct model selection
- **Acts as:** Router/proxy

**Input Schema:**
- `action` (enum: analyze_route, smart_execute, list_models)
- `prompt` (optional)
- `user_tier` (optional)
- Various context-specific fields

---

## MODEL SELECTION PATTERN SUMMARY

### Category 1: Explicit Org Level Selection
- **smart_consensus_v2** - User provides org_level
- **layered_consensus** - User provides org_level
- **pr_review** - Auto-determines org_level from PR analysis

### Category 2: Request-Based Selection
- **dynamic_model_selector** - Analyzes requirements + complexity + budget

### Category 3: No LLM Selection (Operations Only)
- **pr_prepare** - Pure git automation
- **model_evaluator** - Web scraping + evaluation
- **promptcraft_mcp_bridge** - Router only

---

## CRITICAL INSIGHTS

1. **No User-Specified Models at MCP Boundary:** Most tools use automatic selection. Users don't specify which models to use directly.

2. **Band Selector is Central:** `band_selector.py` is the core model selection engine used by:
   - layered_consensus
   - dynamic_model_selector
   - Other tools needing model lists

3. **Org Level Patterns:**
   - Startup: 3 budget-conscious models
   - Scaleup: 6 balanced models  
   - Enterprise: 8 premium models

4. **Workflow vs Simple Tools:**
   - `smart_consensus_v2` = workflow (step-by-step execution)
   - `smart_consensus_simple` = facade (simple interface)
   - Both consult models in sequence

5. **Support Modules Implement Production Features:**
   - Caching (10% hit rate optimization)
   - Circuit breakers (failure handling)
   - Monitoring (metrics tracking)
   - Recovery (graceful degradation)
   - Streaming (token optimization)

6. **Temperature & Thinking:**
   - Most consensus tools: `TEMPERATURE_ANALYTICAL` + `thinking_mode="medium"`
   - Model evaluation: Standard workflow thinking
   - PR tools: No temperature/thinking (not AI-driven)

7. **Free Models Priority:**
   - When prefer_free_models=true (startup): Free models first
   - When prefer_free_models=false: Premium models first
   - Always has fallback to opposite tier

---

## FILE-BY-FILE CLASSIFICATION TABLE

| File | Is Tool? | Tool Type | LLM Use | Models | Auto-Select | Notes |
|------|----------|-----------|---------|--------|-------------|-------|
| smart_consensus_v2.py | YES | WorkflowTool | Multi-model | Via org_level | YES | Role-based consensus |
| smart_consensus_simple.py | YES | SimpleTool | Multi-model | Delegates | YES | Facade for v2 |
| smart_consensus.py | NO | Support | Core impl | Varies | YES | Phase 1-3 implementation |
| layered_consensus.py | YES | SimpleTool | Multi-model | Band select | YES | Role-layered consensus |
| band_selector.py | NO | Support | None | CSV/JSON | N/A | Core selection engine |
| dynamic_model_selector.py | YES/PARTIAL | SimpleTool | AI asks AI | AI chosen | YES | Recommendation tool |
| model_evaluator.py | YES | WorkflowTool | Web scrape | Existing | NO | Model evaluation |
| pr_prepare.py | YES | BaseTool | None | None | N/A | Git automation only |
| pr_review.py | YES | BaseTool | Delegates | Via consensus | YES | Uses layered_consensus |
| smart_consensus_cache.py | NO | Support | None | N/A | N/A | Caching layer |
| smart_consensus_config.py | NO | Support | None | N/A | N/A | Configuration |
| smart_consensus_health.py | NO | Support | None | N/A | N/A | Circuit breaker |
| smart_consensus_recovery.py | NO | Support | None | N/A | N/A | Error recovery |
| smart_consensus_monitoring.py | NO | Support | None | N/A | N/A | Metrics collection |
| smart_consensus_streaming.py | NO | Support | None | N/A | N/A | Token optimization |
| promptcraft_mcp_bridge.py | YES | SimpleTool | Delegates | N/A | YES | Router proxy |

