# Remote Deployment Guide

This guide explains how to deploy Zen MCP Server on a remote server and connect to it via URL.

## Overview

Zen MCP Server supports two transport modes:
- **stdio** (default) - For local usage with Claude Desktop/CLI
- **http** - For remote deployment with HTTP/SSE transport

The HTTP mode enables you to:
- Host Zen MCP on a remote server
- Connect multiple clients to a single server
- Deploy in cloud environments
- Use with web-based MCP clients

## Quick Start

### 1. Install Dependencies

```bash
# Clone the repository on your server
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
cd zen-mcp-server

# Run setup (installs dependencies)
./run-server.sh
```

### 2. Configure Authentication

Edit `.env` file to set secure authentication:

```bash
# Required for remote access
MCP_API_KEY=your-very-secure-api-key-here

# Optional: Disable auth for testing (NOT recommended for production)
# MCP_REQUIRE_AUTH=false
```

### 3. Start the Server

```bash
# Start on default port (8000) - localhost only
./run-server.sh --transport http

# Start on all interfaces (for remote access)
./run-server.sh --transport http --host 0.0.0.0 --port 8000

# Or use environment variables
MCP_HOST=0.0.0.0 MCP_PORT=8000 ./run-server.sh --transport http
```

### 4. Connect Your Client

Configure your MCP client to connect to:
- **URL**: `https://your-server.com:8000/sse`
- **Auth**: API key header `x-api-key` with value from `MCP_API_KEY`

## Security Considerations

### Authentication

1. **Always use authentication in production**
   - Set a strong `MCP_API_KEY`
   - Never commit API keys to version control
   - Rotate API keys regularly

2. **Use HTTPS**
   - Deploy behind a reverse proxy with SSL
   - Never expose HTTP directly to the internet

3. **Network Security**
   - Use firewall rules to restrict access
   - Consider VPN for internal deployments
   - Monitor access logs

### Environment Variables

Required for secure deployment:

```bash
# Authentication
MCP_REQUIRE_AUTH=true
MCP_API_KEY=<generate-secure-api-key>

# API Keys (same as local setup)
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
# etc...
```

## Monitoring

### Health Check

The server provides a health endpoint:
```bash
curl https://your-server.com:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "transport": "http/sse",
  "tools": 15
}
```

### Logs

View server logs:
```bash
# Direct
tail -f logs/mcp_server.log
```

## Troubleshooting

### Connection Issues

1. **"SSE connection not established"**
   - Check firewall allows port 8000
   - Verify server is running: `curl http://localhost:8000/health`
   - Check authentication token

2. **"Unauthorized"**
   - Ensure `MCP_API_KEY` is set correctly
   - Include `x-api-key: <your-api-key>` header

3. **Connection refused from browsers**
   - Note: CORS is not supported; this server is designed for MCP clients only
   - Use proper MCP client libraries for connections

### Performance

- Use connection pooling for database connections
- Monitor memory usage with large contexts
- Consider horizontal scaling for high load

## Client Configuration

### MCP Inspector

Test your deployment with [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector \
  --url https://your-server.com:8000/sse \
  --header "x-api-key: your-api-key"
```

### Custom Client

Example client connection:
```javascript
const client = new MCPClient({
  url: 'https://your-server.com:8000/sse',
  headers: {
    'x-api-key': 'your-api-key'
  }
});
```

## Best Practices

1. **Use environment variables** for all configuration
2. **Enable authentication** for any non-local deployment
3. **Use HTTPS** with proper certificates
4. **Monitor logs** and set up alerts
5. **Regular updates** - keep dependencies current
6. **Backup configuration** before updates

## Support

For issues specific to remote deployment:
1. Check server logs first
2. Verify network connectivity
3. Test with MCP Inspector
4. Review [security considerations](#security-considerations)
5. Open an issue with deployment details