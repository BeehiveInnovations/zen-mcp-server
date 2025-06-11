# Precommit Tool API Reference

## Overview

The **Precommit Tool** provides comprehensive automated quality gates and validation before commits. It performs deep analysis of git repositories, validates changes against architectural decisions, and ensures code quality standards are met before committing to version control.

## Tool Schema

```json
{
  "name": "precommit",
  "description": "Automated quality gates before commits",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Starting directory to search for git repositories (must be absolute path)"
      },
      "include_staged": {
        "type": "boolean",
        "default": true,
        "description": "Include staged changes in the review"
      },
      "include_unstaged": {
        "type": "boolean", 
        "default": true,
        "description": "Include uncommitted (unstaged) changes in the review"
      },
      "compare_to": {
        "type": "string",
        "description": "Optional: A git ref (branch, tag, commit hash) to compare against",
        "optional": true
      },
      "review_type": {
        "type": "string",
        "enum": ["full", "security", "performance", "quick"],
        "default": "full",
        "description": "Type of review to perform on the changes"
      },
      "severity_filter": {
        "type": "string",
        "enum": ["critical", "high", "medium", "all"],
        "default": "all",
        "description": "Minimum severity level to report on the changes"
      },
      "original_request": {
        "type": "string",
        "description": "The original user request description for the changes",
        "optional": true
      },
      "focus_on": {
        "type": "string",
        "description": "Specific aspects to focus on (e.g., 'logic for user authentication', 'database query efficiency')",
        "optional": true
      },
      "thinking_mode": {
        "type": "string",
        "enum": ["minimal", "low", "medium", "high", "max"],
        "default": "medium",
        "description": "Thinking depth for the analysis"
      },
      "files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional files or directories to provide as context",
        "optional": true
      },
      "continuation_id": {
        "type": "string",
        "description": "Thread continuation ID for multi-turn conversations",
        "optional": true
      }
    },
    "required": ["path"]
  }
}
```

## Validation Process

### 1. Git Repository Analysis

**Repository Discovery**:
- **Recursive Search**: Finds all git repositories within specified path
- **Multi-Repository Support**: Handles monorepos and nested repositories
- **Branch Detection**: Identifies current branch and tracking status
- **Change Detection**: Analyzes staged, unstaged, and committed changes

**Git State Assessment**:
```python
# Repository state analysis
{
  "repository_path": "/workspace/project",
  "current_branch": "feature/user-authentication", 
  "tracking_branch": "origin/main",
  "ahead_by": 3,
  "behind_by": 0,
  "staged_files": 5,
  "unstaged_files": 2,
  "untracked_files": 1
}
```

### 2. Change Analysis Pipeline

**Staged Changes Review**:
```bash
# Git diff analysis for staged changes
git diff --staged --name-only
git diff --staged --unified=3
```

**Unstaged Changes Review**:
```bash
# Working directory changes analysis  
git diff --name-only
git diff --unified=3
```

**Commit History Analysis**:
```bash
# Compare against target branch
git diff main...HEAD --name-only
git log --oneline main..HEAD
```

### 3. Quality Gate Validation

**Security Validation**:
- **Secret Detection**: Scans for API keys, passwords, tokens
- **Vulnerability Assessment**: Identifies security anti-patterns
- **Input Validation**: Reviews user input handling
- **Authentication Changes**: Validates auth/authz modifications

**Performance Validation**:
- **Algorithm Analysis**: Reviews complexity and efficiency
- **Database Changes**: Validates query performance and indexing
- **Resource Usage**: Identifies potential memory or CPU issues
- **Caching Strategy**: Reviews caching implementation changes

**Quality Validation**:
- **Code Standards**: Enforces coding conventions and style
- **Documentation**: Ensures code changes include documentation updates
- **Testing**: Validates test coverage and quality
- **Technical Debt**: Identifies new debt introduction

**Architecture Validation**:
- **Design Patterns**: Ensures consistency with architectural decisions
- **Dependencies**: Reviews new dependencies and their impact
- **Integration**: Validates service integration changes
- **Breaking Changes**: Identifies potential breaking changes

## Usage Patterns

### 1. Standard Pre-Commit Validation

**Complete validation before committing**:
```json
{
  "name": "precommit",
  "arguments": {
    "path": "/workspace/project",
    "include_staged": true,
    "include_unstaged": false,
    "review_type": "full",
    "original_request": "Implemented user authentication with JWT tokens"
  }
}
```

### 2. Security-Focused Validation

**Security audit before sensitive commits**:
```json
{
  "name": "precommit", 
  "arguments": {
    "path": "/workspace/security-module",
    "review_type": "security",
    "severity_filter": "high",
    "focus_on": "authentication mechanisms and input validation",
    "thinking_mode": "high"
  }
}
```

### 3. Feature Branch Validation

**Comprehensive review before merge**:
```json
{
  "name": "precommit",
  "arguments": {
    "path": "/workspace/project",
    "compare_to": "main",
    "review_type": "full", 
    "original_request": "Complete user management feature with CRUD operations",
    "thinking_mode": "high"
  }
}
```

### 4. Performance Impact Assessment

**Performance validation for critical changes**:
```json
{
  "name": "precommit",
  "arguments": {
    "path": "/workspace/api-module",
    "review_type": "performance",
    "focus_on": "database queries and API response times",
    "compare_to": "main"
  }
}
```

### 5. Documentation Sync Validation

**Ensure documentation matches code changes**:
```json
{
  "name": "precommit",
  "arguments": {
    "path": "/workspace/",
    "focus_on": "documentation completeness and accuracy",
    "files": ["/workspace/docs/", "/workspace/README.md"],
    "original_request": "Updated API endpoints and added new features"
  }
}
```

## Response Format

### Comprehensive Validation Report

```json
{
  "content": "# Pre-Commit Validation Report\n\n## Repository Analysis\n**Repository**: `/workspace/user-auth-service`\n**Branch**: `feature/jwt-authentication`\n**Changes**: 8 files modified, 245 lines added, 67 lines deleted\n**Commit Readiness**: ⚠️ **CONDITIONAL** - Address medium-severity issues\n\n## Change Summary\n### Files Modified (8)\n- `src/auth/jwt_handler.py` (new file, 89 lines)\n- `src/auth/middleware.py` (modified, +45/-12)\n- `src/models/user.py` (modified, +23/-8)\n- `tests/test_auth.py` (modified, +67/-15)\n- `requirements.txt` (modified, +3/-0)\n- `config/settings.py` (modified, +12/-5)\n- `docs/api/authentication.md` (modified, +18/-3)\n- `README.md` (modified, +6/-2)\n\n## Security Analysis ✅ PASSED\n\n### Strengths Identified\n- JWT implementation uses industry-standard `PyJWT` library\n- Proper secret key management via environment variables\n- Token expiration properly configured (24 hours)\n- Password hashing uses secure bcrypt with proper salt rounds\n\n### Security Validations\n- ✅ No hardcoded secrets detected\n- ✅ Input validation implemented for authentication endpoints\n- ✅ Proper error handling without information disclosure\n- ✅ HTTPS enforcement in middleware\n\n## Performance Analysis ⚠️ REVIEW REQUIRED\n\n### Medium Priority Issues (2)\n\n**🟡 Database Query Optimization** (`src/models/user.py:45`)\n```python\n# Current implementation\ndef get_user_by_email(email):\n    return User.objects.filter(email=email).first()\n\n# Recommendation: Add database index\n# class User(models.Model):\n#     email = models.EmailField(unique=True, db_index=True)\n```\n**Impact**: Authentication queries may be slow without email index\n**Priority**: Medium\n**Fix Time**: 5 minutes (migration required)\n\n**🟡 JWT Token Validation Caching** (`src/auth/jwt_handler.py:67`)\n```python\n# Consider implementing token validation caching\n# to reduce repeated signature verification overhead\n```\n**Impact**: Repeated JWT validation on every request\n**Priority**: Medium\n**Fix Time**: 30 minutes (optional optimization)\n\n## Code Quality Analysis ✅ PASSED\n\n### Quality Metrics\n- **Test Coverage**: 89% (target: 80%) ✅\n- **Code Complexity**: Low-Medium ✅  \n- **Documentation**: Complete API docs updated ✅\n- **Type Hints**: 95% coverage ✅\n\n### New Dependencies Validated\n```\nPyJWT==2.8.0        # Well-maintained, security-focused\nbcrypt==4.0.1        # Latest stable, no known vulnerabilities\npython-dotenv==1.0.0 # Standard environment management\n```\n**Dependency Assessment**: ✅ All dependencies are secure and well-maintained\n\n## Architecture Compliance ✅ PASSED\n\n### Design Pattern Validation\n- ✅ Follows established authentication middleware pattern\n- ✅ Proper separation of concerns (handler/middleware/models)\n- ✅ Consistent error handling approach\n- ✅ RESTful API design maintained\n\n### Integration Validation\n- ✅ Backward compatibility maintained\n- ✅ No breaking changes to existing API endpoints\n- ✅ Proper database migration provided\n- ✅ Environment configuration properly documented\n\n## Documentation Review ✅ PASSED\n\n### Documentation Updates\n- ✅ API documentation updated with authentication endpoints\n- ✅ README.md includes setup instructions for JWT\n- ✅ Environment variable documentation complete\n- ✅ Code comments adequate for complex authentication logic\n\n## Testing Validation ✅ PASSED\n\n### Test Coverage Analysis\n```\nFile                          Coverage\nsrc/auth/jwt_handler.py       92%\nsrc/auth/middleware.py        87%\nsrc/models/user.py           94%\ntests/test_auth.py           100%\n```\n\n### Test Quality\n- ✅ Unit tests for JWT token generation/validation\n- ✅ Integration tests for authentication endpoints\n- ✅ Edge case testing (expired tokens, invalid signatures)\n- ✅ Error condition testing\n\n## Final Recommendation\n\n### ✅ **APPROVED FOR COMMIT** with minor optimizations\n\n**Required Actions**: None (all critical issues resolved)\n\n**Recommended Actions**:\n1. **Add email index** to User model for better performance\n2. **Consider JWT caching** for high-traffic scenarios\n\n**Commit Confidence**: High (92%)\n\n### Suggested Commit Message\n```\nImplement JWT authentication system\n\n- Add JWT token generation and validation\n- Implement authentication middleware\n- Add secure password hashing with bcrypt\n- Update API documentation\n- Add comprehensive test coverage (89%)\n\nTesting: All tests pass, no breaking changes\nSecurity: No vulnerabilities detected\nPerformance: Minor optimization opportunities identified\n```\n\n## Next Steps\n1. **Immediate**: Commit current changes (approved)\n2. **Short-term**: Add database index for email field\n3. **Future**: Implement JWT validation caching for performance\n4. **Monitoring**: Track authentication performance metrics post-deployment",
  "metadata": {
    "repository_path": "/workspace/user-auth-service",
    "commit_readiness": "approved_with_recommendations",
    "files_analyzed": 8,
    "lines_changed": 178,
    "security_score": 9.2,
    "performance_score": 7.8,
    "quality_score": 9.1,
    "overall_confidence": 92,
    "validation_time": "12.3s"
  },
  "git_analysis": {
    "current_branch": "feature/jwt-authentication",
    "staged_files": 8,
    "unstaged_files": 0,
    "commits_ahead": 3,
    "target_branch": "main"
  },
  "continuation_id": "precommit-validation-uuid",
  "status": "success"
}
```

### Commit Readiness Levels

**✅ APPROVED**: 
- No critical or high-severity issues
- All quality gates passed
- Documentation complete
- Tests comprehensive

**⚠️ CONDITIONAL**:
- Medium-severity issues present
- Some quality concerns
- Recommendations for improvement
- Can commit with awareness of trade-offs

**❌ BLOCKED**:
- Critical security vulnerabilities
- High-severity performance issues
- Insufficient test coverage
- Breaking changes without proper migration

## Advanced Usage Patterns

### 1. Cross-Repository Validation

**Monorepo validation**:
```json
{
  "name": "precommit",
  "arguments": {
    "path": "/workspace/monorepo",
    "focus_on": "cross-service impact analysis",
    "files": ["/workspace/shared-libs/", "/workspace/service-contracts/"],
    "thinking_mode": "high"
  }
}
```

### 2. Compliance Validation

**Regulatory compliance check**:
```json
{
  "name": "precommit",
  "arguments": {
    "path": "/workspace/financial-service",
    "review_type": "security",
    "severity_filter": "critical",
    "focus_on": "PCI DSS compliance and data protection",
    "thinking_mode": "max"
  }
}
```

### 3. Migration Safety Validation

**Database migration validation**:
```json
{
  "name": "precommit",
  "arguments": {
    "path": "/workspace/api-service",
    "focus_on": "database migration safety and backward compatibility",
    "files": ["/workspace/migrations/", "/workspace/models/"],
    "original_request": "Database schema changes for user profiles feature"
  }
}
```

### 4. Integration Testing Validation

**Service integration changes**:
```json
{
  "name": "precommit",
  "arguments": {
    "path": "/workspace/microservices",
    "focus_on": "service contract changes and API compatibility",
    "compare_to": "main",
    "review_type": "full"
  }
}
```

## Integration with CI/CD

### Git Hook Integration

**Pre-commit hook implementation**:
```bash
#!/bin/sh
# .git/hooks/pre-commit

echo "Running pre-commit validation..."

# Call precommit tool via MCP
claude-code-cli --tool precommit --path "$(pwd)" --review-type full

if [ $? -ne 0 ]; then
    echo "Pre-commit validation failed. Commit blocked."
    exit 1
fi

echo "Pre-commit validation passed. Proceeding with commit."
```

### GitHub Actions Integration

**CI workflow with precommit validation**:
```yaml
name: Pre-commit Validation
on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Precommit Validation
        run: |
          claude-code-cli --tool precommit \
            --path ${{ github.workspace }} \
            --compare-to origin/main \
            --review-type full
```

## Memory Bank Integration

### Architectural Decision Alignment

**Query past architectural decisions**:
```python
# Check alignment with architectural principles
architectural_decisions = memory.search_nodes("architecture security authentication")
design_patterns = memory.search_nodes("design patterns authentication")
```

**Validate against established patterns**:
```python
# Ensure changes follow established patterns
validation_results = memory.search_nodes("validation authentication security")
previous_reviews = memory.search_nodes("code review authentication")
```

### Context Preservation

**Store validation findings**:
```python
# Store precommit validation results
memory.create_entities([{
    "name": "Precommit Validation - JWT Authentication",
    "entityType": "quality_records", 
    "observations": [
        "Security validation passed with high confidence",
        "Performance optimizations recommended but not blocking",
        "Documentation complete and accurate",
        "Test coverage exceeds target threshold"
    ]
}])
```

## Best Practices

### Effective Validation Strategy

1. **Regular Validation**: Use precommit for every commit, not just major changes
2. **Contextual Focus**: Provide original request context for better validation
3. **Incremental Analysis**: Use continuation for complex multi-part features
4. **Severity Appropriate**: Match thinking mode to change complexity and risk

### Repository Management

1. **Clean Working Directory**: Ensure clean state before validation
2. **Targeted Analysis**: Focus on changed files and their dependencies
3. **Branch Strategy**: Compare against appropriate target branch
4. **Documentation Sync**: Always validate documentation completeness

### Quality Gates

1. **Security First**: Never compromise on security findings
2. **Performance Aware**: Consider performance impact of all changes
3. **Test Coverage**: Maintain or improve test coverage with changes
4. **Documentation Currency**: Keep documentation synchronized with code

---

The Precommit Tool provides comprehensive, automated quality assurance that integrates seamlessly with development workflows while maintaining high standards for security, performance, and code quality.