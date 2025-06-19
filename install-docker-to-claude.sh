#!/bin/bash

# Zen MCP Server - Docker Installation Script for Claude Code
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="zen-mcp-server"
IMAGE_TAG="latest"
MCP_NAME="zen-mcp-server"

echo -e "${BLUE}🚀 Zen MCP Server - Docker Installation for Claude Code${NC}"
echo "======================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if claude CLI is installed
if ! command -v claude &> /dev/null; then
    echo -e "${RED}❌ Claude CLI is not installed or not in PATH.${NC}"
    echo "Please ensure Claude Code is installed and the 'claude' command is available."
    exit 1
fi

# Check if .env file exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from example...${NC}"
    if [ -f "$SCRIPT_DIR/.env.docker.example" ]; then
        cp "$SCRIPT_DIR/.env.docker.example" "$SCRIPT_DIR/.env"
        echo -e "${GREEN}✅ Created .env file from example.${NC}"
        echo -e "${YELLOW}📝 Please edit $SCRIPT_DIR/.env with your API keys before continuing.${NC}"
        read -p "Press Enter after you've added your API keys to .env..."
    else
        echo -e "${RED}❌ No .env.docker.example file found.${NC}"
        exit 1
    fi
fi

# Validate at least one API key is configured
if ! grep -qE "^(GEMINI_API_KEY|OPENAI_API_KEY|XAI_API_KEY|OPENROUTER_API_KEY)=.+" "$SCRIPT_DIR/.env"; then
    echo -e "${RED}❌ No API keys found in .env file.${NC}"
    echo "Please add at least one API key to $SCRIPT_DIR/.env"
    exit 1
fi

echo -e "${GREEN}✅ Configuration validated${NC}"

# Build Docker image
echo -e "\n${YELLOW}🔨 Building Docker image...${NC}"
cd "$SCRIPT_DIR"

if ./docker-build.sh; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Failed to build Docker image${NC}"
    exit 1
fi

# Check if MCP server already exists
echo -e "\n${YELLOW}🔍 Checking existing MCP servers...${NC}"
if claude mcp list 2>/dev/null | grep -q "$MCP_NAME"; then
    echo -e "${YELLOW}⚠️  MCP server '$MCP_NAME' already exists. Removing...${NC}"
    claude mcp remove "$MCP_NAME"
    echo -e "${GREEN}✅ Removed existing MCP server${NC}"
fi

# Add MCP server to Claude Code
echo -e "\n${YELLOW}📦 Adding MCP server to Claude Code...${NC}"

# Create the command with proper escaping
MCP_COMMAND="docker run -i --rm --init --env-file ${SCRIPT_DIR}/.env -v ${SCRIPT_DIR}/logs:/app/logs --name zen-mcp-container ${IMAGE_NAME}:${IMAGE_TAG}"

# Add to Claude
if claude mcp add "$MCP_NAME" $MCP_COMMAND; then
    echo -e "${GREEN}✅ MCP server added successfully to Claude Code${NC}"
else
    echo -e "${RED}❌ Failed to add MCP server to Claude Code${NC}"
    exit 1
fi

# Verify installation
echo -e "\n${YELLOW}🔍 Verifying installation...${NC}"
if claude mcp list | grep -q "$MCP_NAME"; then
    echo -e "${GREEN}✅ MCP server is listed in Claude Code${NC}"
    
    # Display the configuration
    echo -e "\n${BLUE}📋 MCP Server Configuration:${NC}"
    claude mcp list | grep -A 5 "$MCP_NAME" || true
else
    echo -e "${RED}❌ MCP server not found in Claude Code${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"
echo -e "${GREEN}✅ Logs directory ready at: $SCRIPT_DIR/logs${NC}"

# Success message
echo -e "\n${GREEN}🎉 Installation Complete!${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""
echo "The Zen MCP Server has been successfully installed to Claude Code."
echo ""
echo -e "${YELLOW}Available tools:${NC}"
echo "  • thinkdeep - Deep thinking and problem-solving"
echo "  • codereview - Code review and analysis"
echo "  • debug - Debugging assistance"
echo "  • analyze - Code analysis"
echo "  • chat - General conversation"
echo "  • consensus - Multi-perspective analysis"
echo "  • planner - Project planning"
echo "  • precommit - Pre-commit checks"
echo "  • testgen - Test generation"
echo "  • refactor - Code refactoring"
echo "  • tracer - Code tracing"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "  tail -f $SCRIPT_DIR/logs/mcp_server.log"
echo ""
echo -e "${YELLOW}To remove the MCP server:${NC}"
echo "  claude mcp remove $MCP_NAME"
echo ""
echo -e "${GREEN}✨ You can now use Zen MCP tools in Claude Code!${NC}"