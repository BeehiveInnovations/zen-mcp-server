# Scripts Directory

This directory contains utility scripts for the Gemini MCP Server project.

## bump_version.py

A utility script for semantic version bumping that integrates with the automatic versioning workflow.

### Usage

```bash
python scripts/bump_version.py <major|minor|patch>
```

### Examples

```bash
# Bump patch version (e.g., 3.2.0 → 3.2.1)
python scripts/bump_version.py patch

# Bump minor version (e.g., 3.2.0 → 3.3.0)
python scripts/bump_version.py minor

# Bump major version (e.g., 3.2.0 → 4.0.0)
python scripts/bump_version.py major
```

### Features

- Reads current version from `config.py`
- Applies semantic versioning rules
- Updates both `__version__` and `__updated__` fields
- Preserves file formatting and structure
- Outputs new version for GitHub Actions integration

### Integration

This script is primarily used by the GitHub Actions workflow (`.github/workflows/auto-version.yml`) for automatic version bumping based on PR title prefixes. Manual usage is available for special cases.

### Version Bump Rules

- **Major**: Increments first digit, resets others (3.2.1 → 4.0.0)
- **Minor**: Increments second digit, resets patch (3.2.1 → 3.3.0)
- **Patch**: Increments third digit (3.2.1 → 3.2.2)