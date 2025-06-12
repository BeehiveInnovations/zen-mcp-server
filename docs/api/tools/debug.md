# Debug Tool API Reference

## Overview

The **Debug Tool** provides expert-level debugging and root cause analysis capabilities. Leveraging Gemini's analytical power, it systematically investigates errors, analyzes stack traces, and provides comprehensive debugging strategies with 1M token capacity for handling large diagnostic files.

## Tool Schema

```json
{
  "name": "debug",
  "description": "Root cause analysis, error investigation",
  "inputSchema": {
    "type": "object",
    "properties": {
      "error_description": {
        "type": "string",
        "description": "Error message, symptoms, or issue description"
      },
      "error_context": {
        "type": "string",
        "description": "Stack trace, logs, or additional error context",
        "optional": true
      },
      "files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Files or directories that might be related to the issue",
        "optional": true
      },
      "previous_attempts": {
        "type": "string",
        "description": "What has been tried already",
        "optional": true
      },
      "runtime_info": {
        "type": "string",
        "description": "Environment, versions, or runtime information",
        "optional": true
      },
      "thinking_mode": {
        "type": "string",
        "enum": ["minimal", "low", "medium", "high", "max"],
        "default": "medium",
        "description": "Thinking depth for analysis"
      },
      "temperature": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "default": 0.2,
        "description": "Temperature for accuracy in debugging"
      },
      "continuation_id": {
        "type": "string",
        "description": "Thread continuation ID for multi-turn conversations",
        "optional": true
      }
    },
    "required": ["error_description"]
  }
}
```

## Debugging Capabilities

### 1. Stack Trace Analysis

**Multi-language stack trace parsing and analysis**:
- **Python**: Exception hierarchies, traceback analysis, module resolution
- **JavaScript**: Error objects, async stack traces, source map support
- **Java**: Exception chains, thread dumps, JVM analysis
- **C/C++**: Core dumps, segmentation faults, memory corruption
- **Go**: Panic analysis, goroutine dumps, race condition detection

**Example**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Application crashes with segmentation fault during user login",
    "error_context": "Traceback (most recent call last):\n  File \"/app/auth/login.py\", line 45, in authenticate_user\n    result = hash_password(password)\n  File \"/app/utils/crypto.py\", line 23, in hash_password\n    return bcrypt.hashpw(password.encode(), salt)\nSegmentationFault: 11",
    "files": ["/workspace/auth/", "/workspace/utils/crypto.py"],
    "runtime_info": "Python 3.9.7, bcrypt 3.2.0, Ubuntu 20.04, Docker container"
  }
}
```

### 2. Performance Issue Investigation

**Systematic performance debugging**:
- **Memory Leaks**: Heap analysis, reference tracking, garbage collection
- **CPU Bottlenecks**: Profiling data analysis, hot path identification
- **I/O Problems**: Database queries, file operations, network latency
- **Concurrency Issues**: Deadlocks, race conditions, thread contention

**Example**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "API response time degraded from 200ms to 5-10 seconds after recent deployment",
    "error_context": "Memory usage climbing steadily. No obvious errors in logs. CPU usage normal.",
    "files": ["/workspace/api/", "/workspace/database/queries.py"],
    "previous_attempts": "Restarted services, checked database indexes, reviewed recent code changes",
    "runtime_info": "FastAPI 0.68.0, PostgreSQL 13, Redis 6.2, K8s deployment"
  }
}
```

### 3. Integration & Configuration Issues

**System integration debugging**:
- **Database Connections**: Connection pooling, timeout issues, authentication
- **External APIs**: Network connectivity, authentication, rate limiting
- **Configuration**: Environment variables, file permissions, service discovery
- **Deployment**: Container issues, orchestration problems, resource constraints

**Example**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Microservice intermittently fails to connect to database with 'connection timeout' errors",
    "error_context": "Error occurs approximately every 10-15 minutes. Database is accessible from other services. Connection pool shows available connections.",
    "files": ["/workspace/config/database.py", "/workspace/docker-compose.yml"],
    "runtime_info": "Docker Compose, PostgreSQL 13 in separate container, connection pool size: 20"
  }
}
```

### 4. Logic & Business Rule Errors

**Business logic debugging**:
- **Edge Cases**: Boundary conditions, null handling, empty collections
- **State Management**: Inconsistent state, race conditions, data integrity
- **Algorithm Issues**: Incorrect implementations, complexity problems
- **Data Flow**: Transformation errors, validation failures, format issues

**Example**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "E-commerce cart total calculation occasionally shows incorrect amounts during checkout",
    "error_context": "Users report seeing different totals on cart page vs checkout page. Issue seems random but affects ~2% of transactions.",
    "files": ["/workspace/cart/", "/workspace/pricing/"],
    "previous_attempts": "Added logging to cart calculations, reviewed tax calculation logic",
    "runtime_info": "High-traffic e-commerce site, multiple discount types, international tax rules"
  }
}
```

## Response Format

### Comprehensive Debug Report

```json
{
  "content": "# Debug Analysis Report\n\n## Problem Summary\n**Issue**: Segmentation fault during user authentication\n**Severity**: Critical - Application crashes\n**Scope**: Authentication module, affects all user logins\n\n## Root Cause Analysis\n\n### Primary Cause\n**Buffer overflow in bcrypt library** (`utils/crypto.py:23`)\n\n**Technical Details**:\n- bcrypt 3.2.0 has known vulnerability CVE-2023-xxxxx\n- `hash_password()` function passes unvalidated user input\n- Long passwords (>72 chars) trigger buffer overflow\n- Crash occurs in C extension, not caught by Python exception handling\n\n### Contributing Factors\n1. **Missing Input Validation** (`auth/login.py:42`)\n   - No password length validation before hashing\n   - No sanitization of special characters\n\n2. **Outdated Dependencies** (`requirements.txt:15`)\n   - bcrypt 3.2.0 (vulnerable) vs 4.0.1 (patched)\n   - No automated dependency scanning\n\n## Evidence Analysis\n\n### Stack Trace Breakdown\n```\nFile \"/app/auth/login.py\", line 45, in authenticate_user\n    result = hash_password(password)\n```\n**Analysis**: Call originates from user input processing\n\n```\nFile \"/app/utils/crypto.py\", line 23, in hash_password\n    return bcrypt.hashpw(password.encode(), salt)\n```\n**Analysis**: Crash occurs in bcrypt native code, indicates memory corruption\n\n### Code Analysis\n**Vulnerable Code** (`utils/crypto.py:20-25`):\n```python\ndef hash_password(password: str) -> str:\n    salt = bcrypt.gensalt()\n    # VULNERABILITY: No input validation\n    return bcrypt.hashpw(password.encode(), salt)  # Line 23 - crash point\n```\n\n## Reproduction Steps\n1. Send POST request to `/auth/login` with password > 72 characters\n2. Application processes authentication request\n3. `hash_password()` called with long password\n4. bcrypt.hashpw() triggers buffer overflow\n5. Segmentation fault occurs, container restarts\n\n## Immediate Fix\n\n### 1. Input Validation (Deploy immediately)\n```python\ndef hash_password(password: str) -> str:\n    # Add input validation\n    if len(password) > 72:\n        raise ValueError(\"Password too long\")\n    if not password:\n        raise ValueError(\"Password cannot be empty\")\n    \n    salt = bcrypt.gensalt()\n    return bcrypt.hashpw(password.encode(), salt)\n```\n\n### 2. Dependency Update\n```bash\n# Update requirements.txt\nbcrypt>=4.0.1  # Patched version\n\n# Rebuild and redeploy\ndocker build --no-cache .\n```\n\n## Long-term Solutions\n\n### 1. Comprehensive Input Validation\n- Implement request validation middleware\n- Add schema validation for all user inputs\n- Set maximum field lengths application-wide\n\n### 2. Security Hardening\n- Regular dependency scanning (Snyk, OWASP)\n- Automated security testing in CI/CD\n- Runtime application security monitoring\n\n### 3. Error Handling\n- Graceful handling of crypto operations\n- Proper exception propagation\n- User-friendly error messages\n\n## Testing Strategy\n\n### 1. Regression Tests\n```python\ndef test_long_password_handling():\n    with pytest.raises(ValueError):\n        hash_password('x' * 100)  # Should raise, not crash\n\ndef test_empty_password_handling():\n    with pytest.raises(ValueError):\n        hash_password('')\n```\n\n### 2. Security Tests\n- Fuzzing tests for authentication endpoints\n- Boundary value testing for all inputs\n- Load testing with various input combinations\n\n## Monitoring & Prevention\n\n### 1. Enhanced Logging\n```python\ndef hash_password(password: str) -> str:\n    logger.info(f\"Hashing password, length: {len(password)}\")\n    # ... validation and hashing\n    logger.info(\"Password hashing completed successfully\")\n```\n\n### 2. Alerting\n- Container restart alerts\n- Authentication failure rate monitoring\n- Dependency vulnerability scanning\n\n## Verification Steps\n1. Apply input validation patch\n2. Update bcrypt dependency\n3. Run regression test suite\n4. Deploy to staging environment\n5. Perform security testing\n6. Monitor for crashes (should be eliminated)\n7. Deploy to production with rollback plan",
  "metadata": {
    "error_type": "security_vulnerability",
    "severity": "critical",
    "root_cause": "buffer_overflow_in_dependency",
    "fix_complexity": "low",
    "estimated_fix_time": "2-4 hours",
    "risk_level": "high",
    "confidence_level": "high"
  },
  "diagnostic_data": {
    "stack_trace_analyzed": true,
    "vulnerability_identified": "CVE-2023-xxxxx",
    "affected_components": ["auth/login.py", "utils/crypto.py"],
    "reproduction_confirmed": true
  },
  "continuation_id": "debug-session-uuid",
  "status": "success"
}
```

## Advanced Debugging Patterns

### 1. Systematic Investigation Process

**Phase 1: Problem Definition**
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Application experiencing intermittent 500 errors",
    "error_context": "Initial error logs and basic observations",
    "thinking_mode": "low"
  }
}
```

**Phase 2: Deep Analysis**
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Refined problem statement based on initial analysis",
    "error_context": "Complete stack traces, detailed logs, profiling data",
    "files": ["/workspace/affected_modules/"],
    "continuation_id": "phase1-analysis-id",
    "thinking_mode": "high"
  }
}
```

**Phase 3: Solution Validation**
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Proposed solution validation and testing strategy",
    "previous_attempts": "Previous analysis findings and proposed fixes",
    "continuation_id": "phase2-analysis-id",
    "thinking_mode": "medium"
  }
}
```

### 2. Multi-System Integration Debugging

**Component Isolation**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Order processing pipeline failing at random points",
    "files": ["/workspace/order-service/", "/workspace/payment-service/", "/workspace/inventory-service/"],
    "runtime_info": "Microservices architecture, message queues, distributed database",
    "thinking_mode": "high"
  }
}
```

**Data Flow Analysis**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Continuing order pipeline analysis with focus on data flow",
    "error_context": "Request/response logs, message queue contents, database state",
    "continuation_id": "component-analysis-id"
  }
}
```

### 3. Performance Debugging Workflow

**Resource Analysis**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Memory usage climbing steadily leading to OOM kills",
    "error_context": "Memory profiling data, heap dumps, GC logs",
    "files": ["/workspace/memory-intensive-modules/"],
    "thinking_mode": "high"
  }
}
```

**Optimization Strategy**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Memory leak root cause identified, need optimization strategy",
    "previous_attempts": "Profiling analysis completed, leak sources identified",
    "continuation_id": "memory-analysis-id"
  }
}
```

## Large File Analysis Capabilities

### 1M Token Context Window

**Comprehensive Log Analysis**:
- **Large Log Files**: Full application logs, database logs, system logs
- **Memory Dumps**: Complete heap dumps and stack traces
- **Profiling Data**: Detailed performance profiling outputs
- **Multiple File Types**: Logs, configs, source code, database dumps

**Example with Large Files**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Production system crash analysis",
    "files": [
      "/workspace/logs/application.log",    // 50MB log file
      "/workspace/logs/database.log",      // 30MB log file  
      "/workspace/dumps/heap_dump.txt",    // 100MB heap dump
      "/workspace/traces/stack_trace.log"  // 20MB stack trace
    ],
    "thinking_mode": "max"
  }
}
```

### Smart File Processing

**Priority-Based Processing**:
1. **Stack Traces**: Immediate analysis for crash cause
2. **Error Logs**: Recent errors and patterns
3. **Application Logs**: Business logic flow analysis
4. **System Logs**: Infrastructure and environment issues

**Content Analysis**:
- **Pattern Recognition**: Recurring errors and trends
- **Timeline Analysis**: Event correlation and sequence
- **Performance Metrics**: Response times, resource usage
- **Dependency Tracking**: External service interactions

## Integration with Development Workflow

### 1. CI/CD Integration

**Automated Debugging**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Build failure in CI pipeline",
    "error_context": "CI logs, test output, build artifacts",
    "files": ["/workspace/.github/workflows/", "/workspace/tests/"],
    "runtime_info": "GitHub Actions, Docker build, pytest"
  }
}
```

### 2. Production Incident Response

**Incident Analysis**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Production outage - service unavailable",
    "error_context": "Monitoring alerts, service logs, infrastructure metrics",
    "files": ["/workspace/monitoring/", "/workspace/logs/"],
    "runtime_info": "Kubernetes cluster, multiple replicas, load balancer",
    "thinking_mode": "max"
  }
}
```

### 3. Code Review Integration

**Bug Investigation**:
```json
{
  "name": "debug",
  "arguments": {
    "error_description": "Regression introduced in recent PR",
    "files": ["/workspace/modified_files/"],
    "previous_attempts": "Code review completed, tests passing, issue found in production",
    "runtime_info": "Recent deployment, feature flag enabled"
  }
}
```

## Best Practices

### Effective Error Reporting

**Comprehensive Error Description**:
```
Error Description:
- What happened: Application crashes during user registration
- When: Occurs intermittently, ~10% of registration attempts
- Where: Registration form submission, after email validation
- Who: Affects both new and existing users
- Impact: Users cannot complete registration, data loss possible
```

**Detailed Context Provision**:
```
Error Context:
- Stack trace: [Full stack trace with line numbers]
- Request data: [Sanitized request payload]
- Environment state: [Memory usage, CPU load, active connections]
- Timing: [Request timestamps, duration, timeout values]
- Dependencies: [Database state, external API responses]
```

### Debugging Workflow

1. **Collect Comprehensive Information**: Gather all available diagnostic data
2. **Isolate the Problem**: Narrow down to specific components or operations
3. **Analyze Dependencies**: Consider external systems and interactions
4. **Validate Hypotheses**: Test theories with evidence and reproduction
5. **Document Findings**: Create detailed reports for future reference

### Performance Optimization

1. **Use Appropriate Thinking Mode**: Match complexity to issue severity
2. **Leverage Large Context**: Include comprehensive diagnostic files
3. **Iterative Analysis**: Use continuation for complex debugging sessions
4. **Cross-Reference**: Compare with similar issues and solutions

---

The Debug Tool provides systematic, expert-level debugging capabilities that can handle complex production issues while maintaining accuracy and providing actionable solutions for rapid incident resolution.

