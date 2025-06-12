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

- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Manual testing completed
- [ ] Documentation updated (if needed)

## Related Issues

Fixes #(issue number)

## Checklist

- [ ] PR title follows the format guidelines above
- [ ] Code follows the project's style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated as needed
- [ ] Documentation updated as needed
- [ ] All tests passing
- [ ] Ready for review

## Additional Notes

Any additional information that reviewers should know.