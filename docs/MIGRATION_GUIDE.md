# Zen MCP Server - Migration Guide

## Overview

This guide helps users navigate the transition from the current **Tool/Registry Architecture** to the future **LangGraph Multi-Agent Architecture**.

## Architecture Comparison

### Current: Tool/Registry System
- **Entry Point**: `./run-server.sh` → `server.py`
- **Approach**: 16 specialized tools with workflow capabilities
- **State Management**: In-memory conversation threads
- **Provider Support**: Direct API keys (OpenAI, Gemini, OpenRouter, etc.)
- **Maturity**: Production-ready, fully tested

### Future: LangGraph Multi-Agent System
- **Entry Point**: `python server_graph.py`
- **Approach**: Supervisor routing to specialized agents
- **State Management**: Redis-based checkpointing
- **Provider Support**: Unified gateway (Bifrost/LiteLLM)
- **Maturity**: In development (2/7 nodes implemented)

## Migration Timeline

### Phase 1: Preparation (Current)
**Status**: ✅ Complete
- Documentation alignment
- Configuration clarification
- Migration path definition

### Phase 2: Parallel Operation (Next 1-2 months)
**Status**: 🔄 In Progress
- Both architectures available
- Users can choose based on needs
- Feature parity development

### Phase 3: Gradual Transition (Next 3-6 months)
**Status**: ⏳ Planned
- Unified entry point
- Seamless migration tools
- Legacy deprecation planning

## User Migration Paths

### Path A: Stay with Current Architecture (Recommended for Most Users)

**Who should choose this path:**
- Production environments requiring stability
- Users satisfied with current tool capabilities
- Teams needing immediate reliability

**Steps:**
1. Continue using `./run-server.sh`
2. Keep current configuration (individual API keys)
3. Monitor migration progress via `docs/PROJECT_STATUS.md`
4. Plan migration when LangGraph reaches feature parity

**Benefits:**
- ✅ Proven stability
- ✅ Full feature set
- ✅ Comprehensive documentation
- ✅ No migration effort

**Timeline**: Can remain indefinitely during Phase 2

### Path B: Early Adopter (Advanced Users)

**Who should choose this path:**
- Developers wanting to test new architecture
- Users needing specific LangGraph features
- Contributors to the migration effort

**Prerequisites:**
- Redis server running
- Unified gateway (Bifrost/LiteLLM) deployed
- Comfort with experimental features

**Steps:**
1. Deploy Redis: `docker run -d -p 6379:6379 redis:latest`
2. Deploy gateway (Bifrost recommended):
   ```bash
   # Example Bifrost deployment
   docker run -d -p 8080:8080 \
     -e GEMINI_API_KEY=$GEMINI_API_KEY \
     -e OPENAI_API_KEY=$OPENAI_API_KEY \
     bifrost/bifrost:latest
   ```
3. Configure environment:
   ```bash
   export UNIFIED_LLM_GATEWAY=http://localhost:8080
   export UNIFIED_LLM_API_KEY=sk-gateway-key
   export REDIS_URL=redis://localhost:6379/0
   ```
4. Run LangGraph server:
   ```bash
   python server_graph.py
   ```

**Benefits:**
- 🚀 Early access to new architecture
- 🔄 State persistence with Redis
- 🤖 Multi-agent collaboration
- 📈 Influence development direction

**Risks:**
- ⚠️ Limited feature set (2/7 nodes)
- ⚠️ Potential instability
- ⚠️ Breaking changes expected
- ⚠️ Limited documentation

### Path C: Hybrid Approach (Power Users)

**Who should choose this path:**
- Organizations wanting gradual migration
- Users with diverse workloads
- Teams requiring both architectures

**Implementation:**
1. Deploy both architectures on different ports
2. Use client-side routing based on task complexity
3. Gradually shift workloads to LangGraph
4. Maintain tool system for fallback

**Example Setup:**
```bash
# Terminal 1: Current system (port 3000)
ZEN_SERVER_PORT=3000 ./run-server.sh

# Terminal 2: LangGraph system (port 3001)
ZEN_SERVER_PORT=3001 python server_graph.py
```

## Configuration Migration

### Current Configuration (.env)
```bash
# Working configuration for tool/registry system
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_openrouter_key
DEFAULT_MODEL=auto
DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer
```

### Future Configuration (.env)
```bash
# Target configuration for LangGraph system
UNIFIED_LLM_GATEWAY=http://localhost:8080
UNIFIED_LLM_API_KEY=sk-gateway-key
REDIS_URL=redis://localhost:6379/0
```

### Migration Strategy
1. **Phase 1**: Use current configuration
2. **Phase 2**: Deploy gateway alongside current providers
3. **Phase 3**: Gradually migrate API keys to gateway
4. **Phase 4**: Remove individual provider keys

## Feature Mapping

| Current Tool | LangGraph Agent | Status | Migration Notes |
|--------------|-----------------|---------|-----------------|
| chat | Coder | ⏳ Planned | Direct conversation handling |
| thinkdeep | Researcher | ✅ Basic | Enhanced analysis planned |
| planner | Architect | ⏳ Planned | Strategic planning capabilities |
| consensus | Researcher | ✅ Basic | Multi-model consensus |
| codereview | Reviewer | ⏳ Planned | Code quality analysis |
| precommit | Reviewer | ⏳ Planned | Pre-commit validation |
| debug | Debugger | ⏳ Planned | Root cause analysis |
| secaudit | Reviewer | ⏳ Planned | Security audit capabilities |
| docgen | Architect | ⏳ Planned | Documentation generation |
| analyze | Architect | ⏳ Planned | System analysis |
| refactor | Architect | ⏳ Planned | Refactoring strategies |
| tracer | Debugger | ⏳ Planned | Execution tracing |
| testgen | Coder | ⏳ Planned | Test generation |
| challenge | Supervisor | ✅ Basic | Critical thinking integration |
| listmodels | Utilities | ⏳ Planned | Model enumeration |
| version | Utilities | ⏳ Planned | Version information |

## Testing Migration

### Current System Testing
```bash
# Run comprehensive test suite
python -m pytest tests/ -v

# Test specific tools
python -m pytest tests/test_consensus.py -v
python -m pytest tests/test_chat_simple.py -v
```

### LangGraph System Testing
```bash
# Test LangGraph components (limited currently)
python -m pytest tests/test_langgraph/ -v

# Manual testing via MCP client
python server_graph.py
# Then connect with Claude Desktop or other MCP client
```

### Migration Testing
```bash
# Test both systems in parallel
./run_integration_tests.sh  # Tests current system
python scripts/test_langgraph_migration.py  # Tests migration path
```

## Troubleshooting

### Common Issues

#### Issue: Gateway Connection Failed
**Solution**: Check gateway deployment and network connectivity
```bash
# Test gateway directly
curl http://localhost:8080/v1/models

# Check gateway logs
docker logs <gateway_container_id>
```

#### Issue: Redis Connection Failed
**Solution**: Verify Redis server and connection string
```bash
# Test Redis connection
redis-cli -u redis://localhost:6379 ping

# Check Redis logs
docker logs <redis_container_id>
```

#### Issue: Feature Not Available in LangGraph
**Solution**: Use current tool system for missing features
```bash
# Fall back to tool system
./run-server.sh

# Or use hybrid approach
ZEN_ARCHITECTURE=tools ./run-server.sh
```

### Getting Help

1. **Documentation**: Check `docs/PROJECT_STATUS.md` for current status
2. **Issues**: Report problems on GitHub with architecture specified
3. **Community**: Join discussions for migration experiences
4. **Support**: Use architecture-specific troubleshooting guides

## Contributing to Migration

### Development Priorities
1. **Complete Node Implementation**: Architect, Coder, Reviewer, Debugger, Terminal, Utilities
2. **Tool Integration**: Map existing tools to agent capabilities
3. **Testing**: Comprehensive test suite for LangGraph system
4. **Documentation**: User guides and API documentation
5. **Performance**: Optimize for production workloads

### How to Contribute
1. Pick a node from the implementation roadmap
2. Study corresponding tool implementations
3. Implement node with equivalent functionality
4. Add comprehensive tests
5. Update documentation
6. Submit pull request with migration impact analysis

## Rollback Plan

If migration causes issues:

### Immediate Rollback
1. Stop LangGraph server: `pkill -f server_graph.py`
2. Restart tool system: `./run-server.sh`
3. Restore previous configuration from backup
4. Verify functionality with test suite

### Configuration Rollback
```bash
# Restore tool system configuration
cp .env.backup .env
# Remove gateway/Redis variables
unset UNIFIED_LLM_GATEWAY UNIFIED_LLM_API_KEY REDIS_URL
```

### Data Rollback
```bash
# Clear Redis state if needed
redis-cli FLUSHALL

# Reset conversation memory
rm -rf /tmp/zen_conversations/*
```

## Timeline & Milestones

### Q1 2025: Foundation
- ✅ Architecture alignment
- ✅ Documentation updates
- 🔄 Node implementation (target: 4/7 complete)
- 🔄 Basic testing framework

### Q2 2025: Feature Parity
- 🔄 Complete all node implementations
- 🔄 Tool integration
- 🔄 Comprehensive testing
- 🔄 Performance optimization

### Q3 2025: Unification
- ⏳ Unified entry point
- ⏳ Migration tools
- ⏳ Documentation completion
- ⏳ User migration programs

### Q4 2025: Transition
- ⏳ Feature parity achieved
- ⏳ Gradual user migration
- ⏳ Legacy deprecation planning
- ⏳ Production readiness

---

*This guide evolves with the migration. Check `docs/PROJECT_STATUS.md` for latest progress.*
