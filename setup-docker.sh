#!/bin/bash

# Exit on any error, undefined variables, and pipe failures
set -euo pipefail

# Modern Docker setup script for Gemini MCP Server with Redis
# This script sets up the complete Docker environment including Redis for conversation threading

echo "🚀 Setting up Gemini MCP Server with Docker Compose..."
echo ""

# Get the current working directory (absolute path)
CURRENT_DIR=$(pwd)

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists! Updating if needed..."
    echo ""
else
    # Check if GEMINI_API_KEY is already set in environment
    if [ -n "$GEMINI_API_KEY" ]; then
        API_KEY_VALUE="$GEMINI_API_KEY"
        echo "✅ Found existing GEMINI_API_KEY in environment"
    else
        API_KEY_VALUE="your-gemini-api-key-here"
    fi
    
    # Create the .env file
    cat > .env << EOF
# Gemini MCP Server Docker Environment Configuration
# Generated on $(date)

# Your Gemini API key (get one from https://makersuite.google.com/app/apikey)
# IMPORTANT: Replace this with your actual API key
GEMINI_API_KEY=$API_KEY_VALUE

# Redis configuration (automatically set for Docker Compose)
REDIS_URL=redis://redis:6379/0

# Workspace root - host path that maps to /workspace in container
# This should be the host directory path that contains all files Claude might reference
# We use $HOME (not $PWD) because Claude needs access to ANY absolute file path,
# not just files within the current project directory. Additionally, Claude Code
# could be running from multiple locations at the same time.
WORKSPACE_ROOT=$HOME
EOF
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

echo "🛠️  Building and starting services..."
echo ""

# Stop and remove existing containers
echo "  - Stopping existing containers..."
$COMPOSE_CMD down --remove-orphans >/dev/null 2>&1 || true

# Clean up any old containers with different naming patterns
OLD_CONTAINERS_FOUND=false

# Check for old Gemini MCP container
if docker ps -a --format "{{.Names}}" | grep -q "^gemini-mcp-server-gemini-mcp-1$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old container: gemini-mcp-server-gemini-mcp-1"
    docker stop gemini-mcp-server-gemini-mcp-1 >/dev/null 2>&1 || true
    docker rm gemini-mcp-server-gemini-mcp-1 >/dev/null 2>&1 || true
fi

# Check for old Redis container
if docker ps -a --format "{{.Names}}" | grep -q "^gemini-mcp-server-redis-1$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old container: gemini-mcp-server-redis-1"
    docker stop gemini-mcp-server-redis-1 >/dev/null 2>&1 || true
    docker rm gemini-mcp-server-redis-1 >/dev/null 2>&1 || true
fi

# Check for old image
if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^gemini-mcp-server-gemini-mcp:latest$" 2>/dev/null || false; then
    OLD_CONTAINERS_FOUND=true
    echo "  - Cleaning up old image: gemini-mcp-server-gemini-mcp:latest"
    docker rmi gemini-mcp-server-gemini-mcp:latest >/dev/null 2>&1 || true
fi

# Only show cleanup messages if something was actually cleaned up

# Build and start services
echo "  - Building Gemini MCP Server image..."
if $COMPOSE_CMD build --no-cache >/dev/null 2>&1; then
    echo "✅ Docker image built successfully!"
else
    echo "❌ Failed to build Docker image. Run '$COMPOSE_CMD build' manually to see errors."
    exit 1
fi

echo "  - Starting Redis and MCP services..."
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
if grep -q "your-gemini-api-key-here" .env 2>/dev/null || false; then
    echo "1. Edit .env and replace 'your-gemini-api-key-here' with your actual Gemini API key"
    echo "2. Restart services: $COMPOSE_CMD restart"
    echo "3. Copy the configuration below to your Claude Desktop config:"
else
    echo "1. Copy the configuration below to your Claude Desktop config:"
fi

echo ""
echo "===== CLAUDE DESKTOP CONFIGURATION ====="
echo "{"
echo "  \"mcpServers\": {"
echo "    \"gemini\": {"
echo "      \"command\": \"docker\","
echo "      \"args\": ["
echo "        \"exec\","
echo "        \"-i\","
echo "        \"gemini-mcp-server\","
echo "        \"python\","
echo "        \"server.py\""
echo "      ]"
echo "    }"
echo "  }"
echo "}"
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