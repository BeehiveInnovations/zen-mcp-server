#!/bin/bash

# Zen MCP Server - Docker Uninstallation Script for Claude Code
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MCP_NAME="zen-mcp-server"
CONTAINER_NAME="zen-mcp-container"

echo -e "${BLUE}🗑️  Zen MCP Server - Docker Uninstallation${NC}"
echo "=========================================="

# Check if claude CLI is installed
if ! command -v claude &> /dev/null; then
    echo -e "${RED}❌ Claude CLI is not installed or not in PATH.${NC}"
    exit 1
fi

# Check if MCP server exists
echo -e "${YELLOW}🔍 Checking for MCP server...${NC}"

# Check using 'claude mcp get' since 'list' doesn't show project servers
if claude mcp get "$MCP_NAME" 2>&1 | grep -q "$MCP_NAME"; then
    echo -e "${YELLOW}🗑️  Removing MCP server from Claude Code...${NC}"
    if claude mcp remove "$MCP_NAME" -s project; then
        echo -e "${GREEN}✅ MCP server removed from Claude Code${NC}"
    else
        echo -e "${RED}❌ Failed to remove MCP server${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  MCP server '$MCP_NAME' not found in Claude Code.${NC}"
fi

# Remove .mcp.json file if it exists
if [ -f ".mcp.json" ]; then
    echo -e "${YELLOW}🗑️  Removing .mcp.json configuration file...${NC}"
    rm -f .mcp.json
    echo -e "${GREEN}✅ Configuration file removed${NC}"
fi

# Stop any running containers
echo -e "\n${YELLOW}🐳 Checking for running Docker containers...${NC}"
if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    echo -e "${YELLOW}Stopping running container...${NC}"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    echo -e "${GREEN}✅ Container stopped${NC}"
fi

# Remove any stopped containers with the same name
if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
    echo -e "${YELLOW}Removing stopped container...${NC}"
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    echo -e "${GREEN}✅ Container removed${NC}"
fi

echo -e "\n${GREEN}✅ Uninstallation complete!${NC}"
echo ""
echo "The Zen MCP Server has been removed from Claude Code."
echo ""
echo -e "${YELLOW}Note:${NC}"
echo "  • Docker image 'zen-mcp-server:latest' is still available"
echo "  • Your .env file and logs are preserved"
echo ""
echo -e "${YELLOW}To remove the Docker image:${NC}"
echo "  docker rmi zen-mcp-server:latest"
echo ""
echo -e "${YELLOW}To reinstall:${NC}"
echo "  ./install-docker-to-claude.sh"