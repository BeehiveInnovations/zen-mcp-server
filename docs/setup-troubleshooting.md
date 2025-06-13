# Setup and Troubleshooting Guide

This guide covers platform-specific setup instructions, file path requirements, testing procedures, and troubleshooting common issues.

## Table of Contents

- [File Path Requirements](#file-path-requirements)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Windows Users

**Windows users must use WSL2** - Install WSL2 with Ubuntu, then follow the same setup as Linux/macOS. All commands should be run in your WSL2 terminal.

```powershell
# Install WSL2 (run as Administrator in PowerShell)
wsl --install -d Ubuntu
```

Once WSL2 is installed, the setup process is identical to Linux/macOS.

## File Path Requirements

**All file paths must be absolute paths.**

When using any tool, always provide absolute paths:
```
✅ "Use zen to analyze /Users/you/project/src/main.py"
❌ "Use zen to analyze ./src/main.py"  (will be rejected)
```

### Security & File Access

By default, the server allows access to files within your home directory. This is necessary for the server to work with any file you might want to analyze from Claude.

**For Docker environments**, the `WORKSPACE_ROOT` environment variable is used to map your local directory to the internal `/workspace` directory, enabling the MCP to translate absolute file references correctly:

```json
"env": {
  "GEMINI_API_KEY": "your-key",
  "WORKSPACE_ROOT": "/Users/you/project"  // Maps to /workspace inside Docker
}
```

This allows Claude to use absolute paths that will be correctly translated between your local filesystem and the Docker container.

## Testing

### Unit Tests (No API Key Required)
The project includes comprehensive unit tests that use mocks and don't require a Gemini API key:

```bash
# Run all unit tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Simulation Tests (API Key Required)
To test the MCP server with comprehensive end-to-end simulation:

```bash
# Set your API keys (at least one required)
export GEMINI_API_KEY=your-gemini-api-key-here
export OPENAI_API_KEY=your-openai-api-key-here

# Run all simulation tests (default: uses existing Docker containers)
python communication_simulator_test.py

# Run specific tests only
python communication_simulator_test.py --tests basic_conversation content_validation

# Run with Docker rebuild (if needed)
python communication_simulator_test.py --rebuild-docker

# List available tests
python communication_simulator_test.py --list-tests
```

The simulation tests validate:
- Basic conversation flow with continuation
- File handling and deduplication
- Cross-tool conversation threading
- Redis memory persistence
- Docker container integration

### GitHub Actions CI/CD
The project includes GitHub Actions workflows that:

- **✅ Run unit tests automatically** - No API key needed, uses mocks
- **✅ Test on Python 3.10, 3.11, 3.12** - Ensures compatibility
- **✅ Run linting and formatting checks** - Maintains code quality

The CI pipeline works without any secrets and will pass all tests using mocked responses. Simulation tests require API key secrets (`GEMINI_API_KEY` and/or `OPENAI_API_KEY`) to run the communication simulator.

## Troubleshooting

### Docker Issues

**"Connection failed" in Claude Desktop**
- Ensure Docker services are running: `docker compose ps`
- Check if the container name is correct: `docker ps` to see actual container names
- Verify your .env file has at least one valid API key (GEMINI_API_KEY or OPENAI_API_KEY)

**"API key environment variable is required"**
- Edit your .env file and add at least one API key (Gemini or OpenAI)
- Restart services: `docker compose restart`

**Container fails to start**
- Check logs: `docker compose logs zen-mcp`
- Ensure Docker has enough resources (memory/disk space)
- Try rebuilding: `docker compose build --no-cache`

**"spawn ENOENT" or execution issues**
- Verify the container is running: `docker compose ps`
- Check that Docker Desktop is running
- Ensure WSL2 integration is enabled in Docker Desktop (Windows users)

**Testing your Docker setup:**
```bash
# Check if services are running
docker compose ps

# Test manual connection
docker exec -i zen-mcp-server echo "Connection test"

# View logs
docker compose logs -f
```

### Common Setup Issues

**File permission issues**
- Use `sudo chmod +x setup-docker.sh` if the script isn't executable
- Ensure your user is in the docker group: `sudo usermod -aG docker $USER`

**WSL2 issues (Windows users)**
- Ensure you're running Windows 10 version 2004+ or Windows 11
- Enable Docker Desktop WSL2 integration in settings
- Always run commands in WSL2 terminal, not Windows Command Prompt

### API Key Issues

**Invalid API key errors**
- Double-check your API keys are correct
- Ensure there are no extra spaces or characters in your .env file
- For Gemini: Verify your key works at [Google AI Studio](https://makersuite.google.com/app/apikey)
- For OpenAI: Verify your key works at [OpenAI Platform](https://platform.openai.com/api-keys)

**Rate limiting**
- Gemini free tier has limited access to latest models
- Consider upgrading to a paid API plan for better performance
- OpenAI O3 requires sufficient credits in your account

### Performance Issues

**Slow responses**
- Check your internet connection
- Try using a different model (e.g., Flash instead of Pro for faster responses)
- Use lower thinking modes to save tokens and reduce response time

**High token usage**
- Review the [thinking modes section](advanced-usage.md#thinking-modes) to optimize costs
- Use `minimal` or `low` thinking modes for simple tasks
- Consider the auto mode to let Claude choose appropriate models

### Getting Help

If you encounter issues not covered here:

1. **Check the logs**: `docker compose logs -f`
2. **Verify your setup**: Run through the quickstart guide again
3. **Test with simple commands**: Start with basic functionality before complex workflows
4. **Report bugs**: Create an issue at the project repository with detailed error messages and your setup information