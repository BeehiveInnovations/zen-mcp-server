# Test Suite Review (Per Suite Grades, A–F)

Context: Reviewed suites for behavioral intent vs. actual verification, brittleness, and coverage. Grades reflect how well each file asserts meaningful behavior (not just equivalence), resilience to provider/environment drift, and alignment with pytest fixtures.

- tests/test_alias_target_restrictions.py — C: good intent around alias/target parity, but uses concrete providers with missing abstract methods, so it fails before validating behavior; needs provider doubles or registry fakes.
- tests/test_auto_mode.py — C+: broad env-driven scenarios, but assertions hinge on registry side effects and allow silent passes when providers are mocked; lacks negative paths for malformed schemas.
- tests/test_auto_mode_comprehensive.py — B-: solid matrix coverage of providers/models, yet coupling to env + real providers makes it brittle; minimal assertion of error messaging semantics.
- tests/test_auto_mode_custom_provider_only.py — B: focused regression checks with explicit fixtures; still leans on dummy keys instead of contract doubles.
- tests/test_auto_mode_provider_selection.py — B-: selection logic covered, but relies on indirect mocks and omits explicit cost/priority assertions.
- tests/test_auto_model_planner_fix.py — B-: exercises planner/model resolution; could assert concrete payloads rather than lenient substring checks.
- tests/test_buggy_behavior_prevention.py — B: regression coverage for alias/target bugs; still tied to provider instantiation that now fails.
- tests/test_challenge.py — B: clear schema/exec checks; mostly behavior-focused.
- tests/test_chat_simple.py — C: schema assertions are strong, but model availability checks rely on abstract providers and pass/fail due to instantiation errors.
- tests/test_collaboration.py — C+: intent is good (parsing clarification flows) but assertions are loose string contains; misses structured validation of model outputs/errors.
- tests/test_config.py — D: only constant equality checks; no behavioral validation or env interplay.
- tests/test_consensus.py — B: decent workflow coverage; some schema assertions could move to property-based to avoid fixture fragility.
- tests/test_conversation_field_mapping.py — C: relies on default mappings; lacks failure-mode checks and round-trip validation.
- tests/test_conversation_file_features.py — C: covers happy paths; missing error detail assertions and large-file/resource pressure cases.
- tests/test_conversation_memory.py — B-: exercises flows, but dynamic turn limits not validated against actual truncation effects.
- tests/test_conversation_missing_files.py — B-: targeted scenarios; could assert emitted warnings/messages instead of just returns.
- tests/test_custom_provider.py — B: good initialization/multi-provider coverage; still depends on concrete provider ctor behavior.
- tests/test_debug.py — C+: schema coverage OK, but provider usage tied to abstract implementations; limited negative cases.
- tests/test_deploy_scripts.py — C: mostly smoke checks; lacks idempotency/permissions assertions.
- tests/test_dial_provider.py — C+: basic provider wiring; no transport-level validation.
- tests/test_disabled_tools.py — B: clear feature-flag behavior; could add conflict detection cases.
- tests/test_directory_expansion_tracking.py — B-: path tracking checks OK; lacks concurrency/permission edge cases.
- tests/test_docker_claude_desktop_integration.py — B-: integration-oriented but light on assertion depth; depends on external layout.
- tests/test_docker_config_complete.py — B: decent config assembly checks; could validate error paths.
- tests/test_docker_healthcheck.py — B-: smoke healthcheck; minimal failure validation.
- tests/test_docker_implementation.py — B-: basic orchestration assertions; missing lifecycle teardown checks.
- tests/test_docker_mcp_validation.py — B-: validates schema; limited negative validation.
- tests/test_docker_security.py — B-: covers denylist; lacks exploit/escape-path simulations.
- tests/test_docker_volume_persistence.py — B: persistence intent good; missing corruption/partial-write cases.
- tests/test_file_protection.py — B-: guards for file IO; could enforce permissions and symlink traps.
- tests/test_gemini_token_usage.py — C-: intends to validate token accounting, but instantiation fails; needs contract double and property-based ranges.
- tests/test_image_support_integration.py — C: integration intent, but assertions shallow and depend on providers supporting images.
- tests/test_image_validation.py — C: exercises data URLs/files, yet repeats logical equivalence; errors currently stem from provider base. Needs boundary fuzzing and mimetype contract tests.
- tests/test_integration_utf8.py — B: good UTF-8 round trips; could add failure encodings.
- tests/test_intelligent_fallback.py — B-: selection/fallback logic covered; should assert metrics and cost ordering.
- tests/test_large_prompt_handling.py — B: covers truncation; could check token counts vs. limits rather than length heuristics.
- tests/test_line_numbers_integration.py — B-: verifies mapping; add malformed file scenarios.
- tests/test_listmodels.py — B: behaviorally focused; could assert ordering and dedup semantics.
- tests/test_listmodels_restrictions.py — B-: restriction behavior covered; still relies on live provider definitions.
- tests/test_model_enumeration.py — B-: enumerations validated; gaps around alias dedup.
- tests/test_model_metadata_continuation.py — B-: continuation logic covered; needs corrupted metadata cases.
- tests/test_model_resolution_bug.py — B-: regression focused; could assert structured error payloads.
- tests/test_model_restrictions.py — C+: good restriction coverage, but instantiation brittleness and missing denial-of-service style cases.
- tests/test_openai_compatible_token_usage.py — B-: token math checks; could use property-based spans.
- tests/test_openai_provider.py — B-: good capability coverage, but network-less env causes brittle mocks.
- tests/test_openrouter_provider.py — B-: covers routing; lacks quota/error-path assertions.
- tests/test_openrouter_registry.py — B-: registry behaviors OK; missing conflict resolution cases.
- tests/test_o3_pro_output_text_fix.py — B: regression-focused; assertions targeted.
- tests/test_o3_temperature_fix_simple.py — B-: validates temperature clamp; could add fuzzing.
- tests/test_old_behavior_simulation.py — B-: regression guardrails; could assert detailed logs.
- tests/test_parse_model_option.py — B-: option parsing covered; add invalid flag fuzzing.
- tests/test_per_tool_model_defaults.py — B: per-tool defaults meaningful; could validate persisted state.
- tests/test_pii_sanitizer.py — B-: sanitization paths covered; lacks structured PII fixture matrix.
- tests/test_pip_detection_fix.py — B-: regression targeted; add multi-platform cases.
- tests/test_planner.py — B-: planner logic covered; heavy mocking hides real orchestration.
- tests/test_precommit_workflow.py — B: workflow smoke tests; could assert failure messaging.
- tests/test_prompt_regression.py — B-: regression coverage; limited negative prompt validation.
- tests/test_prompt_size_limit_bug_fix.py — B: exercises limit enforcement; could add random-sized payloads.
- tests/test_providers.py — C-: instantiation currently fails; needs provider doubles and streaming contract checks.
- tests/test_provider_routing_bugs.py — B-: routing edge cases; should add concurrent routing cases.
- tests/test_provider_utf8.py — B-: UTF-8 focus; missing invalid byte sequences.
- tests/test_rate_limit_patterns.py — B-: retry logic covered; needs jitter/backoff property checks.
- tests/test_refactor.py — C+: minimal structural assertions; unclear behavior expectations.
- tests/test_registry_behavior.py — C: registry scenarios, but depends on concrete providers causing TypeErrors.
- tests/test_secaudit.py — B-: basic audit checks; add negative/false-positive cases.
- tests/test_server.py — B-: server smoke tests; lacks malformed request tests.
- tests/test_supported_models_aliases.py — C-: alias checks but fail due to abstract methods; needs fake provider or fixtures.
- tests/test_thinking_modes.py — C+: budget mapping intent good; provider instantiation fragile and lacks boundary fuzz.
- tests/test_tools.py — B: tool metadata/execute paths covered; could separate slow paths.
- tests/test_tracer.py — B-: tracer behavior OK; no failure-mode assertions.
- tests/test_utils.py — B: utility coverage decent; could use property-based tests.
- tests/test_utf8_localization.py — B-: localization checks; needs invalid locale cases.
- tests/test_uvx_resource_packaging.py — B-: packaging flow covered; add checksum validation.
- tests/test_uvx_support.py — B-: support detection OK; limited platform matrix.
- tests/test_workflow_file_embedding.py — B: embedding planning checks; needs invalid file path coverage.
- tests/test_workflow_metadata.py — B-: metadata flow covered; missing tampering cases.
- tests/test_workflow_prompt_size_validation_simple.py — B-: validates prompt sizes; could fuzz tokenization.
- tests/test_workflow_utf8.py — B-: UTF-8 workflow; missing error-path assertions.
- tests/test_xai_provider.py — B-: provider coverage OK; relies on dummy keys rather than contract doubles.
- tests/test_registry_contracts_strict.py — A-: new contract tests using concrete doubles, minimal mocking, and explicit restriction behavior.

Helpers/infra:
- tests/conftest.py — C+: useful defaults, but forces real provider classes that now violate ABCs; could provide provider doubles.
- tests/mock_helpers.py, transport_helpers.py — B-: helpful scaffolding; could encode stricter types.
- tests/sanitize_cassettes.py, tests/pii_sanitizer.py — B-: utility scripts; minimal assertions.

Key patterns found:
- Multiple suites instantiate concrete providers lacking `generate_stream`, causing TypeError before assertions (alias, supported_models_aliases, providers, thinking_modes, gemini_token_usage).
- Several suites assert constant equality or existence (config, refactor) without behavioral validation.
- Auto-mode suites rely on environment mutation and implicit conftest mocking; missing explicit contract checks for schemas/errors.
- Restriction/alias suites depend on live provider maps; lack provider doubles to isolate registry logic.

Codebase/doc consistency:
- Tests assume providers fully implement ModelProvider ABC, but Gemini/Mock providers do not implement `generate_stream`; docs and fixtures do not mention this gap.
- conftest registers real providers and forces DEFAULT_MODEL to gemini-2.5-flash, which contradicts docs that expect auto-mode requirements; this masks missing model validation in many suites.
- Image validation tests rely on provider-independent helpers, but production code ties validation to ModelProvider.validate_image; docs do not cover the required data URL/size limits exercised in tests.

New tests added:
- tests/test_registry_contracts_strict.py introduces a concrete FakeProvider implementing full ABC surface to validate registry alias resolution and restriction filtering without brittle real-provider dependencies.

Recommended heavier tooling (not implemented):
- Mutation testing (mutmut or cosmic-ray) on registry/restriction logic to ensure alias/target checks actually fail when broken.
- Property-based testing (hypothesis) for schema generation (tool schemas, model field enums), temperature constraints, and image validation boundaries.
- Contract tests with VCR/pytest-recording for provider adapters to lock HTTP request/response shapes without real keys.
- Coverage gates per package (`pytest --cov=... --cov-fail-under=<target>`), especially providers/ and tools/ to highlight shallow suites.
- Static analysis checks for ABC compliance (e.g., mypy/ruff rule) to catch missing abstract implementations like `generate_stream`.

Priority improvements (tests to replace/augment weak ones):
- Replace alias/provider suites (alias_target_restrictions, supported_models_aliases, providers, thinking_modes, gemini_token_usage) with provider doubles that fully satisfy the ABC while asserting alias/target and restriction interactions.
- Expand config tests to cover env precedence, auto-mode toggling, and failure-on-missing-default cases instead of constant equality.
- Strengthen collaboration/conversation suites with structured assertions (pydantic/model validation) rather than string contains.
- Rework image validation to assert precise error types per input variant and fuzz size/mimetype bounds.
