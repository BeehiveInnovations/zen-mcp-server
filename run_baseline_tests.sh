#!/bin/bash
# Baseline Test Commands for Token Optimization A/B Testing
# Run these in Claude Code CLI sequentially

echo "=== BASELINE TEST PHASE 1: Code Analysis & Architecture ==="

echo "Q1.1: Complex Architecture Analysis (gemini-2.5-flash)"
echo 'zen analyze --model gemini-2.5-flash "Analyze the token optimization architecture in this codebase. Focus on the two-stage approach, mode selection logic, and telemetry system. Include files: server.py, tools/mode_selector.py, token_optimization_config.py"'

echo ""
echo "Q1.2: Security Audit (grok-code-fast-1)"  
echo 'zen secaudit --model grok-code-fast-1 "Perform security audit of the MCP server focusing on: TCP transport security, Docker container isolation, API key handling, and input validation."'

echo ""
echo "Q1.3: Performance Analysis (o3-mini)"
echo 'zen debug --model o3-mini --confidence exploring "Investigate potential performance bottlenecks in the token optimization system. Analyze the two-stage execution flow, Redis conversation memory, and provider selection logic."'

echo ""
echo "=== BASELINE TEST PHASE 2: Code Review & Refactoring ==="

echo "Q2.1: Multi-file Code Review (gemini-2.5-flash)"
echo 'zen codereview --model gemini-2.5-flash "Review the token optimization implementation for code quality, maintainability, and best practices. Focus on server_token_optimized.py, tools/mode_executor.py, and the overall integration."'

echo ""
echo "Q2.2: Refactoring Suggestions (grok-code-fast-1)"
echo 'zen refactor --model grok-code-fast-1 "Suggest refactoring opportunities for the MCP server architecture to improve modularity, reduce coupling, and enhance testability. Consider the provider system and tool registration."'

echo ""
echo "Q2.3: Test Strategy (o3-mini)"
echo 'zen testgen --model o3-mini "Generate comprehensive test strategy for token optimization feature including unit tests, integration tests, and A/B testing validation. Focus on edge cases and error scenarios."'

echo ""
echo "=== BASELINE TEST PHASE 3: Advanced Problem Solving ==="

echo "Q3.1: Debugging Complex Issue (gemini-2.5-flash)"
echo 'zen debug --model gemini-2.5-flash --confidence exploring "Debug why the Docker dual-transport mode occasionally restarts. Analyze server.py transport logic, Docker configuration, and error handling patterns."'

echo ""
echo "Q3.2: Consensus Decision (multiple models)"
echo 'zen consensus "Should we implement WebSocket transport in addition to TCP and stdio? Consider: performance implications, client complexity, Docker networking, and maintenance overhead."'

echo ""
echo "Q3.3: Deep Investigation (grok-code-fast-1)"
echo 'zen thinkdeep --model grok-code-fast-1 --confidence high "Investigate the optimal token budget allocation strategy for different model types. Consider context windows, pricing, response quality, and conversation threading requirements."'

echo ""
echo "=== After running all tests, check telemetry: ==="
echo "cat logs/token_telemetry.jsonl | tail -10"
echo 'grep "v5.11.0-baseline" logs/token_telemetry.jsonl | wc -l'