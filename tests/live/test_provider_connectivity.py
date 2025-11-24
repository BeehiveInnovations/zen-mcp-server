"""
Live provider connectivity tests.

These tests verify real API connectivity to providers.
Only run with LIVE_MODEL_TESTS=1 environment variable.
"""

import pytest


@pytest.mark.live_model
def test_live_client_fixture_available(live_client):
    """Test that live_client fixture provides expected structure."""
    assert isinstance(live_client, dict)
    assert "keys" in live_client
    assert "providers" in live_client
    assert len(live_client["providers"]) > 0
    assert len(live_client["keys"]) > 0


@pytest.mark.live_model
def test_dummy_api_keys_are_filtered(live_client):
    """Test that dummy API keys are filtered out."""
    for _provider, key in live_client["keys"].items():
        assert key != "dummy-key-for-tests"
        assert len(key) > 10  # Basic validation that it's not a placeholder


@pytest.mark.live_model
def test_at_least_one_real_provider_available(live_client):
    """Test that at least one real provider API key is available."""
    assert len(live_client["providers"]) >= 1, "At least one provider API key should be available for live tests"
