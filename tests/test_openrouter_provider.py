"""Tests for OpenRouter provider."""

import os
import pytest
from unittest.mock import patch, MagicMock

from providers.base import ProviderType
from providers.openrouter import OpenRouterProvider
from providers.registry import ModelProviderRegistry


class TestOpenRouterProvider:
    """Test cases for OpenRouter provider."""
    
    def test_provider_initialization(self):
        """Test OpenRouter provider initialization."""
        provider = OpenRouterProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://openrouter.ai/api/v1"
        assert provider.FRIENDLY_NAME == "OpenRouter"
    
    def test_custom_headers(self):
        """Test OpenRouter custom headers."""
        # Test default headers
        assert "HTTP-Referer" in OpenRouterProvider.DEFAULT_HEADERS
        assert "X-Title" in OpenRouterProvider.DEFAULT_HEADERS
        
        # Test with environment variables
        with patch.dict(os.environ, {
            "OPENROUTER_REFERER": "https://myapp.com",
            "OPENROUTER_TITLE": "My App"
        }):
            from importlib import reload
            import providers.openrouter
            reload(providers.openrouter)
            
            provider = providers.openrouter.OpenRouterProvider(api_key="test-key")
            assert provider.DEFAULT_HEADERS["HTTP-Referer"] == "https://myapp.com"
            assert provider.DEFAULT_HEADERS["X-Title"] == "My App"
    
    def test_model_validation_without_allowlist(self):
        """Test model validation without allow-list."""
        provider = OpenRouterProvider(api_key="test-key")
        
        # Should accept any model when no allow-list
        assert provider.validate_model_name("gpt-4") is True
        assert provider.validate_model_name("claude-3-opus") is True
        assert provider.validate_model_name("any-model-name") is True
    
    def test_model_validation_with_allowlist(self):
        """Test model validation with allow-list."""
        with patch.dict(os.environ, {
            "OPENROUTER_ALLOWED_MODELS": "gpt-4,claude-3-opus,mistral-large"
        }):
            provider = OpenRouterProvider(api_key="test-key")
            
            # Test allowed models (case-insensitive)
            assert provider.validate_model_name("gpt-4") is True
            assert provider.validate_model_name("GPT-4") is True
            assert provider.validate_model_name("claude-3-opus") is True
            assert provider.validate_model_name("MISTRAL-LARGE") is True
            
            # Test disallowed models
            assert provider.validate_model_name("gpt-3.5-turbo") is False
            assert provider.validate_model_name("unauthorized-model") is False
    
    def test_get_capabilities(self):
        """Test capability generation returns generic capabilities."""
        provider = OpenRouterProvider(api_key="test-key")
        
        # Should return generic capabilities for any model
        caps = provider.get_capabilities("gpt-4")
        assert caps.provider == ProviderType.OPENROUTER
        assert caps.model_name == "gpt-4"
        assert caps.friendly_name == "OpenRouter"
        assert caps.max_tokens == 32_768  # Safe default
        assert hasattr(caps, '_is_generic') and caps._is_generic is True
    
    def test_openrouter_registration(self):
        """Test OpenRouter can be registered and retrieved."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            # Clean up any existing registration
            ModelProviderRegistry.unregister_provider(ProviderType.OPENROUTER)
            
            # Register the provider
            ModelProviderRegistry.register_provider(ProviderType.OPENROUTER, OpenRouterProvider)
            
            # Retrieve and verify
            provider = ModelProviderRegistry.get_provider(ProviderType.OPENROUTER)
            assert provider is not None
            assert isinstance(provider, OpenRouterProvider)


class TestOpenRouterSSRFProtection:
    """Test SSRF protection for OpenRouter."""
    
    def test_url_validation_rejects_private_ips(self):
        """Test that private IPs are rejected."""
        provider = OpenRouterProvider(api_key="test-key")
        
        # List of private/dangerous IPs to test
        dangerous_urls = [
            "http://192.168.1.1/api/v1",
            "http://10.0.0.1/api/v1",
            "http://172.16.0.1/api/v1",
            "http://169.254.169.254/api/v1",  # AWS metadata
            "http://[::1]/api/v1",  # IPv6 localhost
            "http://0.0.0.0/api/v1",
        ]
        
        for url in dangerous_urls:
            with pytest.raises(ValueError, match="restricted IP|Invalid"):
                provider.base_url = url
                provider._validate_base_url()
    
    def test_url_validation_allows_public_domains(self):
        """Test that legitimate public domains are allowed."""
        provider = OpenRouterProvider(api_key="test-key")
        
        # OpenRouter's actual domain should always be allowed
        provider.base_url = "https://openrouter.ai/api/v1"
        provider._validate_base_url()  # Should not raise
    
    def test_invalid_url_schemes_rejected(self):
        """Test that non-HTTP(S) schemes are rejected."""
        provider = OpenRouterProvider(api_key="test-key")
        
        invalid_urls = [
            "ftp://example.com/api",
            "file:///etc/passwd",
            "gopher://example.com",
            "javascript:alert(1)",
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError, match="Invalid URL scheme"):
                provider.base_url = url
                provider._validate_base_url()