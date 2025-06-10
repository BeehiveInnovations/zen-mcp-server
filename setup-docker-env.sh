#!/bin/bash

# Helper script to set up .env file for Docker usage

echo "Setting up .env file for Gemini MCP Server Docker..."

# Get the current working directory (absolute path)
CURRENT_DIR=$(pwd)

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists! Skipping creation."
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
EOF
    echo "✅ Created .env file"
    echo ""
fi
# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
else
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        echo "⚠️  Docker daemon is not running. Please start Docker."
    else
        # Clean up and build Docker image
        echo ""
        echo "🐳 Building Docker image..."
        
        # Stop running containers
        RUNNING_CONTAINERS=$(docker ps -q --filter ancestor=gemini-mcp-server 2>/dev/null)
        if [ ! -z "$RUNNING_CONTAINERS" ]; then
            echo "  - Stopping running containers..."
            docker stop $RUNNING_CONTAINERS >/dev/null 2>&1
        fi
        
        # Remove containers
        ALL_CONTAINERS=$(docker ps -aq --filter ancestor=gemini-mcp-server 2>/dev/null)
        if [ ! -z "$ALL_CONTAINERS" ]; then
            echo "  - Removing old containers..."
            docker rm $ALL_CONTAINERS >/dev/null 2>&1
        fi
        
        # Remove existing image
        if docker images | grep -q "gemini-mcp-server"; then
            echo "  - Removing old image..."
            docker rmi gemini-mcp-server:latest >/dev/null 2>&1
        fi
        
        # Build fresh image
        echo "  - Building fresh image with --no-cache..."
        if docker build -t gemini-mcp-server:latest . --no-cache >/dev/null 2>&1; then
            echo "✅ Docker image built successfully!"
        else
            echo "❌ Failed to build Docker image. Run 'docker build -t gemini-mcp-server:latest .' manually to see errors."
        fi
        echo ""
    fi
fi

echo "Next steps:"
if [ "$API_KEY_VALUE" = "your-gemini-api-key-here" ]; then
    echo "1. Edit .env and replace 'your-gemini-api-key-here' with your actual Gemini API key"
    echo "2. Copy this configuration to your Claude Desktop config:"
else
    echo "1. Copy this configuration to your Claude Desktop config:"
fi
echo ""
echo "===== COPY BELOW THIS LINE ====="
echo "{"
echo "  \"mcpServers\": {"
echo "    \"gemini\": {"
echo "      \"command\": \"docker\","
echo "      \"args\": ["
echo "        \"run\","
echo "        \"--rm\","
echo "        \"-i\","
echo "        \"--env-file\", \"$CURRENT_DIR/.env\","
echo "        \"-e\", \"WORKSPACE_ROOT=$HOME\","
echo "        \"-v\", \"$HOME:/workspace:ro\","
echo "        \"gemini-mcp-server:latest\""
echo "      ]"
echo "    }"
echo "  }"
echo "}"
echo "===== COPY ABOVE THIS LINE ====="
echo ""
echo "Config file location:"
echo "  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "  Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
echo ""
echo "Note: This configuration mounts your home directory ($HOME)."
echo "Docker can access any file within your home directory."
echo ""
echo "If you want to restrict access to a specific directory:"
echo "Change both the mount (-v) and WORKSPACE_ROOT to match:"
echo "Example: -v \"$CURRENT_DIR:/workspace:ro\" and WORKSPACE_ROOT=$CURRENT_DIR"
echo "The container will automatically use /workspace as the sandbox boundary."