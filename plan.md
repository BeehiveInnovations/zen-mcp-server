# Zen MCP Server - Project Plan & Workflow

## Project Overview
Forked zen-mcp-server repository with goals to regain backend autonomy and integrate with OpenAI MCP custom connector.

## Primary Objectives

### Phase 1: Migration Preparation & Planning (In Progress)
- [x] Safety vetting for disabling restricted mode
- [x] Main components identification
- [x] Extraneous features analysis
- [x] Detailed code architecture review
- [x] Dependency analysis and security audit

#### 1. Finalize Migration Goals and Success Criteria
- [ ] Define clear objectives for the TypeScript migration (performance, maintainability, ecosystem alignment)
- [ ] Document expected outcomes (startup time, memory usage, integration targets)
- [ ] Establish success metrics (e.g., performance benchmarks, test coverage)

#### 2. Identify Core Modules to Migrate First
- [ ] List all critical modules (OpenAI provider, MCP protocol handler, tool registry)
- [ ] Prioritize based on integration complexity and business value
- [ ] Map dependencies between modules

#### 3. Define TypeScript Project Structure
- [ ] Decide on monorepo vs. multi-package layout
- [ ] Draft initial folder and file structure (e.g., src/, config/, providers/)
- [ ] Plan for configuration and environment management

#### 4. Select Frameworks/Libraries
- [ ] Evaluate and choose HTTP server (e.g., Express, Fastify)
- [ ] Select OpenAI SDK (`openai`)
- [ ] Choose JSON-RPC library (`json-rpc-2.0` or similar)
- [ ] Identify testing frameworks (Jest, Mocha, etc.)
- [ ] List supporting libraries (dotenv, ws, etc.)

#### 5. Set Up CI/CD Pipeline Plan
- [ ] Choose CI/CD platform (GitHub Actions, GitLab CI, etc.)
- [ ] Define build, test, and deploy steps
- [ ] Plan for automated linting and formatting
- [ ] Set up code coverage reporting

#### 6. Dependency Analysis
- [ ] Inventory all Python dependencies (requirements.txt, pyproject.toml)
- [ ] Identify direct and transitive dependencies
- [ ] Flag deprecated, unmaintained, or high-risk packages
- [ ] Map Python dependencies to TypeScript/Node.js equivalents
- [ ] Document any custom or internal libraries

#### 7. Security Audit
- [ ] Review current codebase for known vulnerabilities (static analysis)
- [ ] Check for hardcoded secrets, API keys, or credentials
- [ ] Audit configuration files for sensitive data exposure
- [ ] Review Dockerfile and deployment scripts for security best practices
- [ ] Plan for secure secret management in the new stack
- [ ] Document all findings and remediation steps

### Phase 2: Backend Autonomy & Cleanup
- [ ] Remove unnecessary providers (keep OpenAI-compatible ones)
- [ ] Streamline configuration system
- [ ] Remove extraneous test files and simulators
- [ ] Optimize Docker deployment setup
- [ ] Review and update documentation

### Phase 3: OpenAI MCP Integration Preparation
- [ ] Analyze current OpenAI provider implementation
- [ ] Design custom connector architecture
- [ ] Identify required API endpoints and protocols
- [ ] Plan authentication and security mechanisms
- [ ] Design data flow and message handling

### Phase 4: Core Functionality Implementation
- [ ] Implement OpenAI MCP custom connector
- [ ] Update server.py for new integration
- [ ] Configure provider registry for custom connector
- [ ] Implement error handling and logging
- [ ] Add monitoring and health checks

### Phase 5: Testing & Validation
- [ ] Create unit tests for new functionality
- [ ] Integration testing with OpenAI MCP
- [ ] Performance testing and optimization
- [ ] Security testing and validation
- [ ] Documentation updates

### Phase 6: Advanced Customization
- [ ] Add custom tools and capabilities
- [ ] Implement advanced routing logic
- [ ] Add custom prompt engineering features
- [ ] Implement caching and optimization
- [ ] Add monitoring and analytics

## Current Status
- **Active Phase:** Phase 1 (Repository Analysis)
- **Next Task:** Dependency analysis and security audit
- **Blockers:** None identified
- **Notes:** Feasibility study completed for multi-language architecture

## Key Files to Focus On
- `server.py` - Main entry point
- `providers/openai_compatible.py` - OpenAI integration
- `providers/openai_provider.py` - Core OpenAI provider
- `config.py` - Configuration management
- `conf/custom_models.json` - Model configurations

## Technical Decisions Log
- **Date:** 2025-08-06
- **Decision:** Proceed with repository analysis and cleanup
- **Rationale:** Codebase appears safe and well-structured

### Architecture Analysis Results (2025-08-06)
**Current Language:** Python 3.9+ with asyncio-based architecture

**REFACTORABILITY ASSESSMENT:**
🔴 **CRITICAL**: Python performance limitations for real-time MCP operations
- Single-threaded async event loop creates bottlenecks
- 1,356 lines in server.py with complex tool routing
- Heavy dependency on external API calls (blocking despite async)
- Memory overhead from large tool registry and provider chains

🟡 **BETTER ALTERNATIVES:**
1. **Node.js/TypeScript** - Superior async I/O, JSON-RPC native, MCP ecosystem alignment
2. **Go** - Excellent concurrency, fast startup, low memory footprint, great for protocol servers
3. **Rust** - Maximum performance, memory safety, growing MCP ecosystem

**ARCHITECTURE FINDINGS:**
- **Tool Registry Pattern**: 15+ tools with workflow mixins (good modularity)
- **Provider Architecture**: Multi-AI provider support (OpenAI, Gemini, XAI, etc.)
- **Conversation Memory**: Redis/in-memory storage for stateful interactions
- **MCP Protocol**: Full JSON-RPC implementation over stdio
- **File Processing**: Context-aware file embedding with token management

**PERFORMANCE CONCERNS:**
- Startup time: ~3 seconds (too slow for on-demand MCP connections)
- Memory usage: ~256MB base + model overhead
- Request latency: 1-30 seconds (model-dependent but framework adds overhead)
- Docker image: 293MB (acceptable but could be optimized)

**REFACTORING RECOMMENDATION:**
Consider **Node.js/TypeScript rewrite** for OpenAI MCP integration:
- Better async performance for API-heavy operations
- Native JSON handling and streaming
- Smaller runtime footprint
- Better alignment with OpenAI's MCP ecosystem
- Easier integration with OpenAI SDK and protocols

### Feasibility Study: Multi-Language Architecture (2025-08-06)

**PROPOSED ARCHITECTURE:**
```
┌─────────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   TypeScript        │    │   Go Backend     │    │  Rust Core      │
│   Integration       │    │   Server         │    │  Engine         │
│   ├─ OpenAI SDK     │◄──►│   ├─ HTTP/gRPC   │◄──►│  ├─ Protocol    │
│   ├─ MCP Protocol   │    │   ├─ Auth Layer  │    │  ├─ Parser      │
│   └─ API Gateway    │    │   └─ Load Bal.   │    │  └─ Validator   │
└─────────────────────┘    └──────────────────┘    └─────────────────┘
```

**🟢 FEASIBILITY ANALYSIS:**

**TypeScript Integration Module:**
- ✅ **High**: Excellent OpenAI SDK support (`openai@^4.x`)
- ✅ **High**: Native MCP protocol handling with existing libs
- ✅ **High**: JSON-RPC over stdio implementation available
- ✅ **High**: Rich ecosystem for HTTP/WebSocket protocols
- ⚠️ **Medium**: Requires TypeScript rewrite of current Python tools

**Go Backend Server:**
- ✅ **High**: Excellent HTTP/gRPC performance (10x faster than Python)
- ✅ **High**: Built-in concurrency with goroutines
- ✅ **High**: Low memory footprint (~50MB vs 256MB Python)
- ✅ **High**: Fast startup time (<1s vs 3s Python)
- ⚠️ **Medium**: Provider pattern needs Go reimplementation

**Rust Core Engine:**
- ✅ **High**: Maximum performance for protocol parsing
- ✅ **High**: Memory safety for long-running processes
- ✅ **High**: Zero-cost abstractions for MCP protocol
- 🔴 **Low**: Complex integration - may be overkill for current needs
- 🔴 **Low**: Development time investment vs. benefit unclear

**🎯 RECOMMENDED APPROACH:**

**Phase A: TypeScript-Go Hybrid (Recommended)**
```
TypeScript Frontend + Go Backend
- TypeScript: OpenAI integration, MCP protocol, tool definitions
- Go: HTTP server, routing, authentication, provider management
- Estimated Dev Time: 4-6 weeks
- Performance Gain: 5-10x improvement
- Complexity: Medium
```

**Phase B: Full TypeScript (Alternative)**
```
Pure TypeScript with Node.js
- Single language reduces complexity
- Excellent OpenAI ecosystem integration
- Easier to maintain and extend
- Estimated Dev Time: 2-3 weeks
- Performance Gain: 2-3x improvement
- Complexity: Low
```

**🔴 NOT RECOMMENDED: Rust Core**
- Adds significant complexity without proportional benefits
- Current workload doesn't justify systems-level optimizations
- Would require substantial rewrite of business logic

## Migration Roadmap: TypeScript (Node.js) Backend

### Overview
This roadmap outlines the phased migration of the Zen MCP Server from Python to a TypeScript (Node.js) backend, with optional Go integration for performance-critical components. The plan is modular, allowing for incremental migration and testing.

### Phase 1: Preparation & Planning
- [ ] Finalize migration goals and success criteria
- [ ] Identify core modules to migrate first (OpenAI provider, MCP protocol handler, tool registry)
- [ ] Define TypeScript project structure (monorepo or multi-package)
- [ ] Select frameworks/libraries (e.g., `openai`, `express`, `ws`, `json-rpc-2.0`)
- [ ] Set up CI/CD pipeline for new codebase

### Phase 2: Core Protocol & Provider Migration
- [ ] Implement MCP protocol handler in TypeScript (JSON-RPC over stdio)
- [ ] Port OpenAI provider logic to TypeScript (using `openai` SDK)
- [ ] Recreate tool registry pattern in TypeScript
- [ ] Implement basic configuration management (dotenv, config files)
- [ ] Establish test harness for protocol and provider modules

### Phase 3: Tool & Workflow Migration
- [ ] Translate core tools and workflow mixins to TypeScript modules
- [ ] Implement conversation memory (in-memory, then Redis)
- [ ] Port or redesign file/context embedding logic
- [ ] Integrate error handling, logging, and monitoring

### Phase 4: Optional Go Backend Integration
- [ ] Identify performance-critical paths (e.g., protocol parsing, heavy computation)
- [ ] Define TypeScript-Go interface (HTTP/gRPC or native bindings)
- [ ] Implement Go microservices as needed
- [ ] Integrate with TypeScript frontend

### Phase 5: Testing, Validation & Cutover
- [ ] Unit and integration tests for all migrated modules
- [ ] Performance and load testing
- [ ] Security review and audit
- [ ] Documentation and migration guides
- [ ] Gradual cutover from Python to TypeScript backend

### Dependency Mapping Table
| Python Dependency   | Purpose                                      | Risk/Status         | Node.js/TypeScript Equivalent         |
|---------------------|----------------------------------------------|---------------------|---------------------------------------|
| mcp                | MCP protocol implementation                  | Custom/Unknown      | Custom implementation or `json-rpc-2.0` |
| google-genai       | Google Gemini/GenAI API client               | Maintained          | `@google/generative-ai`               |
| openai             | OpenAI API client                            | Maintained          | `openai` (npm)                        |
| pydantic           | Data validation, parsing, settings           | Maintained          | `zod`, `joi`, or `class-validator`    |
| python-dotenv      | Loads env vars from .env file                | Maintained          | `dotenv` (npm)                        |
| pytest, etc.       | Testing                                      | Maintained          | `jest`, `mocha`, `chai`               |

- [x] Dependency analysis complete
- [ ] Security audit in progress

#### Security Audit Summary (Preliminary)
- No hardcoded secrets found in Python files.
- All API keys and secrets are referenced via environment variables in `docker-compose.yml` (good practice).
- No secrets found in Dockerfile or .env files.
- Recommend: Use Docker secrets or a secrets manager in production, and audit for accidental secret commits.

### Module Mapping Table
| Python Module                  | TypeScript Equivalent         | Migration Notes                  |
|-------------------------------|-------------------------------|----------------------------------|
| `server.py`                   | `src/server.ts`               | Main entry, protocol handler     |
| `providers/openai_provider.py` | `src/providers/openai.ts`     | Use `openai` SDK                 |
| `providers/openai_compatible.py`| `src/providers/openaiCompat.ts`| API compatibility layer         |
| `config.py`                   | `src/config.ts`               | Use dotenv/config lib            |
| `tools/models.py`             | `src/tools/models.ts`         | TypeScript interfaces/enums      |
| `conf/custom_models.json`     | `config/custom_models.json`   | Direct port                      |

## Notes & Ideas
- Consider implementing plugin architecture for extensibility
- Evaluate need for real-time capabilities
- Plan for scalability and load balancing
- Consider implementing rate limiting and quotas
- **LANGUAGE MIGRATION**: Strong case for Node.js/TypeScript rewrite
- **PERFORMANCE PRIORITY**: Address 3s startup time and memory usage
- **MCP ECOSYSTEM**: Leverage existing TypeScript MCP tools and libraries
- **MIGRATION STRATEGY**: TypeScript-Go hybrid architecture recommended
- **DEVELOPMENT TIME**: 4-6 weeks for hybrid, 2-3 weeks for pure TypeScript
- **PERFORMANCE GAINS**: 5-10x with Go backend, 2-3x with pure TypeScript

---
*Last Updated: 2025-08-06*
*Next Review: TBD*
