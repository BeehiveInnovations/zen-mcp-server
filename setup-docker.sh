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
    else
        echo "⚠️  GEMINI_API_KEY not found in environment. Please edit .env and add your API key."
    fi
    
    if [ -n "${OPENAI_API_KEY:-}" ]; then
        # Replace the placeholder API key with the actual value
        if command -v sed >/dev/null 2>&1; then
            sed -i.bak "s/your_openai_api_key_here/$OPENAI_API_KEY/" .env && rm .env.bak
            echo "✅ Updated .env with existing OPENAI_API_KEY from environment"
        else
            echo "⚠️  Found OPENAI_API_KEY in environment, but sed not available. Please update .env manually."
        fi
    else
        echo "⚠️  OPENAI_API_KEY not found in environment. Please edit .env and add your API key."
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

# Require at least one valid API key
if [ "$VALID_GEMINI_KEY" = false ] && [ "$VALID_OPENAI_KEY" = false ]; then
    echo ""
    echo "❌ ERROR: At least one valid API key is required!"
    echo ""
    echo "Please edit the .env file and set at least one of:"
    echo "  - GEMINI_API_KEY (get from https://makersuite.google.com/app/apikey)"
    echo "  - OPENAI_API_KEY (get from https://platform.openai.com/api-keys)"
    echo ""
    echo "Example:"
    echo "  GEMINI_API_KEY=your-actual-api-key-here"
    echo "  OPENAI_API_KEY=sk-your-actual-openai-key-here"
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

echo "  - Starting Redis and MCP services... please wait"
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

echo ""
echo "🔄 Next steps:"
NEEDS_KEY_UPDATE=false
if grep -q "your_gemini_api_key_here" .env 2>/dev/null || grep -q "your_openai_api_key_here" .env 2>/dev/null; then
    NEEDS_KEY_UPDATE=true
fi

if [ "$NEEDS_KEY_UPDATE" = true ]; then
    echo "1. Edit .env and replace placeholder API keys with actual ones"
    echo "   - GEMINI_API_KEY: your-gemini-api-key-here"
    echo "   - OPENAI_API_KEY: your-openai-api-key-here"
    echo "2. Restart services: $COMPOSE_CMD restart"
    echo "3. Copy the configuration below to your Claude Desktop config:"
else
    echo "1. Copy the configuration below to your Claude Desktop config:"
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
echo ""
echo "===== CLAUDE CODE CLI CONFIGURATION ====="
echo "# Add the MCP server via Claude Code CLI:"
echo "claude mcp add zen -s user -- docker exec -i zen-mcp-server python server.py"
echo ""
echo "# List your MCP servers to verify:"
echo "claude mcp list"
echo ""
echo "# Remove if needed:"
echo "claude mcp remove zen -s user"
echo "==========================================="
echo ""

echo "📁 Config file locations:"
echo "  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo '  Windows (WSL): /mnt/c/Users/USERNAME/AppData/Roaming/Claude/claude_desktop_config.json'
echo ""

echo "🔧 Useful commands:"
echo "  Start services:    $COMPOSE_CMD up -d"
echo "  Stop services:     $COMPOSE_CMD down"
echo "  View logs:         $COMPOSE_CMD logs -f"
echo "  Restart services:  $COMPOSE_CMD restart"
echo "  Service status:    $COMPOSE_CMD ps"
echo ""

echo "🗃️  Redis for conversation threading is automatically configured and running!"
echo "   All AI-to-AI conversations will persist between requests."