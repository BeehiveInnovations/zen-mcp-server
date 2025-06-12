# CodeReview Tool API Reference

## Overview

The **CodeReview Tool** provides comprehensive code quality, security, and bug detection analysis. Based on Gemini's deep analytical capabilities, it performs systematic code review with severity-based issue categorization and specific fix recommendations.

## Tool Schema

```json
{
  "name": "codereview",
  "description": "Code quality, security, bug detection",
  "inputSchema": {
    "type": "object",
    "properties": {
      "files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Code files or directories to review"
      },
      "context": {
        "type": "string", 
        "description": "User's summary of what the code does, expected behavior, constraints, and review objectives"
      },
      "review_type": {
        "type": "string",
        "enum": ["full", "security", "performance", "quick"],
        "default": "full",
        "description": "Type of review to perform"
      },
      "severity_filter": {
        "type": "string",
        "enum": ["critical", "high", "medium", "all"],
        "default": "all",
        "description": "Minimum severity level to report"
      },
      "standards": {
        "type": "string",
        "description": "Coding standards to enforce",
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
        "description": "Temperature for consistency in analysis"
      },
      "continuation_id": {
        "type": "string",
        "description": "Thread continuation ID for multi-turn conversations",
        "optional": true
      }
    },
    "required": ["files", "context"]
  }
}
```

## Review Types

### 1. Full Review (default)

**Comprehensive analysis covering**:
- **Security**: Vulnerability detection, authentication flaws, input validation
- **Performance**: Bottlenecks, resource usage, optimization opportunities  
- **Quality**: Maintainability, readability, technical debt
- **Bugs**: Logic errors, edge cases, exception handling
- **Standards**: Coding conventions, best practices, style consistency

**Example**:
```json
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/src/auth/", "/workspace/src/api/"],
    "context": "Authentication and API modules for user management system. Handles JWT tokens, password hashing, and role-based access control.",
    "review_type": "full",
    "thinking_mode": "high"
  }
}
```

### 2. Security Review

**Focused security assessment**:
- **Authentication**: Token handling, session management, password security
- **Authorization**: Access controls, privilege escalation, RBAC implementation
- **Input Validation**: SQL injection, XSS, command injection vulnerabilities
- **Data Protection**: Encryption, sensitive data exposure, logging security
- **Configuration**: Security headers, SSL/TLS, environment variables

**Example**:
```json
{
  "name": "codereview", 
  "arguments": {
    "files": ["/workspace/auth/", "/workspace/middleware/"],
    "context": "Security review for production deployment. System handles PII data and financial transactions.",
    "review_type": "security",
    "severity_filter": "high",
    "thinking_mode": "high"
  }
}
```

### 3. Performance Review

**Performance-focused analysis**:
- **Algorithms**: Time/space complexity, optimization opportunities
- **Database**: Query efficiency, N+1 problems, indexing strategies
- **Caching**: Cache utilization, invalidation strategies, cache stampede
- **Concurrency**: Thread safety, deadlocks, race conditions
- **Resource Management**: Memory leaks, connection pooling, file handling

**Example**:
```json
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/api/", "/workspace/database/"],
    "context": "API layer experiencing high latency under load. Database queries taking 2-5 seconds average.",
    "review_type": "performance", 
    "thinking_mode": "high"
  }
}
```

### 4. Quick Review

**Rapid assessment focusing on**:
- **Critical Issues**: Severe bugs and security vulnerabilities only
- **Code Smells**: Obvious anti-patterns and maintainability issues
- **Quick Wins**: Easy-to-fix improvements with high impact
- **Standards**: Basic coding convention violations

**Example**:
```json
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/feature/new-payment-flow.py"],
    "context": "Quick review of new payment processing feature before merge",
    "review_type": "quick",
    "severity_filter": "high"
  }
}
```

## Severity Classification

### Critical Issues
- **Security vulnerabilities** with immediate exploitation risk
- **Data corruption** or loss potential
- **System crashes** or availability impacts
- **Compliance violations** (GDPR, SOX, HIPAA)

**Example Finding**:
```
🔴 CRITICAL - SQL Injection Vulnerability
File: api/users.py:45
Code: f"SELECT * FROM users WHERE id = {user_id}"
Impact: Complete database compromise possible
Fix: Use parameterized queries: cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### High Severity Issues
- **Authentication bypasses** or privilege escalation
- **Performance bottlenecks** affecting user experience
- **Logic errors** in critical business flows
- **Resource leaks** causing system degradation

**Example Finding**:
```
🟠 HIGH - Authentication Bypass
File: middleware/auth.py:23
Code: if token and jwt.decode(token, verify=False):
Impact: JWT signature verification disabled
Fix: Enable verification: jwt.decode(token, secret_key, algorithms=["HS256"])
```

### Medium Severity Issues
- **Code maintainability** problems
- **Minor security** hardening opportunities
- **Performance optimizations** for better efficiency
- **Error handling** improvements

**Example Finding**:
```
🟡 MEDIUM - Error Information Disclosure
File: api/auth.py:67
Code: return {"error": str(e)}
Impact: Sensitive error details exposed to clients
Fix: Log full error, return generic message: logger.error(str(e)); return {"error": "Authentication failed"}
```

### Low Severity Issues
- **Code style** and convention violations
- **Documentation** gaps
- **Minor optimizations** with minimal impact
- **Code duplication** opportunities

## Response Format

### Structured Review Report

```json
{
  "content": "# Code Review Report\n\n## Executive Summary\n- **Files Reviewed**: 12\n- **Issues Found**: 23 (3 Critical, 7 High, 9 Medium, 4 Low)\n- **Overall Quality**: Moderate - Requires attention before production\n\n## Critical Issues (3)\n\n### 🔴 SQL Injection in User Query\n**File**: `api/users.py:45`\n**Severity**: Critical\n**Issue**: Unsafe string interpolation in SQL query\n```python\n# Current (vulnerable)\nquery = f\"SELECT * FROM users WHERE id = {user_id}\"\n\n# Fixed (secure)\nquery = \"SELECT * FROM users WHERE id = %s\"\ncursor.execute(query, (user_id,))\n```\n**Impact**: Complete database compromise\n**Priority**: Fix immediately\n\n## Security Assessment\n- Authentication mechanism: JWT with proper signing ✅\n- Input validation: Missing in 3 endpoints ❌\n- Error handling: Overly verbose error messages ❌\n\n## Performance Analysis\n- Database queries: 2 N+1 query problems identified\n- Caching: No caching layer implemented\n- Algorithm efficiency: Sorting algorithm in user_search O(n²)\n\n## Recommendations\n1. **Immediate**: Fix critical SQL injection vulnerabilities\n2. **Short-term**: Implement input validation middleware\n3. **Medium-term**: Add caching layer for frequently accessed data\n4. **Long-term**: Refactor sorting algorithms for better performance",
  "metadata": {
    "review_type": "full",
    "files_reviewed": 12,
    "lines_of_code": 3420,
    "issues_by_severity": {
      "critical": 3,
      "high": 7, 
      "medium": 9,
      "low": 4
    },
    "security_score": 6.5,
    "maintainability_score": 7.2,
    "performance_score": 5.8,
    "overall_quality": "moderate"
  },
  "continuation_id": "review-550e8400",
  "status": "success"
}
```

### Issue Categorization

**Security Issues**:
- Authentication and authorization flaws
- Input validation vulnerabilities  
- Data exposure and privacy concerns
- Cryptographic implementation errors

**Performance Issues**:
- Algorithm inefficiencies
- Database optimization opportunities
- Memory and resource management
- Concurrency and scaling concerns

**Quality Issues**:
- Code maintainability problems
- Technical debt accumulation
- Testing coverage gaps
- Documentation deficiencies

**Bug Issues**:
- Logic errors and edge cases
- Exception handling problems
- Race conditions and timing issues
- Integration and compatibility problems

## Advanced Usage Patterns

### 1. Pre-Commit Review

**Before committing changes**:
```json
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/modified_files.txt"],
    "context": "Pre-commit review of changes for user authentication feature",
    "review_type": "full",
    "severity_filter": "medium",
    "standards": "PEP 8, security-first coding practices"
  }
}
```

### 2. Security Audit

**Comprehensive security assessment**:
```json
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/"],
    "context": "Security audit for SOC 2 compliance. System processes payment data and PII.",
    "review_type": "security",
    "severity_filter": "critical",
    "thinking_mode": "max",
    "standards": "OWASP Top 10, PCI DSS requirements"
  }
}
```

### 3. Performance Optimization

**Performance-focused review**:
```json
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/api/", "/workspace/database/"],
    "context": "API response times increased 300% with scale. Need performance optimization.",
    "review_type": "performance",
    "thinking_mode": "high"
  }
}
```

### 4. Legacy Code Assessment

**Technical debt evaluation**:
```json
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/legacy/"],
    "context": "Legacy system modernization assessment. Code is 5+ years old, limited documentation.",
    "review_type": "full",
    "thinking_mode": "high",
    "standards": "Modern Python practices, type hints, async patterns"
  }
}
```

## Integration with CLAUDE.md Collaboration

### Double Validation Protocol

**Primary Analysis** (Gemini):
```json
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/security/"],
    "context": "Security-critical authentication module review",
    "review_type": "security",
    "thinking_mode": "high"
  }
}
```

**Adversarial Review** (Claude):
- Challenge findings and look for edge cases
- Validate assumptions about security implications
- Cross-reference with security best practices
- Identify potential false positives or missed issues

### Memory-Driven Context

**Context Retrieval**:
```python
# Before review, query memory for related context
previous_findings = memory.search_nodes("security review authentication")
architectural_decisions = memory.search_nodes("authentication architecture")
```

**Findings Storage**:
```python
# Store review findings for future reference
memory.create_entities([{
    "name": "Security Review - Authentication Module",
    "entityType": "quality_records",
    "observations": ["3 critical vulnerabilities found", "JWT implementation secure", "Input validation missing"]
}])
```

## Best Practices

### Effective Context Provision

**Comprehensive Context**:
```json
{
  "context": "E-commerce checkout flow handling payment processing. Requirements: PCI DSS compliance, 99.9% uptime, <200ms response time. Known issues: occasional payment failures under high load. Recent changes: added new payment provider integration. Team: 3 senior, 2 junior developers. Timeline: Production deployment in 2 weeks."
}
```

**Technical Context**:
```json
{
  "context": "Microservice architecture with Docker containers. Tech stack: Python 3.9, FastAPI, PostgreSQL, Redis. Load balancer: NGINX. Monitoring: Prometheus/Grafana. Authentication: OAuth 2.0 with JWT. Expected load: 1000 RPS peak."
}
```

### Review Scope Management

1. **Start with Critical Paths**: Review security and performance-critical code first
2. **Incremental Reviews**: Review code in logical chunks rather than entire codebase
3. **Context-Aware**: Always provide business context and technical constraints
4. **Follow-up Reviews**: Use continuation for iterative improvement tracking

### Issue Prioritization

1. **Security First**: Address critical security issues immediately
2. **Business Impact**: Prioritize issues affecting user experience or revenue
3. **Technical Debt**: Balance new features with technical debt reduction
4. **Team Capacity**: Consider team skills and available time for fixes

### Quality Gates

**Pre-Commit Gates**:
- No critical or high severity issues
- All security vulnerabilities addressed
- Performance regressions identified and planned
- Code style and standards compliance

**Pre-Production Gates**:
- Comprehensive security review completed
- Performance benchmarks met
- Documentation updated
- Monitoring and alerting configured

---

The CodeReview Tool provides systematic, thorough code analysis that integrates seamlessly with development workflows while maintaining high standards for security, performance, and maintainability.

