#!/bin/bash

# Zen MCP Server - Code Quality Checks
# This script runs all required linting and testing checks before committing changes.
# ALL checks must pass 100% for CI/CD to succeed.

set -e  # Exit on any error

echo "🔍 Running Code Quality Checks for Zen MCP Server"
echo "================================================="

# Determine Python command
if [[ -f ".zen_venv/bin/python" ]]; then
    PYTHON_CMD=".zen_venv/bin/python"
    PIP_CMD=".zen_venv/bin/pip"
    echo "✅ Using venv"
elif [[ -n "$VIRTUAL_ENV" ]]; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
    echo "✅ Using activated virtual environment: $VIRTUAL_ENV"
else
    echo "❌ No virtual environment found!"
    echo "Please run: ./run-server.sh first to set up the environment"
    exit 1
fi
echo ""

# Check and install dev dependencies if needed
echo "🔍 Checking development dependencies..."
DEV_DEPS_NEEDED=false

# Check each dev dependency
for tool in ruff black isort pytest; do
    # Check if tool exists in venv or in PATH
    if [[ -f ".zen_venv/bin/$tool" ]] || command -v $tool &> /dev/null; then
        continue
    else
        DEV_DEPS_NEEDED=true
        break
    fi
done

if [ "$DEV_DEPS_NEEDED" = true ]; then
    echo "📦 Installing development dependencies..."
    $PIP_CMD install -q -r requirements-dev.txt
    echo "✅ Development dependencies installed"
else
    echo "✅ Development dependencies already installed"
fi

# Tool path caching with associative arrays for performance optimization
declare -A _tool_cache
get_tool_path() {
    local tool="$1"
    if [[ -z "${_tool_cache[$tool]:-}" ]]; then
        if [[ -f ".zen_venv/bin/$tool" ]]; then
            _tool_cache[$tool]=".zen_venv/bin/$tool"
        else
            _tool_cache[$tool]="$tool"
        fi
    fi
    echo "${_tool_cache[$tool]}"
}

# Set tool paths using caching
RUFF=$(get_tool_path "ruff")
BLACK=$(get_tool_path "black")
ISORT=$(get_tool_path "isort")
PYTEST=$(get_tool_path "pytest")
echo ""

# Step 1: Linting and Formatting (Parallel Execution)
echo "📋 Step 1: Running Linting and Formatting Checks (Parallel)"
echo "------------------------------------------------------------"

echo "🔧 Running linting and formatting tools in parallel..."

# Run tools in parallel with background processes
echo "  🔧 Starting ruff fix..." && $RUFF check --fix --exclude test_simulation_files &
ruff_fix_pid=$!

echo "  🎨 Starting black formatting..." && $BLACK . --exclude="test_simulation_files/" &
black_pid=$!

echo "  📦 Starting isort..." && $ISORT . --skip-glob=".zen_venv/*" --skip-glob="test_simulation_files/*" &
isort_pid=$!

# Wait for all parallel operations and track failures
failed_jobs=()
echo "  ⏳ Waiting for parallel jobs to complete..."

wait $ruff_fix_pid || failed_jobs+=("ruff-fix")
wait $black_pid || failed_jobs+=("black")
wait $isort_pid || failed_jobs+=("isort")

# Check if any jobs failed
if [[ ${#failed_jobs[@]} -gt 0 ]]; then
    echo "❌ Failed jobs: ${failed_jobs[*]}"
    exit 1
fi

echo "✅ All parallel formatting jobs completed successfully!"

# Final verification (must run after all formatting is complete)
echo "✅ Verifying all linting passes..."
$RUFF check --exclude test_simulation_files

echo "✅ Step 1 Complete: All linting and formatting checks passed!"
echo ""

# Step 2: Unit Tests
echo "🧪 Step 2: Running Complete Unit Test Suite"
echo "---------------------------------------------"

echo "🏃 Running unit tests (excluding integration tests)..."
$PYTHON_CMD -m pytest tests/ -v -x -m "not integration"

echo "✅ Step 2 Complete: All unit tests passed!"
echo ""

# Step 3: Final Summary
echo "🎉 All Code Quality Checks Passed!"
echo "=================================="
echo "✅ Linting (ruff): PASSED"
echo "✅ Formatting (black): PASSED" 
echo "✅ Import sorting (isort): PASSED"
echo "✅ Unit tests: PASSED"
echo ""
echo "🚀 Your code is ready for commit and GitHub Actions!"
echo "💡 Remember to add simulator tests if you modified tools"