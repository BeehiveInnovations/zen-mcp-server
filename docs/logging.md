# Logging

## Viewing Logs in Docker

To monitor MCP server activity in real-time:

```bash
# View all container logs
docker-compose logs -f
```

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