# Claude Code CLI Test Commands for A/B Testing

## Important: How to Run Zen Tools in Claude Code CLI

In Claude Code CLI, Zen MCP tools must be invoked through the MCP protocol, not as bash commands.

**Correct format**: Use the `mcp__zen__` prefix and proper parameter structure
**Incorrect format**: `zen analyze --model gemini-2.5-flash` (this won't work)

## Baseline Test Commands (9 tests)

### Test 1: Architecture Analysis (gemini-2.5-flash)
```
Use mcp__zen__analyze with these parameters:
- step: "Analyze the token optimization architecture in this codebase. Focus on the two-stage approach, mode selection logic, and telemetry system."
- step_number: 1
- total_steps: 1  
- next_step_required: false
- findings: "Starting analysis of token optimization architecture"
- relevant_files: ["/app/server.py", "/app/tools/mode_selector.py", "/app/token_optimization_config.py"]
- model: "gemini-2.5-flash"
```

### Test 2: Security Audit (grok-code-fast-1)
```
Use mcp__zen__secaudit with these parameters:
- step: "Perform comprehensive security audit of the MCP server focusing on: TCP transport security, Docker container isolation, API key handling, and input validation."
- step_number: 1
- total_steps: 1
- next_step_required: false
- findings: "Starting security audit"
- relevant_files: ["/app/server.py", "/app/providers", "/app/docker-compose.yml"]
- model: "grok-code-fast-1"
```

### Test 3: Performance Debug (o3-mini)
```
Use mcp__zen__debug with these parameters:
- step: "Investigate potential performance bottlenecks in the token optimization system. Analyze the two-stage execution flow, Redis conversation memory, and provider selection logic."
- step_number: 1
- total_steps: 1
- next_step_required: false
- findings: "Starting performance investigation"
- confidence: "exploring"
- relevant_files: ["/app/token_optimization_config.py", "/app/tools/mode_selector.py", "/app/utils/conversation_memory.py"]
- model: "o3-mini"
```

### Test 4: Code Review (gemini-2.5-flash)
```
Use mcp__zen__codereview with these parameters:
- step: "Review the token optimization implementation for code quality, maintainability, and best practices."
- step_number: 1
- total_steps: 1
- next_step_required: false
- findings: "Starting code review"
- relevant_files: ["/app/server_token_optimized.py", "/app/tools/mode_executor.py"]
- model: "gemini-2.5-flash"
```

### Test 5: Refactoring Analysis (grok-code-fast-1)
```
Use mcp__zen__refactor with these parameters:
- step: "Suggest refactoring opportunities for the MCP server architecture to improve modularity, reduce coupling, and enhance testability. Consider the provider system and tool registration."
- step_number: 1
- total_steps: 1
- next_step_required: false
- findings: "Starting refactoring analysis"
- relevant_files: ["/app/server.py", "/app/providers/registry.py", "/app/tools/__init__.py"]
- model: "grok-code-fast-1"
```

### Test 6: Test Generation (o3-mini)
```
Use mcp__zen__testgen with these parameters:
- step: "Generate comprehensive test strategy for token optimization feature including unit tests, integration tests, and A/B testing validation. Focus on edge cases and error scenarios."
- step_number: 1
- total_steps: 1
- next_step_required: false
- findings: "Starting test generation"
- relevant_files: ["/app/token_optimization_config.py", "/app/tools/mode_selector.py"]
- model: "o3-mini"
```

### Test 7: Debug Docker Issue (gemini-2.5-flash)
```
Use mcp__zen__debug with these parameters:
- step: "Debug why the Docker dual-transport mode occasionally restarts. Analyze server.py transport logic, Docker configuration, and error handling patterns."
- step_number: 1
- total_steps: 1
- next_step_required: false
- findings: "Starting Docker transport investigation"
- confidence: "exploring"
- relevant_files: ["/app/server.py", "/app/docker-compose.yml"]
- model: "gemini-2.5-flash"
```

### Test 8: Consensus on WebSocket (multiple models)
```
Use mcp__zen__consensus with these parameters:
- step: "Should we implement WebSocket transport in addition to TCP and stdio? Consider: performance implications, client complexity, Docker networking, and maintenance overhead."
- step_number: 1
- total_steps: 3
- next_step_required: true
- findings: "Starting consensus gathering"
- models: [{"model": "o3-mini"}, {"model": "gemini-2.5-flash"}, {"model": "grok-code-fast-1"}]
```

### Test 9: Deep Investigation (grok-code-fast-1)
```
Use mcp__zen__thinkdeep with these parameters:
- step: "Investigate the optimal token budget allocation strategy for different model types. Consider context windows, pricing, response quality, and conversation threading requirements."
- step_number: 1
- total_steps: 1
- next_step_required: false
- findings: "Starting deep investigation"
- confidence: "high"
- relevant_files: ["/app/utils/token_utils.py", "/app/providers/base.py"]
- model: "grok-code-fast-1"
```

## Test Protocol

### Phase 1: Baseline Testing (current configuration)
1. Verify `.env` has `ZEN_TOKEN_OPTIMIZATION=disabled`
2. Container should already be running with baseline config
3. Execute each test command above
4. Monitor logs: `docker exec zen-mcp-server tail -f /app/logs/mcp_server.log`
5. Check telemetry after each test

### Phase 2: Optimized Testing
1. Update `.env`: `ZEN_TOKEN_OPTIMIZATION=enabled`
2. Restart container: `docker-compose restart zen-mcp`
3. Restart Claude Code CLI connection
4. Execute the same 9 tests
5. Compare telemetry results

## Monitoring Commands

Check execution logs:
```bash
docker exec zen-mcp-server tail -50 /app/logs/mcp_activity.log
```

Check telemetry (when implemented):
```bash
docker exec zen-mcp-server cat ~/.zen_mcp/token_telemetry.jsonl | tail -5
```

## Note on File Paths

All file paths must use Docker container paths (`/app/...`) not host paths (`/Users/wrk/...`) because the MCP server runs inside the Docker container.