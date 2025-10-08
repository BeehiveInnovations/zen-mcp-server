#!/bin/bash

# A/B Testing Control Script for Zen MCP Token Optimization
# This script allows easy switching between original and optimized modes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set Python command globally
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    PYTHON_CMD=false
fi

# Safety checks
check_prerequisites() {
    local errors=0
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop."
        ((errors++))
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose is not installed."
        ((errors++))
    fi
    
    # Check if required files exist
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found in current directory."
        ((errors++))
    fi
    
    if [ ! -f "analyze_telemetry.py" ]; then
        print_warning "analyze_telemetry.py not found. Telemetry analysis will not be available."
    fi
    
    # Check if Python is available for telemetry analysis
    if [ "$PYTHON_CMD" = "false" ]; then
        print_warning "Python not found. Telemetry analysis will be limited."
    fi
    
    if [ $errors -gt 0 ]; then
        echo ""
        print_error "Please fix the errors above before continuing."
        exit 1
    fi
}

# Run safety checks at startup
check_prerequisites

# Function to print colored output
print_status() {
    echo -e "${GREEN}[STATUS]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show current configuration
show_status() {
    print_status "Current Token Optimization Configuration:"
    echo ""
    
    # Read current settings from .env file or use defaults
    if [ -f .env ]; then
        source .env
    fi
    
    CURRENT_OPT=${ZEN_TOKEN_OPTIMIZATION:-enabled}
    CURRENT_MODE=${ZEN_OPTIMIZATION_MODE:-two_stage}
    CURRENT_TELEMETRY=${ZEN_TOKEN_TELEMETRY:-true}
    CURRENT_VERSION=${ZEN_OPTIMIZATION_VERSION:-v5.12.0-alpha}
    
    echo "  Token Optimization: ${CURRENT_OPT}"
    echo "  Mode: ${CURRENT_MODE}"
    echo "  Telemetry: ${CURRENT_TELEMETRY}"
    echo "  Version: ${CURRENT_VERSION}"
    echo ""
    
    if [ "$CURRENT_OPT" = "enabled" ]; then
        print_info "🚀 Token optimization is ACTIVE (95% reduction)"
    else
        print_info "📦 Using ORIGINAL tool registration (43k tokens)"
    fi
}

# Function to enable optimization
enable_optimization() {
    print_status "Enabling token optimization..."
    
    # Update or create .env file
    if [ -f .env ]; then
        # Remove existing settings
        grep -v "^ZEN_TOKEN_OPTIMIZATION=" .env > .env.tmp || true
        grep -v "^ZEN_OPTIMIZATION_MODE=" .env.tmp > .env.tmp2 || true
        grep -v "^ZEN_TOKEN_TELEMETRY=" .env.tmp2 > .env.tmp3 || true
        grep -v "^ZEN_OPTIMIZATION_VERSION=" .env.tmp3 > .env || true
        rm -f .env.tmp .env.tmp2 .env.tmp3
    fi
    
    # Add new settings
    echo "ZEN_TOKEN_OPTIMIZATION=enabled" >> .env
    echo "ZEN_OPTIMIZATION_MODE=two_stage" >> .env
    echo "ZEN_TOKEN_TELEMETRY=true" >> .env
    echo "ZEN_OPTIMIZATION_VERSION=v5.12.0-alpha" >> .env
    
    print_info "✅ Token optimization enabled"
    print_info "   Expected token usage: ~2k (95% reduction)"
}

# Function to disable optimization
disable_optimization() {
    print_status "Disabling token optimization..."
    
    # Update or create .env file
    if [ -f .env ]; then
        # Remove existing settings
        grep -v "^ZEN_TOKEN_OPTIMIZATION=" .env > .env.tmp || true
        grep -v "^ZEN_OPTIMIZATION_MODE=" .env.tmp > .env.tmp2 || true
        grep -v "^ZEN_TOKEN_TELEMETRY=" .env.tmp2 > .env.tmp3 || true
        grep -v "^ZEN_OPTIMIZATION_VERSION=" .env.tmp3 > .env || true
        rm -f .env.tmp .env.tmp2 .env.tmp3
    fi
    
    # Add new settings
    echo "ZEN_TOKEN_OPTIMIZATION=disabled" >> .env
    echo "ZEN_OPTIMIZATION_MODE=two_stage" >> .env
    echo "ZEN_TOKEN_TELEMETRY=true" >> .env
    echo "ZEN_OPTIMIZATION_VERSION=v5.11.0-baseline" >> .env
    
    print_info "✅ Token optimization disabled"
    print_info "   Expected token usage: ~43k (original)"
}

# Function to restart Docker container
restart_container() {
    print_status "Restarting Docker container..."
    
    # Backup current logs before restart
    if docker-compose ps | grep -q "zen-mcp"; then
        print_info "Saving current logs..."
        docker-compose logs zen-mcp > "logs_backup_$(date +%Y%m%d_%H%M%S).txt" 2>&1 || true
    fi
    
    # Graceful shutdown with timeout
    docker-compose down --timeout 30 || {
        print_warning "Graceful shutdown failed, forcing..."
        docker-compose down --force
    }
    
    # Rebuild and start
    docker-compose up -d --build || {
        print_error "Failed to start container. Check logs with: docker-compose logs"
        return 1
    }
    
    # Wait for container to be healthy
    print_info "Waiting for container to be ready..."
    sleep 5
    
    if docker-compose ps | grep -q "zen-mcp.*Up"; then
        print_info "✅ Container restarted with new configuration"
    else
        print_error "Container may not have started correctly. Check: docker-compose ps"
        return 1
    fi
}

# Function to view telemetry
view_telemetry() {
    print_status "Extracting telemetry data..."
    
    # Create telemetry directory
    mkdir -p ./telemetry_export
    
    # Copy telemetry from Docker volume
    docker run --rm -v zen-telemetry:/data -v $(pwd)/telemetry_export:/export alpine \
        sh -c "cp -r /data/* /export/ 2>/dev/null || echo 'No telemetry data yet'"
    
    if [ -f ./telemetry_export/token_telemetry.jsonl ]; then
        print_info "Telemetry data exported to ./telemetry_export/"
        echo ""
        echo "Recent telemetry entries:"
        if [ "$PYTHON_CMD" != "false" ]; then
            tail -5 ./telemetry_export/token_telemetry.jsonl | $PYTHON_CMD -m json.tool
        else
            tail -5 ./telemetry_export/token_telemetry.jsonl
        fi
    else
        print_warning "No telemetry data found yet"
    fi
}

# Function to run A/B test
run_ab_test() {
    print_status "Starting A/B Test Sequence..."
    echo ""
    print_info "This will alternate between optimized and original modes"
    print_info "Each mode will run for the specified duration"
    echo ""
    
    read -p "Duration per mode (minutes, default 30): " DURATION
    DURATION=${DURATION:-30}
    
    read -p "Number of cycles (default 3): " CYCLES
    CYCLES=${CYCLES:-3}
    
    print_info "Running $CYCLES cycles of $DURATION minutes each"
    echo ""
    
    for i in $(seq 1 $CYCLES); do
        print_status "Cycle $i/$CYCLES"
        
        # Run optimized mode
        print_info "Enabling optimized mode..."
        enable_optimization
        restart_container
        print_info "Running optimized mode for $DURATION minutes..."
        sleep $((DURATION * 60))
        
        # Run original mode
        print_info "Enabling original mode..."
        disable_optimization
        restart_container
        print_info "Running original mode for $DURATION minutes..."
        sleep $((DURATION * 60))
    done
    
    print_status "A/B test complete!"
    view_telemetry
}

# Main menu
show_menu() {
    echo ""
    echo "================================"
    echo "  Zen MCP Token Optimization"
    echo "      A/B Testing Control"
    echo "================================"
    echo ""
    echo "1) Show current status"
    echo "2) Enable optimization (2k tokens)"
    echo "3) Disable optimization (43k tokens)"
    echo "4) Restart container"
    echo "5) View telemetry data"
    echo "6) Run automated A/B test"
    echo "7) Exit"
    echo ""
}

# Main loop
while true; do
    show_menu
    read -p "Select option: " choice
    
    case $choice in
        1)
            show_status
            ;;
        2)
            enable_optimization
            show_status
            print_warning "Remember to restart the container for changes to take effect"
            ;;
        3)
            disable_optimization
            show_status
            print_warning "Remember to restart the container for changes to take effect"
            ;;
        4)
            restart_container
            show_status
            ;;
        5)
            view_telemetry
            ;;
        6)
            run_ab_test
            ;;
        7)
            print_info "Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid option"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
done