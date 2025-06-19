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
    echo -e "${YELLOW}⚠️  No .env file found. Running setup...${NC}"
    echo ""
    # Run the main setup script to create .env
    if [ -f "$SCRIPT_DIR/run-server.sh" ]; then
        echo "Running run-server.sh to create environment configuration..."
        "$SCRIPT_DIR/run-server.sh" --env-only 2>/dev/null || "$SCRIPT_DIR/run-server.sh"
        
        if [ ! -f "$SCRIPT_DIR/.env" ]; then
            echo -e "${RED}❌ Failed to create .env file.${NC}"
            echo "Please run ./run-server.sh first to set up the environment."
            exit 1
        fi
    else
        echo -e "${RED}❌ run-server.sh not found.${NC}"
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

# Create .mcp.json for project-level MCP configuration
echo -e "\n${YELLOW}📦 Configuring MCP server for Claude Code...${NC}"

# Create the MCP configuration
cat > "$SCRIPT_DIR/.mcp.json" << EOF
{
  "mcpServers": {
    "$MCP_NAME": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--init",
        "--env-file",
        "${SCRIPT_DIR}/.env",
        "-v",
        "${SCRIPT_DIR}/.env:/app/.env:ro",
        "-v",
        "${SCRIPT_DIR}/logs:/app/logs",
        "--name",
        "zen-mcp-container",
        "${IMAGE_NAME}:${IMAGE_TAG}"
      ],
      "transport": "stdio"
    }
  }
}
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Created .mcp.json configuration file${NC}"
else
    echo -e "${RED}❌ Failed to create MCP configuration${NC}"
    exit 1
fi

# Verify installation
echo -e "\n${YELLOW}🔍 Verifying installation...${NC}"

# Check if the server is configured using 'claude mcp get'
if claude mcp get "$MCP_NAME" 2>&1 | grep -q "$MCP_NAME"; then
    echo -e "${GREEN}✅ MCP server is configured in Claude Code${NC}"
    echo -e "${BLUE}📋 Configuration:${NC}"
    claude mcp get "$MCP_NAME"
else
    echo -e "${YELLOW}⚠️  Could not verify MCP server configuration${NC}"
    echo -e "${YELLOW}   The .mcp.json file has been created in the project directory${NC}"
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
echo -e "${RED}IMPORTANT:${NC} You may need to restart Claude Code for the changes to take effect."
echo ""
echo -e "${YELLOW}To verify after restart:${NC}"
echo "  claude mcp list"
echo "  # or in Claude Code, run: /mcp"
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
echo -e "${YELLOW}To test the Docker container manually:${NC}"
echo "  docker run -it --rm --env-file .env -v ./.env:/app/.env:ro -v ./logs:/app/logs zen-mcp-server:latest"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "  tail -f $SCRIPT_DIR/logs/mcp_server.log"
echo ""
echo -e "${YELLOW}To remove the MCP server:${NC}"
echo "  claude mcp remove $MCP_NAME"
echo ""
echo -e "${GREEN}✨ You can now use Zen MCP tools in Claude Code!${NC}"