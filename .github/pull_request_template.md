<!--
Thank you for your contribution to the Gemini MCP Server! 
Please provide a clear description of your changes and ensure all requirements are met.
-->

## Related Issue

<!-- Link to the issue that this PR addresses -->
<!-- e.g., "Closes #123" or "Fixes #456" -->
<!-- If no issue exists, please consider creating one first to discuss the change -->

Closes #

## Type of Change

<!--
Please check the relevant box with [x]
-->

- [ ] 🐞 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 🛠️ New Gemini tool (adds a new tool like `chat`, `codereview`, etc.)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📖 Documentation update
- [ ] 🧹 Refactor or chore (no user-facing changes)
- [ ] 🏗️ Infrastructure/CI changes

## Description

<!--
A clear and concise description of the changes.
- **What** is the change?
- **Why** is this change necessary?
- **How** does it address the issue?
-->

## Testing

<!--
The project has high testing standards. Please describe the tests you have added or updated.
Both unit tests (no API key) and live integration tests (with API key) are important.
-->

### Unit Tests (Required)
- [ ] I have added new unit tests to cover my changes
- [ ] I have run `python -m pytest tests/ --ignore=tests/test_live_integration.py -v` and all tests pass
- [ ] New tests use proper mocking and don't require API keys

### Live Integration Tests (Recommended)
- [ ] I have tested this with a real Gemini API key using `python tests/test_live_integration.py`
- [ ] The changes work as expected with actual API calls
- [ ] I have tested this on [macOS/Linux/Windows (WSL2)]

### Docker Testing (If Applicable)
- [ ] I have tested the Docker build: `docker build -t test-image .`
- [ ] I have tested the Docker functionality: `./setup-docker.sh`
- [ ] Docker integration works with the changes

## Code Quality

<!--
Please confirm you've followed the project's quality standards
-->

- [ ] My code follows the project's style guidelines (`black .` and `ruff check .`)
- [ ] I have run the linting tools and fixed any issues
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings
- [ ] I have updated type hints where applicable

## Documentation

<!--
Documentation should be updated to reflect any user-facing changes
-->

- [ ] I have made corresponding changes to the documentation
- [ ] I have updated the README.md if my changes affect usage
- [ ] I have updated CONTRIBUTING.md if my changes affect the development workflow
- [ ] For new tools: I have added usage examples and parameter documentation

## Breaking Changes

<!--
If this is a breaking change, please describe what breaks and how users should adapt
-->

- [ ] This change is backwards compatible
- [ ] OR: I have documented the breaking changes and migration path below

<!--
If breaking changes, describe them here:
-->

## Additional Context

<!--
Add any other context about the pull request here, such as:
- Performance implications
- Security considerations
- Future improvements this enables
- Screenshots (for UI changes)
- Related PRs or issues
-->

## Checklist for Maintainers

<!--
This section is for maintainers to check during review
-->

- [ ] Code review completed
- [ ] All CI checks passing
- [ ] Breaking changes properly documented
- [ ] Version bump needed (if applicable)
- [ ] Documentation updated and accurate