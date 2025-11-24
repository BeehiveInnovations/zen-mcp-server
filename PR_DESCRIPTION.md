# PR: Stabilize Test Suite & Fix Provider Registry Architecture

## Summary
This PR addresses critical instability in the test suite, specifically fixing `test_large_prompt_handling.py` and resolving architectural issues in `ModelProviderRegistry` and `GeminiModelProvider`. It introduces a robust `FakeModelProvider` for testing and establishes infrastructure for live model testing.

## Changes

### 🏗️ Architecture & Providers
- **`providers/registry.py`**: Fixed Singleton pattern implementation to correctly initialize `_providers` and `_initialized_providers` with proper type hints. Removed dead code.
- **`providers/gemini.py`**: Added `generate_stream` stub (required by ABC), fixed type safety issues with `google-genai` library, and improved error handling.
- **`providers/openai_compatible.py`**: Cleaned up initialization logic.

### 🧪 Testing Infrastructure
- **`tests/fake_provider.py`**: Created a fully ABC-compliant `FakeModelProvider` to replace brittle mocks.
- **`tests/conftest.py`**:
    - Added `reset_registry` fixture to ensure test isolation.
    - Added `fake_provider` fixture.
    - Added `live_client` fixture for secure live API testing.
    - Improved `mock_provider_availability` to respect `no_mock_provider` markers.
- **`tests/mock_helpers.py`**: Enhanced `create_mock_provider` to return more complete mock objects.
- **`tests/live/`**: Added directory for live model tests (opt-in via `LIVE_MODEL_TESTS=1`).

### 🐛 Bug Fixes
- **`test_large_prompt_handling.py`**: Refactored to mock `utils.model_context.ModelContext` instead of the deprecated `get_model_provider` pattern. This aligns tests with the new `SimpleTool` architecture.
- **Static Analysis**: Fixed unbound variables and type errors across multiple files.

### 📝 Documentation
- **`docs/dev/test/remediation_plan.md`**: Added a comprehensive plan for future test suite improvements.

## Verification
- **Unit Tests**: `python -m pytest tests/test_large_prompt_handling.py` passes (12/12).
- **Linting**: Static analysis checks pass for modified files.
- **Manual Check**: Verified `ModelProviderRegistry` no longer throws `AttributeError` on singleton access.

## Next Steps
- Continue migration of other test files to use `FakeModelProvider`.
- Execute the remediation plan outlined in `docs/dev/test/remediation_plan.md`.
