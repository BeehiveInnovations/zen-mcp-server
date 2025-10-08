# 🧪 Token Optimization Test Script

## Quick Test #1: Mode Selection
Ask Claude:
```
Use the zen_select_mode tool to analyze this task: "Debug why OAuth tokens aren't persisting across user sessions in our Flask application"
```

Expected response should include:
- Selected mode: `debug`
- Complexity: `simple` or `workflow`
- Token savings message
- Example usage for zen_execute

## Quick Test #2: Execution
After getting the mode, ask:
```
Now use zen_execute with mode="debug" to investigate this OAuth token persistence issue
```

## Quick Test #3: Compare with Original
For comparison, try the old way:
```
Use the debug tool directly to investigate OAuth token persistence
```

## What Success Looks Like

✅ **Stage 1 (zen_select_mode)**:
- Returns in < 2 seconds
- Provides clear mode recommendation
- Shows token savings info

✅ **Stage 2 (zen_execute)**:
- Accepts the mode parameter
- Executes the appropriate tool
- Returns focused results

✅ **Token Savings**:
- Check Claude's token counter (if visible)
- Should see ~95% reduction in context usage
- Faster responses due to smaller schemas

## Troubleshooting

If tools don't appear:
1. Restart Claude Code
2. Check MCP settings
3. Verify server is on port 3001

If token optimization seems disabled:
```bash
docker-compose restart zen-mcp
docker-compose logs zen-mcp | grep "Token Optimization"
```

## Telemetry Check

After testing, check telemetry:
```bash
docker exec zen-mcp-server cat /root/.zen_mcp/token_telemetry.jsonl | tail -5
```

---

Ready to see 95% token reduction in action! 🚀