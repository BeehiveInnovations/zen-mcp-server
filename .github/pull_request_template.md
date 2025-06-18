## PR Title Format

**Please ensure your PR title follows one of these formats:**

### Version Bumping Prefixes (trigger Docker build + version bump):
- `feat: <description>` - New features (triggers MINOR version bump)
- `fix: <description>` - Bug fixes (triggers PATCH version bump)
- `breaking: <description>` or `BREAKING CHANGE: <description>` - Breaking changes (triggers MAJOR version bump)
- `perf: <description>` - Performance improvements (triggers PATCH version bump)
- `refactor: <description>` - Code refactoring (triggers PATCH version bump)

### Non-Version Prefixes (no version bump):
- `docs: <description>` - Documentation only
- `chore: <description>` - Maintenance tasks
- `test: <description>` - Test additions/changes
- `ci: <description>` - CI/CD changes
- `style: <description>` - Code style changes

### Docker Build Options:
- `docker: <description>` - Force Docker build without version bump
- `docs+docker: <description>` - Documentation + Docker build
- `chore+docker: <description>` - Maintenance + Docker build
- `test+docker: <description>` - Tests + Docker build
- `ci+docker: <description>` - CI changes + Docker build
- `style+docker: <description>` - Style changes + Docker build

## Description

Please provide a clear and concise description of what this PR does.

## Changes Made

- [ ] List the specific changes made
- [ ] Include any breaking changes
- [ ] Note any dependencies added/removed

## Testing

**Please review our [Testing Guide](../docs/testing.md) before submitting.**

### Run all linting and tests (required):
```bash
# Activate virtual environment first
source venv/bin/activate

# Run comprehensive code quality checks (recommended)
./code_quality_checks.sh

# If you made tool changes, also run simulator tests
python communication_simulator_test.py
```

- [ ] All linting passes (ruff, black, isort)
- [ ] All unit tests pass
- [ ] **For new features**: Unit tests added in `tests/`
- [ ] **For tool changes**: Simulator tests added in `simulator_tests/`
- [ ] **For bug fixes**: Tests added to prevent regression
- [ ] Simulator tests pass (if applicable)
- [ ] Manual testing completed with realistic scenarios

## Related Issues

Fixes #(issue number)

## Checklist

- [ ] PR title follows the format guidelines above
- [ ] **Activated venv and ran code quality checks: `source venv/bin/activate && ./code_quality_checks.sh`**
- [ ] Self-review completed
- [ ] **Tests added for ALL changes** (see Testing section above)
- [ ] Documentation updated as needed
- [ ] All unit tests passing
- [ ] Relevant simulator tests passing (if tool changes)
- [ ] Ready for review

## Additional Notes

Any additional information that reviewers should know.