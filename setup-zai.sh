#!/bin/bash
set -euo pipefail

# ============================================================================
# Z.AI Integration Setup Script for Zen MCP Server
#
# This script sets up the Zen MCP Server with Z.AI GLM model support.
# Run this after cloning the zen-mcp-server repository.
# ============================================================================

# Colors for output
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Print colored output
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }

echo "════════════════════════════════════════════════════════════════"
echo "  Z.AI Integration Setup for Zen MCP Server"
echo "════════════════════════════════════════════════════════════════"
echo

# Check if we're in the right directory
if [[ ! -f "server.py" ]] || [[ ! -d "providers" ]]; then
    print_error "This script must be run from the zen-mcp-server directory"
    echo "Please run: cd zen-mcp-server && ./setup-zai.sh"
    exit 1
fi

# Step 1: Check for Z.AI API Key
print_info "Step 1: Checking Z.AI API Key configuration..."
ZAI_API_KEY=""

if [[ -f ".env" ]]; then
    # Try to extract existing key from .env
    ZAI_API_KEY=$(grep "^ZAI_API_KEY=" .env | cut -d'=' -f2 || echo "")
fi

if [[ -z "$ZAI_API_KEY" ]] || [[ "$ZAI_API_KEY" == "your_zai_api_key_here" ]]; then
    echo
    print_warning "Z.AI API Key not found or not configured"
    echo
    echo "To get your Z.AI API Key:"
    echo "  1. Visit: https://z.ai/manage-apikey/apikey-list"
    echo "  2. Sign in or create an account"
    echo "  3. Generate an API key"
    echo "  4. Copy the key (format: xxxxxxxx.yyyyyyyy)"
    echo
    read -p "Enter your Z.AI API Key: " ZAI_API_KEY

    if [[ -z "$ZAI_API_KEY" ]]; then
        print_error "Z.AI API Key is required. Exiting."
        exit 1
    fi
fi

print_success "Z.AI API Key configured"

# Step 2: Run the main setup script
print_info "Step 2: Running main Zen MCP Server setup..."
echo

if [[ ! -x "run-server.sh" ]]; then
    chmod +x run-server.sh
fi

# Run setup but skip the interactive parts by setting environment variable
export ZAI_API_KEY="$ZAI_API_KEY"
./run-server.sh

# Step 3: Verify Z.AI provider is installed
print_info "Step 3: Verifying Z.AI provider installation..."

if [[ -f "providers/zai.py" ]]; then
    # Check if it has the correct endpoint
    if grep -q "api/coding/paas/v4" providers/zai.py; then
        print_success "Z.AI provider correctly configured with Coding API endpoint"
    else
        print_warning "Z.AI provider found but may have wrong endpoint"
        echo "Expected endpoint: https://api.z.ai/api/coding/paas/v4"
    fi
else
    print_error "Z.AI provider not found at providers/zai.py"
    exit 1
fi

# Step 4: Update .env file with Z.AI key if needed
print_info "Step 4: Updating .env file..."

if [[ ! -f ".env" ]]; then
    print_error ".env file not found. The setup script should have created it."
    exit 1
fi

# Check if ZAI_API_KEY is already in .env
if grep -q "^ZAI_API_KEY=" .env; then
    # Update existing key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^ZAI_API_KEY=.*|ZAI_API_KEY=$ZAI_API_KEY|" .env
    else
        sed -i "s|^ZAI_API_KEY=.*|ZAI_API_KEY=$ZAI_API_KEY|" .env
    fi
    print_success "Updated Z.AI API Key in .env"
else
    # Add new key
    echo "" >> .env
    echo "# Z.AI API Configuration" >> .env
    echo "ZAI_API_KEY=$ZAI_API_KEY" >> .env
    print_success "Added Z.AI API Key to .env"
fi

# Step 5: Configure Claude Code MCP
print_info "Step 5: Configuring Claude Code MCP integration..."

# Get the absolute path to the Python virtual environment
VENV_PYTHON="$(pwd)/.zen_venv/bin/python"
SERVER_PATH="$(pwd)/server.py"

if [[ ! -f "$VENV_PYTHON" ]]; then
    print_error "Python virtual environment not found at $VENV_PYTHON"
    exit 1
fi

# Load all API keys from .env for MCP configuration
source .env

# Remove any existing zen MCP configuration
claude mcp remove zen -s local 2>/dev/null || true

# Add zen MCP with all environment variables
print_info "Adding zen MCP server to Claude Code..."
claude mcp add zen "$VENV_PYTHON" "$SERVER_PATH" \
    --env ZAI_API_KEY="$ZAI_API_KEY" \
    --env LOG_LEVEL=INFO \
    ${GEMINI_API_KEY:+--env GEMINI_API_KEY="$GEMINI_API_KEY"} \
    ${OPENAI_API_KEY:+--env OPENAI_API_KEY="$OPENAI_API_KEY"} \
    ${XAI_API_KEY:+--env XAI_API_KEY="$XAI_API_KEY"} \
    2>&1

if [[ $? -eq 0 ]]; then
    print_success "Claude Code MCP configured successfully"
else
    print_error "Failed to configure Claude Code MCP"
    exit 1
fi

# Step 6: Test the installation
echo
print_info "Step 6: Testing Z.AI integration..."
echo

# Test with curl
TEST_RESPONSE=$(curl -s -X POST 'https://api.z.ai/api/coding/paas/v4/chat/completions' \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $ZAI_API_KEY" \
    -d '{"model":"glm-4.6","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}')

if echo "$TEST_RESPONSE" | grep -q '"choices"'; then
    print_success "Z.AI API connection successful!"
else
    print_warning "Z.AI API test returned unexpected response"
    echo "Response: $TEST_RESPONSE"
    echo
    print_info "This might be a temporary issue. Try testing in Claude Code."
fi

# Final instructions
echo
echo "════════════════════════════════════════════════════════════════"
print_success "Z.AI Integration Setup Complete!"
echo "════════════════════════════════════════════════════════════════"
echo
echo "Next steps:"
echo "  1. Restart Claude Code (important - exit and restart)"
echo "  2. In Claude Code, run: zen chat with glm"
echo "  3. The GLM-4.6 model should now respond"
echo
echo "Available model aliases:"
echo "  • glm, glm-4, glm-4.6, glm4.6 → GLM-4.6"
echo
echo "Example commands:"
echo "  • zen chat with glm"
echo "  • zen thinkdeep with glm"
echo "  • zen codereview with glm"
echo
echo "For troubleshooting, check:"
echo "  • Logs: tail -f logs/mcp_server.log"
echo "  • MCP status: claude mcp list"
echo "  • README-ZAI.md for detailed documentation"
echo
print_info "Remember: You MUST restart Claude Code for changes to take effect!"
echo
