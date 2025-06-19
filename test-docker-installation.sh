#!/bin/bash

# Test script for Zen MCP Server Docker installation
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🧪 Testing Zen MCP Server Docker Installation${NC}"
echo "============================================="

# Test 1: Check Docker image exists
echo -e "\n${YELLOW}Test 1: Docker Image${NC}"
if docker images zen-mcp-server:latest --format "{{.Repository}}" | grep -q "zen-mcp-server"; then
    echo -e "${GREEN}✅ Docker image exists${NC}"
    docker images zen-mcp-server:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
else
    echo -e "${RED}❌ Docker image not found${NC}"
    exit 1
fi

# Test 2: Check environment file
echo -e "\n${YELLOW}Test 2: Environment Configuration${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file exists${NC}"
    if grep -qE "^(GEMINI_API_KEY|OPENAI_API_KEY|XAI_API_KEY|OPENROUTER_API_KEY)=.+" ".env"; then
        echo -e "${GREEN}✅ API keys configured${NC}"
    else
        echo -e "${RED}❌ No API keys found in .env${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Test 3: Test container startup
echo -e "\n${YELLOW}Test 3: Container Startup${NC}"
if docker run --rm --env-file .env zen-mcp-server:latest python -c "print('Container starts successfully')" 2>/dev/null; then
    echo -e "${GREEN}✅ Container runs successfully${NC}"
else
    echo -e "${RED}❌ Container failed to start${NC}"
    exit 1
fi

# Test 4: Test MCP server initialization
echo -e "\n${YELLOW}Test 4: MCP Server Module${NC}"
if docker run --rm --env-file .env zen-mcp-server:latest python -c "import server; print('MCP server module loads')" 2>/dev/null; then
    echo -e "${GREEN}✅ MCP server module loads correctly${NC}"
else
    echo -e "${RED}❌ Failed to load MCP server module${NC}"
    exit 1
fi

# Test 5: Check MCP configuration
echo -e "\n${YELLOW}Test 5: MCP Configuration${NC}"
if command -v claude &> /dev/null; then
    echo -e "${GREEN}✅ Claude CLI is installed${NC}"
    echo "  Run 'claude mcp list' after restarting Claude to verify installation"
else
    echo -e "${YELLOW}⚠️  Claude CLI not found - cannot verify MCP configuration${NC}"
fi

# Summary
echo -e "\n${GREEN}🎉 All tests passed!${NC}"
echo ""
echo "The Zen MCP Server Docker installation is working correctly."
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart Claude Code if you haven't already"
echo "2. Run '/mcp' in Claude to see available MCP servers"
echo "3. Use tools like 'thinkdeep', 'codereview', etc."
echo ""
echo -e "${YELLOW}To manually test the container:${NC}"
echo "  docker run -it --rm --env-file .env -v ./logs:/app/logs zen-mcp-server:latest"