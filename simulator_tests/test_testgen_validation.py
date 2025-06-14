#!/usr/bin/env python3
"""
TestGen Tool Validation Test

Tests the testgen tool by:
- Creating a test code file with a specific function
- Using testgen to generate tests with a specific function name
- Validating that the output contains the expected test function
- Confirming the format matches test generation patterns
"""

from .base_test import BaseSimulatorTest


class TestGenValidationTest(BaseSimulatorTest):
    """Test testgen tool validation with specific function name"""

    @property
    def test_name(self) -> str:
        return "testgen_validation"

    @property
    def test_description(self) -> str:
        return "TestGen tool validation with specific test function"

    def run_test(self) -> bool:
        """Test testgen tool with specific function name validation"""
        try:
            self.logger.info("Test: TestGen tool validation")

            # Setup test files
            self.setup_test_files()

            # Create a specific code file for test generation
            test_code_content = '''"""
Sample authentication module for testing testgen
"""

class UserAuthenticator:
    """Handles user authentication logic"""

    def __init__(self):
        self.failed_attempts = {}
        self.max_attempts = 3

    def validate_password(self, username, password):
        """Validate user password with security checks"""
        if not username or not password:
            return False

        if username in self.failed_attempts:
            if self.failed_attempts[username] >= self.max_attempts:
                return False  # Account locked

        # Simple validation for demo
        if len(password) < 8:
            self._record_failed_attempt(username)
            return False

        if password == "password123":  # Demo valid password
            self._reset_failed_attempts(username)
            return True

        self._record_failed_attempt(username)
        return False

    def _record_failed_attempt(self, username):
        """Record a failed login attempt"""
        self.failed_attempts[username] = self.failed_attempts.get(username, 0) + 1

    def _reset_failed_attempts(self, username):
        """Reset failed attempts after successful login"""
        if username in self.failed_attempts:
            del self.failed_attempts[username]
'''

            # Create the auth code file
            auth_file = self.create_additional_test_file("user_auth.py", test_code_content)

            # Test testgen tool with specific requirements
            self.logger.info("  1.1: Generate tests with specific function name")
            response, continuation_id = self.call_mcp_tool(
                "testgen",
                {
                    "files": [auth_file],
                    "prompt": "Generate comprehensive tests for the UserAuthenticator.validate_password method. Include tests for edge cases, security scenarios, and account locking. Use the specific test function name 'test_password_validation_edge_cases' for one of the test methods.",
                    "model": "flash",
                },
            )

            if not response:
                self.logger.error("Failed to get testgen response")
                return False

            self.logger.info("  1.2: Validate response contains expected test function")

            # Check that the response contains the specific test function name
            if "test_password_validation_edge_cases" not in response:
                self.logger.error("Response does not contain the requested test function name")
                self.logger.debug(f"Response content: {response[:500]}...")
                return False

            # Check for common test patterns
            test_patterns = [
                "def test_",  # Test function definition
                "assert",  # Assertion statements
                "UserAuthenticator",  # Class being tested
                "validate_password",  # Method being tested
            ]

            missing_patterns = []
            for pattern in test_patterns:
                if pattern not in response:
                    missing_patterns.append(pattern)

            if missing_patterns:
                self.logger.error(f"Response missing expected test patterns: {missing_patterns}")
                self.logger.debug(f"Response content: {response[:500]}...")
                return False

            self.logger.info("  ✅ TestGen tool validation successful")
            self.logger.info("  ✅ Generated tests contain expected function name")
            self.logger.info("  ✅ Generated tests follow proper test patterns")

            return True

        except Exception as e:
            self.logger.error(f"TestGen validation test failed: {e}")
            return False
        finally:
            self.cleanup_test_files()
