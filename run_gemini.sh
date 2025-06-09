#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Virtual environment not found. Running setup..." >&2
    
    # Check if setup.sh exists and is executable
    if [ -f "$SCRIPT_DIR/setup.sh" ]; then
        if [ ! -x "$SCRIPT_DIR/setup.sh" ]; then
            chmod +x "$SCRIPT_DIR/setup.sh"
        fi
        
        # Run setup script
        "$SCRIPT_DIR/setup.sh" >&2
        
        # Check if setup was successful
        if [ $? -ne 0 ]; then
            echo "Setup failed. Please run setup.sh manually to see the error." >&2
            exit 1
        fi
    else
        echo "Error: setup.sh not found. Please ensure you have the complete repository." >&2
        exit 1
    fi
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory to ensure proper working directory
cd "$SCRIPT_DIR"

# Run the server
exec python "$SCRIPT_DIR/server.py"