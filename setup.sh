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