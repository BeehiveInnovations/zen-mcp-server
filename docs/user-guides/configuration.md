# Configuration Guide

This guide covers all configuration options for the Gemini MCP Server.

## Environment Variables

### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Gemini API key from Google AI Studio (replace entire placeholder) | `AIzaSyC_your_actual_key_here` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL for conversation threading |
| `WORKSPACE_ROOT` | `$HOME` | Root directory mounted as `/workspace` in container |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `GEMINI_MODEL` | `gemini-2.5-pro-preview-06-05` | Gemini model to use |
| `MAX_CONTEXT_TOKENS` | `1000000` | Maximum context window (1M tokens for Gemini Pro) |

## Claude Desktop Configuration

### MCP Server Configuration

Add to your Claude Desktop config file:

**Location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Configuration Options

#### Option 1: Published Docker Image (Recommended)

**Simplest setup using pre-built images from GitHub Container Registry:**

```json
{
  "mcpServers": {
    "gemini": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "GEMINI_API_KEY",
        "ghcr.io/beehiveinnovations/zen-mcp-server:latest"
      ],
      "env": {
        "GEMINI_API_KEY": "AIzaSyC_your_actual_gemini_api_key_here"
      }
    }
  }
}
```

**Available Image Tags:**
- `latest` - Most recent stable release (recommended)
- `v1.2.0`, `v1.1.0` - Specific version tags
- `pr-{number}` - Development builds from pull requests
- `main-{commit-sha}` - Development builds from main branch

**Benefits:**
- ✅ No local build required - instant setup
- ✅ Automatically updated with releases  
- ✅ Smaller local footprint
- ✅ Version pinning for stability
- ✅ Cross-platform compatibility

**Version Pinning Example:**
```json
{
  "mcpServers": {
    "gemini": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "GEMINI_API_KEY",
        "ghcr.io/beehiveinnovations/zen-mcp-server:v1.2.0"
      ],
      "env": {
        "GEMINI_API_KEY": "AIzaSyC_your_actual_gemini_api_key_here"
      }
    }
  }
}
```

#### Option 2: Local Development Build
- **Windows (WSL)**: `/mnt/c/Users/USERNAME/AppData/Roaming/Claude/claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "gemini": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "zen-mcp-server",
        "python",
        "server.py"
      ]
    }
  }
}
```

### Alternative: Claude Code CLI

```bash
# Add MCP server via CLI
claude mcp add zen -s user -- docker exec -i zen-mcp-server python server.py

# List servers
claude mcp list

# Remove server
claude mcp remove zen -s user
```

## Docker Configuration

### Environment File (.env)

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key-here

# Optional - Docker Compose defaults
REDIS_URL=redis://redis:6379/0
WORKSPACE_ROOT=/Users/yourname
LOG_LEVEL=INFO
```

### Docker Compose Overrides

Create `docker-compose.override.yml` for custom settings:

```yaml
services:
  zen-mcp:
    environment:
      - LOG_LEVEL=DEBUG
    volumes:
      - /custom/path:/workspace:ro
```

## Logging Configuration

### Log Levels

- **DEBUG**: Detailed operational messages, conversation threading, tool execution flow
- **INFO**: General operational messages (default)
- **WARNING**: Warnings and errors only
- **ERROR**: Errors only

### Viewing Logs

```bash
# Real-time logs
docker compose logs -f zen-mcp

# Specific service logs
docker compose logs redis
docker compose logs log-monitor
```

## Security Configuration

### API Key Security

1. **Never commit API keys** to version control
2. **Use environment variables** or `.env` files
3. **Restrict key permissions** in Google AI Studio
4. **Rotate keys periodically**

### File Access Security

The container mounts your home directory as read-only. To restrict access:

```yaml
# In docker-compose.override.yml
services:
  zen-mcp:
    environment:
      - WORKSPACE_ROOT=/path/to/specific/project
    volumes:
      - /path/to/specific/project:/workspace:ro
```

## Performance Configuration

### Memory Limits

```yaml
# In docker-compose.override.yml
services:
  zen-mcp:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
```

### Redis Configuration

Redis is pre-configured with optimal settings:
- 512MB memory limit
- LRU eviction policy
- Persistence enabled (saves every 60 seconds if data changed)

To customize Redis:

```yaml
# In docker-compose.override.yml
services:
  redis:
    command: redis-server --maxmemory 1g --maxmemory-policy allkeys-lru
```

## Troubleshooting Configuration

### Common Issues

1. **API Key Not Set**
   ```bash
   # Check .env file
   cat .env | grep GEMINI_API_KEY
   ```

2. **File Access Issues**
   ```bash
   # Check mounted directory
   docker exec -it zen-mcp-server ls -la /workspace
   ```

3. **Redis Connection Issues**
   ```bash
   # Test Redis connectivity
   docker exec -it zen-mcp-redis redis-cli ping
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# In .env file
LOG_LEVEL=DEBUG

# Restart services
docker compose restart
```

## Advanced Configuration

### Custom Model Configuration

To use a different Gemini model, override in `.env`:

```bash
GEMINI_MODEL=gemini-2.5-pro-latest
```

### Network Configuration

For custom networking (advanced users):

```yaml
# In docker-compose.override.yml
networks:
  custom_network:
    driver: bridge

services:
  zen-mcp:
    networks:
      - custom_network
  redis:
    networks:
      - custom_network
```

---

**See Also:**
- [Installation Guide](installation.md)
- [Troubleshooting Guide](troubleshooting.md)

