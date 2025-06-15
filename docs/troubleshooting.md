# Troubleshooting Guide

## Quick Debugging Steps

If you're experiencing issues with the Zen MCP Server, follow these steps:

### 1. Check MCP Connection

Open Claude Desktop and type `/mcp` to see if zen is connected:
- ✅ If zen appears in the list, the connection is working
- ❌ If not listed or shows an error, continue to step 2

### 2. Launch Claude with Debug Mode

Close Claude Desktop and restart with debug logging:

```bash
# macOS/Linux
claude --debug

# Windows (in WSL2)
claude.exe --debug
```

Look for error messages in the console output, especially:
- API key errors
- Docker connection issues
- File permission errors

### 3. Verify API Keys

Check that your API keys are properly set:

```bash
# Check your .env file
cat .env

# Ensure at least one key is set:
# GEMINI_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
```

If you need to update your API keys, edit the `.env` file and then run:

```bash
# Restart services
./run-server.sh

# Or restart and follow logs for troubleshooting
./run-server.sh -f
```

This will validate your configuration and restart the services.

### 4. Check Docker Logs

View the container logs for detailed error information:

```bash
# Check if containers are running
docker-compose ps

# View MCP server logs (recommended - shows actual tool execution)
docker exec zen-mcp-server tail -f -n 500 /tmp/mcp_server.log

# Or use the -f flag when starting to automatically follow logs
./run-server.sh -f
```

**Note**: Due to MCP protocol limitations, `docker-compose logs` only shows startup logs, not tool execution logs. Always use the docker exec command above or the `-f` flag for debugging.

See [Logging Documentation](logging.md) for more details on accessing logs.

### 5. Common Issues

**"Connection failed" in Claude Desktop**
- Ensure Docker is running: `docker ps`
- Restart services: `docker-compose restart`

**"API key environment variable is required"**
- Add your API key to the `.env` file
- Run: `./run-server.sh` to validate and restart

**File path errors**
- Always use absolute paths: `/Users/you/project/file.py`
- Never use relative paths: `./file.py`

### 6. Still Having Issues?

If the problem persists after trying these steps:

1. **Reproduce the issue** - Note the exact steps that cause the problem
2. **Collect logs** - Save relevant error messages from Claude debug mode and Docker logs
3. **Open a GitHub issue** with:
   - Your operating system
   - Error messages
   - Steps to reproduce
   - What you've already tried

## Windows Users

**Important**: Windows users must use WSL2. Install it with:

```powershell
wsl --install -d Ubuntu
```

Then follow the standard setup inside WSL2.