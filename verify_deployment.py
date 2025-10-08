#!/usr/bin/env python3
"""
Deployment Verification Script for Zen MCP Token Optimization

This script verifies that all required files and configurations are in place
for the A/B testing deployment.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# Colors for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check_file_exists(filepath: str) -> Tuple[bool, str]:
    """Check if a file exists and return status."""
    path = Path(filepath)
    if path.exists():
        return True, f"{GREEN}✓{RESET} {filepath}"
    else:
        return False, f"{RED}✗{RESET} {filepath} - MISSING"


def check_import(module_path: str, class_name: str) -> Tuple[bool, str]:
    """Check if a Python module and class can be imported."""
    try:
        module = __import__(module_path, fromlist=[class_name])
        if hasattr(module, class_name):
            return True, f"{GREEN}✓{RESET} {module_path}.{class_name}"
        else:
            return False, f"{RED}✗{RESET} {module_path}.{class_name} - Class not found"
    except ImportError as e:
        return False, f"{RED}✗{RESET} {module_path} - Import error: {e}"


def check_docker_compose() -> Tuple[bool, str]:
    """Check if docker-compose.yml has token optimization variables."""
    try:
        with open("docker-compose.yml") as f:
            content = f.read()
            required_vars = [
                "ZEN_TOKEN_OPTIMIZATION",
                "ZEN_OPTIMIZATION_MODE",
                "ZEN_TOKEN_TELEMETRY",
                "ZEN_OPTIMIZATION_VERSION",
            ]
            missing = []
            for var in required_vars:
                if var not in content:
                    missing.append(var)

            if missing:
                return False, f"{RED}✗{RESET} docker-compose.yml - Missing: {', '.join(missing)}"
            else:
                return True, f"{GREEN}✓{RESET} docker-compose.yml - All token vars present"
    except Exception as e:
        return False, f"{RED}✗{RESET} docker-compose.yml - Error: {e}"


def check_permissions() -> List[Tuple[bool, str]]:
    """Check file permissions for executables."""
    results = []
    executables = ["ab_test_control.sh"]

    for exe in executables:
        if os.path.exists(exe):
            if os.access(exe, os.X_OK):
                results.append((True, f"{GREEN}✓{RESET} {exe} is executable"))
            else:
                results.append((False, f"{YELLOW}⚠{RESET} {exe} not executable - run: chmod +x {exe}"))
        else:
            results.append((False, f"{RED}✗{RESET} {exe} not found"))

    return results


def main():
    """Run all verification checks."""
    print(f"\n{BOLD}🔍 Zen MCP Token Optimization Deployment Verification{RESET}")
    print("=" * 60)

    all_checks_passed = True

    # Check core files
    print(f"\n{BOLD}📁 Core Files:{RESET}")
    core_files = [
        "server.py",
        "server_token_optimized.py",
        "token_optimization_config.py",
        "tools/mode_selector.py",
        "tools/mode_executor.py",
        "docker-compose.yml",
        "ab_test_control.sh",
        "analyze_telemetry.py",
        "DEPLOYMENT_GUIDE.md",
    ]

    for filepath in core_files:
        passed, message = check_file_exists(filepath)
        print(message)
        if not passed:
            all_checks_passed = False

    # Check Python imports (these are Docker-only dependencies, so warnings only)
    print(f"\n{BOLD}🐍 Python Modules (Docker container dependencies):{RESET}")
    modules_to_check = [
        ("tools.mode_selector", "ModeSelectorTool"),
        ("tools.mode_executor", "ModeExecutor"),
        ("server_token_optimized", "get_optimized_tools"),
        ("token_optimization_config", "TokenOptimizationConfig"),
    ]

    docker_import_warnings = False
    for module_path, class_name in modules_to_check:
        passed, message = check_import(module_path, class_name)
        if not passed and ("pydantic" in message or "mcp" in message):
            # These are Docker-only dependencies - show as warnings
            print(f"{YELLOW}⚠{RESET} {module_path}.{class_name} - Docker dependency (OK)")
            docker_import_warnings = True
        else:
            print(message)
            if not passed:
                all_checks_passed = False

    if docker_import_warnings:
        print(f"{YELLOW}  Note: Dependencies like pydantic/mcp are only needed inside Docker{RESET}")

    # Check Docker configuration
    print(f"\n{BOLD}🐳 Docker Configuration:{RESET}")
    passed, message = check_docker_compose()
    print(message)
    if not passed:
        all_checks_passed = False

    # Check file permissions
    print(f"\n{BOLD}🔐 File Permissions:{RESET}")
    permission_results = check_permissions()
    for passed, message in permission_results:
        print(message)
        if not passed and "⚠" not in message:  # Warnings don't fail the check
            all_checks_passed = False

    # Check environment
    print(f"\n{BOLD}🌍 Environment Variables:{RESET}")
    env_vars = ["GEMINI_API_KEY", "OPENAI_API_KEY"]
    env_file_exists = os.path.exists(".env")

    for var in env_vars:
        if os.getenv(var):
            print(f"{GREEN}✓{RESET} {var} is set in environment")
        elif env_file_exists:
            # Check if it's in .env file
            with open(".env") as f:
                env_content = f.read()
                if f"{var}=" in env_content and f"# {var}=" not in env_content:
                    print(f"{GREEN}✓{RESET} {var} configured in .env file")
                else:
                    print(f"{YELLOW}⚠{RESET} {var} not set - Required for full functionality")
        else:
            print(f"{YELLOW}⚠{RESET} {var} not set - Required for full functionality")

    # Summary
    print("\n" + "=" * 60)
    if all_checks_passed:
        print(f"{GREEN}{BOLD}✅ All checks passed! Ready for deployment.{RESET}")
        print(f"\n{BOLD}Next steps:{RESET}")
        print("1. Run: docker-compose up --build -d")
        print("2. Run: ./ab_test_control.sh")
        print("3. Monitor with: docker-compose logs -f zen-mcp")
        return 0
    else:
        print(f"{RED}{BOLD}❌ Some checks failed. Please fix the issues above.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
