# 🐳 Docker User Guide: Using Gemini MCP Server

This guide is for users who want to use the Gemini MCP Server with Claude Desktop **without cloning the repository**. You'll use the pre-built Docker image published to GitHub Container Registry.

## 🎯 What You'll Get

After following this guide, you'll have:
- ✅ Gemini MCP Server running with Claude Desktop
- ✅ Access to all Gemini tools: `chat`, `thinkdeep`, `codereview`, `debug`, `analyze`, `precommit`
- ✅ Automatic conversation threading between Claude and Gemini
- ✅ No need to manage Python dependencies or clone code

## 📋 Prerequisites

### Required
1. **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
2. **Claude Desktop** - [Download here](https://claude.ai/download)
3. **Gemini API Key** - [Get one here](https://makersuite.google.com/app/apikey)

### Platform Support
- ✅ **macOS** (Intel and Apple Silicon)
- ✅ **Linux** 
- ✅ **Windows** (requires WSL2 for Claude Desktop)

## 🚀 Quick Setup (5 minutes)

### Step 1: Start Redis (Required for AI Conversations)

```bash
# Start Redis for conversation threading
docker run -d \
  --name gemini-redis \
  --restart unless-stopped \
  -p 6379:6379 \
  redis:latest
```

This creates a persistent Redis container that will survive system restarts.

### Step 2: Start Gemini MCP Server

```bash
# Create and start the MCP server
docker run -d \
  --name gemini-mcp-server \
  --restart unless-stopped \
  --network host \
  -e GEMINI_API_KEY="your-gemini-api-key-here" \
  -e REDIS_URL="redis://localhost:6379/0" \
  -v "$(pwd):/workspace" \
  ghcr.io/beehiveinnovations/gemini-mcp-server:latest
```

**Replace `your-gemini-api-key-here` with your actual API key.**

**Command explained:**
- `-d`: Run in background
- `--restart unless-stopped`: Auto-restart container
- `--network host`: Connect to your local Redis
- `-e`: Set environment variables
- `-v "$(pwd):/workspace"`: Mount current directory for file access
- `ghcr.io/beehiveinnovations/gemini-mcp-server:latest`: The published image

### Step 3: Configure Claude Desktop

Find your Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows (WSL)**: `/mnt/c/Users/USERNAME/AppData/Roaming/Claude/claude_desktop_config.json`

Add this configuration:

```json
{
  "mcpServers": {
    "gemini": {
      "command": "docker",
      "args": [
        "exec",
        "-i", 
        "gemini-mcp-server",
        "python",
        "server.py"
      ]
    }
  }
}
```

### Step 4: Restart Claude Desktop

Completely quit and restart Claude Desktop for changes to take effect.

### Step 5: Test It Works

Open Claude Desktop and try:
```
"Use gemini to chat about Python best practices"
```

You should see Gemini respond through Claude!

## 🛠️ Available Tools

Once set up, you can use any of these tools naturally in Claude:

| Tool | Example Usage |
|------|---------------|
| **`chat`** | "Use gemini to brainstorm API design ideas" |
| **`thinkdeep`** | "Use gemini to think deeper about this architecture" |
| **`codereview`** | "Use gemini to review my Python code for security issues" |
| **`debug`** | "Use gemini to debug this error: [paste stack trace]" |
| **`analyze`** | "Use gemini to analyze my project structure" |
| **`precommit`** | "Use gemini to validate my git changes before commit" |

## 📁 File Access

The Docker setup automatically mounts your current directory as `/workspace`. This means:

- ✅ Gemini can read files in your current directory and subdirectories
- ✅ You can analyze entire projects: "Use gemini to analyze my src/ directory"
- ✅ Works with relative paths: "Use gemini to review ./main.py"

## 🔧 Management Commands

### Check Status
```bash
# See if containers are running
docker ps

# Should show both 'gemini-redis' and 'gemini-mcp-server'
```

### View Logs
```bash
# Check MCP server logs
docker logs gemini-mcp-server

# Follow logs in real-time
docker logs -f gemini-mcp-server
```

### Update to Latest Version
```bash
# Stop current container
docker stop gemini-mcp-server
docker rm gemini-mcp-server

# Pull latest image and restart (repeat Step 2)
docker pull ghcr.io/beehiveinnovations/gemini-mcp-server:latest
# Then run the docker run command from Step 2
```

### Stop Everything
```bash
# Stop containers (keeps Redis data)
docker stop gemini-mcp-server gemini-redis

# Or remove everything completely
docker stop gemini-mcp-server gemini-redis
docker rm gemini-mcp-server gemini-redis
```

## 🔒 Security Notes

1. **API Key**: Your Gemini API key is stored in the Docker container environment. Use a dedicated key for this purpose.

2. **File Access**: The container can read files in your mounted directory. Don't mount sensitive directories unnecessarily.

3. **Network**: The container uses host networking to connect to Redis. This is safe for local development.

## 🚨 Troubleshooting

### "Connection failed" in Claude Desktop
```bash
# Check if containers are running
docker ps

# Restart MCP server if needed
docker restart gemini-mcp-server

# Check logs for errors
docker logs gemini-mcp-server
```

### "GEMINI_API_KEY environment variable is required"
```bash
# Stop and recreate container with correct API key
docker stop gemini-mcp-server
docker rm gemini-mcp-server
# Then run Step 2 again with the correct API key
```

### "Redis connection failed"
```bash
# Check if Redis is running
docker ps | grep redis

# Start Redis if stopped
docker start gemini-redis

# Or recreate Redis
docker rm -f gemini-redis
# Then run Step 1 again
```

### Tools not responding / hanging
```bash
# Check for resource constraints
docker stats

# Restart everything
docker restart gemini-redis gemini-mcp-server
```

### Windows WSL2 Issues
- Ensure Docker Desktop is set to use WSL2 backend
- Run commands from within WSL2, not Windows Command Prompt
- Use WSL2 paths for file mounting

## 🎉 What's Next?

Once you're set up:

1. **Explore the tools**: Try each tool to understand their specialties
2. **Read the main README**: [Full documentation](../README.md) has advanced usage patterns
3. **Join discussions**: [GitHub Discussions](https://github.com/BeehiveInnovations/gemini-mcp-server/discussions) for tips and tricks
4. **Contribute**: Found a bug or want a feature? [Open an issue](https://github.com/BeehiveInnovations/gemini-mcp-server/issues)

## 💡 Pro Tips

1. **Conversation Threading**: Gemini remembers context across multiple interactions - you can have extended conversations!

2. **File Analysis**: Point Gemini at entire directories: "Use gemini to analyze my entire project for architectural improvements"

3. **Collaborative Workflows**: Combine tools: "Use gemini to analyze this code, then review it for security issues"

4. **Thinking Modes**: Control depth vs cost: "Use gemini with minimal thinking to quickly explain this function"

5. **Web Search**: Enable web search for current info: "Use gemini to debug this React error with web search enabled"

---

**Need Help?** 
- 📖 [Full Documentation](../README.md)
- 💬 [Community Discussions](https://github.com/BeehiveInnovations/gemini-mcp-server/discussions)  
- 🐛 [Report Issues](https://github.com/BeehiveInnovations/gemini-mcp-server/issues)