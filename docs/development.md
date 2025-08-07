# Development Guide

This guide covers setting up the development environment for the Zen MCP server, including dependency management with UV.

## Prerequisites

- Python 3.9 or higher
- [UV](https://github.com/astral-sh/uv) - Ultra-fast Python package installer and resolver
- Docker (for containerized development)

## Setting Up the Development Environment

### 1. Install UV

UV is used for fast and reliable dependency management. Install it with:

```bash
# On Unix-like systems
curl -sSf https://astral.sh/uv/install.sh | sh

# On Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/zen-mcp-server.git
cd zen-mcp-server
```

### 3. Install Dependencies

```bash
# Install production dependencies
uv pip install -r requirements.txt

# Install development dependencies (optional, for testing and development)
uv pip install -r requirements-dev.txt
```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_my_feature.py
```

### Linting and Formatting

```bash
# Run linter
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run black .

# Sort imports
uv run isort .
```

## Docker Development

### Building the Development Image

```bash
# Build the development image
docker-compose -f docker-compose.yml build

# Start the development server
docker-compose -f docker-compose.yml up
```

The development server will automatically reload when you make changes to the source code.

### Running Tests in Docker

```bash
docker-compose -f docker-compose.yml run --rm app uv run pytest
```

## Dependency Management

### Adding a New Dependency

```bash
# Add a production dependency
uv pip install package-name
uv pip freeze --exclude-editable > requirements.txt

# Add a development dependency
uv pip install --group dev package-name
uv pip freeze --group dev --exclude-editable > requirements-dev.txt
```

### Updating Dependencies

```bash
# Update all dependencies
uv pip compile --upgrade --output-file=requirements.txt pyproject.toml
uv pip sync requirements.txt

# Update a specific package
uv pip install --upgrade package-name
uv pip freeze --exclude-editable > requirements.txt
```

## Troubleshooting

### Common Issues

**Issue**: UV command not found
**Solution**: Make sure to add UV to your PATH. On Unix-like systems, add this to your shell configuration:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

**Issue**: Dependency resolution errors
**Solution**: Try clearing the UV cache and reinstalling:

```bash
uv pip install --reinstall --no-cache-dir -r requirements.txt
```

## Contributing

1. Create a new branch for your feature or bugfix
2. Make your changes
3. Run tests and linters
4. Submit a pull request

For more information, see our [Contributing Guide](CONTRIBUTING.md).
