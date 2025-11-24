"""
Live model tests for Zen MCP Server

This module contains tests that make real API calls to providers.
These tests are excluded by default and only run with LIVE_MODEL_TESTS=1.

To run live tests:
    LIVE_MODEL_TESTS=1 python -m pytest tests/live/ -v

To run specific live test:
    LIVE_MODEL_TESTS=1 python -m pytest tests/live/test_provider_connectivity.py -v
"""
