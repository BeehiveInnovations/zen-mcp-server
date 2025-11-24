# Test Suite Remediation Plan

## Executive Summary

This plan addresses critical issues in the zen-mcp-server test suite identified in the comprehensive review. The primary focus is on replacing brittle provider dependencies with proper test doubles, strengthening assertions, and establishing measurable metrics for progress tracking.

**Current State Baselines:**
- Total tests: ~100 (estimated from file count)
- Failing tests: ~20-30 (from review analysis)
- Coverage: ~70% (estimated)
- Critical issue: Multiple tests fail due to missing `generate_stream` implementation in concrete providers

**Target State (6 weeks):**
- Failures: ≤3 (90% reduction)
- Coverage: 85% overall, 90% for critical packages (providers/, tools/)
- All tests using provider doubles instead of brittle concrete implementations
- Structured assertions replacing loose string contains checks

## Phase 1: Infrastructure Foundation (Week 1)

### 1.1 Create Comprehensive FakeModelProvider

**Objective:** Replace brittle concrete provider dependencies with a fully compliant test double.

**Implementation Steps:**
1. Create `tests/fake_provider.py` with `FakeModelProvider` class
2. Implement all abstract methods from `ModelProvider` ABC
3. Add configurable model capabilities and alias support
4. Include streaming support and token counting
5. Add temperature constraint validation

**Success Criteria:**
- `FakeModelProvider` passes `mypy --strict` ABC compliance checks
- All existing provider tests run without TypeError when using `FakeModelProvider`
- Provider can be configured for different test scenarios (streaming, images, etc.)

### 1.2 Update conftest.py with Provider Double Support

**Implementation Steps:**
1. Add `fake_provider` fixture that returns configured `FakeModelProvider`
2. Update `mock_provider_availability` fixture to use fake providers
3. Add guard rails to prevent concrete provider instantiation in tests
4. Implement provider registry isolation for each test

**Success Criteria:**
- Tests can opt-in to fake providers via fixture
- No test can accidentally instantiate concrete providers missing `generate_stream`
- Registry state is properly isolated between tests

### 1.3 Establish Baseline Metrics

**Commands to Capture Current State:**
```bash
# Count total tests
python -m pytest tests/ --collect-only | wc -l

# Count failing tests
python -m pytest tests/ -v --tb=no | grep FAIL | wc -l

# Get coverage report
python -m pytest tests/ --cov-report=term-missing --cov=providers --cov=tools

# Per-package coverage
python -m pytest tests/ --cov=providers --cov-report=term-missing
python -m pytest tests/ --cov=tools --cov-report=term-missing
```

**Success Criteria:**
- Baseline metrics documented and stored
- Automated metric collection in CI pipeline
- Progress tracking dashboard established

### 1.4 Live Test Infrastructure

**Objective:** Establish infrastructure for safe, opt-in live model testing against real providers.

**Implementation Steps:**
1. Add `live_model` marker to pytest.ini for proper test categorization
2. Create `tests/live/` directory structure with `__init__.py`
3. Implement `live_client` fixture in `conftest.py` for secure API key retrieval
4. Add environment variable gate (`LIVE_MODEL_TESTS=1`) to prevent accidental execution
5. Create pytest configuration to exclude live tests from default runs

**Success Criteria:**
- Live tests are excluded by default and only run with explicit opt-in
- API keys are securely retrieved with proper skipping when missing
- `pytest tests/live/ --collect-only` shows 0 tests initially
- CI pipeline configuration prevents accidental live test execution

## Phase 2: Critical Test File Remediation (Weeks 2-3)

### 2.1 High-Priority Provider Tests

**Files Requiring Immediate Attention:**

| Test File | Current Issue | Success Criteria |
|-----------|---------------|-----------------|
| `test_alias_target_restrictions.py` | TypeError from missing `generate_stream` | Runs with `pytest -k test_alias_target_restrictions`, validates alias/target parity with structured assertions |
| `test_providers.py` | Concrete provider instantiation failures | All provider tests pass using `FakeModelProvider`, validates streaming contract |
| `test_gemini_token_usage.py` | Provider instantiation before token validation | Validates token extraction with property-based test cases |
| `test_supported_models_aliases.py` | Missing abstract method implementations | Alias resolution tested with fake provider, validates both directions |
| `test_thinking_modes.py` | Provider dependency failures | Thinking mode validation uses fake provider with configurable capabilities |

**Remediation Steps per File:**
1. Replace concrete provider imports with `FakeModelProvider`
2. Update fixtures to use provider doubles
3. Replace string contains assertions with structured validation
4. Add negative test cases for error conditions
5. Validate against ABC contract requirements

### 2.2 Configuration and Registry Tests

**Files to Strengthen:**

| Test File | Current Issue | Success Criteria |
|-----------|---------------|-----------------|
| `test_config.py` | Only constant equality checks | Tests env precedence, auto-mode toggling, failure-on-missing-default |
| `test_registry_behavior.py` | Concrete provider dependencies | Registry logic tested with isolation, validates multi-provider scenarios |
| `test_collaboration.py` | Loose string assertions | Structured JSON validation for clarification requests and responses |

**Enhancement Steps:**
1. Add environment mutation testing for config
2. Test registry state isolation and cleanup
3. Replace string contains with pydantic model validation
4. Add error path testing and boundary conditions

### 2.3 Auto Mode Test Suite

**Files to Improve:**

| Test File | Current Issue | Success Criteria |
|-----------|---------------|-----------------|
| `test_auto_mode.py` | Silent passes with mocked providers | Explicit schema validation, error messaging assertions |
| `test_auto_mode_comprehensive.py` | Brittle environment coupling | Provider-independent validation matrix |
| `test_auto_mode_provider_selection.py` | Indirect assertions | Concrete cost/priority validation metrics |

**Remediation Approach:**
1. Isolate auto mode logic from provider dependencies
2. Add structured schema validation for model selection
3. Test cost ordering and priority algorithms explicitly
4. Validate error conditions and fallback behavior

## Phase 2b: Live Model Integration (Parallel Track)

**Objective:** Leverage z.ai subscription for high-fidelity integration testing against real providers.

**Target Test Suites:**
| Test File | Scope | Success Criteria |
|-----------|-------|------------------|
| `tests/live/test_provider_connectivity.py` | Basic Auth/Gen | Successful "Hello World" from z.ai, OpenAI, Anthropic |
| `tests/live/test_streaming_real.py` | Network Streaming | Validates real chunk handling and timing |
| `tests/live/test_tool_roundtrip.py` | Orchestration | Model correctly calls a local tool and interprets result |
| `tests/live/test_registry_live.py` | Model Discovery | Verify `list_models` returns expected models from remote API |
| `tests/live/test_z_ai_live.py` | Provider-Specific | Basic generation, streaming, and error handling against z.ai |

**Implementation Steps:**
1. Create `tests/live/` directory structure with test files
2. Implement `@pytest.mark.live_model` decorator for all live tests
3. Add `live_client` fixture for z.ai authentication with API key handling
4. Create retry decorators for handling network flakiness
5. Implement structured assertions for real API responses
6. Add token usage validation to ensure actual API consumption

**Success Criteria:**
- All live tests pass with real z.ai API calls
- Tests validate actual token usage (>0 tokens consumed)
- Proper error handling for API failures and rate limits
- Tests complete within 5 minutes to control costs
- 100% pass rate for live test suite

## Phase 3: Assertion Strengthening (Week 4)

### 3.1 Replace String Contains with Structured Validation

**Target Files:**
- `test_collaboration.py`
- `test_conversation_*.py` files
- `test_debug.py`
- `test_analyze.py` (if exists)

**Implementation Steps:**
1. Identify all `assert "substring" in response` patterns
2. Create pydantic models for expected response structures
3. Replace with `assert response.model_validate()` patterns
4. Add field-level validation for critical attributes

### 3.2 Add Negative Test Coverage

**Focus Areas:**
- Malformed JSON parsing in collaboration tests
- Invalid image data and size limits
- Permission denied scenarios
- Network timeout and error conditions
- Invalid model names and configurations

**Success Criteria:**
- Each happy path has corresponding error path test
- Error types are validated (not just presence of error)
- Boundary conditions are explicitly tested

## Phase 4: Coverage and Quality Gates (Week 5)

### 4.1 Coverage Targets by Package

| Package | Current Coverage | Target Coverage | Focus Areas |
|---------|------------------|-----------------|-------------|
| `providers/` | ~60% | 85% | Abstract methods, error paths, streaming |
| `tools/` | ~75% | 90% | Request validation, error handling |
| `utils/` | ~70% | 85% | Model restrictions, file handling |
| Overall | ~70% | 85% | Critical paths integration |

**Implementation Steps:**
1. Add `--cov-fail-under` gates to pytest configuration
2. Create per-package coverage reporting
3. Add coverage for missing branches and edge cases
4. Implement coverage tracking in CI pipeline

### 4.2 Property-Based Testing Introduction

**Target Areas for Hypothesis:**
- Model schema generation and validation
- Temperature constraint boundaries
- Image size and format validation
- Token counting accuracy
- Alias resolution edge cases

**Implementation Steps:**
1. Install `hypothesis[pytest]` dependency
2. Create strategy definitions for test data generation
3. Replace static test cases with property-based tests
4. Add shrinking and failure reproduction documentation

## Phase 5: Advanced Tooling (Week 6)

### 5.1 Mutation Testing Setup

**Tools:**
- Install `cosmic-ray` for mutation testing
- Configure mutation testing for critical packages
- Set up mutation score thresholds (70% kill rate minimum)

**Target Modules:**
- `providers/registry.py`
- `utils/model_restrictions.py`
- `providers/base.py` (contract validation)

### 5.2 Contract Testing with VCR

**Implementation Steps:**
1. Set up `pytest-recording` for HTTP contract tests
2. Record provider API interactions once
3. Validate request/response shapes without live calls
4. Add contract regression detection

### 5.3 Static Analysis Enhancements

**Add to CI Pipeline:**
```bash
# ABC compliance check
mypy --strict providers/base.py

# Abstract method implementation verification
ruff check --select=B024 providers/

# Import organization and type checking
black --check tests/
isort --check-only tests/
```

## Risk Mitigation Strategies

### 6.1 Preventing Regression

**Automated Guards:**
1. **ABC Compliance Gate**: `mypy --strict` check in CI prevents missing abstract methods
2. **Provider Double Enforcement**: Linter rule prevents concrete provider imports in tests
3. **Registry Isolation**: Fixture validation ensures registry cleanup after each test
4. **Coverage Gates**: Per-package minimum coverage prevents silent coverage loss

### 6.2 Migration Safety

**Rollout Sequence:**
1. Add `FakeModelProvider` alongside existing tests (no breaking changes)
2. Migrate tests one file at a time with before/after validation
3. Remove concrete provider dependencies only after migration verified
4. Add deprecation warnings for any remaining brittle patterns

### 6.3 Cost Control for Live Tests

**Financial Safety Measures:**
1. **Environment Gating**: Live tests only run with `LIVE_MODEL_TESTS=1` environment variable
2. **CI Exclusion**: Live tests excluded from default CI pipelines
3. **Test Limits**: Each live test has maximum token/usage limits
4. **Monitoring**: Token usage tracked and reported for each test run
5. **Opt-in Only**: Manual execution required for live test validation

### 6.4 Documentation Updates

**Required Updates:**
1. `AGENTS.md`: Add testing guidelines for provider doubles and live tests
2. `pytest.ini`: Add custom markers for provider double and live model tests
3. `PR_SUMMARY.md`: Include test remediation checklist with live test notes
4. `docs/dev/test/`: Add provider double usage examples and live test guide

## Governance Integration

### 7.1 Alignment with AGENTS.md

**Updates Required:**
1. Add provider double requirement to testing guidelines
2. Specify ABC compliance checks in build commands
3. Document coverage gates per package
4. Add mutation testing to CI requirements

### 7.2 Pytest Configuration Enhancements

**Add to `pytest.ini`:**
```ini
[pytest]
markers =
    provider_double: Tests using FakeModelProvider instead of concrete providers
    contract_test: Tests validating provider contracts
    mutation_test: Tests designed for mutation testing
    property_based: Tests using hypothesis for property-based testing
    live_model: Tests making real API calls to providers (requires LIVE_MODEL_TESTS=1)
```

### 7.3 CI Pipeline Integration

**New Checks:**
1. ABC compliance validation
2. Coverage gates per package
3. Mutation testing score thresholds
4. Provider double enforcement
5. Static analysis for test patterns

## Success Metrics and Owners

### 8.1 Quantitative Metrics

| Metric | Baseline | Target | Owner |
|--------|----------|--------|-------|
| Failing tests | 25 | ≤3 | Code mode (Phase 2) |
| Overall coverage | 70% | 85% | Code mode (Phase 4) |
| Provider coverage | 60% | 85% | Code mode (Phase 4) |
| Tools coverage | 75% | 90% | Code mode (Phase 4) |
| Mutation score | 0% | 70% | Code mode (Phase 5) |
| ABC violations | Unknown | 0 | Code mode (Phase 1) |
| Live test pass rate | 0% | 100% | Code mode (Phase 2b) |
| Live test count | 0 | 10 | Code mode (Phase 2b) |

### 8.2 Qualitative Metrics

**Success Indicators:**
- No tests depend on concrete provider implementations
- All assertions use structured validation
- Error conditions are explicitly tested
- Test suite runs in isolation without external dependencies
- Documentation clearly explains testing patterns

## Implementation Timeline

### Week 1: Infrastructure
- Create `FakeModelProvider` with full ABC compliance
- Update `conftest.py` with provider double support
- Establish baseline metrics and CI gates
- Add live test infrastructure (Phase 1.4)

### Week 2-3: Critical Remediation
- Migrate high-priority provider tests to use doubles
- Strengthen configuration and registry tests
- Improve auto mode test suite
- Begin Phase 2b: Live Model Integration (parallel track)

### Week 4: Assertion Enhancement
- Replace string contains with structured validation
- Add comprehensive negative test coverage
- Implement error path testing
- Complete Phase 2b: Live Model Integration

### Week 5: Coverage and Quality
- Implement coverage gates per package
- Add property-based testing for critical areas
- Strengthen test isolation and cleanup
- Validate live test suite execution and metrics

### Week 6: Advanced Tooling
- Deploy mutation testing pipeline
- Add contract testing with VCR
- Implement enhanced static analysis
- Document live test execution procedures

## Conclusion

This remediation plan addresses the critical issues identified in the test suite review while establishing a foundation for long-term test quality. The phased approach ensures incremental progress with measurable outcomes at each stage.

The key success factors are:
1. **Complete ABC compliance** through provider doubles
2. **Structured assertions** replacing loose string checks
3. **Measurable metrics** with clear baselines and targets
4. **Automated guards** preventing regression
5. **Governance integration** with existing development practices

By following this plan, the test suite will become more reliable, maintainable, and effective at preventing regressions while providing clear confidence in code changes.