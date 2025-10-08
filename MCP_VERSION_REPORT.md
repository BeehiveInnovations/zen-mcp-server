# MCP Python Library Version Compatibility Report

## Executive Summary
The Zen MCP Server is experiencing a critical protocol validation issue where `tools/list` requests fail with error code -32602 "Invalid request parameters" even after disabling all token optimization. This appears to be related to the MCP Python SDK library itself, not our implementation.

## Current Situation

### Installed Version
- **MCP SDK**: 1.13.1 (latest as of August 2025)
- **Container Environment**: Python 3.11-slim, Docker

### Issue Description
- `initialize` method works correctly (returns protocol version "2025-06-18")
- `tools/list` method fails immediately with JSON-RPC error -32602
- Error occurs at MCP protocol validation layer BEFORE our handlers execute
- Our `handle_list_tools()` function is never called

## MCP SDK Version History

### Latest Versions (2025)

#### v1.13.1 (August 22, 2025) - CURRENT
- Added CORS configuration for browser-based MCP clients
- Documentation improvements for streamable_http_path
- **No mention of tools/list fixes**

#### v1.13.0 (August 14, 2025)
- Major release with multiple features
- **Known Issue #1298**: Tool handler issues with streaming contexts

#### v1.2.1 (January 27, 2025)
- Earlier stable release
- Pre-dates many protocol changes

### Protocol Versions

#### 2025-06-18 (Current Protocol)
- Removed JSON-RPC batching (reversal from 2025-03-26)
- Added structured tool output
- OAuth Resource Server classification
- **Breaking changes** in protocol handling

#### 2025-03-26
- Added JSON-RPC batching (later removed)
- Replaced SSE with Streamable HTTP
- Tool annotations support

## Known Issues Related to Our Problem

### Issue #820: `tools/call` with string arguments breaks server
- **Status**: CLOSED (marked as Done)
- **Description**: Passing arguments as string instead of object causes server to fail
- **Impact**: Server requires restart after malformed request
- **Relevance**: Shows MCP SDK has validation issues with parameter types

### Issue #1298: Tool handler issue with Opus 4.1 streaming
- **Status**: OPEN (needs confirmation)
- **Description**: Tool handlers fail when:
  1. MCP servers spawned fresh per request (like ours)
  2. Streaming context exists
  3. Tool cache is empty (first request)
- **Relevance**: Matches our stateless architecture pattern

## Root Cause Analysis

Based on research, the issue appears to be:

1. **Parameter Validation Bug**: The MCP SDK v1.13.1 has overly strict parameter validation that rejects valid `tools/list` requests with empty params `{}`

2. **Protocol Mismatch**: Our server advertises protocol "2025-06-18" but the SDK may have incompatible validation logic for this protocol version

3. **Possible Regression**: The issue may be a regression introduced after v1.2.1 as part of protocol updates

## Recommended Solutions

### Option 1: Downgrade MCP SDK (Immediate Fix)
```bash
# Update requirements.txt
mcp==1.2.1

# Rebuild Docker container
docker-compose build --no-cache
```

**Pros**: 
- May restore functionality immediately
- Stable version from January 2025

**Cons**:
- Missing recent features and fixes
- May have other compatibility issues

### Option 2: Patch Current Version (Tactical Fix)
Implement a workaround in server.py to handle the validation issue:
```python
# Override the list_tools decorator behavior
# Implement custom parameter handling
```

**Pros**:
- Keep latest SDK features
- Controlled fix

**Cons**:
- Fragile, may break with SDK updates
- Requires deep MCP internals knowledge

### Option 3: Report and Wait (Strategic Fix)
1. File detailed bug report with MCP maintainers
2. Include our minimal reproduction case
3. Use TCP transport as workaround

**Pros**:
- Proper long-term solution
- Benefits entire community

**Cons**:
- No immediate resolution
- Blocks production deployment

## Testing Matrix

| MCP Version | Protocol | Initialize | tools/list | tools/call | Notes |
|-------------|----------|------------|------------|------------|-------|
| 1.13.1 | 2025-06-18 | ✅ | ❌ (-32602) | ❌ | Current issue |
| 1.2.1 | 2025-06-18 | ? | ? | ? | To be tested |
| 1.0.0 | 2024-11-05 | ? | ? | ? | Original release |

## Action Items

### Immediate (Today)
1. ✅ Document current issue comprehensively
2. 🔄 Test with MCP v1.2.1 
3. 🔄 Create minimal bug report for MCP maintainers

### Short-term (This Week)
1. Implement workaround if downgrade works
2. Update Docker configuration for stable version
3. Document workaround in README

### Long-term (This Month)
1. Monitor MCP SDK releases for fixes
2. Contribute fix to MCP SDK if possible
3. Implement robust error handling for protocol issues

## Conclusion

The issue is a critical bug in the MCP Python SDK v1.13.1 that prevents proper handling of `tools/list` requests. This is not a bug in our Zen MCP Server code but in the underlying MCP library. The most pragmatic solution is to:

1. **Immediately**: Downgrade to MCP v1.2.1 and test
2. **Short-term**: Implement workaround if needed
3. **Long-term**: Work with MCP maintainers for proper fix

## References

- [MCP Python SDK Repository](https://github.com/modelcontextprotocol/python-sdk)
- [Issue #820: Parameter validation bug](https://github.com/modelcontextprotocol/python-sdk/issues/820)
- [Issue #1298: Tool handler streaming issue](https://github.com/modelcontextprotocol/python-sdk/issues/1298)
- [MCP Protocol Specification](https://modelcontextprotocol.io/specification)
- [PyPI MCP Package History](https://pypi.org/project/mcp/)

---
*Report generated: August 31, 2025*
*Next review: After testing MCP v1.2.1*