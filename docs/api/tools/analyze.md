# Analyze Tool API Reference

## Overview

The **Analyze Tool** provides comprehensive codebase exploration and understanding capabilities. It's designed for in-depth analysis of existing systems, dependency mapping, pattern detection, and architectural comprehension.

## Tool Schema

```json
{
  "name": "analyze",
  "description": "Code exploration and understanding of existing systems",
  "inputSchema": {
    "type": "object",
    "properties": {
      "files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Files or directories that might be related to the issue"
      },
      "question": {
        "type": "string",
        "description": "What to analyze or look for"
      },
      "analysis_type": {
        "type": "string",
        "enum": ["architecture", "performance", "security", "quality", "general"],
        "default": "general",
        "description": "Type of analysis to perform"
      },
      "output_format": {
        "type": "string",
        "enum": ["summary", "detailed", "actionable"],
        "default": "detailed",
        "description": "How to format the output"
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
    "required": ["files", "question"]
  }
}
```

## Usage Patterns

### 1. Architecture Analysis

**Ideal For**:
- Understanding system design patterns
- Mapping component relationships
- Identifying architectural anti-patterns
- Documentation of existing systems

**Example**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/src/", "/workspace/config/"],
    "question": "Analyze the overall architecture pattern and component relationships",
    "analysis_type": "architecture",
    "thinking_mode": "high",
    "output_format": "detailed"
  }
}
```

**Response Includes**:
- System architecture overview
- Component interaction diagrams
- Data flow patterns
- Integration points and dependencies
- Design pattern identification

### 2. Performance Analysis

**Ideal For**:
- Identifying performance bottlenecks
- Resource usage patterns
- Optimization opportunities
- Scalability assessment

**Example**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/api/", "/workspace/database/"],
    "question": "Identify performance bottlenecks and optimization opportunities",
    "analysis_type": "performance",
    "thinking_mode": "high"
  }
}
```

**Response Includes**:
- Performance hotspots identification
- Resource usage analysis
- Caching opportunities
- Database query optimization
- Concurrency and parallelization suggestions

### 3. Security Analysis

**Ideal For**:
- Security vulnerability assessment
- Authentication/authorization review
- Input validation analysis
- Secure coding practice evaluation

**Example**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/auth/", "/workspace/api/"],
    "question": "Assess security vulnerabilities and authentication patterns",
    "analysis_type": "security",
    "thinking_mode": "high"
  }
}
```

**Response Includes**:
- Security vulnerability inventory
- Authentication mechanism analysis
- Input validation assessment
- Data exposure risks
- Secure coding recommendations

### 4. Code Quality Analysis

**Ideal For**:
- Code maintainability assessment
- Technical debt identification
- Refactoring opportunities
- Testing coverage evaluation

**Example**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/src/"],
    "question": "Evaluate code quality, maintainability, and refactoring needs",
    "analysis_type": "quality",
    "thinking_mode": "medium"
  }
}
```

**Response Includes**:
- Code quality metrics
- Maintainability assessment
- Technical debt inventory
- Refactoring prioritization
- Testing strategy recommendations

### 5. Dependency Analysis

**Ideal For**:
- Understanding module dependencies
- Circular dependency detection
- Third-party library analysis
- Dependency graph visualization

**Example**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/package.json", "/workspace/requirements.txt", "/workspace/src/"],
    "question": "Map dependencies and identify potential issues",
    "analysis_type": "general",
    "output_format": "actionable"
  }
}
```

## Parameter Details

### files (required)
- **Type**: array of strings
- **Purpose**: Specifies which files/directories to analyze
- **Behavior**:
  - **Individual Files**: Direct analysis of specified files
  - **Directories**: Recursive scanning with intelligent filtering
  - **Mixed Input**: Combines files and directories in single analysis
  - **Priority Processing**: Source code files processed before documentation

**Best Practices**:
- Use specific paths for focused analysis
- Include configuration files for complete context
- Limit scope to relevant components for performance
- Use absolute paths for reliability

### question (required)
- **Type**: string
- **Purpose**: Defines the analysis focus and expected outcomes
- **Effective Question Patterns**:
  - **Exploratory**: "How does the authentication system work?"
  - **Diagnostic**: "Why is the API response time slow?"
  - **Evaluative**: "How maintainable is this codebase?"
  - **Comparative**: "What are the trade-offs in this design?"

### analysis_type (optional)
- **Type**: string enum
- **Default**: "general"
- **Purpose**: Tailors analysis approach and output format

**Analysis Types**:

**architecture**:
- Focus on system design and component relationships
- Identifies patterns, anti-patterns, and architectural decisions
- Maps data flow and integration points
- Evaluates scalability and extensibility

**performance**:
- Identifies bottlenecks and optimization opportunities
- Analyzes resource usage and efficiency
- Evaluates caching strategies and database performance
- Assesses concurrency and parallelization

**security**:
- Vulnerability assessment and threat modeling
- Authentication and authorization analysis
- Input validation and data protection review
- Secure coding practice evaluation

**quality**:
- Code maintainability and readability assessment
- Technical debt identification and prioritization
- Testing coverage and strategy evaluation
- Refactoring opportunity analysis

**general**:
- Balanced analysis covering multiple aspects
- Good for initial exploration and broad understanding
- Flexible approach adapting to content and question

### output_format (optional)
- **Type**: string enum
- **Default**: "detailed"
- **Purpose**: Controls response structure and depth

**Format Types**:

**summary**:
- High-level findings in 2-3 paragraphs
- Key insights and primary recommendations
- Executive summary style for quick understanding

**detailed** (recommended):
- Comprehensive analysis with examples
- Code references with line numbers
- Multiple perspectives and alternatives
- Actionable recommendations with context

**actionable**:
- Focused on specific next steps
- Prioritized recommendations
- Implementation guidance
- Clear success criteria

### thinking_mode (optional)
- **Type**: string enum  
- **Default**: "medium"
- **Purpose**: Controls analysis depth and computational budget

**Recommendations by Analysis Scope**:
- **low** (2048 tokens): Small files, focused questions
- **medium** (8192 tokens): Standard analysis, moderate complexity
- **high** (16384 tokens): Comprehensive analysis, complex systems
- **max** (32768 tokens): Deep research, critical system analysis

## Response Format

### Detailed Analysis Structure

```json
{
  "content": "# Architecture Analysis Report\n\n## System Overview\n[High-level architecture summary]\n\n## Component Analysis\n[Detailed component breakdown with file references]\n\n## Design Patterns\n[Identified patterns and their implementations]\n\n## Integration Points\n[External dependencies and API interfaces]\n\n## Recommendations\n[Specific improvement suggestions]\n\n## Technical Debt\n[Areas requiring attention]\n\n## Next Steps\n[Prioritized action items]",
  "metadata": {
    "analysis_type": "architecture",
    "files_analyzed": 23,
    "lines_of_code": 5420,
    "patterns_identified": ["MVC", "Observer", "Factory"],
    "complexity_score": "medium",
    "confidence_level": "high"
  },
  "files_processed": [
    "/workspace/src/main.py:1-150",
    "/workspace/config/settings.py:1-75"
  ],
  "continuation_id": "arch-analysis-uuid",
  "status": "success"
}
```

### Code Reference Format

Analysis responses include precise code references:

```
## Authentication Implementation

The authentication system uses JWT tokens with RSA256 signing:

**Token Generation** (`src/auth/jwt_handler.py:45-67`):
- RSA private key loading from environment
- Token expiration set to 24 hours
- User claims include role and permissions

**Token Validation** (`src/middleware/auth.py:23-41`):
- Public key verification
- Expiration checking
- Role-based access control

**Security Concerns**:
1. No token refresh mechanism (jwt_handler.py:45)
2. Hardcoded secret fallback (jwt_handler.py:52) 
3. Missing rate limiting on auth endpoints (auth.py:15)
```

## Advanced Usage Patterns

### 1. Progressive Analysis

**Phase 1: System Overview**
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/"],
    "question": "Provide high-level architecture overview",
    "analysis_type": "architecture",
    "output_format": "summary",
    "thinking_mode": "low"
  }
}
```

**Phase 2: Deep Dive**
```json
{
  "name": "analyze", 
  "arguments": {
    "files": ["/workspace/core/", "/workspace/api/"],
    "question": "Analyze core components and API design in detail",
    "analysis_type": "architecture", 
    "output_format": "detailed",
    "thinking_mode": "high",
    "continuation_id": "overview-analysis-id"
  }
}
```

### 2. Comparative Analysis

**Current State Analysis**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/legacy/"],
    "question": "Document current system architecture and limitations",
    "analysis_type": "architecture"
  }
}
```

**Target State Analysis**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/new-design/"],
    "question": "Analyze proposed architecture and compare with legacy system",
    "analysis_type": "architecture",
    "continuation_id": "current-state-id"
  }
}
```

### 3. Multi-Perspective Analysis

**Technical Analysis**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/"],
    "question": "Technical implementation analysis",
    "analysis_type": "quality",
    "thinking_mode": "high"
  }
}
```

**Performance Analysis**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/"],
    "question": "Performance characteristics and optimization opportunities", 
    "analysis_type": "performance",
    "continuation_id": "technical-analysis-id"
  }
}
```

**Security Analysis**:
```json
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/"],
    "question": "Security posture and vulnerability assessment",
    "analysis_type": "security", 
    "continuation_id": "technical-analysis-id"
  }
}
```

## File Processing Behavior

### Directory Processing

**Recursive Scanning**:
- Automatically discovers relevant files in subdirectories
- Applies intelligent filtering based on file types
- Prioritizes source code over documentation and logs
- Respects `.gitignore` patterns when present

**File Type Prioritization**:
1. **Source Code** (.py, .js, .ts, .java, etc.) - 60% of token budget
2. **Configuration** (.json, .yaml, .toml, etc.) - 25% of token budget
3. **Documentation** (.md, .txt, .rst, etc.) - 10% of token budget
4. **Other Files** (.log, .tmp, etc.) - 5% of token budget

### Content Processing

**Smart Truncation**:
- Preserves file structure and important sections
- Maintains code context and comments
- Includes file headers and key functions
- Adds truncation markers with statistics

**Line Number References**:
- All code examples include precise line numbers
- Enables easy navigation to specific locations
- Supports IDE integration and quick access
- Maintains accuracy across file versions

## Integration with Other Tools

### Analyze → ThinkDeep Flow

```json
// 1. Comprehensive analysis
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/"],
    "question": "Understand current architecture and identify improvement areas",
    "analysis_type": "architecture"
  }
}

// 2. Strategic planning based on findings
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Analysis findings: monolithic architecture with performance bottlenecks...",
    "focus_areas": ["modernization", "scalability", "migration_strategy"],
    "continuation_id": "architecture-analysis-id"
  }
}
```

### Analyze → CodeReview Flow

```json
// 1. System understanding
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/auth/"],
    "question": "Understand authentication implementation patterns",
    "analysis_type": "security"
  }
}

// 2. Detailed code review
{
  "name": "codereview",
  "arguments": {
    "files": ["/workspace/auth/"],
    "context": "Analysis revealed potential security concerns in authentication",
    "review_type": "security",
    "continuation_id": "auth-analysis-id"
  }
}
```

## Performance Characteristics

### Analysis Speed by File Count
- **1-10 files**: 2-5 seconds
- **11-50 files**: 5-15 seconds  
- **51-200 files**: 15-45 seconds
- **200+ files**: 45-120 seconds (consider breaking into smaller scopes)

### Memory Usage
- **Small projects** (<1MB): ~100MB
- **Medium projects** (1-10MB): ~300MB
- **Large projects** (10-100MB): ~800MB
- **Enterprise projects** (>100MB): May require multiple focused analyses

### Quality Indicators
- **Coverage**: Percentage of files analyzed vs total files
- **Depth**: Number of insights per file analyzed
- **Accuracy**: Precision of code references and explanations
- **Actionability**: Specificity of recommendations

## Best Practices

### Effective Analysis Questions

**Specific and Focused**:
```
✅ "How does the caching layer integrate with the database access patterns?"
✅ "What are the security implications of the current API authentication?"
✅ "Where are the performance bottlenecks in the request processing pipeline?"

❌ "Analyze this code"
❌ "Is this good?"
❌ "What should I know?"
```

**Context-Rich Questions**:
```
✅ "Given that we need to scale to 10x current traffic, what are the architectural constraints?"
✅ "For a team of junior developers, what are the maintainability concerns?"
✅ "Considering SOX compliance requirements, what are the audit trail gaps?"
```

### Scope Management

1. **Start Broad, Then Focus**: Begin with high-level analysis, drill down to specific areas
2. **Logical Grouping**: Analyze related components together for better context
3. **Iterative Refinement**: Use continuation to build deeper understanding
4. **Balance Depth and Breadth**: Match thinking mode to analysis scope

### File Selection Strategy

1. **Core First**: Start with main application files and entry points
2. **Configuration Included**: Always include config files for complete context
3. **Test Analysis**: Include tests to understand expected behavior
4. **Documentation Review**: Add docs to understand intended design

---

The Analyze Tool serves as your code comprehension partner, providing deep insights into existing systems and enabling informed decision-making for development and modernization efforts.