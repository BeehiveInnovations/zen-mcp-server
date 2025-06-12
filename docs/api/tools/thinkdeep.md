# ThinkDeep Tool API Reference

## Overview

The **ThinkDeep Tool** provides access to Gemini's maximum analytical capabilities for complex architecture decisions, system design, and strategic planning. It's designed for comprehensive analysis that requires deep computational thinking and extensive reasoning.

## Tool Schema

```json
{
  "name": "thinkdeep",
  "description": "Complex architecture, system design, strategic planning",
  "inputSchema": {
    "type": "object",
    "properties": {
      "current_analysis": {
        "type": "string",
        "description": "Your current thinking/analysis to extend and validate"
      },
      "problem_context": {
        "type": "string",
        "description": "Additional context about the problem or goal",
        "optional": true
      },
      "focus_areas": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Specific aspects to focus on (architecture, performance, security, etc.)",
        "optional": true
      },
      "files": {
        "type": "array", 
        "items": {"type": "string"},
        "description": "Optional file paths or directories for additional context",
        "optional": true
      },
      "thinking_mode": {
        "type": "string",
        "enum": ["minimal", "low", "medium", "high", "max"],
        "default": "high",
        "description": "Thinking depth for analysis"
      },
      "temperature": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "default": 0.7,
        "description": "Temperature for creative thinking"
      },
      "continuation_id": {
        "type": "string",
        "description": "Thread continuation ID for multi-turn conversations",
        "optional": true
      }
    },
    "required": ["current_analysis"]
  }
}
```

## Usage Patterns

### 1. Architecture Decision Making

**Ideal For**:
- Evaluating architectural alternatives
- Designing system components
- Planning scalability strategies
- Technology selection decisions

**Example**:
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "We have an MCP server that needs to handle 100+ concurrent Claude sessions. Currently using single-threaded processing with Redis for conversation memory.",
    "problem_context": "Growing user base requires better performance and reliability. Budget allows for infrastructure changes.",
    "focus_areas": ["scalability", "performance", "reliability", "cost"],
    "thinking_mode": "max"
  }
}
```

### 2. System Design Exploration

**Ideal For**:
- Complex system architecture
- Integration pattern analysis
- Security architecture design
- Performance optimization strategies

**Example**:
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Need to design a secure file processing pipeline that handles user uploads, virus scanning, content analysis, and storage with audit trails.",
    "focus_areas": ["security", "performance", "compliance", "monitoring"],
    "files": ["/workspace/security/", "/workspace/processing/"],
    "thinking_mode": "high"
  }
}
```

### 3. Strategic Technical Planning

**Ideal For**:
- Long-term technical roadmaps
- Migration strategies
- Technology modernization
- Risk assessment and mitigation

**Example**:
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Legacy monolithic application needs migration to microservices. 500K+ LOC, 50+ developers, critical business system with 99.9% uptime requirement.",
    "problem_context": "Must maintain business continuity while modernizing. Team has limited microservices experience.",
    "focus_areas": ["migration_strategy", "risk_mitigation", "team_training", "timeline"],
    "thinking_mode": "max",
    "temperature": 0.3
  }
}
```

### 4. Problem Solving & Innovation

**Ideal For**:
- Novel technical challenges
- Creative solution development
- Cross-domain problem analysis
- Innovation opportunities

**Example**:
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "AI model serving platform needs to optimize GPU utilization across heterogeneous hardware while minimizing latency and maximizing throughput.",
    "focus_areas": ["resource_optimization", "scheduling", "performance", "cost_efficiency"],
    "thinking_mode": "max",
    "temperature": 0.8
  }
}
```

## Parameter Details

### current_analysis (required)
- **Type**: string
- **Purpose**: Starting point for deep analysis and extension
- **Best Practices**:
  - Provide comprehensive background and context
  - Include current understanding and assumptions
  - Mention constraints and requirements
  - Reference specific challenges or decision points

**Example Structure**:
```
Current Analysis:
- Problem: [Clear problem statement]
- Context: [Business/technical context]
- Current State: [What exists now]
- Requirements: [What needs to be achieved]
- Constraints: [Technical, business, resource limitations]
- Open Questions: [Specific areas needing analysis]
```

### problem_context (optional)
- **Type**: string
- **Purpose**: Additional contextual information
- **Usage**:
  - Business requirements and priorities
  - Technical constraints and dependencies
  - Team capabilities and limitations
  - Timeline and budget considerations

### focus_areas (optional)
- **Type**: array of strings
- **Purpose**: Directs analysis toward specific aspects
- **Common Values**:
  - **Technical**: `architecture`, `performance`, `scalability`, `security`
  - **Operational**: `reliability`, `monitoring`, `deployment`, `maintenance`
  - **Business**: `cost`, `timeline`, `risk`, `compliance`
  - **Team**: `skills`, `training`, `processes`, `communication`

### thinking_mode (optional)
- **Type**: string enum
- **Default**: "high"
- **Purpose**: Controls depth and computational budget
- **Recommendations by Use Case**:
  - **high** (16384 tokens): Standard complex analysis
  - **max** (32768 tokens): Critical decisions, comprehensive research
  - **medium** (8192 tokens): Moderate complexity, time-sensitive decisions
  - **low** (2048 tokens): Quick strategic input (unusual for thinkdeep)

### temperature (optional)
- **Type**: number (0.0 - 1.0)
- **Default**: 0.7
- **Purpose**: Balances analytical rigor with creative exploration
- **Guidelines**:
  - **0.0-0.3**: High accuracy, conservative recommendations (critical systems)
  - **0.4-0.7**: Balanced analysis with creative alternatives (most use cases)
  - **0.8-1.0**: High creativity, innovative solutions (research, innovation)

## Response Format

### Comprehensive Analysis Structure

```json
{
  "content": "# Deep Analysis Report\n\n## Executive Summary\n[High-level findings and recommendations]\n\n## Current State Analysis\n[Detailed assessment of existing situation]\n\n## Alternative Approaches\n[Multiple solution paths with trade-offs]\n\n## Recommended Strategy\n[Specific recommendations with rationale]\n\n## Implementation Roadmap\n[Phased approach with milestones]\n\n## Risk Assessment\n[Potential challenges and mitigation strategies]\n\n## Success Metrics\n[Measurable outcomes and KPIs]\n\n## Next Steps\n[Immediate actions and decision points]",
  "metadata": {
    "thinking_mode": "high",
    "analysis_depth": "comprehensive",
    "alternatives_considered": 5,
    "focus_areas": ["architecture", "performance", "scalability"],
    "confidence_level": "high",
    "tokens_used": 15840,
    "analysis_time": "8.2s"
  },
  "continuation_id": "arch-analysis-550e8400",
  "status": "success"
}
```

### Analysis Components

**Executive Summary**:
- Key findings in 2-3 sentences
- Primary recommendation
- Critical decision points
- Success probability assessment

**Current State Analysis**:
- Strengths and weaknesses of existing approach
- Technical debt and architectural issues
- Performance bottlenecks and limitations
- Security and compliance gaps

**Alternative Approaches**:
- 3-5 distinct solution paths
- Trade-off analysis for each option
- Resource requirements and timelines
- Risk profiles and success factors

**Recommended Strategy**:
- Detailed recommendation with clear rationale
- Step-by-step implementation approach
- Resource allocation and timeline
- Success criteria and validation methods

**Risk Assessment**:
- Technical risks and mitigation strategies
- Business risks and contingency plans
- Team and organizational challenges
- External dependencies and uncertainties

## Advanced Usage Patterns

### 1. Multi-Phase Analysis

**Phase 1: Problem Exploration**
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Initial problem statement and context",
    "focus_areas": ["problem_definition", "requirements_analysis"],
    "thinking_mode": "high"
  }
}
```

**Phase 2: Solution Development**
```json
{
  "name": "thinkdeep", 
  "arguments": {
    "current_analysis": "Previous analysis findings + refined problem definition",
    "focus_areas": ["solution_design", "architecture", "implementation"],
    "continuation_id": "previous-analysis-id",
    "thinking_mode": "max"
  }
}
```

**Phase 3: Implementation Planning**
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Chosen solution approach + design details",
    "focus_areas": ["implementation_strategy", "risk_mitigation", "timeline"],
    "continuation_id": "previous-analysis-id",
    "thinking_mode": "high"
  }
}
```

### 2. Adversarial Analysis

**Primary Analysis**:
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Proposed solution with detailed rationale",
    "focus_areas": ["solution_validation", "feasibility"],
    "thinking_mode": "high",
    "temperature": 0.4
  }
}
```

**Devil's Advocate Review**:
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Previous analysis + instruction to challenge assumptions and find flaws",
    "focus_areas": ["risk_analysis", "failure_modes", "alternative_perspectives"],
    "continuation_id": "primary-analysis-id",
    "thinking_mode": "high",
    "temperature": 0.6
  }
}
```

### 3. Collaborative Decision Making

**Technical Analysis**:
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Technical requirements and constraints",
    "focus_areas": ["technical_feasibility", "architecture", "performance"],
    "thinking_mode": "high"
  }
}
```

**Business Analysis**:
```json
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Technical findings + business context",
    "focus_areas": ["business_value", "cost_benefit", "strategic_alignment"],
    "continuation_id": "technical-analysis-id",
    "thinking_mode": "high"
  }
}
```

## Integration with Other Tools

### ThinkDeep → CodeReview Flow

```json
// 1. Strategic analysis
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "Need to refactor authentication system for better security",
    "focus_areas": ["security", "architecture"]
  }
}

// 2. Detailed code review based on strategic insights
{
  "name": "codereview", 
  "arguments": {
    "files": ["/workspace/auth/"],
    "context": "Strategic analysis identified need for security-focused refactoring",
    "review_type": "security",
    "continuation_id": "strategic-analysis-id"
  }
}
```

### ThinkDeep → Analyze Flow

```json
// 1. High-level strategy
{
  "name": "thinkdeep",
  "arguments": {
    "current_analysis": "System performance issues under high load",
    "focus_areas": ["performance", "scalability"]
  }
}

// 2. Detailed codebase analysis
{
  "name": "analyze",
  "arguments": {
    "files": ["/workspace/"],
    "question": "Identify performance bottlenecks based on strategic analysis",
    "analysis_type": "performance",
    "continuation_id": "strategy-analysis-id"
  }
}
```

## Performance Characteristics

### Response Times by Thinking Mode
- **medium**: 4-8 seconds (unusual for thinkdeep)
- **high**: 8-15 seconds (recommended default)
- **max**: 15-30 seconds (comprehensive analysis)

### Quality Indicators
- **Depth**: Number of alternatives considered
- **Breadth**: Range of focus areas covered
- **Precision**: Specificity of recommendations
- **Actionability**: Clarity of next steps

### Resource Usage
- **Memory**: 200-500MB per analysis session
- **Network**: High (extensive Gemini API usage)
- **Storage**: Redis conversation persistence (48h TTL for complex analyses)
- **CPU**: Low (primarily network I/O bound)

## Best Practices

### Effective Analysis Prompts

**Provide Rich Context**:
```
Current Analysis:
We're designing a real-time collaborative editing system like Google Docs. 
Key requirements:
- Support 1000+ concurrent users per document
- Sub-100ms latency for edits
- Conflict resolution for simultaneous edits
- Offline support with sync

Current challenges:
- Operational Transform vs CRDT decision
- Server architecture (centralized vs distributed)
- Client-side performance with large documents
- Database design for version history

Constraints:
- Team of 8 developers (2 senior, 6 mid-level)
- 6-month timeline
- Cloud-first deployment (AWS/Azure)
- Must integrate with existing authentication system
```

**Focus on Decisions**:
- Frame analysis around specific decisions that need to be made
- Include decision criteria and trade-offs
- Mention stakeholders and their priorities
- Reference timeline and resource constraints

### Conversation Management

1. **Use Continuation for Related Analyses**: Build complex understanding over multiple calls
2. **Reference Previous Insights**: Explicitly connect new analysis to previous findings
3. **Validate Assumptions**: Use follow-up calls to challenge and refine thinking
4. **Document Decisions**: Capture key insights for future reference

### Quality Optimization

1. **Match Thinking Mode to Complexity**: Use 'max' only for truly complex decisions
2. **Balance Temperature**: Lower for critical systems, higher for innovation
3. **Iterative Refinement**: Multiple focused analyses often better than single broad one
4. **Cross-Validation**: Use adversarial analysis for critical decisions

---

The ThinkDeep Tool serves as your strategic thinking partner, providing comprehensive analysis and creative problem-solving capabilities for the most challenging technical and architectural decisions.

