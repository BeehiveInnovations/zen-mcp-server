# System Patterns *Optional*

This file documents recurring patterns and standards used in the project.
It is optional, but recommended to be updated as the project evolves.
2025-01-11 22:47:00 - Log of updates made.

*

## Coding Patterns

- **MCP Tool Structure**: Individual tools in `tools/` directory inherit from BaseTool
- **Configuration Management**: Centralized config.py with environment variable handling
- **Utility Organization**: Shared utilities in `utils/` for file operations, git, tokens
- **Testing Strategy**: Comprehensive test suite with both unit tests and live integration tests
- **Dependency Management**: Poetry with pyproject.toml as single source of truth
- **Code Quality**: Black for formatting, Ruff for linting, pre-commit hooks integration

## Architectural Patterns

- **Docker Compose Orchestration**: Multi-service setup with Redis for conversation memory
- **Memory Management**: Dual approach - file-based Memory Bank + Memory MCP entities
- **Documentation-Driven Development**: All code changes require corresponding documentation
- **Collaboration Framework**: Structured Claude-Gemini interaction patterns with tool selection matrix
- **CI/CD Pipeline**: GitHub Actions with automated Docker build and GHCR publishing
- **Branching Strategy**: Simplified GitFlow - feature/* → main via Pull Requests

## Testing Patterns

- **Separation of Concerns**: Unit tests (no API key) vs live integration tests (API key required)
- **Mocking Strategy**: Mock external API calls in unit tests to avoid rate limits
- **Quality Gates**: Pre-commit validation with multiple tools (codereview, precommit, etc.)
- **Environment Isolation**: Docker-based testing to ensure consistent environments

---
2025-01-11 22:47:00 - Initial creation with observed patterns from codebase analysis