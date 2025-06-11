#!/usr/bin/env python3
"""
Communication Simulator Test for Gemini MCP Server

This script provides comprehensive end-to-end testing of the Gemini MCP server
by simulating real Claude CLI communications and validating conversation
continuity, file handling, deduplication features, and clarification scenarios.

Test Flow:
1. Setup fresh Docker environment with clean containers
2. Load and run individual test modules
3. Validate system behavior through logs and Redis
4. Cleanup and report results

Usage:
    python communication_simulator_test.py [--verbose] [--keep-logs] [--tests TEST_NAME...] [--individual TEST_NAME] [--skip-docker]
    
    --tests: Run specific tests only (space-separated)
    --list-tests: List all available tests
    --individual: Run a single test individually
    --skip-docker: Skip Docker setup (assumes containers are already running)
    
Available tests:
    basic_conversation          - Basic conversation flow with chat tool
    per_tool_deduplication      - File deduplication for individual tools
    cross_tool_continuation     - Cross-tool conversation continuation scenarios
    content_validation          - Content validation and duplicate detection
    logs_validation             - Docker logs validation
    redis_validation            - Redis conversation memory validation

Examples:
    # Run all tests
    python communication_simulator_test.py
    
    # Run only basic conversation and content validation tests
    python communication_simulator_test.py --tests basic_conversation content_validation
    
    # Run a single test individually (with full Docker setup)
    python communication_simulator_test.py --individual content_validation
    
    # Run a single test individually (assuming Docker is already running)
    python communication_simulator_test.py --individual content_validation --skip-docker
    
    # List available tests
    python communication_simulator_test.py --list-tests
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Optional


class CommunicationSimulator:
    """Simulates real-world Claude CLI communication with MCP Gemini server"""

    def __init__(self, verbose: bool = False, keep_logs: bool = False, selected_tests: list[str] = None):
        self.verbose = verbose
        self.keep_logs = keep_logs
        self.selected_tests = selected_tests or []
        self.temp_dir = None
        self.container_name = "gemini-mcp-server"
        self.redis_container = "gemini-mcp-redis"

        # Import test registry
        from simulator_tests import TEST_REGISTRY
        self.test_registry = TEST_REGISTRY

        # Available test methods mapping
        self.available_tests = {
            name: self._create_test_runner(test_class)
            for name, test_class in self.test_registry.items()
        }

        # Test result tracking
        self.test_results = {test_name: False for test_name in self.test_registry.keys()}

        # Configure logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

    def _create_test_runner(self, test_class):
        """Create a test runner function for a test class"""
        def run_test():
            test_instance = test_class(verbose=self.verbose)
            result = test_instance.run_test()
            # Update results
            test_name = test_instance.test_name
            self.test_results[test_name] = result
            return result
        return run_test

    def setup_test_environment(self) -> bool:
        """Setup fresh Docker environment"""
        try:
            self.logger.info("🚀 Setting up test environment...")

            # Create temporary directory for test files
            self.temp_dir = tempfile.mkdtemp(prefix="mcp_test_")
            self.logger.debug(f"Created temp directory: {self.temp_dir}")

            # Setup Docker environment
            return self._setup_docker()

        except Exception as e:
            self.logger.error(f"Failed to setup test environment: {e}")
            return False

    def _setup_docker(self) -> bool:
        """Setup fresh Docker environment"""
        try:
            self.logger.info("🐳 Setting up Docker environment...")

            # Stop and remove existing containers
            self._run_command(["docker", "compose", "down", "--remove-orphans"], check=False, capture_output=True)

            # Clean up any old containers/images
            old_containers = [self.container_name, self.redis_container]
            for container in old_containers:
                self._run_command(["docker", "stop", container], check=False, capture_output=True)
                self._run_command(["docker", "rm", container], check=False, capture_output=True)

            # Build and start services
            self.logger.info("📦 Building Docker images...")
            result = self._run_command(["docker", "compose", "build", "--no-cache"], capture_output=True)
            if result.returncode != 0:
                self.logger.error(f"Docker build failed: {result.stderr}")
                return False

            self.logger.info("🚀 Starting Docker services...")
            result = self._run_command(["docker", "compose", "up", "-d"], capture_output=True)
            if result.returncode != 0:
                self.logger.error(f"Docker startup failed: {result.stderr}")
                return False

            # Wait for services to be ready
            self.logger.info("⏳ Waiting for services to be ready...")
            time.sleep(10)  # Give services time to initialize

            # Verify containers are running
            if not self._verify_containers():
                return False

            self.logger.info("✅ Docker environment ready")
            return True

        except Exception as e:
            self.logger.error(f"Docker setup failed: {e}")
            return False

    def _verify_containers(self) -> bool:
        """Verify that required containers are running"""
        try:
            result = self._run_command(["docker", "ps", "--format", "{{.Names}}"], capture_output=True)
            running_containers = result.stdout.decode().strip().split("\\n")

            required = [self.container_name, self.redis_container]
            for container in required:
                if container not in running_containers:
                    self.logger.error(f"Container not running: {container}")
                    return False

            self.logger.debug(f"Verified containers running: {required}")
            return True

        except Exception as e:
            self.logger.error(f"Container verification failed: {e}")
            return False

    def simulate_claude_cli_session(self) -> bool:
        """Simulate a complete Claude CLI session with conversation continuity"""
        try:
            self.logger.info("🤖 Starting Claude CLI simulation...")

            # If specific tests are selected, run only those
            if self.selected_tests:
                return self._run_selected_tests()
            
            # Otherwise run all tests in order
            test_sequence = list(self.test_registry.keys())
            
            for test_name in test_sequence:
                if not self._run_single_test(test_name):
                    return False

            self.logger.info("✅ All tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Claude CLI simulation failed: {e}")
            return False

    def _run_selected_tests(self) -> bool:
        """Run only the selected tests"""
        try:
            self.logger.info(f"🎯 Running selected tests: {', '.join(self.selected_tests)}")
            
            for test_name in self.selected_tests:
                if not self._run_single_test(test_name):
                    return False
                    
            self.logger.info("✅ All selected tests passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Selected tests failed: {e}")
            return False

    def _run_single_test(self, test_name: str) -> bool:
        """Run a single test by name"""
        try:
            if test_name not in self.available_tests:
                self.logger.error(f"Unknown test: {test_name}")
                self.logger.info(f"Available tests: {', '.join(self.available_tests.keys())}")
                return False
                
            self.logger.info(f"🧪 Running test: {test_name}")
            test_function = self.available_tests[test_name]
            result = test_function()
            
            if result:
                self.logger.info(f"✅ Test {test_name} passed")
            else:
                self.logger.error(f"❌ Test {test_name} failed")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Test {test_name} failed with exception: {e}")
            return False

    def run_individual_test(self, test_name: str, skip_docker_setup: bool = False) -> bool:
        """Run a single test individually with optional Docker setup skip"""
        try:
            if test_name not in self.available_tests:
                self.logger.error(f"Unknown test: {test_name}")
                self.logger.info(f"Available tests: {', '.join(self.available_tests.keys())}")
                return False

            self.logger.info(f"🧪 Running individual test: {test_name}")

            # Setup environment unless skipped
            if not skip_docker_setup:
                if not self.setup_test_environment():
                    self.logger.error("❌ Environment setup failed")
                    return False

            # Run the single test
            test_function = self.available_tests[test_name]
            result = test_function()

            if result:
                self.logger.info(f"✅ Individual test {test_name} passed")
            else:
                self.logger.error(f"❌ Individual test {test_name} failed")

            return result

        except Exception as e:
            self.logger.error(f"Individual test {test_name} failed with exception: {e}")
            return False
        finally:
            if not skip_docker_setup and not self.keep_logs:
                self.cleanup()

    def get_available_tests(self) -> dict[str, str]:
        """Get available tests with descriptions"""
        descriptions = {}
        for name, test_class in self.test_registry.items():
            # Create temporary instance to get description
            temp_instance = test_class(verbose=False)
            descriptions[name] = temp_instance.test_description
        return descriptions

    def print_test_summary(self):
        """Print comprehensive test results summary"""
        print("\\n" + "=" * 70)
        print("🧪 GEMINI MCP COMMUNICATION SIMULATOR - TEST RESULTS SUMMARY")
        print("=" * 70)

        passed_count = sum(1 for result in self.test_results.values() if result)
        total_count = len(self.test_results)

        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            # Get test description
            temp_instance = self.test_registry[test_name](verbose=False)
            description = temp_instance.test_description
            print(f"📝 {description}: {status}")

        print(f"\\n🎯 OVERALL RESULT: {'🎉 SUCCESS' if passed_count == total_count else '❌ FAILURE'}")
        print(f"✅ {passed_count}/{total_count} tests passed")
        print("=" * 70)
        return passed_count == total_count

    def run_full_test_suite(self, skip_docker_setup: bool = False) -> bool:
        """Run the complete test suite"""
        try:
            self.logger.info("🚀 Starting Gemini MCP Communication Simulator Test Suite")

            # Setup
            if not skip_docker_setup:
                if not self.setup_test_environment():
                    self.logger.error("❌ Environment setup failed")
                    return False
            else:
                self.logger.info("⏩ Skipping Docker setup (containers assumed running)")

            # Main simulation
            if not self.simulate_claude_cli_session():
                self.logger.error("❌ Claude CLI simulation failed")
                return False

            # Print comprehensive summary
            overall_success = self.print_test_summary()

            return overall_success

        except Exception as e:
            self.logger.error(f"Test suite failed: {e}")
            return False
        finally:
            if not self.keep_logs and not skip_docker_setup:
                self.cleanup()

    def cleanup(self):
        """Cleanup test environment"""
        try:
            self.logger.info("🧹 Cleaning up test environment...")

            if not self.keep_logs:
                # Stop Docker services
                self._run_command(["docker", "compose", "down", "--remove-orphans"], check=False, capture_output=True)
            else:
                self.logger.info("📋 Keeping Docker services running for log inspection")

            # Remove temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.debug(f"Removed temp directory: {self.temp_dir}")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")

    def _run_command(self, cmd: list[str], check: bool = True, capture_output: bool = False, **kwargs):
        """Run a shell command with logging"""
        if self.verbose:
            self.logger.debug(f"Running: {' '.join(cmd)}")

        return subprocess.run(cmd, check=check, capture_output=capture_output, **kwargs)


def parse_arguments():
    """Parse and validate command line arguments"""
    parser = argparse.ArgumentParser(description="Gemini MCP Communication Simulator Test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--keep-logs", action="store_true", help="Keep Docker services running for log inspection")
    parser.add_argument("--tests", "-t", nargs="+", help="Specific tests to run (space-separated)")
    parser.add_argument("--list-tests", action="store_true", help="List available tests and exit")
    parser.add_argument("--individual", "-i", help="Run a single test individually")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker setup (assumes containers are already running)")

    return parser.parse_args()


def list_available_tests():
    """List all available tests and exit"""
    simulator = CommunicationSimulator()
    print("Available tests:")
    for test_name, description in simulator.get_available_tests().items():
        print(f"  {test_name:<25} - {description}")


def run_individual_test(simulator, test_name, skip_docker):
    """Run a single test individually"""
    try:
        success = simulator.run_individual_test(test_name, skip_docker_setup=skip_docker)
        
        if success:
            print(f"\\n🎉 INDIVIDUAL TEST {test_name.upper()}: PASSED")
            return 0
        else:
            print(f"\\n❌ INDIVIDUAL TEST {test_name.upper()}: FAILED")
            return 1
            
    except KeyboardInterrupt:
        print(f"\\n🛑 Individual test {test_name} interrupted by user")
        if not skip_docker:
            simulator.cleanup()
        return 130
    except Exception as e:
        print(f"\\n💥 Individual test {test_name} failed with error: {e}")
        if not skip_docker:
            simulator.cleanup()
        return 1


def run_test_suite(simulator, skip_docker=False):
    """Run the full test suite or selected tests"""
    try:
        success = simulator.run_full_test_suite(skip_docker_setup=skip_docker)

        if success:
            print("\\n🎉 COMPREHENSIVE MCP COMMUNICATION TEST: PASSED")
            return 0
        else:
            print("\\n❌ COMPREHENSIVE MCP COMMUNICATION TEST: FAILED")
            print("⚠️  Check detailed results above")
            return 1

    except KeyboardInterrupt:
        print("\\n🛑 Test interrupted by user")
        if not skip_docker:
            simulator.cleanup()
        return 130
    except Exception as e:
        print(f"\\n💥 Unexpected error: {e}")
        if not skip_docker:
            simulator.cleanup()
        return 1


def main():
    """Main entry point"""
    args = parse_arguments()

    # Handle list tests request
    if args.list_tests:
        list_available_tests()
        return

    # Initialize simulator consistently for all use cases
    simulator = CommunicationSimulator(
        verbose=args.verbose,
        keep_logs=args.keep_logs,
        selected_tests=args.tests
    )

    # Determine execution mode and run
    if args.individual:
        exit_code = run_individual_test(simulator, args.individual, args.skip_docker)
    else:
        exit_code = run_test_suite(simulator, args.skip_docker)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()