#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if virtual environment exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate"
    PYTHON_EXEC="python"
else
    # Fallback to system Python if venv doesn't exist
    echo "Warning: Virtual environment not found at $SCRIPT_DIR/venv" >&2
    echo "Using system Python. Make sure dependencies are installed." >&2
    PYTHON_EXEC="python3"
fi

# Change to script directory to ensure proper working directory
cd "$SCRIPT_DIR"

# Run the server
exec "$PYTHON_EXEC" "$SCRIPT_DIR/server.py"