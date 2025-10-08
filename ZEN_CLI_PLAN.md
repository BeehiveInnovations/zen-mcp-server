# Zen CLI Implementation Plan

## Executive Summary

**Goal**: Replace 16 MCP tools (23k tokens) with a single `zen` CLI command (~1k tokens) while maintaining 100% functionality and improving user experience.

**Strategy**: Leverage Claude's operational strengths and the existing Bash tool to provide progressive schema discovery and human-readable interfaces.

**Target**: 95% token reduction (23k → 1k tokens) with enhanced usability.

---

## Architecture Overview

### Current State (MCP Tools)
```
┌─────────────────────────────────────┐
│ Claude Code Context                 │
├─────────────────────────────────────┤
│ Bash Tool (~400 tokens)            │
│ + 16 Zen Tools (~22,600 tokens)    │  
│   - chat, debug, codereview, etc.  │
│   - Full schemas loaded at startup  │
│   - Static parameter definitions    │
└─────────────────────────────────────┘
Total: ~23,000 tokens
```

### Proposed State (Zen CLI)
```
┌─────────────────────────────────────┐
│ Claude Code Context                 │
├─────────────────────────────────────┤
│ Bash Tool (~400 tokens)            │
│ + Claude Code Template (~600 tokens)│
│   - Zen CLI command knowledge       │
│   - Progressive discovery patterns  │  
│   - Usage examples and guidance     │
└─────────────────────────────────────┘
Total: ~1,000 tokens
```

---

## Command Structure

### Base Command
```bash
zen --help                    # Show main help and available modes
zen --version                 # Show version and server status
zen --discover               # Interactive mode discovery
```

### Core Modes

#### 1. Debug Mode
```bash
zen debug --help                                    # Show debug options
zen debug --problem "OAuth not persisting"         # Basic debugging
zen debug --problem "Memory leak" --files src/ --confidence high
zen debug --hypothesis "Connection pool issue" --trace-mode dependencies
zen debug --continue <session-id>                  # Continue previous debug session
```

#### 2. Code Review Mode  
```bash
zen codereview --help                              # Show review options
zen codereview --files src/auth.py                # Review specific files
zen codereview --request "Security audit" --type security --severity critical
zen codereview --standards "PEP8,security" --output detailed
```

#### 3. Analysis Mode
```bash
zen analyze --help                                 # Show analysis options  
zen analyze --files src/ --type architecture      # Architectural analysis
zen analyze --performance --files src/db/         # Performance analysis
zen analyze --patterns --similar-to src/auth.py   # Pattern analysis
```

#### 4. Consensus Mode
```bash
zen consensus --help                               # Show consensus options
zen consensus --question "Microservices vs monolith?"
zen consensus --models gemini-2.5-pro,o3 --decision "Database choice"
zen consensus --stakeholders --format executive    # Executive summary format
```

#### 5. Security Audit Mode
```bash
zen secaudit --help                               # Show security options
zen secaudit --files src/ --focus owasp          # OWASP Top 10 focus
zen secaudit --compliance "SOC2,HIPAA" --level critical
zen secaudit --threat-model --assets "user-data,payments"
```

#### 6. Planning Mode
```bash
zen plan --help                                   # Show planning options
zen plan --task "Migrate to microservices"       # Project planning
zen plan --architecture --scope backend          # Architecture planning  
zen plan --timeline --resources 3-engineers      # Resource planning
```

#### 7. Testing Mode
```bash
zen testgen --help                                # Show test generation options
zen testgen --files src/auth.py --coverage edge-cases
zen testgen --framework pytest --style tdd       # Test-driven development
zen testgen --integration --services auth,payment # Integration tests
```

#### 8. Refactoring Mode
```bash
zen refactor --help                               # Show refactoring options
zen refactor --files src/legacy/ --target modern # Modernization
zen refactor --extract-service --domain auth     # Service extraction
zen refactor --patterns --anti-patterns          # Code smell detection
```

### Advanced Features

#### Session Management
```bash
zen --sessions                                    # List active sessions
zen --session <id> --status                      # Check session status  
zen --session <id> --continue                    # Resume session
zen --session <id> --export report.md            # Export session report
```

#### Multi-Stage Operations
```bash
zen --pipeline "debug -> analyze -> refactor"    # Multi-stage workflow
zen --chain debug,testgen --files src/auth.py   # Chain multiple operations
```

#### Integration Features  
```bash
zen --git-hook pre-commit                        # Git integration
zen --watch src/ --auto-review                   # File watching
zen --report --format json | jq '.summary'      # Structured output
```

---

## Implementation Phases

### Phase 1: Core CLI Framework (Week 1)
**Deliverables:**
- `zen.py` with Click framework
- Basic command routing and help system
- Integration with existing Zen MCP server
- Core modes: debug, codereview, analyze

**Technical Tasks:**
```python
# zen.py structure
import click
from zen_client import ZenClient

@click.group()
@click.version_option("5.12.0")
def cli():
    """Zen AI Orchestration CLI - Your AI-powered development assistant"""
    pass

@cli.command()
@click.option('--problem', required=True, help='Issue description')
@click.option('--files', multiple=True, help='Files to analyze')
@click.option('--confidence', type=click.Choice(['exploring', 'low', 'medium', 'high']))
def debug(problem: str, files: List[str], confidence: str):
    """Systematic debugging with AI assistance"""
    client = ZenClient()
    result = client.debug(problem=problem, files=files, confidence=confidence)
    click.echo(result.format_output())
```

### Phase 2: Advanced Features (Week 2)
**Deliverables:**
- Session management and continuations
- All 16 tool modes implemented
- Progressive discovery system
- Claude Code Template integration

### Phase 3: User Experience Polish (Week 3)
**Deliverables:**
- Interactive mode with prompts
- Rich help system with examples
- Error handling and recovery
- Integration testing with Claude Code

### Phase 4: Advanced Integration (Week 4)
**Deliverables:**
- Git hooks and CI integration
- File watching and auto-execution
- Report generation and exports
- Performance optimization

---

## Technical Specifications

### CLI Client Architecture
```python
# zen_client.py - Communication layer
class ZenClient:
    def __init__(self, server_url="localhost:3001"):
        self.server_url = server_url
        self.session_manager = SessionManager()
    
    def debug(self, problem: str, files: List[str] = None, **kwargs):
        """Execute debug operation via MCP protocol"""
        request = self._build_debug_request(problem, files, **kwargs)
        return self._execute_mcp_call("debug", request)
    
    def _execute_mcp_call(self, tool: str, request: dict):
        """Execute MCP tool call with session management"""
        # Handle MCP JSON-RPC communication
        # Manage conversation threading
        # Parse and format responses
```

### Schema Discovery System
```python
# schema_discovery.py - Progressive help system
class SchemaDiscovery:
    def get_command_help(self, command: str) -> str:
        """Generate context-aware help for specific command"""
        return self.tool_schemas[command].generate_help()
    
    def discover_options(self, partial_command: str) -> List[str]:
        """Provide option suggestions for partial commands"""
        # Smart completion and suggestions
```

### Claude Code Template Integration
```markdown
# Addition to CLAUDE.md template
## Zen CLI Integration

When users request AI assistance that matches Zen capabilities:

**Auto-detect patterns:**
- "debug this issue" → `zen debug --problem "..." --files ...`
- "review this code" → `zen codereview --files ... --type security`
- "analyze architecture" → `zen analyze --type architecture --files ...`

**Progressive discovery:**
- Start with `zen --help` to show available modes
- Use `zen <mode> --help` for specific command guidance
- Provide example commands based on context

**Session management:**
- Track ongoing zen operations with `zen --sessions`
- Continue complex multi-turn workflows
- Export results for documentation
```

---

## Token Economics Comparison

### Current MCP Tools Approach
```yaml
Context_Usage:
  Bash_Tool: ~400 tokens
  Zen_Tools_Schema: ~22,600 tokens
  Total_Overhead: ~23,000 tokens
  
Usage_Pattern:
  - All schemas loaded at startup
  - Static parameter definitions
  - Full context for every request
  
Efficiency: 23k tokens / request (high overhead)
```

### Proposed Zen CLI Approach  
```yaml
Context_Usage:
  Bash_Tool: ~400 tokens  
  Template_Knowledge: ~600 tokens
  Total_Overhead: ~1,000 tokens
  
Usage_Pattern:
  - Schema discovery on-demand via --help
  - Progressive parameter revelation
  - Context-aware assistance
  
Efficiency: 1k tokens / request (minimal overhead)
```

### Token Savings Analysis
```
Traditional: zen debug --problem "auth issue" 
└── MCP Call: 23k tokens + execution

CLI Approach: zen debug --problem "auth issue"
└── Bash Call: 1k tokens + execution

Savings: 22k tokens (95% reduction)
```

---

## Benefits Analysis

### For Claude Code Users
✅ **Familiar Interface**: Command-line tools feel natural  
✅ **Progressive Discovery**: Learn commands incrementally via --help  
✅ **Rich Context**: Examples and guidance available on-demand  
✅ **Human Readable**: Commands make sense to developers  
✅ **Session Continuity**: Resume complex multi-turn workflows  

### For Claude AI
✅ **Operational Strength**: Leverages bash tool proficiency  
✅ **Context Efficiency**: 95% token reduction  
✅ **Natural Integration**: Fits existing tool usage patterns  
✅ **Extensibility**: Easy to add new modes and options  

### For Development Teams  
✅ **Scriptable**: CLI commands work in automation/CI  
✅ **Documentation**: Help text provides self-documenting API  
✅ **Integration**: Git hooks, file watching, report generation  
✅ **Consistency**: Unified interface across all AI capabilities  

---

## Risk Assessment

### Technical Risks
**Medium Risk: CLI Development Complexity**
- Mitigation: Phased implementation, existing MCP backend
- Fallback: Gradual rollout alongside existing MCP tools

**Low Risk: MCP Protocol Changes**  
- Mitigation: Abstract communication layer
- Fallback: Continue using MCP tools if needed

### User Experience Risks
**Low Risk: Learning Curve**
- Mitigation: Rich help system, examples, progressive disclosure
- Benefit: CLI is more discoverable than MCP tool schemas

**Low Risk: Feature Parity**
- Mitigation: Direct mapping from MCP tools to CLI commands
- Benefit: Can enhance UX beyond current MCP limitations

---

## Success Criteria

### Performance Metrics
- [ ] **Token Usage**: <2k tokens overhead (95% reduction achieved)
- [ ] **Response Time**: Comparable to current MCP tools
- [ ] **Feature Parity**: All 16 tool functions available via CLI

### User Experience Metrics  
- [ ] **Discoverability**: Users can find commands via --help
- [ ] **Usability**: Complex workflows completable without documentation
- [ ] **Integration**: Works seamlessly in Claude Code environment

### Technical Metrics
- [ ] **Reliability**: 99%+ success rate for tool operations
- [ ] **Maintainability**: Clear separation between CLI and backend
- [ ] **Extensibility**: New tools can be added without schema changes

---

## Alternative Considerations

### Hybrid Approach
Keep MCP tools for complex scenarios, add CLI for common cases:
- Simple operations → `zen` CLI (token efficient)
- Complex multi-turn → MCP tools (full context)

### Gradual Migration
- Phase 1: CLI alongside existing MCP tools
- Phase 2: User feedback and refinement
- Phase 3: Deprecate MCP tools if CLI proves superior

### Configuration Options
```bash
# Allow users to choose their preferred interface
export ZEN_INTERFACE=cli     # Use CLI commands
export ZEN_INTERFACE=mcp     # Use MCP tools  
export ZEN_INTERFACE=hybrid  # Use both based on context
```

---

## Development Branching Strategy

### Parallel Development Tracks

Given the multiple optimization approaches identified, we'll pursue **parallel development tracks** to maximize our chances of achieving the 5k token target while minimizing risk.

#### Branch Structure
```
main (current: schema fix, 23k tokens)
├── feature/cli-implementation          # Zen CLI development track
├── feature/token-optimization         # MCP tool optimization track  
├── feature/hybrid-approach           # Combined CLI + optimized MCP
└── experimental/two-stage-enabled    # Test existing token optimization
```

### Track 1: CLI Implementation Branch
**Branch**: `feature/cli-implementation`
**Goal**: Replace MCP tools with unified CLI (target: 1k tokens)
**Timeline**: 4 weeks full implementation, 1 week MVP

#### Development Phases
```yaml
Week_1_MVP:
  - Basic zen.py with Click framework
  - Core modes: debug, codereview, analyze
  - MCP backend communication layer
  - Claude Code template integration

Week_2_Core_Features:
  - All 16 tool modes implemented
  - Session management system
  - Progressive help/discovery system
  - Error handling and recovery

Week_3_UX_Polish:
  - Interactive prompts and guidance  
  - Rich help with examples
  - Output formatting options
  - Integration testing

Week_4_Advanced_Features:
  - Git hooks integration
  - File watching capabilities
  - Report generation/exports
  - Performance optimization
```

#### CLI Branch Milestones
- [ ] **Week 1**: MVP with 3 core commands working
- [ ] **Week 2**: Feature parity with all MCP tools
- [ ] **Week 3**: User experience optimization complete
- [ ] **Week 4**: Production-ready with advanced features

### Track 2: Token Optimization Branch  
**Branch**: `feature/token-optimization`
**Goal**: Optimize existing MCP tools (target: 5k tokens)
**Timeline**: 2 weeks intensive optimization

#### Optimization Approaches
```yaml
Phase_A_Quick_Wins:
  Duration: 3-5 days
  Target: 8k tokens (65% reduction)
  Approach:
    - Ultra-minimal model schemas
    - Remove provider configuration details
    - Consolidate tool descriptions
    - Optimize enum values further

Phase_B_Structural_Changes:
  Duration: 1 week  
  Target: 5k tokens (78% reduction)
  Approach:
    - Category consolidation (16→7 tools)
    - Meta-tool pattern implementation
    - Dynamic parameter loading
    - Schema compression techniques

Phase_C_Advanced_Optimization:
  Duration: 1 week
  Target: 3k tokens (87% reduction)
  Approach:
    - Single orchestrator tool
    - Discovery-action pattern
    - Lazy schema loading
    - Context-aware parameter sets
```

#### Token Optimization Milestones
- [ ] **Day 3**: Ultra-minimal schemas implemented (8k tokens)
- [ ] **Week 1**: Category consolidation complete (5k tokens)
- [ ] **Week 2**: Advanced optimization techniques (3k tokens)

### Track 3: Dynamic MCP Tools Branch ⭐ **NEW PRIORITY** 
**Branch**: `feature/dynamic-mcp-tools`
**Goal**: Implement true 2-step dynamic tool optimization via MCP spec
**Timeline**: 1-2 weeks for complete implementation
**Token Target**: 2k tokens (91% reduction) - **ACHIEVABLE**

#### **BREAKTHROUGH DISCOVERY** 🚀
Your research has uncovered that MCP **DOES** support dynamic tools via:
- `tools/list_changed` notifications 
- `listChanged: true` capability declaration
- Runtime tool schema updates
- Progressive tool registration

#### MCP Dynamic Tools Implementation
```python
# server.py - Enable dynamic tools capability
async def get_capabilities():
    return {
        "capabilities": {
            "tools": {
                "listChanged": True  # Enable dynamic tool updates
            }
        }
    }

# Step 1: Register minimal tool set (200 tokens)
initial_tools = [
    {
        "name": "zen_select_mode", 
        "description": "Select optimal AI mode for your task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string"},
                "confidence": {"type": "string", "enum": ["exploring", "low", "medium", "high"]}
            }
        }
    }
]

# Step 2: After mode selection, dynamically register specific tool (600-800 tokens)
async def update_tools_for_mode(selected_mode: str):
    new_tool = generate_mode_specific_tool(selected_mode)
    
    # Send list_changed notification
    await send_notification({
        "jsonrpc": "2.0",
        "method": "notifications/tools/list_changed"
    })
    
    # Client will call tools/list again and get updated schema
    return [initial_tools[0], new_tool]
```

#### Dynamic Optimization Strategy
```yaml
Phase_1_Registration:
  - Single "zen_select_mode" tool (minimal schema)
  - Token cost: ~200 tokens
  - Handles task analysis and mode selection

Phase_2_Dynamic_Update:
  - Send tools/list_changed notification
  - Register mode-specific tool with focused schema  
  - Token cost: ~600-800 tokens
  - Total: ~1k tokens vs 23k (95% reduction)

Example_Flow:
  1. Client sees only zen_select_mode tool (200 tokens)
  2. User calls zen_select_mode with task description
  3. Server analyzes task, selects optimal mode (debug/review/etc)
  4. Server sends tools/list_changed notification
  5. Client re-requests tools/list
  6. Server returns zen_select_mode + zen_execute_debug (total 1k tokens)
  7. User executes with full functionality
```

#### Two-Stage Branch Goals (Updated)
- [ ] **Day 1-2**: Implement dynamic tool capability declaration
- [ ] **Day 3-5**: Build zen_select_mode tool and mode-specific generators  
- [ ] **Week 1**: Test all 16 tool modes via dynamic registration
- [ ] **Week 2**: Performance optimization and error handling
- [ ] **Goal**: 95% token reduction with zero functionality loss

### Track 4: Hybrid Approach Branch
**Branch**: `feature/hybrid-approach`
**Goal**: Combine best of CLI + optimized MCP
**Timeline**: 1 week after CLI MVP and optimization results

#### Hybrid Strategy
```yaml
CLI_For_Common_Operations:
  - debug, codereview, analyze (80% of usage)
  - Simple parameter sets
  - Fast execution, minimal tokens

Optimized_MCP_For_Complex_Operations:
  - consensus, planning, advanced workflows
  - Multi-turn conversations
  - Complex parameter validation

Smart_Routing:
  - Claude automatically chooses CLI vs MCP
  - Based on operation complexity
  - User can override with --force-cli or --force-mcp
```

### Development Coordination

#### Weekly Integration Points
```yaml
Week_1:
  - CLI MVP ready for testing
  - Token optimization quick wins deployed
  - Two-stage results analyzed
  - Decision point: Which approach to prioritize

Week_2:  
  - CLI core features vs optimized MCP comparison
  - Performance benchmarks across approaches
  - User experience feedback collection
  - Technical debt assessment

Week_3:
  - Integration testing of preferred approach
  - Migration planning for production deployment
  - Documentation and training material prep
  - Rollback strategy confirmation

Week_4:
  - Production deployment preparation
  - A/B testing setup for token optimization
  - Final performance validation
  - Success metrics measurement
```

#### Risk Mitigation Through Parallel Development
```yaml
CLI_Implementation_Risk:
  Risk: Development complexity or timeline overruns
  Mitigation: Token optimization branch provides backup solution
  Fallback: Deploy optimized MCP tools if CLI not ready

Token_Optimization_Risk:  
  Risk: Diminishing returns or functionality compromise
  Mitigation: CLI branch provides alternative approach
  Fallback: Hybrid approach combines best of both

Integration_Risk:
  Risk: Neither approach meets 5k token target
  Mitigation: Hybrid branch combines successful elements
  Fallback: Current system with advanced schema optimization
```

#### Testing Strategy Across Branches

**Continuous Testing Matrix**
```yaml
Performance_Tests:
  - Token usage measurement (automated)
  - Response time benchmarking  
  - Memory usage profiling
  - Connection stability testing

Functionality_Tests:
  - All 16 tool operations working
  - Conversation threading maintained
  - File processing capabilities
  - Error handling robustness

Integration_Tests:  
  - Claude Code compatibility
  - MCP protocol compliance
  - Docker deployment testing
  - Multi-session handling

User_Experience_Tests:
  - Discoverability of features
  - Learning curve assessment  
  - Error message clarity
  - Workflow completion rates
```

#### Merge Strategy
```yaml
Success_Criteria_For_Merge:
  Token_Usage: <5k tokens overhead
  Feature_Parity: 100% of current MCP capabilities  
  Performance: Response time within 10% of current
  Stability: 99%+ success rate in testing
  UX_Quality: Measurably better than current interface

Merge_Priority_Order:
  1. feature/dynamic-mcp-tools (95% token reduction, spec-compliant)
  2. feature/token-optimization (proven wins, fallback)
  3. feature/cli-implementation (alternative approach)
  4. feature/hybrid-approach (combination strategy)
```

#### Branch Maintenance
```yaml
Daily_Sync:
  - Pull latest main into all feature branches
  - Cross-branch learnings sharing  
  - Blocker identification and resolution
  - Progress reporting to decision makers

Weekly_Review:
  - Performance comparison across branches
  - Resource allocation assessment
  - Timeline adjustment if needed
  - Go/no-go decisions for each track
```

### Resource Allocation

#### Estimated Effort Distribution
```yaml
CLI_Implementation: 60% effort (highest potential return)
Token_Optimization: 25% effort (lower risk, proven approach)  
Two_Stage_Testing: 10% effort (immediate validation)
Hybrid_Coordination: 5% effort (integration planning)

Parallel_Development_Benefits:
  - Risk mitigation through multiple approaches
  - Faster time-to-solution through competition
  - Learning acceleration across approaches
  - Higher confidence in final solution choice
```

#### Decision Gates
```yaml
Day_3_Decision: Two-stage results → Continue or pivot
Week_1_Decision: CLI MVP vs Token optimization → Resource reallocation  
Week_2_Decision: Which approach to prioritize for production
Week_3_Decision: Final approach selection and deployment planning
```

---

## Next Steps for Refinement

### Questions for Decision
1. **Scope**: Implement all 16 tools or start with core subset?
2. **Timeline**: 4-week full implementation or MVP in 1 week?
3. **Integration**: Replace MCP tools entirely or hybrid approach?
4. **Features**: Which advanced features (sessions, pipelines, git hooks) are priorities?

### Technical Decisions Needed
1. **Python vs Bash**: Pure bash script or Python with Click framework?
2. **Server Communication**: Direct MCP calls or REST API wrapper?
3. **Session Storage**: Redis, file-based, or in-memory?
4. **Error Handling**: How to gracefully handle server connectivity issues?

### User Experience Decisions
1. **Help System**: How detailed should --help output be?
2. **Output Formatting**: Plain text, markdown, or structured (JSON/YAML)?
3. **Interactive Mode**: Should there be a zen shell/REPL mode?
4. **Configuration**: How much should be configurable vs convention-over-configuration?

---

**Status**: Planning Phase - Ready for Refinement  
**Next**: Review, refine scope, and decide on implementation approach  
**Timeline**: 1-4 weeks depending on scope decisions