# Logging

## Quick Start - Follow Logs

The easiest way to monitor logs is to use the `-f` flag when starting the server:

```bash
# Start server and automatically follow MCP logs
./run-server.sh -f
```

This will start the server and immediately begin tailing the MCP server logs.

## Viewing Logs in Docker

To monitor MCP server activity in real-time:

```bash
# Follow MCP server logs (recommended)
docker exec zen-mcp-server tail -f -n 500 /tmp/mcp_server.log

# Or use the -f flag when starting the server
./run-server.sh -f
```

**Note**: Due to MCP protocol limitations, container logs don't show tool execution details. Always use the commands above for debugging.

## Log Files

Logs are stored in the container's `/tmp/` directory and rotate daily at midnight, keeping 7 days of history:

- **`mcp_server.log`** - Main server operations
- **`mcp_activity.log`** - Tool calls and conversations
- **`mcp_server_overflow.log`** - Overflow protection for large logs

## Accessing Log Files

To access log files directly:

```bash
# Enter the container
docker exec -it zen-mcp-server /bin/sh

# View current logs
cat /tmp/mcp_server.log
cat /tmp/mcp_activity.log

# View previous days (with date suffix)
cat /tmp/mcp_server.log.2024-06-14
```

## Log Level

Set verbosity with `LOG_LEVEL` in your `.env` file or docker-compose.yml:

```yaml
environment:
  - LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```