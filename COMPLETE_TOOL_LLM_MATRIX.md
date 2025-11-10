# Complete Tool & LLM Usage Matrix
**Zen MCP Server - All Tools Analysis**
**Date:** 2025-11-09

This document provides a comprehensive list of ALL tools (core + custom) in the Zen MCP Server, and for each tool identifies:
1. Whether it uses LLMs
2. How LLMs are selected (user-provided vs system-determined)
3. The specific selection mechanism

---

## Quick Reference Summary

**Total Tools:** 27 (18 core + 9 custom: 5 active + 3 deprecated + 1 router)

**By LLM Usage Pattern:**
- **User provides model (optional):** 9 core tools (analyze, chat, codereview, debug, precommit, refactor, secaudit, testgen, thinkdeep)
- **User provides models array:** 1 core tool (consensus)
- **System auto-selects models:** 1 custom tool (tiered_consensus) ✨ NEW
- **AI recommends models:** 1 custom tool (dynamic_model_selector)
- **No LLM usage:** 7 core tools + 3 custom tools (model_evaluator*, pr_prepare, promptcraft_mcp_bridge)
- **Delegates to external CLI:** 1 core tool (clink)
- **Auto-determines then delegates:** 1 custom tool (pr_review → tiered_consensus)
- **Deprecated:** 3 custom consensus tools (smart_consensus_v2, smart_consensus_simple, layered_consensus)

*model_evaluator: Partial LLM usage (optional expert analysis only)

**Recent Changes (2025-11-09):**
- ✨ Added: tiered_consensus - Unified consensus with additive tier architecture
- 🗑️ Deprecated: 3 consensus tools → moved to `/tools/custom/to_be_deprecated/` (deletion: 2025-12-09)

---

## PART 1: CORE MCP TOOLS (18 tools)

### Category A: Standard Tools - User Provides Model (Optional)

These tools accept an optional `model` parameter. If not provided, they use `DEFAULT_MODEL` from config.

---

#### 1. analyze
**Purpose:** Code analysis and investigation
**LLM Usage:** YES - Single model
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py
- **How determined:** If `DEFAULT_MODEL="auto"`, parameter becomes required in schema

**Additional Parameters:**
- `temperature` (0-1)
- `thinking_mode` (minimal/low/medium/high/max)

**Implementation:** SimpleTool - direct AI call

---

#### 2. chat
**Purpose:** General conversation with AI models
**LLM Usage:** YES - Single model
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py
- **How determined:** Same as analyze

**Additional Parameters:**
- `temperature` (0-1)
- `thinking_mode` (minimal/low/medium/high/max)

**Implementation:** SimpleTool - direct AI call

**Special Feature:** Supports conversation continuity via `continuation_id`

---

#### 3. codereview
**Purpose:** Code review and quality analysis
**LLM Usage:** YES - Single model + optional expert
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py
- **Expert Analysis:** Optional second model call for validation

**Additional Parameters:**
- `temperature` - Not exposed (uses analytical default)
- `thinking_mode` - Not exposed (WorkflowTool)
- `confidence` - If "certain", skips expert analysis

**Implementation:** WorkflowTool - multi-step with CLI guidance

---

#### 4. debug
**Purpose:** Debug issue investigation
**LLM Usage:** YES - Single model + optional expert
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py
- **Expert Analysis:** Optional for final validation

**Implementation:** WorkflowTool

---

#### 5. precommit
**Purpose:** Pre-commit checks and validation
**LLM Usage:** YES - Single model + optional expert
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py

**Implementation:** WorkflowTool

---

#### 6. refactor
**Purpose:** Code refactoring assistance
**LLM Usage:** YES - Single model + optional expert
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py

**Implementation:** WorkflowTool

---

#### 7. secaudit
**Purpose:** Security auditing
**LLM Usage:** YES - Single model + optional expert
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py

**Implementation:** WorkflowTool

---

#### 8. testgen
**Purpose:** Test generation
**LLM Usage:** YES - Single model + optional expert
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py

**Implementation:** WorkflowTool

---

#### 9. thinkdeep
**Purpose:** Deep reasoning and analysis
**LLM Usage:** YES - Single model
**Model Selection:**
- **Type:** User provides OR auto-default
- **Parameter:** `model` (optional)
- **Default:** `DEFAULT_MODEL` from config.py

**Special Feature:** Extended thinking capabilities

**Implementation:** SimpleTool

---

### Category B: Multi-Model Tool - User Provides Models Array

---

#### 10. consensus
**Purpose:** Multi-model consensus with stance-based analysis
**LLM Usage:** YES - Multi-model (2+ required)
**Model Selection:**
- **Type:** USER PROVIDES ARRAY
- **Parameter:** `models` (required) - Array of model configs
- **Format:** `[{"model": "gpt-5", "stance": "for"}, {"model": "gemini-pro", "stance": "against"}]`
- **Minimum:** 2 models required
- **Stances:** for / against / neutral

**How It Works:**
1. User provides 2+ models with stances
2. Each model analyzes from their assigned stance
3. System synthesizes consensus from all perspectives

**Additional Parameters:**
- `temperature` (0-1, default 0.7)
- `thinking_mode` (default "medium")

**Implementation:** ConsensusTool - orchestrates multiple model calls

**Key Constraint:** Each (model, stance) pair must be unique

---

### Category C: CLI Workflow Tools - No Direct LLM Calls

These tools guide the CLI through workflows but don't make direct AI calls themselves.

---

#### 11. docgen
**Purpose:** Documentation generation workflow
**LLM Usage:** NO - CLI workflow only
**Model Selection:** N/A

**How It Works:**
- Guides CLI through documentation steps
- CLI makes its own AI calls as needed
- Returns structured instructions

**Implementation:** WorkflowTool (CLI-driven)

---

#### 12. planner
**Purpose:** Task planning workflow
**LLM Usage:** NO - CLI workflow only
**Model Selection:** N/A

**How It Works:**
- Guides CLI through planning steps
- CLI executes analysis with its own model
- Returns planning framework

**Implementation:** WorkflowTool (CLI-driven)

---

#### 13. tracer
**Purpose:** Execution tracing workflow
**LLM Usage:** NO - CLI workflow only
**Model Selection:** N/A

**Implementation:** WorkflowTool (CLI-driven)

---

### Category D: Orchestration Tool - Returns Instructions

---

#### 14. apilookup
**Purpose:** API/SDK documentation lookup
**LLM Usage:** NO - Orchestration only
**Model Selection:** N/A

**How It Works:**
1. Analyzes request
2. Returns web search instructions to CLI
3. CLI executes search with its own tools
4. No direct AI model calls

**Implementation:** LookupTool - orchestration layer

---

### Category E: Data Transformation Tool

---

#### 15. challenge
**Purpose:** Critical thinking validation
**LLM Usage:** NO - Data transformation only
**Model Selection:** N/A

**How It Works:**
- Wraps user prompt with critical thinking instructions
- Returns transformed prompt
- CLI then uses transformed prompt with its own model
- No direct model calls

**Implementation:** ChallengeTool - prompt transformer

---

### Category F: Utility Tools - No AI

---

#### 16. listmodels
**Purpose:** List available AI models
**LLM Usage:** NO
**Model Selection:** N/A

**How It Works:**
- Queries ModelProviderRegistry
- Returns available models, aliases, capabilities
- Pure data retrieval

**Implementation:** ListModelsTool

---

#### 17. version
**Purpose:** Show server version info
**LLM Usage:** NO
**Model Selection:** N/A

**Implementation:** VersionTool

---

### Category G: External CLI Bridge

---

#### 18. clink
**Purpose:** CLI-to-CLI bridging (spawn external AI CLI as subagent)
**LLM Usage:** YES - But delegates to external CLI
**Model Selection:**
- **Type:** User specifies CLI, CLI handles model
- **Parameter:** `cli_name` (required) - e.g., "gemini", "codex", "claude"
- **Available CLIs:** claude, codex, gemini (configured in conf/cli_clients)
- **Model selection:** Delegated to the external CLI

**How It Works:**
1. User specifies which CLI to use (gemini/codex/claude)
2. Spawns that CLI as subprocess
3. Forwards prompt to external CLI
4. External CLI uses its own model selection
5. Returns CLI's response

**Additional Parameters:**
- `role` (optional) - Preset role for CLI (default/codereviewer/planner)

**Implementation:** CLinkTool - subprocess manager

---

## PART 2: CUSTOM TOOLS (5 active tools, 3 deprecated)

### Category A: Multi-Model Consensus Tools - System Auto-Selects

---

#### 19. tiered_consensus ✨ NEW
**Purpose:** Unified consensus with additive tier architecture
**LLM Usage:** YES - Multi-model (3-8 models, additive tiers)
**Model Selection:**
- **Type:** SYSTEM AUTO-SELECTS via BandSelector
- **User provides:** `level` (1, 2, or 3) + `prompt`
- **System determines:** Which models + how many + which roles (data-driven)

**How System Determines Models:**

**Step 1 - Load Models via BandSelector:**
```
Source 1: docs/models/models.csv (36 models)
Source 2: docs/models/bands_config.json (9 band categories)
NO HARDCODED LISTS - Fully data-driven
```

**Step 2 - Select Models by Level (ADDITIVE ARCHITECTURE):**
```
Level 1 (Foundation): 3 free models
  - BandSelector.get_models_by_cost_tier("free", limit=5)
  - Failover: Try multiple free models (transient availability)
  - Target: 3 available free models
  - Cost: $0

Level 2 (Professional): Level 1 + 3 economy models (6 total)
  - Includes: All 3 models from Level 1 (ADDITIVE)
  - Plus: BandSelector.get_models_by_cost_tier("economy", limit=3)
  - Cost: ~$0.50

Level 3 (Executive): Level 2 + 2 premium models (8 total)
  - Includes: All 6 models from Level 2 (ADDITIVE)
  - Plus: BandSelector.get_models_by_cost_tier("premium", limit=2)
  - Cost: ~$5.00
```

**Step 3 - Assign Roles by Level (ADDITIVE):**
```
Level 1: 3 roles
  - code_reviewer
  - security_checker
  - technical_validator

Level 2: Level 1 + 3 roles (6 total)
  - All roles from Level 1 (ADDITIVE)
  - Plus: senior_developer, system_architect, devops_engineer

Level 3: Level 2 + 2 roles (8 total)
  - All roles from Level 2 (ADDITIVE)
  - Plus: lead_architect, technical_director
```

**Input Parameters:**
- `prompt` (required) - The question/proposal to analyze
- `level` (required) - Tier level (1, 2, or 3)
- `domain` (optional, default "code_review") - code_review, security, architecture, general
- `include_synthesis` (optional, default true)
- `max_cost` (optional) - Override cost limit

**Temperature & Thinking:**
- Temperature: Analytical (0.3-0.5)
- Thinking mode: "medium"
- Applied to all model consultations

**Free Model Failover (from dynamic-model-availability.md ADR):**
- Free models: Transient availability (try multiple)
- Cache: 5-minute TTL for availability status
- Paid models: Alert on failure (deprecation indicator)

**Implementation:** WorkflowTool - Sequential role consultation with synthesis

**Key Files:**
- `tools/custom/tiered_consensus.py` - Main tool (400 lines)
- `tools/custom/consensus_models.py` - TierManager + BandSelector (450 lines)
- `tools/custom/consensus_roles.py` - RoleAssigner + domains (350 lines)
- `tools/custom/consensus_synthesis.py` - SynthesisEngine (400 lines)

**Replaces:** smart_consensus_v2, smart_consensus_simple, layered_consensus (deprecated 2025-11-09)

---

#### 20. ~~smart_consensus_v2~~ (DEPRECATED - moved to to_be_deprecated)
**Purpose:** Intelligent multi-model consensus with role-based analysis
**LLM Usage:** YES - Multi-model (3-8 models)
**Model Selection:**
- **Type:** SYSTEM AUTO-SELECTS
- **User provides:** `org_level` (startup/scaleup/enterprise)
- **System determines:** Which models + how many + which roles

**How System Determines Models:**

**Step 1 - Determine Role Count:**
```
Startup: 3 roles
Scaleup: 6 roles
Enterprise: 8 roles
```

**Step 2 - Assign Roles:**
```
Startup:
  - code_reviewer
  - security_checker
  - technical_validator

Scaleup (adds 3):
  - senior_developer
  - system_architect
  - devops_engineer

Enterprise (adds 2):
  - lead_architect
  - technical_director
```

**Step 3 - Select Models for Each Role:**
```
If prefer_free_models=True (startup):
  Priority: Free models first
  - deepseek/deepseek-chat:free
  - meta-llama/llama-3.3-70b-instruct:free
  - qwen/qwen-2.5-coder-32b-instruct:free
  - microsoft/phi-4-reasoning:free
  - meta-llama/llama-3.1-405b-instruct:free
  Fallback: Premium models

If prefer_free_models=False (scaleup/enterprise):
  Priority: Premium models
  - anthropic/claude-opus-4.1
  - openai/gpt-5
  - google/gemini-2.5-pro
  - deepseek/deepseek-r1-0528
  - mistralai/mistral-large-2411
  Fallback: Free models
```

**Input Parameters:**
- `question` (required) - The analysis question
- `org_level` (optional, default "scaleup")
- `relevant_files` (optional)
- `images` (optional)

**Temperature & Thinking:**
- Temperature: Analytical (0.3-0.5)
- Thinking mode: "medium"

**Implementation:** WorkflowTool - Sequential role consultation

---

#### 21. ~~smart_consensus_simple~~ (DEPRECATED - moved to to_be_deprecated)
**Deprecated:** 2025-11-09
**Replaced By:** tiered_consensus
**Reason:** Fragmented functionality, hardcoded models, complex API

---

#### 22. ~~layered_consensus~~ (DEPRECATED - moved to to_be_deprecated)
**Deprecated:** 2025-11-09
**Replaced By:** tiered_consensus
**Reason:** SimpleTool (1 LLM call simulating perspectives), not true multi-model consensus

---

### Category B: Other Custom Tools

---

#### 23. dynamic_model_selector
**Purpose:** AI-powered model recommendation system
**LLM Usage:** YES - Uses AI to recommend models
**Model Selection:**
- **Type:** HYBRID - AI analyzes requirements and recommends models
- **User provides:** Task requirements, complexity, budget
- **System (AI) determines:** Which models to recommend

**How System Determines Models:**

**Step 1 - User Provides Context:**
```
- requirements: "I need to debug a memory leak in a Python service"
- task_type: "debugging"
- complexity_level: "high"
- budget_preference: "balanced"
- num_models: 3
```

**Step 2 - System Creates Analysis Prompt:**
```
Prompt template includes:
- Task requirements
- Complexity assessment
- Available model catalog
- Budget constraints
- Specialization needs
```

**Step 3 - AI Model Analyzes:**
An AI model (specified by user or default) analyzes the prompt and returns:
```
Recommended models:
1. deepseek-r1 (reasoning capability for debugging)
2. claude-opus-4.1 (code analysis)
3. qwen-coder:free (cost-effective supplementary)

Rationale: High complexity debugging requires reasoning models...
```

**Input Parameters:**
- `requirements` (required) - Task description
- `task_type` (optional, default "general")
- `complexity_level` (optional, enum: low/medium/high/critical)
- `budget_preference` (optional, enum: cost-optimized/balanced/performance)
- `num_models` (optional, default 3, range 1-10)

**Implementation:** SimpleTool - AI asks AI which models to use

**Key Distinction:** This tool doesn't directly select models; it asks another AI to make recommendations.

---

### Category C: Workflow Tools - Optional LLM

---

#### 24. model_evaluator
**Purpose:** Evaluate new OpenRouter models
**LLM Usage:** PARTIAL - Web scraping + optional expert analysis
**Model Selection:**
- **Type:** User provides OR auto-default (for expert analysis only)
- **Parameter:** `model` (optional)
- **Default:** Uses parent WorkflowTool expert analysis

**How It Works:**
1. Extract metrics from OpenRouter URL (web scraping)
2. Classify model into tiers (algorithm-based)
3. Score against existing models (comparison)
4. Generate recommendations (analysis)
5. Optional: Expert AI validation

**Not a Multi-Model Tool:** Evaluates models but doesn't use consensus

**Input Parameters:**
- `openrouter_url` (required in step 1)
- `evaluation_type` (optional, enum: comprehensive/quick/metrics_only)

**Implementation:** WorkflowTool

---

### Category D: Automation Tools - No LLM

---

#### 25. pr_prepare
**Purpose:** GitHub PR preparation automation
**LLM Usage:** NO
**Model Selection:** N/A

**How It Works:**
1. Analyzes git changes (git diff, git log)
2. Validates branch strategy
3. Generates PR description (template-based)
4. Creates GitHub PR (via gh CLI)
5. Includes WhatTheDiff shortcode for AI summary

**Pure Automation:** Git operations, no AI model calls

**Input Parameters:**
- `target_branch` (default "main")
- `base_branch` (default "auto")
- `change_type` (feat/fix/docs/etc.)
- `title` (default "auto")
- `create_pr` (default false)
- Multiple flags: breaking, security, performance, etc.

**Implementation:** BaseTool - Git/GitHub automation

---

#### 26. pr_review
**Purpose:** GitHub PR review with AI consensus
**LLM Usage:** YES - Delegates to tiered_consensus
**Model Selection:**
- **Type:** SYSTEM AUTO-DETERMINES via delegation
- **Delegates to:** tiered_consensus tool
- **How:** Analyzes PR, determines level, calls tiered_consensus

**How System Determines Models:**

**Step 1 - Analyze PR Issues:**
```python
issue_count = len(quality_issues)
has_security = any(issue.severity == "security")
has_performance = any(issue.severity == "performance")
```

**Step 2 - Determine Tier Level:**
```python
if has_security or has_performance or issue_count > 10:
    level = 3  # Executive tier - 8 models
elif issue_count > 5:
    level = 2  # Professional tier - 6 models
else:
    level = 1  # Foundation tier - 3 models
```

**Step 3 - Call tiered_consensus:**
```python
tiered_consensus(
    prompt=f"Should we approve PR #{pr_number}?",
    level=level,
    domain="code_review"
)
```

**Step 4 - Map Consensus to Approval:**
```
Consensus Result → PR Action
Strong approval → APPROVE
Conditional approval → COMMENT (with conditions)
Rejection → REQUEST_CHANGES
```

**Input Parameters:**
- `pr_number` (required)
- `repo` (optional)
- `review_type` (optional, enum: quick/standard/thorough/critical)

**Implementation:** BaseTool with AI delegation

---

### Category E: Router/Proxy Tool

---

#### 27. promptcraft_mcp_bridge
**Purpose:** Bridge between PromptCraft MCP client and zen tools
**LLM Usage:** NO - Router only
**Model Selection:** N/A (delegates to other tools)

**How It Works:**
1. Receives request from PromptCraft
2. Routes to appropriate zen tool:
   - ChatTool
   - ListModelsTool
   - DynamicModelSelectorTool
3. Returns tool response

**Input Parameters:**
- `action` (enum: analyze_route, smart_execute, list_models)
- `prompt` (optional)
- `user_tier` (optional)
- Various context fields

**Implementation:** SimpleTool - Router/proxy

---

## PART 3: SUPPORT MODULES (Not MCP Tools)

These are NOT callable tools but support the custom tools above.

### Active Support Modules

#### band_selector.py
**Type:** Support Module (BandSelector class)
**Purpose:** Core model selection engine
**Used by:** tiered_consensus, dynamic_model_selector

**Key Methods:**
- `get_models_by_org_level(org_level, limit, role)`
- `get_models_by_cost_tier(tier, limit)`
- `get_models_by_role(role, org_level, limit)`
- `get_models_by_specialization(specialization, tier)`

**Model Sources:**
1. `docs/models/bands_config.json` - Band configuration
2. `docs/models/models.csv` - Model catalog
3. Hardcoded fallback models

---

#### consensus_models.py
**Type:** Support Module (TierManager, AvailabilityCache)
**Purpose:** Tiered consensus model selection and availability caching
**Used by:** tiered_consensus

**Key Classes:**
- `TierManager` - Additive tier model selection
- `AvailabilityCache` - 5-minute TTL model availability cache

**Key Features:**
- Additive tier architecture (Level 2 includes Level 1's models)
- Free model failover logic
- Paid model deprecation alerts

---

#### consensus_roles.py
**Type:** Support Module (RoleAssigner)
**Purpose:** Domain-specific role management for tiered consensus
**Used by:** tiered_consensus

**Key Features:**
- 18 professional role definitions
- 4 domains: code_review, security, architecture, general
- Additive role assignments per tier level

---

#### consensus_synthesis.py
**Type:** Support Module (SynthesisEngine)
**Purpose:** Multi-model perspective aggregation and consensus generation
**Used by:** tiered_consensus

**Key Features:**
- Aggregates perspectives from multiple models
- Identifies consensus and disagreements
- Generates executive summaries

---

### Deprecated Support Modules (moved to to_be_deprecated/)

**Deletion Date:** 2025-12-09

- **smart_consensus.py** - Core implementation (deprecated)
- **smart_consensus_cache.py** - LRU cache with TTL
- **smart_consensus_config.py** - Configuration profiles
- **smart_consensus_health.py** - Circuit breaker
- **smart_consensus_recovery.py** - Error recovery
- **smart_consensus_monitoring.py** - Metrics collection
- **smart_consensus_streaming.py** - Token optimization

---

## PART 4: MODEL SELECTION PATTERN SUMMARY

### Pattern 1: User Provides Model (Optional) - 9 Core Tools
```
Tools: analyze, chat, codereview, debug, precommit, refactor, secaudit, testgen, thinkdeep

Mechanism:
- User can specify `model` parameter
- If not specified, uses DEFAULT_MODEL from config
- If DEFAULT_MODEL="auto", parameter becomes required
- Runtime checks ModelProviderRegistry for availability
```

### Pattern 2: User Provides Models Array - 1 Core Tool
```
Tool: consensus

Mechanism:
- User MUST provide `models` array
- Each entry: {"model": "name", "stance": "for/against/neutral"}
- Minimum 2 models
- Each (model, stance) pair must be unique
```

### Pattern 3: System Auto-Selects via Tier Level - 1 Custom Tool
```
Tool: tiered_consensus

Mechanism:
- User provides level (1/2/3)
- System determines models via BandSelector (data-driven)
  - Level 1: 3 free models ($0)
  - Level 2: Level 1 + 3 economy models = 6 total (~$0.50)
  - Level 3: Level 2 + 2 premium models = 8 total (~$5)
- System assigns roles per domain (additive tiers)
- Free model failover with 5-minute availability cache
- Additive architecture (higher levels include all lower level models)

Deprecated Tools (moved to to_be_deprecated/):
- smart_consensus_v2, smart_consensus_simple, layered_consensus (deletion: 2025-12-09)
```

### Pattern 4: AI Recommends Models - 1 Custom Tool
```
Tool: dynamic_model_selector

Mechanism:
- User describes requirements
- System creates analysis prompt
- AI model analyzes and recommends models
- Returns recommendation with rationale
```

### Pattern 5: Auto-Determines then Delegates - 1 Custom Tool
```
Tool: pr_review

Mechanism:
- Analyzes PR for issues
- Determines tier level from severity (1/2/3)
- Delegates to tiered_consensus
- tiered_consensus selects models via BandSelector
```

### Pattern 6: No LLM Usage - 9 Tools
```
Tools: docgen, planner, tracer, apilookup, challenge, listmodels, version, pr_prepare, promptcraft_mcp_bridge

Mechanism:
- Pure workflow guidance
- Data transformation
- Git/GitHub automation
- Routing/orchestration
```

### Pattern 7: External CLI Delegation - 1 Core Tool
```
Tool: clink

Mechanism:
- User specifies CLI name (gemini/codex/claude)
- Spawns external CLI subprocess
- CLI handles its own model selection
- Returns CLI response
```

---

## PART 5: KEY INSIGHTS

### 1. Model Selection Hierarchy
```
Level 1: User Explicit (consensus models array)
Level 2: User Optional (model parameter in 9 tools)
Level 3: System Auto (org_level in consensus tools)
Level 4: AI Recommends (dynamic_model_selector)
Level 5: Auto-Determine + Delegate (pr_review)
Level 6: External (clink to other CLIs)
Level 7: None (utility/automation tools)
```

### 2. Default Model Resolution
```
When DEFAULT_MODEL in config.py:
- "auto" → requires model parameter in schema
- "gpt-5" → model parameter optional, defaults to gpt-5
- Provider unavailable → falls back to auto mode

is_effective_auto_mode() checks:
1. DEFAULT_MODEL value
2. Provider availability in ModelProviderRegistry
3. Returns true if model selection required
```

### 3. Tier Level Model Counts (tiered_consensus)
```
Level 1 (Foundation): 3 models (free tier)
  - All free models
  - Cost: $0
  - Core roles only
  - Use case: Quick validation

Level 2 (Professional): 6 models (ADDITIVE)
  - Includes: All 3 models from Level 1
  - Plus: 3 economy models
  - Cost: ~$0.50
  - Professional roles added
  - Use case: Standard decisions

Level 3 (Executive): 8 models (ADDITIVE)
  - Includes: All 6 models from Level 2
  - Plus: 2 premium models
  - Cost: ~$5.00
  - Executive roles added
  - Use case: Critical decisions
```

### 4. Free Model Failover (tiered_consensus)
```
Free Model Availability Pattern:
  - Transient availability (404 today ≠ permanently broken)
  - Try multiple free models before economy tier fallback
  - AvailabilityCache: 5-minute TTL to avoid repeated checks
  - Alerts: Paid model failures indicate deprecation needed

Example Failover Flow (Level 1):
  Target: 3 available free models
  Candidates: BandSelector.get_models_by_cost_tier("free", limit=5)

  For each candidate:
    1. Check availability cache
    2. Skip if known unavailable (cached)
    3. Perform health check if not cached
    4. Add to available list if responsive
    5. Stop when target count reached (3 models)

  If insufficient free models available:
    - Log warning
    - Return available free models (may be < 3)
    - Do NOT auto-fallback to paid tiers

Deprecated Model Selection (old consensus tools):
  - Hardcoded FREE_MODELS and PREMIUM_MODELS lists
  - prefer_free_models flag controlled priority
  - No availability caching
```

### 5. Temperature & Thinking Patterns
```
SimpleTool (user-facing):
  - Exposes temperature (0-1)
  - Exposes thinking_mode (minimal/low/medium/high/max)
  - User controls

WorkflowTool (CLI-driven):
  - Does NOT expose temperature/thinking in schema
  - Uses analytical defaults
  - Controlled by tool implementation

Consensus Tools:
  - TEMPERATURE_ANALYTICAL (0.3-0.5)
  - thinking_mode="medium"
  - Consistent across consultations
```

### 6. Expert Analysis Pattern (WorkflowTool)
```
After CLI completes workflow investigation:
  If use_assistant_model=True (default):
    - Calls expert model for validation
    - Expert reviews CLI findings
    - Synthesizes final recommendation

  If use_assistant_model=False:
    - Skips expert analysis
    - Returns CLI findings directly

  If confidence="certain":
    - Skips expert analysis
    - Assumes local analysis complete
```

### 7. Multi-Model Consultation Patterns

**Consensus Tool (core):**
```
User provides: 2+ models with stances
Process: Parallel or sequential consultation
Output: Synthesized consensus from all stances
```

**Tiered Consensus Tool (custom):**
```
User provides: level (1/2/3) + prompt
System determines: 3-8 models + roles (data-driven via BandSelector)
Process: Sequential role-based consultation with synthesis
Output: Executive summary with consensus/disagreements
Features:
  - Additive tier architecture (higher levels include lower tier models)
  - Free model failover with 5-minute availability cache
  - Domain-specific roles (code_review, security, architecture, general)
  - Cost estimation per tier
```

**Deprecated Tools (moved to to_be_deprecated/):**

**Smart Consensus V2 (deprecated 2025-11-09):**
```
User provides: org_level
System determines: 3-8 models + roles (hardcoded lists)
Issues: Hardcoded models, no additive architecture
Replaced by: tiered_consensus
```

**Layered Consensus (deprecated 2025-11-09):**
```
User provides: org_level + cost_threshold
Issues: SimpleTool (1 LLM call simulating perspectives)
Replaced by: tiered_consensus
```

### 8. CLI vs Tool LLM Usage

**CLI-Driven Tools (docgen, planner, tracer):**
- Tool returns workflow steps
- CLI executes steps
- CLI makes its own AI calls
- Tool doesn't call AI directly

**AI-Calling Tools (analyze, chat, codereview, etc.):**
- Tool calls AI models directly
- Returns AI response to CLI
- CLI receives final output

---

## PART 6: CONFIGURATION FILES

### Model Selection Configs
```
/home/byron/dev/zen-mcp-server/config.py
- DEFAULT_MODEL setting
- Provider configurations

/home/byron/dev/zen-mcp-server/docs/models/bands_config.json
- Band definitions
- Model capabilities
- Cost tier assignments
- Use case mappings

/home/byron/dev/zen-mcp-server/docs/models/models.csv
- Model catalog
- Performance metrics
- Availability status

/home/byron/dev/zen-mcp-server/conf/cli_clients/
- External CLI configurations (for clink)
- claude.yaml
- codex.yaml
- gemini.yaml
```

---

## PART 7: COMPLETE TOOL REFERENCE TABLE

| # | Tool Name | Type | LLM Use | Selection Method | Models Count | User Input | System Determines |
|---|-----------|------|---------|------------------|--------------|------------|-------------------|
| **CORE TOOLS** |
| 1 | analyze | Simple | Yes | User/Auto | 1 | `model` (opt) | DEFAULT_MODEL |
| 2 | chat | Simple | Yes | User/Auto | 1 | `model` (opt) | DEFAULT_MODEL |
| 3 | codereview | Workflow | Yes | User/Auto | 1+expert | `model` (opt) | DEFAULT_MODEL |
| 4 | debug | Workflow | Yes | User/Auto | 1+expert | `model` (opt) | DEFAULT_MODEL |
| 5 | precommit | Workflow | Yes | User/Auto | 1+expert | `model` (opt) | DEFAULT_MODEL |
| 6 | refactor | Workflow | Yes | User/Auto | 1+expert | `model` (opt) | DEFAULT_MODEL |
| 7 | secaudit | Workflow | Yes | User/Auto | 1+expert | `model` (opt) | DEFAULT_MODEL |
| 8 | testgen | Workflow | Yes | User/Auto | 1+expert | `model` (opt) | DEFAULT_MODEL |
| 9 | thinkdeep | Simple | Yes | User/Auto | 1 | `model` (opt) | DEFAULT_MODEL |
| 10 | consensus | Consensus | Yes | User Array | 2+ | `models` (req) | User specifies all |
| 11 | docgen | Workflow | No | N/A | 0 | - | CLI-driven |
| 12 | planner | Workflow | No | N/A | 0 | - | CLI-driven |
| 13 | tracer | Workflow | No | N/A | 0 | - | CLI-driven |
| 14 | apilookup | Orchestrator | No | N/A | 0 | - | Returns instructions |
| 15 | challenge | Transformer | No | N/A | 0 | - | Prompt wrapper |
| 16 | listmodels | Utility | No | N/A | 0 | - | Data query |
| 17 | version | Utility | No | N/A | 0 | - | Data query |
| 18 | clink | Bridge | Yes | External | 1 | `cli_name` | External CLI |
| **CUSTOM TOOLS (Active)** |
| 19 | tiered_consensus | Workflow | Yes | Auto | 3-8 | `level` + `prompt` | BandSelector + tiers |
| 20 | ~~smart_consensus_v2~~ | ~~Workflow~~ | ~~Yes~~ | ~~Auto~~ | ~~3-8~~ | ~~`org_level`~~ | **DEPRECATED 2025-11-09** |
| 21 | ~~smart_consensus_simple~~ | ~~Simple~~ | ~~Yes~~ | ~~Auto~~ | ~~3-8~~ | ~~`org_level`~~ | **DEPRECATED 2025-11-09** |
| 22 | ~~layered_consensus~~ | ~~Simple~~ | ~~Yes~~ | ~~Auto~~ | ~~Variable~~ | ~~`org_level`~~ | **DEPRECATED 2025-11-09** |
| 23 | dynamic_model_selector | Simple | Yes | AI Recommends | Variable | `requirements` + `complexity` | AI analyzes |
| 24 | model_evaluator | Workflow | Partial | User/Auto | 0+expert | `model` (opt) | Expert only |
| 25 | pr_prepare | Automation | No | N/A | 0 | - | Git automation |
| 26 | pr_review | Automation | Yes | Auto-Delegate | 3-8 | `pr_number` | Analyzes → level → delegates |
| 27 | promptcraft_mcp_bridge | Router | No | N/A | 0 | - | Routes to other tools |

---

## CONCLUSION

This comprehensive matrix documents all 27 tools in the Zen MCP Server (18 core + 9 custom), showing:

1. **User-Controlled:** 10 tools where user can specify models (9 core + 1 consensus)
2. **System-Controlled:** 1 active consensus tool (tiered_consensus) + 3 deprecated
3. **Hybrid:** 1 tool (dynamic_model_selector) where AI recommends models
4. **No LLM:** 9 tools that don't use AI models (7 core + 2 custom)
5. **External:** 1 tool (clink) that delegates to external CLIs

**Recent Changes (2025-11-09):**
- ✨ **NEW:** tiered_consensus - Unified consensus with additive tier architecture
- 🗑️ **DEPRECATED:** smart_consensus_v2, smart_consensus_simple, layered_consensus
  - Moved to: `/tools/custom/to_be_deprecated/`
  - Deletion date: 2025-12-09
  - Reason: Fragmented functionality, hardcoded models, complex API
  - Replaced by: tiered_consensus with 71% parameter reduction and BandSelector integration

The system demonstrates sophisticated model selection patterns ranging from simple user choice to complex multi-model consensus with additive tier architecture and data-driven model selection via BandSelector.
