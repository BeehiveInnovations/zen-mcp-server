# Gemini MCP Server Documentation

Welcome to the comprehensive documentation for the **Gemini MCP Server** - a sophisticated Model Context Protocol server that enables Claude to access Google's Gemini AI models through specialized tools for AI-assisted development workflows.

## 📖 Documentation Overview

This documentation is organized into four main categories to serve different audiences and use cases:

### 🚀 For End Users
- **[Installation Guide](user-guides/installation.md)** - Set up the server locally or with Docker
- **[Configuration](user-guides/configuration.md)** - Configure the server for your environment  
- **[Troubleshooting](user-guides/troubleshooting.md)** - Common issues and solutions

### 🛠️ For Developers
- **[Development Setup](contributing/setup.md)** - Set up your development environment
- **[Development Workflows](contributing/workflows.md)** - Git workflows, testing, and collaboration patterns
- **[Code Style Guide](contributing/code-style.md)** - Coding standards and best practices
- **[Testing Strategy](contributing/testing.md)** - Testing approaches and quality assurance
- **[Test Structure Analysis](contributing/test-structure.md)** - Detailed analysis of existing test suite
- **[Repository Overview](contributing/file-overview.md)** - Understanding the codebase structure

### 🏗️ For System Architects
- **[Architecture Overview](architecture/overview.md)** - High-level system design and components
- **[Component Details](architecture/components.md)** - Detailed component descriptions and interactions
- **[Data Flow Patterns](architecture/data-flow.md)** - How data moves through the system
- **[Architecture Decisions](architecture/decisions/)** - Architecture Decision Records (ADRs)

### 🔧 For API Users
- **[MCP Protocol](api/mcp-protocol.md)** - Model Context Protocol implementation details
- **[Tool Reference](api/tools/)** - Individual tool API documentation

## 🎯 Quick Start Paths

### New User Journey
1. **[Install the Server](user-guides/installation.md)** → Get up and running quickly
2. **[Configure Your Setup](user-guides/configuration.md)** → Customize for your environment
3. **[Start Using Tools](#tool-reference)** → Explore AI-assisted workflows
4. **[Troubleshoot Issues](user-guides/troubleshooting.md)** → Resolve common problems

### Developer Journey  
1. **[Set Up Development](contributing/setup.md)** → Prepare your dev environment
2. **[Understand the Codebase](contributing/file-overview.md)** → Navigate the repository
3. **[Follow Workflows](contributing/workflows.md)** → Git, testing, and collaboration
4. **[Code Quality Standards](contributing/code-style.md)** → Maintain code quality

### Architect Journey
1. **[System Overview](architecture/overview.md)** → Understand the high-level design
2. **[Component Architecture](architecture/components.md)** → Deep dive into system parts
3. **[Data Flow Analysis](architecture/data-flow.md)** → Trace information flow
4. **[Decision Context](architecture/decisions/)** → Understand design choices

## 🛠️ Tool Reference

The server provides six specialized tools for different AI collaboration scenarios:

| Tool | Purpose | Best For | Documentation |
|------|---------|----------|---------------|
| **[chat](api/tools/chat.md)** | Quick questions, brainstorming | Immediate answers, idea exploration | Low complexity, fast iteration |
| **[thinkdeep](api/tools/thinkdeep.md)** | Complex analysis, strategic planning | Architecture decisions, system design | High complexity, deep analysis |
| **[analyze](api/tools/analyze.md)** | Code exploration, system understanding | Codebase comprehension, dependency analysis | Medium complexity, systematic exploration |
| **[codereview](api/tools/codereview.md)** | Code quality, security, bug detection | PR reviews, security audits | Quality assurance, comprehensive validation |
| **[debug](api/tools/debug.md)** | Root cause analysis, error investigation | Bug fixing, performance issues | Problem-solving, systematic debugging |
| **[precommit](api/tools/precommit.md)** | Automated quality gates | Pre-commit validation, change analysis | Quality gates, automated validation |

### Tool Selection Guide

**For Quick Tasks**: Start with [chat](api/tools/chat.md) for immediate answers and brainstorming
**For Complex Planning**: Use [thinkdeep](api/tools/thinkdeep.md) for architecture and strategic decisions  
**For Code Understanding**: Use [analyze](api/tools/analyze.md) to explore and understand existing code
**For Quality Assurance**: Use [codereview](api/tools/codereview.md) and [precommit](api/tools/precommit.md) for validation
**For Problem Solving**: Use [debug](api/tools/debug.md) for systematic error investigation

## 🔄 Collaboration Framework

This project follows the **[CLAUDE.md Collaboration Framework](../CLAUDE.md)** which defines:
- **Tool Selection Matrix**: Guidelines for choosing the right tool for each task
- **Memory Bank Integration**: Context preservation across development sessions  
- **Quality Gates**: Mandatory validation and review processes
- **Documentation Standards**: Comprehensive documentation requirements

### Key Collaboration Patterns
- **Complex Tasks (>3 steps)**: Always use TodoWrite to plan and track progress
- **Architecture Decisions**: Must involve `thinkdeep` for exploration before implementation
- **Code Reviews**: All significant changes require `codereview` analysis before committing
- **Documentation Updates**: Any code change must include corresponding documentation updates

## 📚 Additional Resources

### Configuration Examples
- **[macOS Setup](../examples/claude_config_macos.json)** - Local development on macOS
- **[WSL Setup](../examples/claude_config_wsl.json)** - Windows Subsystem for Linux
- **[Docker Setup](../examples/claude_config_docker_home.json)** - Container-based deployment

### Project Information
- **[Main README](../README.md)** - Project overview and quick start
- **[Contributing Guidelines](../CONTRIBUTING.md)** - How to contribute to the project
- **[License](../LICENSE)** - MIT License details
- **[Collaboration Framework](../CLAUDE.md)** - Development collaboration patterns

### Memory Bank System
The project uses a **Memory Bank** system for context preservation:
- **[Product Context](../memory-bank/productContext.md)** - Project goals and architecture
- **[Active Context](../memory-bank/activeContext.md)** - Current development status
- **[Decision Log](../memory-bank/decisionLog.md)** - Architectural decisions and rationale
- **[Progress Tracking](../memory-bank/progress.md)** - Task completion and milestones

## 🎨 Documentation Standards

### For Technical Audiences
- **Code Context**: All explanations include specific file and line number references (`file_path:line_number`)
- **Architecture Focus**: Explain *why* decisions were made, not just *what* was implemented
- **Data Flow**: Trace data through the system with concrete examples
- **Error Scenarios**: Document failure modes and recovery strategies

### For Non-Technical Audiences  
- **Plain Language**: Avoid jargon, explain technical terms when necessary
- **Purpose-Driven**: Start with "what problem does this solve?"
- **Visual Aids**: Use diagrams and flowcharts where helpful
- **Practical Examples**: Show real usage scenarios

## 🔍 Finding What You Need

### By Role
- **System Administrators**: Start with [Installation](user-guides/installation.md) and [Configuration](user-guides/configuration.md)
- **End Users**: Begin with [Tool Reference](#tool-reference) and [Quick Start](#new-user-journey)
- **Developers**: Follow the [Developer Journey](#developer-journey) starting with [Development Setup](contributing/setup.md)
- **Architects**: Review [Architecture Overview](architecture/overview.md) and [System Design](architecture/components.md)

### By Task
- **Setting Up**: [Installation](user-guides/installation.md) → [Configuration](user-guides/configuration.md)
- **Using Tools**: [Tool Reference](#tool-reference) → Specific tool documentation
- **Developing**: [Setup](contributing/setup.md) → [Workflows](contributing/workflows.md) → [Code Style](contributing/code-style.md)
- **Understanding Architecture**: [Overview](architecture/overview.md) → [Components](architecture/components.md) → [Data Flow](architecture/data-flow.md)
- **Troubleshooting**: [Troubleshooting Guide](user-guides/troubleshooting.md) or relevant tool documentation

### By Problem Type
- **Installation Issues**: [Installation Guide](user-guides/installation.md) and [Troubleshooting](user-guides/troubleshooting.md)
- **Configuration Problems**: [Configuration Guide](user-guides/configuration.md)
- **Tool Behavior Questions**: Specific [Tool Documentation](api/tools/)
- **Development Questions**: [Contributing Guides](contributing/)
- **Architecture Questions**: [Architecture Documentation](architecture/)

## 📝 Contributing to Documentation

This documentation follows the standards defined in [CLAUDE.md](../CLAUDE.md):

1. **Accuracy**: Documentation must reflect actual code behavior
2. **Completeness**: Cover all user-facing functionality  
3. **Accessibility**: Understandable by intended audience
4. **Currency**: Updated with every related code change

To contribute:
1. Follow the [Development Workflows](contributing/workflows.md)
2. Maintain [Code Style Standards](contributing/code-style.md)
3. Include comprehensive [Testing](contributing/testing.md)
4. Update relevant documentation sections

---

**Need Help?** Check the [Troubleshooting Guide](user-guides/troubleshooting.md) or explore the specific documentation section for your use case. For development questions, start with the [Contributing Guidelines](contributing/setup.md).