# Zen MCP Server - Docker Implementation

This document describes how to run the Zen MCP Server using Docker containers.

## Quick Start

### Automatic Installation (Claude Code)

1. **One-command installation:**
   ```bash
   ./install-docker-to-claude.sh
   ```
   This script will:
   - Build the Docker image
   - Validate your configuration
   - Add the MCP server to Claude Code
   - Verify the installation

2. **To uninstall:**
   ```bash
   ./uninstall-docker-from-claude.sh
   ```

### Manual Installation

1. **Build the Docker image:**
   ```bash
   ./docker-build.sh
   ```

2. **Configure environment variables:**
   ```bash
   # Run the setup script to create .env
   ./run-server.sh
   # This will create and configure .env with your API keys
   ```

3. **Run the container:**
   ```bash
   # Using docker-compose (recommended)
   docker-compose up

   # Or using the run script
   ./docker-run.sh
   ```

## Architecture

The Docker implementation provides:
- Single container running the Python MCP server
- Stdio communication support for Claude integration
- Volume mounts for persistent logs
- Environment variable configuration
- Resource limits following MCP standards (1 CPU, 2GB RAM)

## Files Created

- `Dockerfile` - Multi-stage build for optimized image
- `docker-compose.yml` - Orchestration configuration
- `.dockerignore` - Excludes unnecessary files from build
- `claude-config-docker.json` - Claude Desktop configuration
- `docker-build.sh` - Build script with multi-platform support
- `docker-run.sh` - Run script with various options

## Usage Options

### Building

```bash
# Basic build
./docker-build.sh

# Multi-platform build
./docker-build.sh --multi-platform

# Build and push to registry
./docker-build.sh --push --multi-platform
```

### Running

```bash
# Run with docker-compose
docker-compose up

# Run in detached mode
./docker-run.sh -d

# Follow logs
./docker-run.sh -f

# Stop the container
./docker-run.sh --stop
```

### Claude Integration

To use with Claude Desktop, add the configuration from `claude-config-docker.json` to your Claude settings:

```json
{
  "mcpServers": {
    "zen-mcp-server": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--init",
        "--env-file", ".env",
        "-v", "./logs:/app/logs",
        "--name", "zen-mcp-container",
        "zen-mcp-server:latest"
      ]
    }
  }
}
```

## Environment Variables

The `.env` file is created and managed by `run-server.sh`. Configure these variables:

- `GEMINI_API_KEY` - Google Gemini API key
- `OPENAI_API_KEY` - OpenAI API key
- `XAI_API_KEY` - X.AI API key
- `OPENROUTER_API_KEY` - OpenRouter API key
- `LOG_LEVEL` - Logging level (default: INFO)
- `OLLAMA_API_URL` - Ollama URL (use `http://host.docker.internal:11434` for local)

The Docker container uses the same `.env` file as the standalone installation, ensuring consistency across deployment methods.

## Volumes

- `./.env:/app/.env:ro` - Environment configuration (read-only)
- `./logs:/app/logs` - Persistent log storage

## Security

- Runs as non-root user (uid 1000)
- Resource limits enforced (1 CPU, 2GB RAM)
- Uses tini for proper signal handling
- No host filesystem access except logs

## Troubleshooting

1. **Check logs:**
   ```bash
   docker logs zen-mcp-container
   # or
   ./docker-run.sh --logs
   ```

2. **Verify image exists:**
   ```bash
   docker images | grep zen-mcp-server
   ```

3. **Rebuild if needed:**
   ```bash
   docker-compose build --no-cache
   ```

## Notes

- The container uses stdio for MCP communication
- Requires at least one AI provider API key
- Logs are persisted to the host filesystem
- Compatible with both x86_64 and ARM64 architectures