# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for custom tool development.

## Contents

### Foundational ADRs
- **`centralized-model-registry.md`** - ✅ IMPLEMENTED (Partial) - **CRITICAL** - Data-driven model management architecture
- **`dynamic-model-availability.md`** - ✅ IMPLEMENTED - **CRITICAL** - Free model failover and paid model deprecation patterns
- **`tiered-consensus-implementation.md`** - ✅ IMPLEMENTED - Unified consensus tool with additive tier architecture

### Active ADRs
- **`quickreview.md`** - ✅ IMPLEMENTED - Basic validation tool using free models
- **`review.md`** - 📋 PLANNED - Peer review tool using value tier models
- **`criticalreview.md`** - 📋 PLANNED - Executive analysis using premium models
- **`future.md`** - 🔮 FUTURE - Long-term enhancements and extensions
- **`prepare-pr.md`** - 📋 ACTIVE - PR preparation checklist and validation

## Purpose

These ADRs document architectural decisions for the custom tools system, including:
- **Foundational architecture** (centralized model registry - READ FIRST)
- Tool design rationales and trade-offs
- Model selection strategies
- Implementation approaches
- Integration patterns

## Development Workflow

1. Review existing ADRs before implementing new tools
2. Update ADRs as implementations progress
3. Add new ADRs for additional custom tools
4. Reference ADRs in implementation files