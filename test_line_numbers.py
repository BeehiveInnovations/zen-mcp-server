#!/usr/bin/env python3
"""Test file to verify line number accuracy"""


# Line 4: Empty line above
def example_function():
    """Line 6: Docstring"""
    # Line 7: Comment
    pass  # Line 8


# Line 10: Another comment
class TestClass:
    """Line 12: Class docstring"""

    def __init__(self):
        """Line 15: Init docstring"""
        # Line 16: This is where we'll test
        self.test_variable = "Line 17"

    def method_one(self):
        """Line 20: Method docstring"""
        # Line 21: Important assignment below
        ignore_patterns = ["pattern1", "pattern2", "pattern3"]  # Line 22: This is our test line
        return ignore_patterns


# Line 25: More code below
def another_function():
    """Line 27: Another docstring"""
    # Line 28: Another assignment
    ignore_patterns = ["different", "patterns"]  # Line 29: Second occurrence
    return ignore_patterns


# Line 32: End of file marker
