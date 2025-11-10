# Fork Inventory - Local Changes vs Upstream

> Files that are unique to this fork or modified from the upstream zen-mcp-server
>
> **Upstream**: https://github.com/BeehiveInnovations/zen-mcp-server
>
> **Last Updated**: 2025-11-09

## Summary

- **Added Files**: 82 (19 moved to to_be_deprecated)
- **Modified Files**: 13
- **Deleted Files**: 1
- **To Be Deprecated**: 27 (deletion: 2025-12-09)
- **Untracked Files**: 10

---

## Added Files (101)

### GitHub Workflows & CI/CD
- `.github/workflows/codecov.yml`

### Documentation - Root Level
- `DYNAMIC_ROUTING_IMPLEMENTATION.md`
- `DYNAMIC_ROUTING_PROTECTION.md`
- `DYNAMIC_ROUTING_TOOL_INTEGRATION.md`
- `UPSTREAM_UPDATE_ANALYSIS.md`
- `claude_config_with_safety_example.json`
- `codecov.yaml`

### Documentation - Setup & Guides
- `docs/setup-guide.md`
- `docs/codecov-implementation.md`
- `docs/custom-tool-updates.md`

### Documentation - Development/ADRs
- `docs/development/adrs/README.md`
- `docs/development/adrs/centralized-model-registry.md`
- `docs/development/adrs/criticalreview.md`
- `docs/development/adrs/dynamic-model-availability.md`
- `docs/development/adrs/future.md`
- `docs/development/adrs/prepare-pr.md`
- `docs/development/adrs/quickreview.md`
- `docs/development/adrs/review.md`
- `docs/development/adrs/tiered-consensus-implementation.md`
- `docs/development/custom-tools.md`

### Documentation - Models
- `docs/models/README.md`
- `docs/models/automated_evaluation_criteria.py`
- `docs/models/band_assignments_cache.json`
- `docs/models/bands_config.json`
- `docs/models/cost_tier_assignments_cache.json`
- `docs/models/current-models.md`
- `docs/models/model_allocation_config.yaml`
- `docs/models/models.csv`
- `docs/models/models_schema.json`

### Documentation - Planning
- `docs/planning/workflow-command-summary.md`

### Documentation - Promptcraft (MCP Integration)
- `docs/promptcraft/mcp-client-api.md`
- `docs/promptcraft/mcp-integration-guide.md`
- `docs/promptcraft/migration-guide.md`
- `docs/promptcraft/troubleshooting.md`

### Documentation - Custom Tools
- `docs/tools/custom/README.md`
- `docs/tools/custom/dynamic_model_selector.md`
- `docs/tools/custom/model_evaluator.md`
- `docs/tools/custom/pr_prepare.md`
- `docs/tools/custom/pr_review.md`

### To Be Deprecated (scheduled deletion: 2025-12-09)
- `tools/custom/to_be_deprecated/` - 27 files
  - 10 deprecated consensus tools (layered_consensus, smart_consensus variants)
  - 1 deprecated documentation file (layered_consensus.md)
  - 13 archived hub implementation files (archive/hub-implementation-20250825/)
  - 2 configuration backup files (conf_backup_20250821/)
  - 1 README explaining deprecation

### Configuration
- `config/default.yaml`

### Data - Promptcraft System
- `data/promptcraft/channel_config.json`
- `data/promptcraft/experimental_models.json`
- `data/promptcraft/graduation_queue.json`
- `data/promptcraft/performance_metrics.json`

### Scripts
- `enable_dynamic_routing.sh`
- `preserve-dynamic-routing.sh`
- `upgrade-with-routing-protection.sh`
- `evaluate_model.py`
- `validate_codecov.py`

### Plugins
- `plugins/__init__.py`
- `plugins/dynamic_routing_plugin.py`
- `plugins/promptcraft_system/__init__.py`
- `plugins/promptcraft_system/api_server.py`
- `plugins/promptcraft_system/background_workers.py`
- `plugins/promptcraft_system/data_manager.py`

### Routing System
- `routing/__init__.py`
- `routing/complexity_analyzer.py`
- `routing/hooks.py`
- `routing/integration.py`
- `routing/model_level_router.py`
- `routing/model_routing_config.json`
- `routing/model_wrapper.py`
- `routing/monitoring.py`

### System Prompts
- `systemprompts/shared_instructions.py`

### Tests
- `tests/fixtures/routing_test_data.py`
- `tests/test_consensus_models.py`
- `tests/test_pr_review.py`
- `tests/test_promptcraft_core.py`
- `tests/test_promptcraft_integration.py`
- `tests/test_promptcraft_mcp_integration.py`
- `tests/test_promptcraft_pytest.py`
- `tests/test_promptcraft_simple.py`
- `tests/test_routing_integration.py`
- `tests/test_routing_scenarios.py`
- `tests/test_routing_system.py`

### Tools - Custom
- `tools/custom/__init__.py`
- `tools/custom/band_selector.py`
- `tools/custom/consensus_models.py`
- `tools/custom/consensus_roles.py`
- `tools/custom/consensus_synthesis.py`
- `tools/custom/dynamic_model_selector.py`
- `tools/custom/model_evaluator.py`
- `tools/custom/pr_prepare.py`
- `tools/custom/pr_review.py`
- `tools/custom/tiered_consensus.py`
- `tools/custom/promptcraft_mcp_bridge.py`
- `tools/custom/promptcraft_mcp_client/__init__.py`
- `tools/custom/promptcraft_mcp_client/client.py`
- `tools/custom/promptcraft_mcp_client/error_handler.py`
- `tools/custom/promptcraft_mcp_client/models.py`
- `tools/custom/promptcraft_mcp_client/protocol_bridge.py`
- `tools/custom/promptcraft_mcp_client/subprocess_manager.py`
- `tools/routing_status.py`

### Dependencies
- `requirements-hub.txt`

---

## Modified Files (13)

### GitHub Workflows
- `.github/workflows/test.yml`

### Project Documentation
- `CLAUDE.md` - Project-specific development guide

### Scripts
- `code_quality_checks.sh` - Quality validation script
- `communication_simulator_test.py` - End-to-end MCP testing

### Configuration
- `pyproject.toml` - Python project configuration
- `pytest.ini` - Pytest configuration
- `requirements-dev.txt` - Development dependencies
- `requirements.txt` - Production dependencies

### Core Server
- `server.py` - Main MCP server

### System Prompts
- `systemprompts/thinkdeep_prompt.py` - Modified prompt

### Tests
- `simulator_tests/base_test.py`
- `tests/test_conversation_missing_files.py`
- `tests/test_disabled_tools.py`
- `tests/test_file_protection.py`

---

## Deleted Files (1)

- `simulator_tests/test_planner_validation_old.py`

---

## Untracked Files (Not Committed) (10)

### Analysis Documents
- `COMPLETE_TOOL_LLM_MATRIX.md`
- `CUSTOM_TOOLS_ANALYSIS.md`
- `docs/development/custom_tools_analysis.md`
- `docs/development/custom_tools_consolidation_visual.md`


### Temporary Reference Files
- `tmp_cleanup/.tmp-adr-summary-20251109.md`
- `tmp_cleanup/.tmp-comprehensive-status-review-20251109.md`
- `tmp_cleanup/.tmp-consensus-architecture-gap-analysis-20251109.md`
- `tmp_cleanup/.tmp-model-registry-architecture-20251109.md`

---

## Category Breakdown

### 1. Dynamic Routing System (17 files)
Custom intelligent model routing based on task complexity and budget preferences.

**Core Files:**
- `routing/` directory (8 files)
- `plugins/dynamic_routing_plugin.py`
- Related documentation and scripts (8 files)

### 2. Promptcraft System (17 files)
MCP client integration and experimental model management system.

**Core Files:**
- `plugins/promptcraft_system/` (3 files)
- `tools/custom/promptcraft_mcp_client/` (5 files)
- `data/promptcraft/` (4 files)
- Related documentation (5 files)

### 3. Custom Tools (15 active files)
Plugin-style custom MCP tools to avoid merge conflicts.

**Core Files:**
- `tools/custom/` (11 Python files + 4 doc files)
  - **New**: tiered_consensus.py, consensus_models.py, consensus_roles.py, consensus_synthesis.py
  - **New**: band_selector.py, model_evaluator.py, pr_prepare.py, pr_review.py
  - Existing: dynamic_model_selector.py, promptcraft_mcp_bridge.py, routing_status.py

### 4. Model Management (9 files)
Comprehensive model registry and evaluation system.

**Core Files:**
- `docs/models/` directory (9 files)

### 5. Development Documentation (24 files)
ADRs, guides, and development standards.

**Core Files:**
- `docs/development/adrs/` (9 files)
  - **New**: centralized-model-registry.md, dynamic-model-availability.md, tiered-consensus-implementation.md
  - Existing: README.md, criticalreview.md, future.md, prepare-pr.md, quickreview.md, review.md
- Various setup and integration guides

### 6. Testing Infrastructure (15 files)
Enhanced testing with routing, promptcraft, PR review, and consensus tests.

**Core Files:**
- New test files (11 files)
  - **New**: test_consensus_models.py
  - Existing: test_pr_review.py, test_promptcraft_*, test_routing_*
- Modified test files (4 files)

### 7. CI/CD & Quality (5 files)
Codecov integration and enhanced quality checks.

**Core Files:**
- `.github/workflows/codecov.yml`
- `codecov.yaml`
- `validate_codecov.py`
- Modified `code_quality_checks.sh`
- Modified `communication_simulator_test.py`

### 8. To Be Deprecated (27 files - deletion: 2025-12-09)
Deprecated consensus tools, archived hub implementation, and configuration backups.

**Location:** `tools/custom/to_be_deprecated/`

**Core Files:**
- Deprecated consensus tools (10 files)
- Deprecated documentation (1 file: layered_consensus.md)
- Archived hub implementation (13 files: archive/hub-implementation-20250825/)
- Configuration backups (2 files: conf_backup_20250821/)
- Deprecation README (1 file)

---

## Key Differentiators from Upstream

1. **Dynamic Model Routing**: Intelligent model selection based on task complexity
2. **Promptcraft Integration**: MCP client bridge for external model management
3. **Custom Tools Architecture**: Plugin-style tools in `tools/custom/`
4. **Tiered Consensus Tool**: Unified consensus with additive tier architecture (replaces 4 fragmented tools)
5. **Enhanced Model Registry**: Comprehensive model metadata, BandSelector, and automated evaluation
6. **Codecov Integration**: Test coverage tracking and reporting
7. **Extensive Documentation**: ADRs (3 foundational), setup guides, and tool documentation
8. **Advanced Testing**: Routing tests, promptcraft tests, PR review tests, consensus tests

---

## Maintenance Notes

### Files to Keep
- All `tools/custom/` files - Core fork functionality
- All `routing/` files - Dynamic routing system
- All `plugins/` files - Promptcraft and routing plugins
- Documentation in `docs/` - Fork-specific guides
- Modified test files - Enhanced test coverage

### Files to Review
- `tools/custom/to_be_deprecated/` - **DELETE ON 2025-12-09** (27 files scheduled for deletion)
- Untracked analysis documents - Commit or clean up
- `tmp_cleanup/` reference files - Review and archive

### Recent Changes (2025-11-09)
- **Added**: tiered_consensus tool (4 new files) - Unified consensus with additive tier architecture
- **Added**: 3 new ADRs (centralized-model-registry, dynamic-model-availability, tiered-consensus-implementation)
- **Deprecated**: 27 files moved to `tools/custom/to_be_deprecated/` (deletion: 2025-12-09)
  - 10 old consensus tools
  - 1 deprecated documentation
  - 13 archived hub files
  - 2 configuration backups

### Upstream Sync Strategy
When merging upstream updates:
1. Preserve all `tools/custom/` files
2. Preserve all `routing/` files
3. Preserve all `plugins/` files
4. Review changes to `server.py` carefully (modified in fork)
5. Review changes to test infrastructure
6. Update documentation for any upstream changes

---

*Generated: 2025-11-09*
*Last Upstream Sync: v9.1.3 (commit 5c9d232e)*
