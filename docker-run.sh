#!/bin/bash

# Zen MCP Server Docker Run Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="zen-mcp-server"
IMAGE_TAG="latest"
CONTAINER_NAME="zen-mcp-container"

echo -e "${GREEN}🚀 Zen MCP Server Docker Runner${NC}"
echo "================================="

# Parse command line arguments
FOLLOW_LOGS=false
USE_COMPOSE=false
DETACHED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW_LOGS=true
            shift
            ;;
        -c|--compose)
            USE_COMPOSE=true
            shift
            ;;
        -d|--detach)
            DETACHED=true
            shift
            ;;
        --stop)
            echo -e "${YELLOW}Stopping Zen MCP Server...${NC}"
            if [ "$USE_COMPOSE" = true ]; then
                docker-compose down
            else
                docker stop $CONTAINER_NAME 2>/dev/null || true
            fi
            echo -e "${GREEN}✅ Stopped${NC}"
            exit 0
            ;;
        --logs)
            if [ "$USE_COMPOSE" = true ]; then
                docker-compose logs -f zen-mcp-server
            else
                docker logs -f $CONTAINER_NAME
            fi
            exit 0
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -f, --follow    Follow logs after starting"
            echo "  -c, --compose   Use docker-compose"
            echo "  -d, --detach    Run in detached mode"
            echo "  --stop          Stop the running container"
            echo "  --logs          Show logs from running container"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from example...${NC}"
    if [ -f ".env.docker.example" ]; then
        cp .env.docker.example .env
        echo -e "${GREEN}✅ Created .env file. Please edit it with your API keys.${NC}"
        echo -e "${YELLOW}   Edit .env and run this script again.${NC}"
        exit 1
    else
        echo -e "${RED}❌ No .env.docker.example file found.${NC}"
        exit 1
    fi
fi

# Check if image exists
if ! docker images | grep -q "$IMAGE_NAME.*$IMAGE_TAG"; then
    echo -e "${YELLOW}⚠️  Docker image not found. Building...${NC}"
    ./docker-build.sh
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Build failed!${NC}"
        exit 1
    fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the container
if [ "$USE_COMPOSE" = true ]; then
    echo -e "${BLUE}🐳 Starting with docker-compose...${NC}"
    
    if [ "$DETACHED" = true ]; then
        docker-compose up -d
    else
        docker-compose up
    fi
    
    if [ "$FOLLOW_LOGS" = true ] && [ "$DETACHED" = true ]; then
        echo -e "${GREEN}📋 Following logs...${NC}"
        docker-compose logs -f zen-mcp-server
    fi
else
    echo -e "${BLUE}🐳 Starting container...${NC}"
    
    # Stop any existing container
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    
    # Build run command
    RUN_CMD="docker run"
    
    if [ "$DETACHED" = true ]; then
        RUN_CMD="$RUN_CMD -d"
    else
        RUN_CMD="$RUN_CMD -it"
    fi
    
    RUN_CMD="$RUN_CMD --rm --init"
    RUN_CMD="$RUN_CMD --name $CONTAINER_NAME"
    RUN_CMD="$RUN_CMD --env-file .env"
    RUN_CMD="$RUN_CMD -v $(pwd)/logs:/app/logs"
    RUN_CMD="$RUN_CMD $IMAGE_NAME:$IMAGE_TAG"
    
    # Execute run command
    eval $RUN_CMD
    
    if [ "$FOLLOW_LOGS" = true ] && [ "$DETACHED" = true ]; then
        echo -e "${GREEN}📋 Following logs...${NC}"
        docker logs -f $CONTAINER_NAME
    fi
fi

echo -e "${GREEN}✅ Zen MCP Server is running!${NC}"