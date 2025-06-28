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
MCP_AUTH_TOKEN=your-very-secure-token-here

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
- **Auth**: Bearer token from `MCP_AUTH_TOKEN`

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/zen-mcp.service`:

```ini
[Unit]
Description=Zen MCP Server
After=network.target

[Service]
Type=exec
User=your-user
WorkingDirectory=/path/to/zen-mcp-server
Environment="PATH=/path/to/zen-mcp-server/.zen_venv/bin:/usr/bin"
ExecStart=/path/to/zen-mcp-server/.zen_venv/bin/python /path/to/zen-mcp-server/server.py --transport http --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable zen-mcp
sudo systemctl start zen-mcp
sudo systemctl status zen-mcp
```

### Using PM2 (Process Manager)

Install PM2 globally:
```bash
npm install -g pm2
```

Create `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [{
    name: 'zen-mcp',
    script: 'server.py',
    interpreter: '.zen_venv/bin/python',
    args: '--transport http --host 0.0.0.0 --port 8000',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      MCP_TRANSPORT: 'http',
      MCP_HOST: '0.0.0.0',
      MCP_PORT: '8000'
    }
  }]
};
```

Start with PM2:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Enable autostart on boot
```

## Nginx Reverse Proxy

For production, use Nginx as a reverse proxy with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name mcp.your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # SSE specific settings
    location /sse {
        proxy_pass http://localhost:8000/sse;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header Cache-Control 'no-cache';
        proxy_set_header X-Accel-Buffering 'no';
        proxy_buffering off;
        
        # SSE timeouts
        proxy_read_timeout 24h;
        keepalive_timeout 24h;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Message endpoint
    location /messages/ {
        proxy_pass http://localhost:8000/messages/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name mcp.your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Security Considerations

### Authentication

1. **Always use authentication in production**
   - Set a strong `MCP_AUTH_TOKEN`
   - Never commit tokens to version control
   - Rotate tokens regularly

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
MCP_AUTH_TOKEN=<generate-secure-token>

# API Keys (same as local setup)
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
# etc...
```

## Cloud Deployment Examples

### AWS EC2

1. Launch an EC2 instance (t3.small or larger)
2. Install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3.12 python3.12-venv git nginx certbot
   ```
3. Clone and setup Zen MCP
4. Configure Nginx with SSL using Let's Encrypt
5. Set up as systemd service

### Google Cloud Compute Engine

1. Create a VM instance
2. SSH into the instance
3. Install Python and dependencies:
   ```bash
   sudo apt update
   sudo apt install python3.12 python3.12-venv git
   ```
4. Clone and setup:
   ```bash
   git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
   cd zen-mcp-server
   ./run-server.sh
   ```
5. Set up as systemd service (see above)

### Heroku

1. Create `Procfile`:
   ```
   web: python server.py --transport http --host 0.0.0.0 --port $PORT
   ```
2. Deploy:
   ```bash
   heroku create your-zen-mcp
   heroku config:set MCP_TRANSPORT=http MCP_AUTH_TOKEN=your-token
   git push heroku main
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
# Systemd
sudo journalctl -u zen-mcp -f

# PM2
pm2 logs zen-mcp

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
   - Ensure `MCP_AUTH_TOKEN` is set correctly
   - Include `Authorization: Bearer <token>` header

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
  --header "Authorization: Bearer your-token"
```

### Custom Client

Example client connection:
```javascript
const client = new MCPClient({
  url: 'https://your-server.com:8000/sse',
  headers: {
    'Authorization': 'Bearer your-token'
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