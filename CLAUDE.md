# Collaborating with Claude & Gemini on the Gemini MCP Server

This document establishes the framework for effective collaboration between Claude, Gemini, and human developers on this repository. It defines tool usage patterns, best practices, and documentation standards to ensure high-quality, comprehensive work.

## 🎯 Project Overview

The **Gemini MCP Server** is a Model Context Protocol (MCP) server that provides Claude with access to Google's Gemini AI models through specialized tools. This enables sophisticated AI-assisted development workflows combining Claude's general capabilities with Gemini's deep analytical and creative thinking abilities.

### Core Philosophy
- **Collaborative Intelligence**: Claude and Gemini work together, with Claude handling immediate tasks and coordination while Gemini provides deep analysis, creative solutions, and comprehensive code review
- **Task-Appropriate Tools**: Different tools for different purposes - quick chat for simple questions, deep thinking for architecture, specialized review for code quality
- **Documentation-Driven Development**: All code changes must be accompanied by comprehensive, accessible documentation

## 🛠️ The Collaboration Toolbox

### Tool Selection Matrix

| Tool | Primary Use Cases | When to Use | Collaboration Level |
|------|------------------|-------------|-------------------|
| **`chat`** | Quick questions, brainstorming, simple code snippets | Immediate answers, exploring ideas, general discussion | Low - Claude leads |
| **`thinkdeep`** | Complex architecture, system design, strategic planning | Major features, refactoring strategies, design decisions | High - Gemini leads |
| **`analyze`** | Code exploration, understanding existing systems | Onboarding, dependency analysis, codebase comprehension | Medium - Both collaborate |
| **`codereview`** | Code quality, security, bug detection | PR reviews, pre-commit validation, security audits | High - Gemini leads |
| **`debug`** | Root cause analysis, error investigation | Bug fixes, stack trace analysis, performance issues | Medium - Gemini leads |
| **`precommit`** | Automated quality gates | Before every commit (automated) | Medium - Gemini validates |

### Mandatory Collaboration Rules

1. **Complex Tasks (>3 steps)**: Always use TodoWrite to plan and track progress
2. **Architecture Decisions**: Must involve `thinkdeep` for exploration before implementation
3. **Code Reviews**: All significant changes require `codereview` analysis before committing
4. **Documentation Updates**: Any code change must include corresponding documentation updates

## 📋 Task Categories & Workflows

### 🏗️ New Feature Development
```
1. Planning (thinkdeep) → Architecture and approach
2. Analysis (analyze) → Understanding existing codebase
3. Implementation (human + Claude) → Writing the code
4. Review (codereview) → Quality validation
5. Documentation (both) → Comprehensive docs
6. Testing (precommit) → Automated validation
```

### 🐛 Bug Investigation & Fixing
```
1. Diagnosis (debug) → Root cause analysis  
2. Analysis (analyze) → Understanding affected code
3. Implementation (human + Claude) → Fix development
4. Review (codereview) → Security and quality check
5. Testing (precommit) → Validation before commit
```

### 📖 Documentation & Analysis
```
1. Exploration (analyze) → Understanding current state
2. Planning (chat/thinkdeep) → Structure and approach
3. Documentation (both) → Writing comprehensive docs
4. Review (human) → Accuracy validation
```

## 📚 Documentation Standards & Best Practices

### Documentation Directory Structure
```
docs/
├── architecture/           # System design and technical architecture
│   ├── overview.md        # High-level system architecture
│   ├── components.md      # Component descriptions and interactions
│   ├── data-flow.md       # Data flow diagrams and explanations
│   └── decisions/         # Architecture Decision Records (ADRs)
├── contributing/          # Development and contribution guidelines
│   ├── setup.md          # Development environment setup
│   ├── workflows.md      # Development workflows and processes
│   ├── code-style.md     # Coding standards and style guide
│   ├── testing.md        # Testing strategies and requirements
│   └── file-overview.md  # Guide to repository structure
├── api/                  # API documentation
│   ├── mcp-protocol.md   # MCP protocol implementation details
│   └── tools/            # Individual tool documentation
└── user-guides/          # End-user documentation
    ├── installation.md   # Installation and setup
    ├── configuration.md  # Configuration options
    └── troubleshooting.md # Common issues and solutions
```

### Documentation Quality Standards

#### For Technical Audiences
- **Code Context**: All explanations must reference specific files and line numbers using `file_path:line_number` format
- **Architecture Focus**: Explain *why* decisions were made, not just *what* was implemented
- **Data Flow**: Trace data through the system with concrete examples
- **Error Scenarios**: Document failure modes and recovery strategies

#### For Non-Technical Audiences  
- **Plain Language**: Avoid jargon, explain technical terms when necessary
- **Purpose-Driven**: Start with "what problem does this solve?"
- **Visual Aids**: Use diagrams and flowcharts where helpful
- **Practical Examples**: Show real usage scenarios

### File Overview Requirements (Contributing Guide)

Each file must be documented with:
- **Purpose**: What problem does this file solve?
- **Key Components**: Main classes/functions and their roles
- **Dependencies**: What other files/modules does it interact with?
- **Data Flow**: How data moves through this component
- **Extension Points**: Where/how can this be extended?

## 🔄 Mandatory Collaboration Patterns

### Double Validation Protocol
**Critical Code Reviews**: For security-sensitive or architecture-critical changes:
1. **Primary Analysis** (Gemini): Deep analysis using `codereview` or `thinkdeep`
2. **Adversarial Review** (Claude): Challenge findings, look for edge cases, validate assumptions
3. **Synthesis**: Combine insights, resolve disagreements, document final approach
4. **Memory Update**: Record key decisions and validation results

### Memory-Driven Context Management
**Active Memory Usage**: Always maintain project context via memory MCP:
```bash
# Store key insights
mcp_memory_create_entities: Project decisions, validation findings, user preferences
# Track progress  
mcp_memory_add_observations: Task status, approach changes, learning insights
# Retrieve context
mcp_memory_search_nodes: Before starting tasks, query relevant past decisions
```

### Pre-Implementation Analysis
Before any significant code change:
1. **Query Memory**: Search for related past decisions and constraints
2. Use `analyze` to understand current implementation  
3. Use `thinkdeep` for architectural planning if complex
4. **Store Plan**: Document approach in memory and todos
5. Get consensus on direction before coding

### Pre-Commit Validation  
Before every commit:
1. **Memory Check**: Verify alignment with past architectural decisions
2. Run `precommit` tool for automated validation
3. Use `codereview` for manual quality check (with adversarial validation if critical)
4. **Update Progress**: Record completion status in memory
5. Ensure documentation is updated

### Cross-Tool Continuation & Memory Persistence
- Use `continuation_id` to maintain context across tool calls
- **Mandatory Memory Updates**: Record all significant findings and decisions
- Document decision rationale when switching between tools
- Always summarize findings when moving between analysis phases
- **Context Retrieval**: Start complex tasks by querying memory for relevant background

### CLAUDE.md Auto-Refresh Protocol
**Mandatory context updates for consistent collaboration:**

1. **Session Start**: Always read CLAUDE.md to understand current collaboration rules
2. **Every 10 interactions**: Re-read CLAUDE.md to ensure rule compliance
3. **Before complex tasks**: Check CLAUDE.md for appropriate tool selection and collaboration patterns
4. **After rule changes**: Immediately inform Gemini of any CLAUDE.md updates
5. **Memory synchronization**: Store CLAUDE.md key principles in Memory MCP for quick reference

**Implementation Pattern:**
```bash
# At session start and every 10 interactions
Read: /path/to/CLAUDE.md

# Store key rules in memory
mcp_memory_create_entities: "CLAUDE Collaboration Rules" (entityType: "guidelines")

# Inform Gemini of rule updates
mcp_gemini_chat: "CLAUDE.md has been updated with new collaboration rules: [summary]"
```

**Rule Propagation**: When CLAUDE.md is updated, both Claude and Gemini must acknowledge and adapt to new collaboration patterns within the same session.

## 📋 Quality Gates & Standards

### Code Quality Requirements
- **Security**: No exposed secrets, proper input validation
- **Performance**: Consider token usage, avoid unnecessary API calls  
- **Maintainability**: Clear variable names, logical structure
- **Documentation**: Inline comments for complex logic only when requested

### Documentation Quality Gates
- **Accuracy**: Documentation must reflect actual code behavior
- **Completeness**: Cover all user-facing functionality
- **Accessibility**: Understandable by intended audience
- **Currency**: Updated with every related code change

### Collaboration Quality Gates
- **Task Planning**: Use TodoWrite for complex tasks
- **Tool Appropriateness**: Use the right tool for each job
- **Context Preservation**: Maintain conversation threads
- **Validation**: Always validate assumptions with appropriate tools

## 🖥️ MCP Server Integration Rules

### Memory MCP Server (`mcp__memory__*`)
**Primary Usage**: Long-term context preservation and project knowledge management

#### Entity Management Strategy
```bash
# Project Structure Entities
- "Repository Architecture" (entityType: "codebase_structure")  
- "User Preferences" (entityType: "configuration")
- "Active Tasks" (entityType: "work_items")
- "Validation History" (entityType: "quality_records")

# Relationship Patterns  
- "depends_on", "conflicts_with", "validates", "implements"
```

#### Mandatory Memory Operations
1. **Task Start**: Query memory for related context
2. **Key Decisions**: Create entities for architectural choices
3. **Progress Updates**: Add observations to track status
4. **Task Completion**: Record final outcomes and learnings
5. **Validation Results**: Store both positive and negative findings

### Context7 MCP Server (`mcp__context7__*`)
**Primary Usage**: External documentation and library reference

#### Usage Guidelines
1. **Library Research**: Always resolve library IDs before requesting docs
2. **Architecture Decisions**: Fetch relevant framework documentation
3. **Best Practices**: Query for current industry standards
4. **Token Management**: Use focused topics to optimize context usage

```bash
# Workflow Example
mcp__context7__resolve-library-id libraryName="fastapi"
mcp__context7__get-library-docs context7CompatibleLibraryID="/tiangolo/fastapi" topic="security middleware"
```

### IDE MCP Server (`mcp__ide__*`)  
**Primary Usage**: Real-time code validation and execution

#### Integration Pattern
1. **Live Validation**: Check diagnostics before final review
2. **Testing**: Execute code snippets for validation
3. **Error Verification**: Confirm fixes resolve actual issues

### Memory Bank Strategy

#### Initialization Protocol
**ALWAYS start every session by checking for `memory-bank/` directory:**

**Initial Check:**
```bash
# First action in any session
<thinking>
- **CHECK FOR MEMORY BANK:**
  * First, check if the memory-bank/ directory exists.
  * If memory-bank DOES exist, skip immediately to `if_memory_bank_exists`.
</thinking>

LS tool: Check for memory-bank/ directory existence
```

**If No Memory Bank Exists:**
1. **Inform User**: "No Memory Bank was found. I recommend creating one to maintain project context."
2. **Offer Initialization**: Ask user if they would like to initialize the Memory Bank.
3. **Conditional Actions**:
   - **If user declines**:
     ```bash
     <thinking>
     I need to proceed with the task without Memory Bank functionality.
     </thinking>
     ```
     a. Inform user that Memory Bank will not be created
     b. Set status to `[MEMORY BANK: INACTIVE]`
     c. Proceed with task using current context or ask followup question if no task provided

   - **If user agrees**:
     ```bash
     <thinking>
     I need to create the `memory-bank/` directory and core files. I should use Write tool for this, and I should do it one file at a time, waiting for confirmation after each. The initial content for each file is defined below. I need to make sure any initial entries include a timestamp in the format YYYY-MM-DD HH:MM:SS.
     </thinking>
     ```

4. **Check for `projectBrief.md`**:
   - Use LS tool to check for `projectBrief.md` *before* offering to create memory bank
   - If `projectBrief.md` exists: Read its contents *before* offering to create memory bank
   - If no `projectBrief.md`: Skip this step (handle prompting for project info *after* user agrees to initialize)

5. **Memory Bank Creation Process**:
   ```bash
   <thinking>
   I need to add default content for the Memory Bank files.
   </thinking>
   ```
   a. Create the `memory-bank/` directory
   b. Create `memory-bank/productContext.md` with initial content template
   c. Create `memory-bank/activeContext.md` with initial content template  
   d. Create `memory-bank/progress.md` with initial content template
   e. Create `memory-bank/decisionLog.md` with initial content template
   f. Create `memory-bank/systemPatterns.md` with initial content template
   g. Set status to `[MEMORY BANK: ACTIVE]` and inform user
   h. Proceed with task using Memory Bank context or ask followup question if no task provided

**If Memory Bank Exists:**
```bash
**READ *ALL* MEMORY BANK FILES**
<thinking>
I will read all memory bank files, one at a time.
</thinking>

Plan: Read all mandatory files sequentially.
1. Read `productContext.md`
2. Read `activeContext.md` 
3. Read `systemPatterns.md` 
4. Read `decisionLog.md` 
5. Read `progress.md` 
6. Set status to [MEMORY BANK: ACTIVE] and inform user
7. Proceed with task using Memory Bank context or ask followup question if no task provided
```

**Status Requirement:**
- Begin EVERY response with either `[MEMORY BANK: ACTIVE]` or `[MEMORY BANK: INACTIVE]` according to current state

#### Memory Bank File Structure & Templates
```
memory-bank/
├── productContext.md     # High-level project overview and goals
├── activeContext.md      # Current status, recent changes, open issues  
├── progress.md          # Task tracking (completed, current, next)
├── decisionLog.md       # Architectural decisions with rationale
└── systemPatterns.md    # Recurring patterns and standards
```

**Initial Content Templates**:

**productContext.md**:
```markdown
# Product Context

This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon projectBrief.md (if provided) and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.
YYYY-MM-DD HH:MM:SS - Log of updates made will be appended as footnotes to the end of this file.

*

## Project Goal

*   

## Key Features

*   

## Overall Architecture

*   
```

**activeContext.md**:
```markdown
# Active Context

This file tracks the project's current status, including recent changes, current goals, and open questions.
YYYY-MM-DD HH:MM:SS - Log of updates made.

*

## Current Focus

*   

## Recent Changes

*   

## Open Questions/Issues

*   
```

**progress.md**:
```markdown
# Progress

This file tracks the project's progress using a task list format.
YYYY-MM-DD HH:MM:SS - Log of updates made.

*

## Completed Tasks

*   

## Current Tasks

*   

## Next Steps

*
```

**decisionLog.md**:
```markdown
# Decision Log

This file records architectural and implementation decisions using a list format.
YYYY-MM-DD HH:MM:SS - Log of updates made.

*

## Decision

*

## Rationale 

*

## Implementation Details

*
```

**systemPatterns.md**:
```markdown
# System Patterns *Optional*

This file documents recurring patterns and standards used in the project.
It is optional, but recommended to be updated as the project evolves.
YYYY-MM-DD HH:MM:SS - Log of updates made.

*

## Coding Patterns

*   

## Architectural Patterns

*   

## Testing Patterns

*
```

#### Update Triggers & Patterns
**Real-time updates throughout session when:**

- **Product Context**: High-level goals/features/architecture changes
- **Active Context**: Focus shifts, significant progress, new issues arise
- **Progress**: Tasks begin, complete, or change status
- **Decision Log**: Architectural decisions, technology choices, design patterns
- **System Patterns**: New patterns introduced or existing ones modified

#### UMB Command (`Update Memory Bank`)
**Manual synchronization command for comprehensive updates:**

```bash
User: "UMB" or "Update Memory Bank"
Response: "[MEMORY BANK: UPDATING]"
```

**UMB Process**:
1. Review complete chat history
2. Extract cross-mode information and context
3. Update all affected memory-bank files
4. Sync with Memory MCP entities
5. Ensure consistency across all systems

#### Memory Bank ↔ Memory MCP Integration
**Dual-system approach for maximum context preservation:**

```bash
# On Memory Bank creation/update
1. Update memory-bank/*.md files
2. Create/update corresponding Memory MCP entities:
   - "Project Context" (entityType: "memory_bank_sync") 
   - "Active Tasks" (entityType: "memory_bank_sync")
   - "Decision History" (entityType: "memory_bank_sync")

# Cross-reference pattern
mcp__memory__create_relations:
- "Memory Bank" -> "validates" -> "Memory MCP Context"
- "Decision Log Entry" -> "implements" -> "Architecture Decision"
```

### MCP Server Orchestration Rules

#### Priority Order for Context  
1. **Memory Bank**: Local file-based project context (primary)
2. **Memory MCP**: Entity-based context and relationships (secondary)
3. **Context7**: External documentation when needed
4. **IDE**: Live validation as final check

#### Resource Management
- **Token Budgeting**: Reserve 40% of context (30% Memory Bank + 10% Memory MCP)
- **Update Frequency**: Memory Bank updates real-time, Memory MCP after significant decisions
- **Cleanup**: Archive completed entities monthly, rotate old memory-bank entries

#### Error Handling
- **Memory Bank Unavailable**: Fall back to Memory MCP only
- **Memory MCP Unavailable**: Use Memory Bank files only  
- **Both Unavailable**: Fall back to TodoWrite for basic tracking
- **Context7 Timeout**: Use web search as backup
- **IDE Issues**: Continue with static analysis only

## 🚀 Repository-Specific Guidelines

### File Structure Understanding
- `tools/`: Individual MCP tool implementations
- `utils/`: Shared utilities (file handling, git operations, token management)
- `prompts/`: System prompts for different tool types
- `tests/`: Comprehensive test suite
- `config.py`: Centralized configuration

### Key Integration Points
- `config.py:24`: Model configuration (`GEMINI_MODEL`)
- `config.py:30`: Token limits (`MAX_CONTEXT_TOKENS`)  
- `utils/git_utils.py`: Git operations for code analysis
- `utils/file_utils.py`: File reading and processing
- `utils/conversation_memory.py`: Cross-session context

### Development Workflows
1. **Feature Branches**: Always work on feature branches
2. **Testing**: Run full test suite before PR
3. **Documentation**: Update docs with every change
4. **Review Process**: Use `codereview` tool, then human review

## 🎯 Success Metrics

### For Claude & Gemini Collaboration
- All complex tasks tracked with TodoWrite
- Appropriate tool selection for each phase
- Comprehensive pre-commit validation
- Documentation updated with every code change

### For Code Quality
- No critical security issues in `codereview`
- All tests passing
- Documentation accuracy verified
- Performance considerations addressed

### For User Experience
- Technical users can contribute using contributing docs
- Non-technical users can understand system purpose
- Clear troubleshooting guidance available
- Setup instructions are complete and tested

---

This framework ensures that every contribution to the repository maintains high standards while leveraging the full collaborative potential of Claude and Gemini working together.