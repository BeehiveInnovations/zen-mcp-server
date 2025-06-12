"""
Pytest configuration for Zen MCP Server tests
"""

import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the parent directory is in the Python path for imports
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Set dummy API keys for tests if not already set
if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = "dummy-key-for-tests"
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-tests"

# Set default model to a specific value for tests to avoid auto mode
# This prevents all tests from failing due to missing model parameter
os.environ["DEFAULT_MODEL"] = "gemini-2.5-flash-preview-05-20"

# Force reload of config module to pick up the env var
import config  # noqa: E402

importlib.reload(config)

# Set MCP_PROJECT_ROOT to a temporary directory for tests
# This provides a safe sandbox for file operations during testing
# Create a temporary directory that will be used as the project root for all tests
test_root = tempfile.mkdtemp(prefix="zen_mcp_test_")
os.environ["MCP_PROJECT_ROOT"] = test_root

# Configure asyncio for Windows compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Register providers for all tests
from providers import ModelProviderRegistry  # noqa: E402
from providers.base import ProviderType  # noqa: E402
from providers.gemini import GeminiModelProvider  # noqa: E402
from providers.openai import OpenAIModelProvider  # noqa: E402

# Register providers at test startup
ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)
ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)


@pytest.fixture
def project_path(tmp_path):
    """
    Provides a temporary directory within the PROJECT_ROOT sandbox for tests.
    This ensures all file operations during tests are within the allowed directory.
    """
    # Get the test project root
    test_root = Path(os.environ.get("MCP_PROJECT_ROOT", "/tmp"))

    # Create a subdirectory for this specific test
    test_dir = test_root / f"test_{tmp_path.name}"
    test_dir.mkdir(parents=True, exist_ok=True)

    return test_dir


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
