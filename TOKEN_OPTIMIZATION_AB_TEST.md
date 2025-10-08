# Token Optimization A/B Test Plan

## Test Overview
Compare token usage between baseline and optimized modes using identical queries across different models.

**Goal**: Validate 95% token reduction (43k → 2k tokens) while maintaining effectiveness.

## Test Configuration

### Baseline Mode (Control)
```env
ZEN_TOKEN_OPTIMIZATION=disabled
ZEN_OPTIMIZATION_MODE=two_stage  
ZEN_TOKEN_TELEMETRY=true
ZEN_OPTIMIZATION_VERSION=v5.11.0-baseline
```

### Optimized Mode (Treatment)  
```env
ZEN_TOKEN_OPTIMIZATION=enabled
ZEN_OPTIMIZATION_MODE=two_stage
ZEN_TOKEN_TELEMETRY=true  
ZEN_OPTIMIZATION_VERSION=v5.12.0-alpha-two-stage
```

## Target Models for Testing

1. **Gemini-2.5-flash** - Fast responses, good for code analysis
2. **grok-fast-code-1** - Code-focused model via X.AI  
3. **o3-mini** - Smaller GPT model for logical reasoning

## Test Questions

### Test Set 1: Code Analysis & Architecture

#### Q1.1: Complex Architecture Analysis
```bash
zen analyze "Analyze the token optimization architecture in this codebase. Focus on the two-stage approach, mode selection logic, and telemetry system. Include files: server.py, tools/mode_selector.py, token_optimization_config.py"
```

#### Q1.2: Security Audit  
```bash
zen secaudit "Perform comprehensive security audit of the MCP server focusing on: TCP transport security, Docker container isolation, API key handling, and input validation. Include relevant security-related files."
```

#### Q1.3: Performance Analysis
```bash
zen debug "Investigate potential performance bottlenecks in the token optimization system. Analyze the two-stage execution flow, Redis conversation memory, and provider selection logic."
```

### Test Set 2: Code Review & Refactoring

#### Q2.1: Multi-file Code Review
```bash
zen codereview "Review the token optimization implementation for code quality, maintainability, and best practices. Focus on server_token_optimized.py, tools/mode_executor.py, and the overall integration."
```

#### Q2.2: Refactoring Suggestions
```bash
zen refactor "Suggest refactoring opportunities for the MCP server architecture to improve modularity, reduce coupling, and enhance testability. Consider the provider system and tool registration."
```

#### Q2.3: Test Strategy Development
```bash
zen testgen "Generate comprehensive test strategy for token optimization feature including unit tests, integration tests, and A/B testing validation. Focus on edge cases and error scenarios."
```

### Test Set 3: Advanced Problem Solving

#### Q3.1: Debugging Complex Issue
```bash
zen debug "Debug why the Docker dual-transport mode occasionally restarts. Analyze server.py transport logic, Docker configuration, and error handling patterns. Confidence: exploring"
```

#### Q3.2: Consensus on Technical Decision
```bash
zen consensus "Should we implement WebSocket transport in addition to TCP and stdio? Consider: performance implications, client complexity, Docker networking, and maintenance overhead."
```

#### Q3.3: Deep Technical Investigation  
```bash
zen thinkdeep "Investigate the optimal token budget allocation strategy for different model types. Consider context windows, pricing, response quality, and conversation threading requirements. Confidence: high"
```

## Testing Protocol

### Phase 1: Baseline Testing
1. Ensure `.env` has `ZEN_TOKEN_OPTIMIZATION=disabled`
2. Restart container: `docker-compose restart zen-mcp`
3. Restart Claude Code CLI
4. Execute all test questions, recording:
   - Token usage per query
   - Response quality/completeness  
   - Execution time
   - Any errors or issues

### Phase 2: Optimized Testing  
1. Update `.env` to `ZEN_TOKEN_OPTIMIZATION=enabled`
2. Restart container: `docker-compose restart zen-mcp`
3. Restart Claude Code CLI
4. Execute identical test questions, recording same metrics

### Phase 3: Analysis
1. Compare telemetry from `logs/token_telemetry.jsonl`
2. Validate token reduction percentages
3. Assess response quality differences
4. Document any functional regressions

## Success Criteria

### Token Usage Reduction
- **Target**: 85-95% reduction (43k → 2-6k tokens)
- **Acceptable**: 70%+ reduction with maintained quality
- **Failure**: <50% reduction or significant quality loss

### Response Quality
- **Identical functionality**: All queries should work in both modes
- **Comparable depth**: Similar analysis depth and accuracy  
- **No missing features**: All tool capabilities preserved

### Performance
- **Response time**: Optimized mode should be faster or equivalent
- **Error rate**: No increase in errors or failures
- **Stability**: No additional container restarts or issues

## Results Template

### Test Results Summary
| Model | Mode | Avg Tokens | Total Time | Quality Score | Errors |
|-------|------|------------|------------|---------------|---------|
| Gemini-2.5-flash | Baseline | | | | |
| Gemini-2.5-flash | Optimized | | | | |
| grok-fast-code-1 | Baseline | | | | |  
| grok-fast-code-1 | Optimized | | | | |
| o3-mini | Baseline | | | | |
| o3-mini | Optimized | | | | |

### Key Findings
- [ ] Token reduction achieved: __%
- [ ] Response quality maintained: Yes/No
- [ ] Performance improvement: __%  
- [ ] Issues identified: ____________

## Notes
- Use Claude Code CLI for true context pressure testing
- Record exact commands used for reproducibility
- Monitor Docker container stability during testing
- Save telemetry files for detailed analysis