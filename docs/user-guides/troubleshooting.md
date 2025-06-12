# Troubleshooting Guide

This guide helps you resolve common issues with the Gemini MCP Server.

## Quick Diagnostics

### Check System Status

```bash
# Verify containers are running
docker compose ps

# Check logs for errors
docker compose logs -f

# Test API connectivity
docker exec -it zen-mcp-server python -c "import os; print('API Key set:', bool(os.getenv('GEMINI_API_KEY')))"
```

## Common Issues

### 1. "Connection failed" in Claude Desktop

**Symptoms:**
- Claude Desktop shows "Connection failed" when trying to use Gemini tools
- MCP server appears disconnected

**Diagnosis:**
```bash
# Check if containers are running
docker compose ps

# Should show both containers as 'Up'
```

**Solutions:**

1. **Containers not running:**
   ```bash
   docker compose up -d
   ```

2. **Container name mismatch:**
   ```bash
   # Check actual container name
   docker ps --format "{{.Names}}"
   
   # Update Claude Desktop config if needed
   ```

3. **Docker Desktop not running:**
   - Ensure Docker Desktop is started
   - Check Docker daemon status: `docker info`

### 2. "GEMINI_API_KEY environment variable is required"

**Symptoms:**
- Server logs show API key error
- Tools respond with authentication errors

**Solutions:**

1. **Check .env file:**
   ```bash
   cat .env | grep GEMINI_API_KEY
   ```

2. **Update API key:**
   ```bash
   nano .env
   # Change: GEMINI_API_KEY=your_actual_api_key
   
   # Restart services
   docker compose restart
   ```

3. **Verify key is valid:**
   - Check [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Ensure key has proper permissions

### 3. Redis Connection Issues

**Symptoms:**
- Conversation threading not working
- Error logs mention Redis connection failures

**Diagnosis:**
```bash
# Check Redis container
docker compose ps redis

# Test Redis connectivity
docker exec -it gemini-mcp-redis redis-cli ping
# Should return: PONG
```

**Solutions:**

1. **Start Redis container:**
   ```bash
   docker compose up -d redis
   ```

2. **Reset Redis data:**
   ```bash
   docker compose down
   docker volume rm zen-mcp-server_redis_data
   docker compose up -d
   ```

3. **Check Redis logs:**
   ```bash
   docker compose logs redis
   ```

### 4. Tools Not Responding / Hanging

**Symptoms:**
- Gemini tools start but never complete
- Long response times
- Timeout errors

**Diagnosis:**
```bash
# Check resource usage
docker stats

# Check for memory/CPU constraints
```

**Solutions:**

1. **Restart services:**
   ```bash
   docker compose restart
   ```

2. **Increase memory limits:**
   ```yaml
   # In docker-compose.override.yml
   services:
     gemini-mcp:
       deploy:
         resources:
           limits:
             memory: 4G
   ```

3. **Check API rate limits:**
   - Verify your Gemini API quota
   - Consider using a paid API key for higher limits

### 5. File Access Issues

**Symptoms:**
- "File not found" errors when using file paths
- Permission denied errors

**Diagnosis:**
```bash
# Check mounted directory
docker exec -it zen-mcp-server ls -la /workspace

# Verify file permissions
ls -la /path/to/your/file
```

**Solutions:**

1. **Use absolute paths:**
   ```
   ✅ /Users/yourname/project/file.py
   ❌ ./file.py
   ```

2. **Check file exists in mounted directory:**
   ```bash
   # Files must be within WORKSPACE_ROOT (default: $HOME)
   echo $WORKSPACE_ROOT
   ```

3. **Fix permissions (Linux):**
   ```bash
   sudo chown -R $USER:$USER /path/to/your/files
   ```

### 6. Port Conflicts

**Symptoms:**
- "Port already in use" errors
- Services fail to start

**Diagnosis:**
```bash
# Check what's using port 6379
lsof -i :6379
netstat -tulpn | grep 6379
```

**Solutions:**

1. **Stop conflicting services:**
   ```bash
   # If you have local Redis running
   sudo systemctl stop redis
   # or
   brew services stop redis
   ```

2. **Use different ports:**
   ```yaml
   # In docker-compose.override.yml
   services:
     redis:
       ports:
         - "6380:6379"
   ```

## Platform-Specific Issues

### Windows (WSL2)

**Common Issues:**
- Docker Desktop WSL2 integration not enabled
- File path format issues
- Permission problems

**Solutions:**

1. **Enable WSL2 integration:**
   - Docker Desktop → Settings → Resources → WSL Integration
   - Enable integration for your WSL distribution

2. **Use WSL2 paths:**
   ```bash
   # Run commands from within WSL2
   cd /mnt/c/Users/yourname/project
   ./setup-docker.sh
   ```

3. **File permissions:**
   ```bash
   # In WSL2
   chmod +x setup-docker.sh
   ```

### macOS

**Common Issues:**
- Docker Desktop not allocated enough resources
- File sharing permissions

**Solutions:**

1. **Increase Docker resources:**
   - Docker Desktop → Settings → Resources
   - Increase memory to at least 4GB

2. **File sharing:**
   - Docker Desktop → Settings → Resources → File Sharing
   - Ensure your project directory is included

### Linux

**Common Issues:**
- Docker permission issues
- systemd conflicts

**Solutions:**

1. **Docker permissions:**
   ```bash
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **Start Docker daemon:**
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

## Advanced Troubleshooting

### Debug Mode

Enable detailed logging:

```bash
# In .env file
LOG_LEVEL=DEBUG

# Restart with verbose output
docker compose down && docker compose up
```

### Container Debugging

Access container for inspection:

```bash
# Enter MCP server container
docker exec -it zen-mcp-server bash

# Check Python environment
python --version
pip list

# Test Gemini API directly
python -c "
import google.generativeai as genai
import os
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')
print('API connection test successful')
"
```

### Network Debugging

Check container networking:

```bash
# Inspect Docker network
docker network ls
docker network inspect zen-mcp-server_default

# Test container communication
docker exec -it zen-mcp-server ping redis
```

### Clean Reset

Complete environment reset:

```bash
# Stop everything
docker compose down -v

# Remove images
docker rmi $(docker images "zen-mcp-server*" -q)

# Clean setup
./setup-docker.sh
```

## Performance Optimization

### Resource Monitoring

```bash
# Monitor container resources
docker stats

# Check system resources
htop  # or top
df -h  # disk space
```

### Optimization Tips

1. **Allocate adequate memory:**
   - Minimum: 2GB for Docker Desktop
   - Recommended: 4GB+ for large projects

2. **Use SSD storage:**
   - Docker volumes perform better on SSDs

3. **Limit context size:**
   - Use specific file paths instead of entire directories
   - Utilize thinking modes to control token usage

## Getting Help

### Collect Debug Information

Before seeking help, collect:

```bash
# System information
docker --version
docker compose --version
uname -a

# Container status
docker compose ps
docker compose logs --tail=100

# Configuration
cat .env | grep -v "GEMINI_API_KEY"
```

### Support Channels

- 📖 [Documentation](../README.md)
- 💬 [GitHub Discussions](https://github.com/BeehiveInnovations/zen-mcp-server/discussions)
- 🐛 [Issue Tracker](https://github.com/BeehiveInnovations/zen-mcp-server/issues)

### Creating Bug Reports

Include in your bug report:
1. System information (OS, Docker version)
2. Steps to reproduce
3. Expected vs actual behavior
4. Relevant log output
5. Configuration (without API keys)

---

**See Also:**
- [Installation Guide](installation.md)
- [Configuration Guide](configuration.md)
