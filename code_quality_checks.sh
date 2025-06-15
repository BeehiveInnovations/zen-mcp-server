#!/bin/bash

# Zen MCP Server - Code Quality Checks
# This script runs all required linting and testing checks before committing changes.
# ALL checks must pass 100% for CI/CD to succeed.

set -e  # Exit on any error

echo "🔍 Running Code Quality Checks for Zen MCP Server"
echo "================================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ Virtual environment not activated!"
    echo "Please run: source venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment detected: $VIRTUAL_ENV"
echo ""

# Step 1: Linting and Formatting
echo "📋 Step 1: Running Linting and Formatting Checks"
echo "--------------------------------------------------"

echo "🔧 Running ruff linting with auto-fix..."
ruff check --fix

echo "🎨 Running black code formatting..."
black .

echo "📦 Running import sorting with isort..."
isort .

echo "✅ Verifying all linting passes..."
ruff check

echo "✅ Step 1 Complete: All linting and formatting checks passed!"
echo ""

# Step 2: Unit Tests
echo "🧪 Step 2: Running Complete Unit Test Suite"
echo "---------------------------------------------"

echo "🏃 Running all 361 unit tests..."
python -m pytest tests/ -v

echo "✅ Step 2 Complete: All unit tests passed!"
echo ""

# Step 3: Final Summary
echo "🎉 All Code Quality Checks Passed!"
echo "=================================="
echo "✅ Linting (ruff): PASSED"
echo "✅ Formatting (black): PASSED" 
echo "✅ Import sorting (isort): PASSED"
echo "✅ Unit tests (361 tests): PASSED"
echo ""
echo "🚀 Your code is ready for commit and GitHub Actions!"
echo "💡 Remember to add simulator tests if you modified tools"