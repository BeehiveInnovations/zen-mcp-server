# 🐳 Docker User Guide: Using Gemini MCP Server

This guide shows you how to use the Gemini MCP Server with Claude Desktop using the automated Docker setup. **Everything is handled automatically** - no manual Redis setup required!

## 🎯 What You'll Get

After following this guide, you'll have:
- ✅ Gemini MCP Server running with Claude Desktop
- ✅ Redis automatically configured for conversation threading
- ✅ Access to all Gemini tools: `chat`, `thinkdeep`, `codereview`, `debug`, `analyze`, `precommit`
- ✅ Persistent data storage that survives container restarts

## 📋 Prerequisites

### Required
1. **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
2. **Claude Desktop** - [Download here](https://claude.ai/download)
3. **Gemini API Key** - [Get one here](https://makersuite.google.com/app/apikey)
4. **Git** - For cloning the repository

### Platform Support
- ✅ **macOS** (Intel and Apple Silicon M1/M2/M3)
- ✅ **Linux** (AMD64 and ARM64)
- ✅ **Windows** (requires WSL2 + Docker Desktop for Claude Desktop)

### Windows Setup Requirements
**Windows users must use WSL2 + Docker Desktop:**
1. **Install WSL2** - [Microsoft WSL Guide](https://docs.microsoft.com/en-us/windows/wsl/install)
2. **Install Docker Desktop** - [Docker for Windows](https://docs.docker.com/desktop/windows/install/)
3. **Enable WSL2 integration** in Docker Desktop settings
4. **Run Claude Desktop** in Windows (Docker containers run in WSL2)

**Why WSL2 is required:**
- Docker images are Linux-based (python:3.11-slim)
- Docker Desktop automatically runs containers in WSL2 Linux environment
- Provides full compatibility with Linux containers on Windows

**Alternative for Windows:** Install Python directly and run server with `pip install -r requirements.txt && python server.py`

## 🚀 Setup Option 1: Published Docker Image (Fastest)

**Quick setup using pre-built image from GitHub Container Registry - no build required!**

### Step 1: Pull Published Image

```bash
# Download the latest stable version
docker pull ghcr.io/beehiveinnovations/zen-mcp-server:latest

# Optional: Pull a specific version
docker pull ghcr.io/beehiveinnovations/zen-mcp-server:v1.2.0
```

### Step 2: Configure Claude Desktop

**Find your Claude Desktop config file:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows (WSL required)**: `/mnt/c/Users/USERNAME/AppData/Roaming/Claude/claude_desktop_config.json`

**Add this configuration:**
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
        "GEMINI_API_KEY": "your-gemini-api-key-here"
      }
    }
  }
}
```

### Step 3: Update Available Tags

Available image tags:
- `latest` - Most recent stable release
- `v1.2.0`, `v1.1.0`, etc. - Specific version releases
- `pr-{number}` - Development builds from pull requests
- `main-{sha}` - Development builds from main branch

```bash
# See all available tags
docker search ghcr.io/beehiveinnovations/zen-mcp-server

# Or check GitHub Container Registry
open https://github.com/BeehiveInnovations/zen-mcp-server/pkgs/container/zen-mcp-server
```

### Step 4: Test Installation

Restart Claude Desktop and try:
```
"Use gemini to say hello and confirm the connection works"
```

**Benefits of Published Image:**
- ✅ **Instant setup** - No build time, no source code needed
- ✅ **Always updated** - Automatically built with every release
- ✅ **Smaller footprint** - No development dependencies
- ✅ **Version control** - Pin to specific versions for stability
- ✅ **Cross-platform** - Works on any Docker-supported OS

---

## 🛠️ Setup Option 2: Local Build (For Development)

### Step 1: Clone Repository

```bash
git clone https://github.com/BeehiveInnovations/zen-mcp-server.git
cd zen-mcp-server
```

### Step 2: One-Command Setup

```bash
# Automated setup - builds images and starts all services
./setup-docker.sh
```

**What this script does automatically:**
- ✅ Creates `.env` file with your API key (if `GEMINI_API_KEY` environment variable is set)
- ✅ Builds the Gemini MCP Server Docker image
- ✅ Starts Redis container for conversation threading
- ✅ Starts MCP server container
- ✅ Configures networking between containers
- ✅ Shows you the exact Claude Desktop configuration

### Step 3: Add Your API Key (if needed)

If you see a message about updating your API key:

```bash
# Edit .env file and replace placeholder with your actual key
nano .env
# Change: GEMINI_API_KEY=your-gemini-api-key-here
# To: GEMINI_API_KEY=your_actual_api_key

# Restart services to apply changes
docker compose restart
```

### Step 4: Configure Claude Desktop

The setup script shows you the exact configuration. Add this to your Claude Desktop config:

**Find your config file:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
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
        "gemini-mcp-server",
        "python",
        "server.py"
      ]
    }
  }
}
```

### Step 5: Restart Claude Desktop & Test

1. Completely quit and restart Claude Desktop
2. Test with: `"Use gemini to chat about Python best practices"`

## 🚀 Setup Option 2: Published Docker Image (Advanced)

If you prefer to use the published image without cloning:

```bash
# Create a directory for your work
mkdir gemini-mcp-project && cd gemini-mcp-project

# Create minimal docker-compose.yml
cat > docker-compose.yml << 'EOF'
services:
  redis:
    image: redis:7-alpine
    container_name: gemini-mcp-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  gemini-mcp:
    image: ghcr.io/beehiveinnovations/zen-mcp-server:latest
    container_name: gemini-mcp-server
    restart: unless-stopped
    depends_on:
      - redis
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - REDIS_URL=redis://redis:6379/0
      - WORKSPACE_ROOT=${HOME}
    volumes:
      - ${HOME}:/workspace:ro
    stdin_open: true
    tty: true

volumes:
  redis_data:
EOF

# Create .env file
echo "GEMINI_API_KEY=your-gemini-api-key-here" > .env

# Start services
docker compose up -d
```

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

The Docker setup automatically mounts your home directory as `/workspace`. This means:

- ✅ Gemini can read files anywhere in your home directory
- ✅ You can analyze entire projects: "Use gemini to analyze my ~/Projects/myapp/src/ directory"
- ✅ Works with absolute paths: "Use gemini to review /Users/yourname/project/main.py"

## 🔧 Management Commands

### Check Status
```bash
# See if containers are running
docker compose ps

# Should show both 'gemini-mcp-redis' and 'gemini-mcp-server' as 'Up'
```

### View Logs
```bash
# Check MCP server logs
docker compose logs gemini-mcp -f

# Check Redis logs
docker compose logs redis -f

# View all logs
docker compose logs -f
```

### Update to Latest Version
```bash
# For cloned repository setup
git pull origin main
./setup-docker.sh

# For published image setup  
docker compose pull
docker compose up -d
```

### Stop/Start Services
```bash
# Stop containers (keeps data)
docker compose stop

# Start containers again
docker compose start

# Restart all services
docker compose restart

# Stop and remove everything
docker compose down

# Stop and remove everything including volumes (⚠️ deletes Redis data)
docker compose down -v
```

## 🔒 Security Notes

1. **API Key**: Your Gemini API key is stored in the container environment. The `.env` file is gitignored for security.

2. **File Access**: The container can read files in your home directory (mounted as read-only). This is necessary for file analysis.

3. **Network**: Redis runs on localhost:6379 but is only accessible to the MCP server container by default.

## 🚨 Troubleshooting

### "Connection failed" in Claude Desktop
```bash
# Check if containers are running
docker compose ps

# Should show both containers as 'Up'
# If not, check logs:
docker compose logs gemini-mcp
```

### "GEMINI_API_KEY environment variable is required"
```bash
# Edit your .env file
nano .env
# Update: GEMINI_API_KEY=your_actual_api_key

# Restart services
docker compose restart
```

### Containers won't start
```bash
# Check logs for specific errors
docker compose logs

# Rebuild and restart
docker compose down
docker compose up --build -d
```

### Tools not responding
```bash
# Check container resources
docker stats

# Restart everything
docker compose restart

# If still having issues, check Claude Desktop config
```

### Permission issues (Linux)
```bash
# Ensure proper ownership
sudo chown -R $USER:$USER .

# Make setup script executable
chmod +x setup-docker.sh
```

## 💡 How It Works (Technical Details)

The setup uses Docker Compose to orchestrate two services:

1. **Redis Container** (`gemini-mcp-redis`)
   - Official Redis 7 Alpine image
   - Automatic data persistence with Docker volume
   - Available at `redis:6379` within Docker network
   - Available at `localhost:6379` from host machine

2. **Gemini MCP Server** (`gemini-mcp-server`)
   - Built from local Dockerfile or pulled from GHCR
   - Automatically connects to Redis container
   - Your home directory mounted for file access
   - Configured with proper environment variables

**Key Benefits:**
- 🔄 **Automatic Service Discovery**: No IP configuration needed
- 💾 **Data Persistence**: Redis data survives container restarts
- 🛡️ **Isolation**: Services run in isolated containers
- 🚀 **Easy Updates**: Pull latest images with one command

## 🎉 What's Next?

Once you're set up:

1. **Explore the tools**: Try each tool to understand their specialties
2. **Read the main README**: [Full documentation](../README.md) has advanced usage patterns
3. **Join discussions**: [GitHub Discussions](https://github.com/BeehiveInnovations/zen-mcp-server/discussions) for tips and tricks
4. **Contribute**: Found a bug or want a feature? [Open an issue](https://github.com/BeehiveInnovations/zen-mcp-server/issues)

## 💡 Pro Tips

1. **Conversation Threading**: Gemini remembers context across multiple interactions thanks to automatic Redis setup!

2. **File Analysis**: Point Gemini at entire directories: "Use gemini to analyze my entire ~/Projects/myapp for architectural improvements"

3. **Collaborative Workflows**: Combine tools: "Use gemini to analyze this code, then review it for security issues"

4. **Thinking Modes**: Control depth vs cost: "Use gemini with minimal thinking to quickly explain this function"

5. **Logs are your friend**: Always check `docker compose logs -f` if something seems wrong

---

**Need Help?** 
- 📖 [Full Documentation](../README.md)
- 💬 [Community Discussions](https://github.com/BeehiveInnovations/zen-mcp-server/discussions)  
- 🐛 [Report Issues](https://github.com/BeehiveInnovations/zen-mcp-server/issues)
