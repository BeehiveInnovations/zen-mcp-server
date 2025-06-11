# Product Context

This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon projectBrief.md (if provided) and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.
2025-01-11 22:47:00 - Log of updates made will be appended as footnotes to the end of this file.

*

## Project Goal

The Gemini MCP Server is a Model Context Protocol (MCP) server that provides Claude with access to Google's Gemini AI models through specialized tools. This enables sophisticated AI-assisted development workflows combining Claude's general capabilities with Gemini's deep analytical and creative thinking abilities.

## Key Features

- **Multiple specialized tools**: chat, thinkdeep, codereview, debug, analyze, precommit
- **Docker-based deployment** with automated Redis for conversation threading
- **Comprehensive documentation structure** for both technical and non-technical users
- **GitHub integration** with issue/PR templates
- **Memory Bank strategy** for long-term context preservation
- **Cross-tool collaboration** between Claude and Gemini

## Overall Architecture

MCP server architecture with:
- Individual tool implementations in `tools/` directory
- Shared utilities for file handling, git operations, token management
- Redis-based conversation memory for context preservation
- Docker Compose orchestration for easy deployment
- Comprehensive test suite for quality assurance

---
2025-01-11 22:47:00 - Initial creation with project overview from README.md and CLAUDE.md