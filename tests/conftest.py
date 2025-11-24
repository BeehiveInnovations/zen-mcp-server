"""
Pytest configuration for Zen MCP Server tests
"""

import asyncio
import importlib
import os
import sys
from pathlib import Path

import pytest

# Ensure the parent directory is in the Python path for imports
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# --------------------------------------------------------------------
# Test environment setup
# --------------------------------------------------------------------
# Set default model to a specific value for tests to avoid auto mode
# This prevents all tests from failing due to missing model parameter
os.environ["DEFAULT_MODEL"] = "gemini-2.5-flash"

# Force reload of config module to pick up the env var
import config  # noqa: E402

importlib.reload(config)

# Note: This creates a test sandbox environment
# Tests create their own temporary directories as needed

# Configure asyncio for Windows compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --------------------------------------------------------------------
# Provider registration
# --------------------------------------------------------------------
from providers import ModelProviderRegistry  # noqa: E402
from providers.base import ProviderType  # noqa: E402
from providers.gemini import GeminiModelProvider  # noqa: E402
from providers.openai_provider import OpenAIModelProvider  # noqa: E402
from providers.xai import XAIModelProvider  # noqa: E402

# Register providers at test startup – will be overridden by the
# ``reset_registry`` fixture for isolation between tests.
ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)
ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)
ModelProviderRegistry.register_provider(ProviderType.XAI, XAIModelProvider)

# Register CUSTOM provider if CUSTOM_API_URL is available (for integration tests)
# But only if we're actually running integration tests, not unit tests
if os.getenv("CUSTOM_API_URL") and "test_prompt_regression.py" in os.getenv("PYTEST_CURRENT_TEST", ""):
    from providers.custom import CustomProvider  # noqa: E402

    def custom_provider_factory(api_key=None):
        """Factory function that creates CustomProvider with proper parameters."""
        base_url = os.getenv("CUSTOM_API_URL", "")
        return CustomProvider(api_key=api_key or "", base_url=base_url)

    ModelProviderRegistry.register_provider(ProviderType.CUSTOM, custom_provider_factory)


# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------
@pytest.fixture
def project_path(tmp_path):
    """
    Provides a temporary directory for tests.
    This ensures all file operations during tests are isolated.
    """
    # Create a subdirectory for this specific test
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


def _set_dummy_keys_if_missing():
    """Set dummy API keys only when they are completely absent."""
    for var in ("GEMINI_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"):
        if not os.environ.get(var):
            os.environ[var] = "dummy-key-for-tests"


# --------------------------------------------------------------------
# Registry isolation
# --------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_registry():
    """
    Ensure each test starts with a clean provider registry.
    This prevents state leakage between tests.
    """
    # Reset the singleton instance and clear all registrations
    ModelProviderRegistry._instance = None  # type: ignore
    # Reset model restriction cache to ensure environment-specific rules don't leak across tests
    import utils.model_restrictions

    utils.model_restrictions._restriction_service = None
    registry = ModelProviderRegistry()
    registry._providers.clear()
    # Re‑register the standard providers (real providers are optional;
    # they will be re‑added by ``mock_provider_availability`` if needed)
    ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)
    ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)
    ModelProviderRegistry.register_provider(ProviderType.XAI, XAIModelProvider)


# --------------------------------------------------------------------
# Fake provider fixture
# --------------------------------------------------------------------
from tests.mock_helpers import create_mock_provider


@pytest.fixture
def fake_provider():
    """
    Returns a fully‑compliant mock provider using ``create_mock_provider``.
    Tests can request this fixture to avoid instantiating real providers.
    """
    return create_mock_provider()


# --------------------------------------------------------------------
# Pytest configuration
# --------------------------------------------------------------------
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "no_mock_provider: disable automatic provider mocking")
    # Assume we need dummy keys until we learn otherwise
    config._needs_dummy_keys = True


def pytest_collection_modifyitems(session, config, items):
    """Hook that runs after test collection to check for no_mock_provider and live_model markers."""
    # Always set dummy keys if real keys are missing
    # This ensures tests work in CI even with no_mock_provider marker
    _set_dummy_keys_if_missing()

    # Handle live_model marker - exclude by default
    live_model_enabled = os.getenv("LIVE_MODEL_TESTS")

    for item in items:
        # If live_model tests are not enabled, skip them
        if item.get_closest_marker("live_model") and not live_model_enabled:
            item.add_marker(pytest.mark.skip(reason="Live model tests disabled. Set LIVE_MODEL_TESTS=1 to enable."))


# --------------------------------------------------------------------
# Mock provider availability
# --------------------------------------------------------------------
@pytest.fixture(autouse=True)
def mock_provider_availability(request, monkeypatch):
    """
    Automatically mock provider availability for all tests to prevent
    effective auto mode from being triggered when DEFAULT_MODEL is unavailable.
    This fixture respects the ``no_mock_provider`` marker.
    """
    # Skip this fixture for tests that need real providers
    if hasattr(request, "node"):
        marker = request.node.get_closest_marker("no_mock_provider")
        if marker:
            return

    # Ensure providers are registered (in case other tests cleared the registry)
    from providers.base import ProviderType

    registry = ModelProviderRegistry()

    if ProviderType.GOOGLE not in registry._providers:
        ModelProviderRegistry.register_provider(ProviderType.GOOGLE, GeminiModelProvider)
    if ProviderType.OPENAI not in registry._providers:
        ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)
    if ProviderType.XAI not in registry._providers:
        ModelProviderRegistry.register_provider(ProviderType.XAI, XAIModelProvider)

    # Ensure CUSTOM provider is registered if needed for integration tests
    if (
        os.getenv("CUSTOM_API_URL")
        and "test_prompt_regression.py" in os.getenv("PYTEST_CURRENT_TEST", "")
        and ProviderType.CUSTOM not in registry._providers
    ):
        from providers.custom import CustomProvider

        def custom_provider_factory(api_key=None):
            base_url = os.getenv("CUSTOM_API_URL", "")
            return CustomProvider(api_key=api_key or "", base_url=base_url)

        ModelProviderRegistry.register_provider(ProviderType.CUSTOM, custom_provider_factory)

    # Also mock is_effective_auto_mode for all BaseTool instances to return False
    # unless we're specifically testing auto mode behavior
    from tools.shared.base_tool import BaseTool

    def mock_is_effective_auto_mode(self):
        # If this is an auto mode test file or specific auto mode test, use the real logic
        test_file = request.node.fspath.basename if hasattr(request, "node") and hasattr(request.node, "fspath") else ""
        test_name = request.node.name if hasattr(request, "node") else ""

        # Allow auto mode for tests in auto mode files or with auto in the name
        if (
            "auto_mode" in test_file.lower()
            or "auto" in test_name.lower()
            or "intelligent_fallback" in test_file.lower()
            or "per_tool_model_defaults" in test_file.lower()
        ):
            # Call original method logic
            from config import DEFAULT_MODEL

            if DEFAULT_MODEL.lower() == "auto":
                return True
            provider = ModelProviderRegistry.get_provider_for_model(DEFAULT_MODEL)
            return provider is None
        # For all other tests, return False to disable auto mode
        return False

    monkeypatch.setattr(BaseTool, "is_effective_auto_mode", mock_is_effective_auto_mode)


# --------------------------------------------------------------------
# Live test infrastructure
# --------------------------------------------------------------------
@pytest.fixture
def live_client():
    """
    Fixture for live model testing with secure API key retrieval.
    Only active when LIVE_MODEL_TESTS=1 environment variable is set.
    Skips tests when API keys are missing.
    """
    # Check if live tests are enabled
    if not os.getenv("LIVE_MODEL_TESTS"):
        pytest.skip("Live model tests disabled. Set LIVE_MODEL_TESTS=1 to enable.")

    # Check for required API keys
    required_keys = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "XAI_API_KEY": os.getenv("XAI_API_KEY"),
        "Z_AI_API_KEY": os.getenv("Z_AI_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    }

    available_keys = {k: v for k, v in required_keys.items() if v and v != "dummy-key-for-tests"}

    if not available_keys:
        pytest.skip("No real API keys found. Set at least one provider API key to run live tests.")

    return {"keys": available_keys, "providers": list(available_keys.keys())}
