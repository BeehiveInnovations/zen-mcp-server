#!/bin/bash

# Exit on any error, undefined variables, and pipe failures
set -euo pipefail

# Modern Docker setup script for Zen MCP Server with Redis
# This script sets up the complete Docker environment including Redis for conversation threading

echo "🚀 Setting up Zen MCP Server with Docker Compose..."
echo ""

# Get the current working directory (absolute path)
CURRENT_DIR=$(pwd)

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists! Updating if needed..."
    echo ""
else
    # Copy from .env.example and customize
    if [ ! -f .env.example ]; then
        echo "❌ .env.example file not found! This file should exist in the project directory."
        exit 1
    fi
    
    # Copy .env.example to .env
    cp .env.example .env
    echo "✅ Created .env from .env.example"
    
    # Customize the API keys if they're set in environment
    if [ -n "${GEMINI_API_KEY:-}" ]; then
        # Replace the placeholder API key with the actual value
        if command -v sed >/dev/null 2>&1; then
            sed -i.bak "s/your_gemini_api_key_here/$GEMINI_API_KEY/" .env && rm .env.bak
            echo "✅ Updated .env with existing GEMINI_API_KEY from environment"
        else
            echo "⚠️  Found GEMINI_API_KEY in environment, but sed not available. Please update .env manually."
        fi
    fi
    
    if [ -n "${OPENAI_API_KEY:-}" ]; then
        # Replace the placeholder API key with the actual value
        if command -v sed >/dev/null 2>&1; then
            sed -i.bak "s/your_openai_api_key_here/$OPENAI_API_KEY/" .env && rm .env.bak
            echo "✅ Updated .env with existing OPENAI_API_KEY from environment"
        else
            echo "⚠️  Found OPENAI_API_KEY in environment, but sed not available. Please update .env manually."
        fi
    fi
    
    if [ -n "${OPENROUTER_API_KEY:-}" ]; then
        # Replace the placeholder API key with the actual value
        if command -v sed >/dev/null 2>&1; then
            sed -i.bak "s/your_openrouter_api_key_here/$OPENROUTER_API_KEY/" .env && rm .env.bak
            echo "✅ Updated .env with existing OPENROUTER_API_KEY from environment"
        else
            echo "⚠️  Found OPENROUTER_API_KEY in environment, but sed not available. Please update .env manually."
        fi
    fi
    
    # Update WORKSPACE_ROOT to use current user's home directory
    if command -v sed >/dev/null 2>&1; then
        sed -i.bak "s|WORKSPACE_ROOT=/Users/your-username|WORKSPACE_ROOT=$HOME|" .env && rm .env.bak
        echo "✅ Updated WORKSPACE_ROOT to $HOME"
    fi
    echo "✅ Created .env file with Redis configuration"
    echo ""
fi

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running. Please start Docker."
    exit 1
fi

# Use modern docker compose syntax if available, fall back to docker-compose
COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    COMPOSE_CMD="docker-compose"
fi

# Check if at least one API key is properly configured
echo "🔑 Checking API key configuration..."
source .env 2>/dev/null || true

VALID_GEMINI_KEY=false
VALID_OPENAI_KEY=false
VALID_OPENROUTER_KEY=false

# Check if GEMINI_API_KEY is set and not the placeholder
if [ -n "${GEMINI_API_KEY:-}" ] && [ "$GEMINI_API_KEY" != "your_gemini_api_key_here" ]; then
    VALID_GEMINI_KEY=true
    echo "✅ Valid GEMINI_API_KEY found"
fi

# Check if OPENAI_API_KEY is set and not the placeholder
if [ -n "${OPENAI_API_KEY:-}" ] && [ "$OPENAI_API_KEY" != "your_openai_api_key_here" ]; then
    VALID_OPENAI_KEY=true
    echo "✅ Valid OPENAI_API_KEY found"
fi

# Check if OPENROUTER_API_KEY is set and not the placeholder
if [ -n "${OPENROUTER_API_KEY:-}" ] && [ "$OPENROUTER_API_KEY" != "your_openrouter_api_key_here" ]; then
    VALID_OPENROUTER_KEY=true
    echo "✅ Valid OPENROUTER_API_KEY found"
fi

# Require at least one valid API key
if [ "$VALID_GEMINI_KEY" = false ] && [ "$VALID_OPENAI_KEY" = false ] && [ "$VALID_OPENROUTER_KEY" = false ]; then
    echo ""
    echo "❌ ERROR: At least one valid API key is required!"
    echo ""
    echo "Please edit the .env file and set at least one of:"
    echo "  - GEMINI_API_KEY (get from https://makersuite.google.com/app/apikey)"
    echo "  - OPENAI_API_KEY (get from https://platform.openai.com/api-keys)"
    echo "  - OPENROUTER_API_KEY (get from https://openrouter.ai/)"
    echo ""
    echo "Example:"
    echo "  GEMINI_API_KEY=your-actual-api-key-here"
    echo "  OPENAI_API_KEY=sk-your-actual-openai-key-here"
    echo "  OPENROUTER_API_KEY=sk-or-your-actual-openrouter-key-here"
    echo ""
    exit 1
fi

echo "🛠️  Building and starting services..."
echo ""

# Stop and remove existing containers
echo "  - Stopping existing containers..."
$COMPOSE_CMD down --remove-orphans >/dev/null 2>&1 || true

# Clean up any old containers with different naming patterns
OLD_CONTAINERS_FOUND=false

# Check for old Gemini MCP containers (for migration)
if docker ps -a --format "{{.Names}}" | grep -q "^gemini-mcp-server-gemini-mcp-1$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old container: gemini-mcp-server-gemini-mcp-1"
    docker stop gemini-mcp-server-gemini-mcp-1 >/dev/null 2>&1 || true
    docker rm gemini-mcp-server-gemini-mcp-1 >/dev/null 2>&1 || true
fi

if docker ps -a --format "{{.Names}}" | grep -q "^gemini-mcp-server$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old container: gemini-mcp-server"
    docker stop gemini-mcp-server >/dev/null 2>&1 || true
    docker rm gemini-mcp-server >/dev/null 2>&1 || true
fi

# Check for current old containers (from recent versions)
if docker ps -a --format "{{.Names}}" | grep -q "^gemini-mcp-log-monitor$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old container: gemini-mcp-log-monitor"
    docker stop gemini-mcp-log-monitor >/dev/null 2>&1 || true
    docker rm gemini-mcp-log-monitor >/dev/null 2>&1 || true
fi

# Check for old Redis container
if docker ps -a --format "{{.Names}}" | grep -q "^gemini-mcp-server-redis-1$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old container: gemini-mcp-server-redis-1"
    docker stop gemini-mcp-server-redis-1 >/dev/null 2>&1 || true
    docker rm gemini-mcp-server-redis-1 >/dev/null 2>&1 || true
fi

if docker ps -a --format "{{.Names}}" | grep -q "^gemini-mcp-redis$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old container: gemini-mcp-redis"
    docker stop gemini-mcp-redis >/dev/null 2>&1 || true
    docker rm gemini-mcp-redis >/dev/null 2>&1 || true
fi

# Check for old images
if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^gemini-mcp-server-gemini-mcp:latest$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old image: gemini-mcp-server-gemini-mcp:latest"
    docker rmi gemini-mcp-server-gemini-mcp:latest >/dev/null 2>&1 || true
fi

if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^gemini-mcp-server:latest$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old image: gemini-mcp-server:latest"
    docker rmi gemini-mcp-server:latest >/dev/null 2>&1 || true
fi

# Check for current old network (if it exists)
if docker network ls --format "{{.Name}}" | grep -q "^gemini-mcp-server_default$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old network: gemini-mcp-server_default"
    docker network rm gemini-mcp-server_default >/dev/null 2>&1 || true
fi

# Only show cleanup messages if something was actually cleaned up

# Build and start services
echo "  - Building Zen MCP Server image..."
if $COMPOSE_CMD build --no-cache >/dev/null 2>&1; then
    echo "✅ Docker image built successfully!"
else
    echo "❌ Failed to build Docker image. Run '$COMPOSE_CMD build' manually to see errors."
    exit 1
fi

echo "  - Starting Redis (needed for conversation memory)... please wait"
if $COMPOSE_CMD up -d >/dev/null 2>&1; then
    echo "✅ Services started successfully!"
else
    echo "❌ Failed to start services. Run '$COMPOSE_CMD up -d' manually to see errors."
    exit 1
fi

# Wait for services to be healthy
echo "  - Waiting for Redis to be ready..."
sleep 3

# Check service status
if $COMPOSE_CMD ps --format table | grep -q "Up" 2>/dev/null || false; then
    echo "✅ All services are running!"
else
    echo "⚠️  Some services may not be running. Check with: $COMPOSE_CMD ps"
fi

echo ""
echo "📋 Service Status:"
$COMPOSE_CMD ps --format table

# Function to show configuration steps - only if CLI not already set up
show_configuration_steps() {
    echo ""
    echo "🔄 Next steps:"
    NEEDS_KEY_UPDATE=false
    if grep -q "your_gemini_api_key_here" .env 2>/dev/null || grep -q "your_openai_api_key_here" .env 2>/dev/null || grep -q "your_openrouter_api_key_here" .env 2>/dev/null; then
        NEEDS_KEY_UPDATE=true
    fi

    if [ "$NEEDS_KEY_UPDATE" = true ]; then
        echo "1. Edit .env and replace placeholder API keys with actual ones"
        echo "   - GEMINI_API_KEY: your-gemini-api-key-here"
        echo "   - OPENAI_API_KEY: your-openai-api-key-here"
        echo "   - OPENROUTER_API_KEY: your-openrouter-api-key-here (optional)"
        echo "2. Restart services: $COMPOSE_CMD restart"
        echo "3. Copy the configuration below to your Claude Desktop config if required:"
    else
        echo "1. Copy the configuration below to your Claude Desktop config if required:"
    fi

    echo ""
    echo "===== CLAUDE DESKTOP CONFIGURATION ====="
    echo "{"
    echo "  \"mcpServers\": {"
    echo "    \"zen\": {"
    echo "      \"command\": \"docker\","
    echo "      \"args\": ["
    echo "        \"exec\","
    echo "        \"-i\","
    echo "        \"zen-mcp-server\","
    echo "        \"python\","
    echo "        \"server.py\""
    echo "      ]"
    echo "    }"
    echo "  }"
    echo "}"
    echo "==========================================="
}
# Function to automatically configure Claude Code CLI
# Returns: 0 if already configured, 1 if CLI not found, 2 if configured/skipped
setup_claude_code_cli() {
    # Check if claude command exists
    if ! command -v claude &> /dev/null; then
        echo "⚠️  Claude Code CLI not found. Install it to use with CLI:"
        echo "   npm install -g @anthropic-ai/claude-code"
        echo ""
        echo "📋 Manual MCP configuration for Claude Code CLI:"
        echo "claude mcp add zen -s user -- docker exec -i zen-mcp-server python server.py"
        return 1
    fi
    
    echo "🔧 Configuring Claude Code CLI..."
    
    # Get current MCP list and check if zen-mcp-server already exists
    if claude mcp list 2>/dev/null | grep -q "zen-mcp-server" 2>/dev/null; then
        echo "✅ Zen MCP Server already configured in Claude Code CLI"
        echo ""
        return 0  # Already configured
    else
        echo "  - Zen MCP Server not found in Claude Code CLI configuration"
        echo ""
        echo -n "Would you like to add the Zen MCP Server to Claude Code CLI now? [Y/n]: "
        read -r response
        
        # Default to yes if empty response (just pressed enter)
        if [[ -z "$response" || "$response" =~ ^[Yy]$ ]]; then
            echo "  - Adding Zen MCP Server to Claude Code CLI..."
            if claude mcp add zen -s user -- docker exec -i zen-mcp-server python server.py >/dev/null 2>&1; then
                echo "✅ Zen MCP Server added to Claude Code CLI successfully!"
                echo "   Use 'claude' command to start a session with the MCP server"
            else
                echo "⚠️  Failed to add MCP server automatically. You can add it manually:"
                echo "   claude mcp add zen -s user -- docker exec -i zen-mcp-server python server.py"
            fi
        else
            echo "  - Skipped adding MCP server. You can add it manually later:"
            echo "   claude mcp add zen -s user -- docker exec -i zen-mcp-server python server.py"
        fi
        echo ""
        return 2  # Configured or skipped
    fi
}

# Set up Claude Code CLI automatically
setup_claude_code_cli
CLI_STATUS=$?

# Only show configuration details if zen is NOT already configured
if [ $CLI_STATUS -ne 0 ]; then
    # Show configuration steps
    show_configuration_steps
    
    echo ""
    echo "===== CLAUDE CODE CLI CONFIGURATION ====="
    echo "# Useful Claude Code CLI commands:"
    echo "claude                                    # Start interactive session"
    echo "claude mcp list                          # List your MCP servers"
    echo "claude mcp remove zen -s user            # Remove if needed"
    echo "==========================================="
    echo ""
    
    echo "📁 Config file locations:"
    echo "  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
    echo '  Windows (WSL): /mnt/c/Users/USERNAME/AppData/Roaming/Claude/claude_desktop_config.json'
    echo ""
fi

echo "🔧 Useful commands:"
echo "  Start services:    $COMPOSE_CMD up -d"
echo "  Stop services:     $COMPOSE_CMD down"
echo "  View logs:         $COMPOSE_CMD logs -f"
echo "  Restart services:  $COMPOSE_CMD restart"
echo "  Service status:    $COMPOSE_CMD ps"
echo ""

echo "Happy Clauding!"