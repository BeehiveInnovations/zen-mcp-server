#!/bin/bash

# Zen MCP Server Docker Build Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="zen-mcp-server"
IMAGE_TAG="latest"
PLATFORMS="linux/amd64,linux/arm64"

echo -e "${GREEN}🐳 Building Zen MCP Server Docker Image${NC}"
echo "================================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Parse command line arguments
BUILD_PUSH=false
MULTI_PLATFORM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            BUILD_PUSH=true
            shift
            ;;
        --multi-platform)
            MULTI_PLATFORM=true
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            echo "Usage: $0 [--push] [--multi-platform] [--tag TAG] [--name NAME]"
            echo "  --push          Push image to registry after build"
            echo "  --multi-platform Build for multiple platforms (amd64, arm64)"
            echo "  --tag TAG       Image tag (default: latest)"
            echo "  --name NAME     Image name (default: zen-mcp-server)"
            exit 1
            ;;
    esac
done

# Build command
if [ "$MULTI_PLATFORM" = true ]; then
    echo -e "${YELLOW}📦 Setting up multi-platform build...${NC}"
    
    # Check if buildx is available
    if ! docker buildx version &> /dev/null; then
        echo -e "${RED}❌ Docker buildx is not available. Please update Docker.${NC}"
        exit 1
    fi
    
    # Create builder if it doesn't exist
    if ! docker buildx ls | grep -q "zen-mcp-builder"; then
        echo "Creating buildx builder..."
        docker buildx create --name zen-mcp-builder --driver docker-container --bootstrap
    fi
    
    # Build for multiple platforms
    echo -e "${GREEN}🔨 Building for platforms: $PLATFORMS${NC}"
    
    BUILD_CMD="docker buildx build --builder=zen-mcp-builder --platform $PLATFORMS"
    
    if [ "$BUILD_PUSH" = true ]; then
        BUILD_CMD="$BUILD_CMD --push"
    else
        BUILD_CMD="$BUILD_CMD --load"
        echo -e "${YELLOW}⚠️  Note: Multi-platform builds can only be loaded for the current platform without --push${NC}"
    fi
    
    BUILD_CMD="$BUILD_CMD -t $IMAGE_NAME:$IMAGE_TAG ."
    
else
    # Regular single-platform build
    echo -e "${GREEN}🔨 Building for current platform...${NC}"
    BUILD_CMD="docker build -t $IMAGE_NAME:$IMAGE_TAG ."
fi

# Execute build
echo -e "${YELLOW}Executing: $BUILD_CMD${NC}"
eval $BUILD_CMD

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Build successful!${NC}"
    echo ""
    echo "Image: $IMAGE_NAME:$IMAGE_TAG"
    
    if [ "$BUILD_PUSH" = true ]; then
        echo -e "${GREEN}📤 Image pushed to registry${NC}"
    else
        echo ""
        echo "To run the container:"
        echo "  docker run -i --rm --init --env-file .env -v ./logs:/app/logs $IMAGE_NAME:$IMAGE_TAG"
        echo ""
        echo "Or use docker-compose:"
        echo "  docker-compose up"
    fi
else
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi