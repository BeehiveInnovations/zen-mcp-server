#!/bin/bash

# Gemini MCP Server Setup Script
# This script helps users set up the virtual environment and install dependencies

echo "🚀 Gemini MCP Server Setup"
echo "========================="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "Please install Python 3.10 or higher from https://python.org"
    exit 1
fi

# Display Python version
PYTHON_VERSION=$(python3 --version)
echo "✓ Found $PYTHON_VERSION"

# Check Python version is at least 3.10
PYTHON_VERSION_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_VERSION_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_VERSION_MAJOR" -lt 3 ] || ([ "$PYTHON_VERSION_MAJOR" -eq 3 ] && [ "$PYTHON_VERSION_MINOR" -lt 10 ]); then
    echo "❌ Error: Python 3.10 or higher is required (you have Python $PYTHON_VERSION_MAJOR.$PYTHON_VERSION_MINOR)"
    echo ""
    echo "The 'mcp' package requires Python 3.10 or newer."
    echo "Please upgrade Python from https://python.org"
    echo ""
    echo "On macOS with Homebrew:"
    echo "  brew install python@3.10"
    echo ""
    echo "On Ubuntu/Debian:"
    echo "  sudo apt update && sudo apt install python3.10 python3.10-venv"
    exit 1
fi

# Check if venv exists
if [ -d "venv" ]; then
    echo "✓ Virtual environment already exists"
else
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo "✓ Virtual environment created"
    else
        echo "❌ Error: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Get your Gemini API key from: https://makersuite.google.com/app/apikey"
    echo "2. Configure Claude Desktop with your API key (see README.md)"
    echo "3. Restart Claude Desktop"
    echo ""
    echo "Note: The virtual environment has been activated for this session."
    echo "The run_gemini.sh script will automatically activate it when needed."
else
    echo "❌ Error: Failed to install dependencies"
    echo "Please check the error messages above and try again."
    exit 1
fi