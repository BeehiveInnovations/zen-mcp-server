# MCP Token Optimization - Recommendations

## Current Situation
The two-stage token optimization achieves 95% reduction but breaks MCP protocol at a fundamental level. The server rejects all requests with "Invalid request parameters" before handlers are even called.

## Root Cause
The MCP server library appears to perform validation during initialization that our optimized tools fail, causing the entire protocol layer to become non-functional.

## Recommendations

### 1. Immediate Fix: Revert and Research
```bash
# Disable optimization temporarily
ZEN_TOKEN_OPTIMIZATION=disabled
docker-compose restart zen-mcp
```

This restores functionality while we investigate.

### 2. Investigation Path
- Check if MCP requires specific base classes (not just duck typing)
- Verify all async/await patterns match MCP expectations
- Test if the issue is with tool count (12 vs 16+ original)
- Check if SimpleTool base class conflicts with MCP internals

### 3. Alternative Implementation: Proxy Pattern

Instead of modifying the tool registry directly, implement a proxy layer:

```python
# Keep original tools for MCP compliance
ORIGINAL_TOOLS = { /* all 16 original tools */ }

# Add optimization layer in handle_call_tool
async def handle_call_tool(name, arguments):
    # Intercept and optimize BEFORE MCP validation
    if optimization_enabled and name in ["debug", "codereview", ...]:
        # Redirect to two-stage flow
        return await handle_optimized_flow(name, arguments)
    
    # Fall through to original tools
    return await original_handle_call_tool(name, arguments)
```

### 4. Hybrid Approach: Gradual Migration

Start with a subset of tools:
1. Keep most tools original (for MCP compliance)
2. Add only zen_select_mode as new tool
3. Handle optimization internally within existing tools

### 5. MCP Library Investigation

The core issue appears to be in the MCP library itself. Consider:
- Filing an issue with MCP library maintainers
- Examining MCP source code for validation logic
- Testing with different MCP library versions

### 6. Workaround: Client-Side Optimization

Instead of server-side optimization, implement in Claude Code template:
```javascript
// Claude Code template
const optimizeRequest = (tool, args) => {
  // Stage 1: Determine mode
  const mode = selectMode(tool, args);
  // Stage 2: Minimal schema
  return { tool: 'zen_execute', args: { mode, request: minimalArgs }};
};
```

## Testing Strategy

1. **Minimal Reproduction**: Create smallest possible server that exhibits the issue
2. **Binary Search**: Add tools one by one to find breaking point
3. **Type Checking**: Ensure all tool objects match MCP's expected types exactly
4. **Protocol Tracing**: Use Wireshark/tcpdump to see exact JSON-RPC messages

## Long-Term Solution

Consider implementing token optimization at a different layer:
- **Transport Layer**: Compress JSON-RPC messages
- **Caching Layer**: Cache repeated schema definitions
- **Smart Routing**: Use lightweight tools that delegate to heavy ones

## Conclusion

The two-stage optimization is architecturally sound but conflicts with MCP's internal validation. The best path forward is:

1. **Short term**: Disable optimization, restore functionality
2. **Medium term**: Implement proxy pattern or hybrid approach
3. **Long term**: Work with MCP maintainers for native support

The 95% token reduction is achievable, but needs to work within MCP's constraints rather than against them.