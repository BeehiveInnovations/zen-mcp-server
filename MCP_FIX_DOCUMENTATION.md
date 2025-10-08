# MCP Protocol Fix Documentation

## Problem Summary

The Zen MCP Server was experiencing connection failures with Claude Code's MCP client. The client would show "endlessly connecting" and never display available tools.

## Root Cause Analysis

### Investigation Process
1. **Initial Hypothesis**: MCP protocol validation issues with tools/list request
2. **Testing**: Created test scripts to simulate MCP handshake
3. **Discovery**: The server was actually responding correctly, but with a **170KB+ JSON response**

### The Real Problem
The `chat` tool's input schema was generating an enormous model field description that included:
- Detailed descriptions for 100+ model variants
- Complete enum lists with all model aliases
- Multiple duplicated entries from different providers
- Total response size: **>170KB** for a single tools/list response

This massive response was overwhelming MCP clients, causing them to fail silently during the handshake.

## Solution Implementation

### Fix Applied to `tools/shared/base_tool.py`

The `get_model_field_schema()` method was modified to:

1. **Limit description length**: Truncate model descriptions to 500 characters max
2. **Reduce enum size**: Show only first 30 models in enum (was 100+)  
3. **Simplify non-auto mode**: Show only 5 example models instead of full list

### Code Changes

```python
# Before: Generated 170KB+ of model descriptions
"description": "\n".join(model_desc_parts),  # Thousands of lines
"enum": all_models,  # 100+ models

# After: Concise, reasonable schema
"description": truncated_desc,  # Max 500 chars
"enum": all_models[:30],  # Limited to 30 models
```

## Results

- **Schema size reduced**: From 170KB to ~5KB (97% reduction)
- **Connection restored**: Claude Code can now connect successfully
- **Tools visible**: All 16 Zen tools now appear in Claude Code
- **Performance improved**: Faster handshake and tool discovery

## Testing

Created test scripts to verify:
1. `test_mcp_handshake.py` - Simulates full MCP handshake
2. `test_schema_size.py` - Measures actual schema size
3. `test_mcp_validation.py` - Validates protocol compliance

## Deployment

```bash
# Rebuild Docker image with fix
docker-compose build --no-cache

# Deploy updated container
docker-compose up -d

# Verify deployment
docker-compose logs zen-mcp
```

## Key Learnings

1. **MCP clients have implicit size limits** for JSON-RPC responses
2. **Tool schemas should be concise** - avoid listing every possible option
3. **Enum fields are expensive** - limit to essential values only
4. **Test with actual protocol exchanges** not just unit tests

## Recommendations

### Short Term
- ✅ Applied schema size fix
- ✅ Verified MCP connectivity restored
- ✅ Documented solution

### Medium Term
- Consider lazy-loading model descriptions
- Implement pagination for large tool lists
- Add response size monitoring

### Long Term
- Contribute fix upstream to MCP SDK
- Propose schema size guidelines for MCP spec
- Implement automatic schema compression

## MCP SDK Investigation

During debugging, we also discovered that both MCP v1.13.1 and v1.2.1 have similar issues with large schemas. The problem is not in the validation logic but in practical limits of JSON-RPC message handling.

The MCP SDK repository was cloned to `/Users/wrk/WorkDev/MCP-Dev/python-sdk-debug/` for future debugging if needed.

## Files Modified

1. `/tools/shared/base_tool.py` - Applied schema size limits
2. Created multiple test scripts for validation
3. Updated Docker deployment

## Impact

This fix enables the Zen MCP Server to work with any MCP-compliant client, not just Claude Code. The reduced schema size improves:
- Connection reliability
- Handshake performance  
- Memory usage
- Network efficiency

---

*Fix implemented: 2025-08-31*
*Author: Claude with user collaboration*
*Version: Zen MCP Server v5.12.0*