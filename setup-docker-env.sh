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
    # Create the .env file
    cat > .env << EOF
# Gemini MCP Server Docker Environment Configuration
# Generated on $(date)

# The absolute path to your project root on the host machine
# This should be the directory containing your code that you want to analyze
WORKSPACE_ROOT=$CURRENT_DIR

# Your Gemini API key (get one from https://makersuite.google.com/app/apikey)
# IMPORTANT: Replace this with your actual API key
GEMINI_API_KEY=your-gemini-api-key-here

# Optional: Set logging level (DEBUG, INFO, WARNING, ERROR)
# LOG_LEVEL=INFO
EOF
    echo "✅ Created .env file"
    echo ""
fi
echo "Next steps:"
echo "1. Edit .env and replace 'your-gemini-api-key-here' with your actual Gemini API key"
echo "2. Run 'docker build -t gemini-mcp-server .' to build the Docker image"
echo "3. Copy this configuration to your Claude Desktop config:"
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
echo "        \"-v\", \"$CURRENT_DIR:/workspace:ro\","
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
echo "Note: The configuration above mounts the current directory ($CURRENT_DIR)"
echo "as the workspace. You can change this path to any project directory you want to analyze."