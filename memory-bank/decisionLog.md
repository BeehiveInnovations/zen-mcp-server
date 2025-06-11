# Decision Log

This file records architectural and implementation decisions using a list format.
2025-01-11 22:47:00 - Log of updates made.

*

## Decision

**Documentation Structure**: Follow CLAUDE.md specified directory structure exactly
**Rationale**: User emphasized importance of following CLAUDE.md structure rather than creating custom organization
**Implementation Details**: Created docs/{user-guides,contributing,architecture,api} structure with specified files

**Docker Documentation Approach**: Emphasize automated Redis setup rather than manual configuration
**Rationale**: Analysis revealed Redis is fully automated through docker-compose.yml, previous docs were incorrect
**Implementation Details**: Rewrote installation guide to highlight "Everything is handled automatically - no manual Redis setup required!"

**Memory Bank Integration**: Implement file-based Memory Bank alongside Memory MCP server
**Rationale**: Dual-system approach for maximum context preservation and cross-session continuity
**Implementation Details**: Created initialization protocols, update triggers, and UMB command for comprehensive memory management

**GitHub Templates Strategy**: Create comprehensive templates matching CONTRIBUTING.md patterns
**Rationale**: Professional repository needs structured issue/PR workflows for contributors
**Implementation Details**: 4 YAML issue templates + markdown PR template with validation requirements

**GitHub Workflow Decision**: Create automated Docker build and push workflow
**Rationale**: Automate CI/CD pipeline for consistent Docker image deployment to GHCR
**Implementation Details**: .github/workflows/build_and_publish_docker.yml with push trigger on main branch, GHCR authentication using secrets.GITHUB_TOKEN, dual tagging (latest + commit SHA)

**Dependencies Management**: Use Poetry for Python dependency management
**Rationale**: Deterministic builds with poetry.lock, single source of truth in pyproject.toml
**Implementation Details**: Existing pyproject.toml configuration, Poetry-based dependency tracking

**Code Quality Tools**: Black for formatting, Ruff for linting
**Rationale**: Consistent code style and quality across project
**Implementation Details**: Configuration in pyproject.toml, integration with pre-commit hooks and CI

**Branching Strategy**: Simplified GitFlow with feature branches
**Rationale**: Clean main branch representing production, structured development workflow
**Implementation Details**: feature/* branches → main via Pull Requests

---
2025-01-11 22:47:00 - Initial creation with key decisions from session
2025-01-11 22:50:00 - Added GitHub workflow, Poetry, code quality, and branching decisions from Memory MCP history