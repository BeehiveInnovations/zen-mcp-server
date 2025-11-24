**Prompt Template**

Use the following prompt (fill in any placeholders you later refine) to direct another engineering-capable AI agent to analyze all feature branches and produce an enhanced refactor dossier plus a forward plan.

---
You are an expert software analysis agent. Repository: zen-mcp-server (current checkout is a fork rewound to upstream commit 12090646ee83f2368311d595d87ae947e46ddacd). The prior work (now removed from main) lives across several branches. Your job: 1) Reconstruct and enhance the refactor summary with deeper, quantified evidence, and 2) Produce a clean, dependency-ordered implementation plan to redo this work from scratch with improvements.

Pillars (high-level themes to expand into 'refactor pillars'):

- Pillar 1 — Kilo / OpenRouter Integration:
  - Intent: Add explicit support for Kilo-hosted models while preserving OpenRouter proxy compatibility.
  - Focus: API key precedence (KILO_API_KEY vs OPENROUTER_KEY), endpoint selection (direct Kilo vs proxy), model prefix resolution (kilo: / openrouter:), header mutation for proxy validation, and tests for both code paths.

- Pillar 2 — Consensus Async Refactor:
  - Intent: Replace sequential multi-model consultations with a concurrent asyncio-based approach to lower wall-clock latency while preserving deterministic aggregation and robust error normalization.
  - Focus: `tools/consensus.py` concurrency helper, per-model timing/latency capture, normalized response schema, and safety around partial failures.

- Pillar 3 — CLI Bridge Provider:
  - Intent: Introduce a CLI provider bridge so CLI tools can route to MCP models safely and with argument validation; reduce complexity to a single logical CLI model where appropriate.
  - Focus: provider registration, hybrid routing/conflict resolution, model restrictions and mapping for CLI contexts, tests for argument parsing and registration.

- Pillar 4 — Testing & Model Updates:
  - Intent: Improve test reliability and local dev ergonomics by standardizing on lighter-weight models for CI/dev (e.g., qwen3:0.6b), adding env sanitization, and marking/flaking vision tests until stable.
  - Focus: test parametrization, env isolation, xfail policies for vision, and CI performance improvements.

- Pillar 5 — Documentation & Chores:
  - Intent: Provide clear design docs, upgrade guides, changelogs, and housekeeping (linting, scripts, gitignore) to reduce onboarding friction.
  - Focus: docs/consensus-async-refactor.md, README updates (Kilo usage), scripts for integrations, and ruff/isort fixes.

ANALYSIS SCOPE
Baseline (fork point): commit 12090646ee83f2368311d595d87ae947e46ddacd on upstream/main.
Branches to inspect (local or remote):
- feature/consensus-async-refactor-doc (97ea377)
- local-modifications (efebb56)
- update-gitignore-and-remote (f8dcf1e) and remote variant (084fff3)
- feature/cli-bridge-provider (33fc9c8)
- feature/kilo-api-support (94e8af9)
- codex/fix-critical-regression-in-modelproviderregistry (648e070)
- fix/registry-overwrite-default (2b0f594)

(If any branch missing locally: fetch origin and use remote ref.)

DELIVERABLES (Produce BOTH a richly formatted Markdown report AND a machine-readable JSON block at the end)

1. Thematic Expansion:
  For each refined theme (you may split or merge):
  - Intent (one-line mission)
  - Motivation (problem addressed with evidence from code/messages)
  - Key Files (group by subsystem: providers/, tools/, tests/, docs/, scripts/, conf/)
  - Quantitative Diff Metrics (lines added/removed, files touched, net complexity: e.g., functions added, async conversions)
  - Notable Code Patterns (e.g., asyncio concurrency pattern, model prefix normalization, header mutation, error normalization)
  - Added/Changed Environment Variables (name, purpose, default behavior)
  - Risks Introduced (e.g., silent fallback ambiguity, race conditions, API key precedence confusion)
  - Test Coverage Impact (new test modules, parametrizations, xfails, skipped vision tests)
  - Observability & Logging changes (structure, latency metrics, structured fields)
  - Improvement Opportunities (what should change in a re-implementation)

2. Cross-Cutting Inventory:
  - Providers Impact Matrix: provider name → changes (routing logic, key selection, model alias rules, validation)
  - Model Taxonomy Adjustments: new logical models, removed/replaced models (e.g., qwen3:0.6b vs llama3.2 vs flash)
  - Tooling Changes: consensus workflow shift (sequential → concurrent), timing capture, normalization schema
  - Documentation Artifacts Added (list + inferred intent)
  - Scripts / automation modifications (e.g., run-server.sh, configure-integrations.sh)
  - Logging Format Standardization details

3. Dependency Graph:
  - Nodes: Thematic deliverables or subsystems (e.g., "Provider key precedence", "Async consensus engine", "CLI bridge registration", "Model alias resolution", "Test env sanitization")
  - Edges: Must precede relationships (justify briefly)
  - Identify critical path and parallelizable clusters

4. Risk & Mitigation Register:
  Table (or list) with: Risk ID, Description, Impact, Likelihood, Proposed Mitigation, Detection Strategy.

5. Re-Implementation Plan (Greenfield):
  Phased approach (Phase 0…N). For each phase:
  - Objective
  - Entry Criteria
  - Exit Criteria (objective acceptance tests)
  - Tasks (concise, actionable)
  - Quality Gates (lint/tests/perf thresholds)
  - Rollback / fallback plan (if applicable)
  Provide a final "Cutover Checklist".

6. Test Strategy:
  - Test layers: unit, provider integration (mock vs live), performance (latency assertions), regression (model alias resolution), resilience (partial model failure in consensus).
  - Enumerate missing tests we should add (e.g., header stripping when switching to direct Kilo, error normalization when one model times out).
  - Suggest a minimal test naming schema.

7. Observability Plan:
  - Metrics to emit (latency per model, concurrency span, key selection path, failure taxonomy)
  - Log structure recommendations (JSON fields)
  - Suggested tracing spans

8. Proposed Improvements Beyond Original:
  - Caching or debounce for repetitive model metadata calls
  - Structured schema versioning for provider responses
  - Pluggable consensus strategies (sequential, concurrent, quorum, weighted)
  - Unified model alias registry with validation
  - Configuration validator for env + custom_models.json coherence

9. JSON Summary (final block):
  {
    "baseline_commit": "...",
    "themes": [ { "name": "...", "metrics": {...}, "env_vars":[...], "risks":[...] } ],
    "dependencies": { "nodes":[...], "edges":[["A","B"], ...] },
    "phases":[ { "phase": 0, "objective":"...", "tasks":[...], "exit_criteria":[...] } ],
    "tests": { "missing":[...], "layers": {...} },
    "observability": { "metrics":[...], "logs":[...], "tracing":[...] },
    "improvements":[ ... ]
  }

METHODOLOGY (Follow explicitly)
1. Git Data Collection:
  For each branch B:
    a. Diff summary vs baseline:
      git diff --stat 12090646ee83f2368311d595d87ae947e46ddacd..B
    b. Focused provider changes:
      git diff --name-only 12090646ee83f2368311d595d87ae947e46ddacd..B | grep '^providers/' || true
    c. Test additions & changes:
      git diff --name-only 12090646ee83f2368311d595d87ae947e46ddacd..B | grep -E '(^tests/|^simulator_tests/)' || true
    d. Async introduction:
      git diff 12090646ee83f2368311d595d87ae947e46ddacd..B -- 'tools/consensus.py'
    e. Environment variables:
      grep -R --line-number -E 'os\\.getenv|environ\\[|KILO_|OPENROUTER_|KILO_CODE_VERSION|KILO_PREFERRED' .
2. Extract code snippets (≤25 lines each) only when they illustrate a transformation (e.g., key precedence logic, concurrency wrapper).
3. Normalize environment variables: name, purpose, default detection, behavioral effect.
4. Classify risks (Taxonomy: performance, correctness, security, maintainability, observability).
5. Build dependency graph (justify each edge in one short clause).
6. Produce phases: Map each theme to one or more phases; maximize early infrastructure foundation (config validation, alias registry) before feature layering.

HEURISTICS
- Treat branches that overlap (e.g., feature/cli-bridge-provider and fix/registry-overwrite-default) as cumulative; identify conflicting or redundant patterns.
- If two branches modify same file region differently, note reconciliation strategy.
- Collapse trivial doc-only changes unless they define new usage semantics.

CONSTRAINTS
- Do not execute destructive git operations.
- Do not reformat or rewrite code—read-only analysis.
- Prefer precise metrics; if ambiguous, state "estimate" and explain.
- Keep JSON syntactically valid (no trailing commas).

OUTPUT STYLE
- Markdown first (human-readable); JSON block last.
- Use tables sparingly (themes, risks). Wrap long code lines where necessary.
- Keep code snippet fences annotated with language (e.g., ```python).

VALIDATION CHECKLIST (apply before final output)
- All branches referenced at least once
- Every theme has metrics + risks + improvements
- JSON parses (validate mentally)
- Dependencies have no orphan node (except root primitives)
- Phases have increasing numbers and unique objectives

END OF PROMPT
---

**Optional Quick Commands (fish) for the other agent**
```fish
# List branches
git fetch --all --prune
git branch -a

# Single branch diff stat
set BR feature/kilo-api-support
git diff --stat 12090646ee83f2368311d595d87ae947e46ddacd..$BR

# Providers only
git diff --name-only 12090646ee83f2368311d595d87ae947e46ddacd..$BR | grep '^providers/' || true

# Consensus async changes
git diff 12090646ee83f2368311d595d87ae947e46ddacd..feature/consensus-async-refactor-doc -- tools/consensus.py

# Env var scan
grep -R --line-number -E 'KILO_|OPENROUTER_|os\\.getenv' .
```

**If You Want Enhancements to the Prompt**
I can tailor for a specific agent system (e.g., adding tool invocation schema, rate limits, or splitting into stages). Let me know if you’d like a staged version or an immediately executable checklist format.

Would you like a staged (multi-pass) variant or is this sufficient?
<parameter name="filePath">/home/coldaine/Desktop/ZenMcp/staged_refactor_prompt_and_plan.md
